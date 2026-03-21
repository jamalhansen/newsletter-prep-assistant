"""Data sources for the newsletter prep assistant.

Reads from:
- Obsidian vault: issue draft, blog post file, daily notes
- content-discovery SQLite DB: recent kept finds
"""

import os
import re
import sqlite3
import tomllib
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

import frontmatter


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class IssueMeta:
    """Parsed frontmatter from an issue draft file."""

    issue_number: int
    draft_path: Path
    issue_folder: Path
    blog_post_wikilinks: list[str] = field(default_factory=list)
    finds_included: list[str] = field(default_factory=list)
    status: str = "draft"


@dataclass
class BlogPost:
    """Metadata extracted from a blog post vault file."""

    title: str
    url: str
    slug: str
    excerpt: str = ""


@dataclass
class Find:
    """A kept content-discovery item."""

    title: str
    url: str
    summary: str
    source: str
    reviewed_at: str = ""


# ---------------------------------------------------------------------------
# Issue discovery
# ---------------------------------------------------------------------------

_ISSUE_FOLDER_RE = re.compile(r"Issue\s+(\d+)\s*-\s*(\d{4}-\d{2}-\d{2})")
_DRAFT_FILE_RE = re.compile(r"Issue\s+0*(\d+)\.md$", re.IGNORECASE)


def find_issue_folders(vault_root: Path, newsletter_dir: str = "_newsletter") -> list[tuple[int, Path]]:
    """Return (issue_number, folder_path) pairs sorted by issue number."""
    base = vault_root / newsletter_dir
    if not base.exists():
        raise FileNotFoundError(f"Newsletter directory not found: {base}")

    results = []
    for entry in base.iterdir():
        if entry.is_dir():
            m = _ISSUE_FOLDER_RE.match(entry.name)
            if m:
                results.append((int(m.group(1)), entry))
    return sorted(results)


def find_draft_file(issue_folder: Path) -> Path | None:
    """Find the draft .md file in an issue folder."""
    for f in issue_folder.glob("*.md"):
        if _DRAFT_FILE_RE.search(f.name):
            return f
    # Fallback: any .md file
    mds = list(issue_folder.glob("*.md"))
    return mds[0] if mds else None


def find_next_issue(vault_root: Path, newsletter_dir: str = "_newsletter") -> IssueMeta | None:
    """Return the metadata for the next unpublished issue (status=draft or no published_date)."""
    issues = find_issue_folders(vault_root, newsletter_dir)
    for num, folder in issues:
        draft = find_draft_file(folder)
        if draft is None:
            continue
        try:
            post = frontmatter.load(str(draft))
        except Exception:
            continue
        published = post.metadata.get("published_date") or post.metadata.get("status", "") == "published"
        if not published:
            return _parse_issue_meta(num, draft, folder, post)
    # All published — return the last one
    if issues:
        num, folder = issues[-1]
        draft = find_draft_file(folder)
        if draft:
            post = frontmatter.load(str(draft))
            return _parse_issue_meta(num, draft, folder, post)
    return None


def find_issue_by_number(vault_root: Path, issue_number: int, newsletter_dir: str = "_newsletter") -> IssueMeta | None:
    """Return metadata for a specific issue number."""
    issues = find_issue_folders(vault_root, newsletter_dir)
    for num, folder in issues:
        if num == issue_number:
            draft = find_draft_file(folder)
            if draft is None:
                return None
            post = frontmatter.load(str(draft))
            return _parse_issue_meta(num, draft, folder, post)
    return None


def _parse_issue_meta(num: int, draft: Path, folder: Path, post: frontmatter.Post) -> IssueMeta:
    """Extract IssueMeta from a loaded frontmatter Post."""
    raw_bp = post.metadata.get("blog_post", [])
    if isinstance(raw_bp, str):
        raw_bp = [raw_bp]
    blog_links = [_strip_wikilink(s) for s in (raw_bp or []) if s]

    raw_finds = post.metadata.get("finds_included", [])
    if isinstance(raw_finds, str):
        raw_finds = [raw_finds]
    finds = [_strip_wikilink(s) for s in (raw_finds or []) if s]

    return IssueMeta(
        issue_number=post.metadata.get("issue_number") or num,
        draft_path=draft,
        issue_folder=folder,
        blog_post_wikilinks=blog_links,
        finds_included=finds,
        status=post.metadata.get("status", "draft") or "draft",
    )


def _strip_wikilink(s: str) -> str:
    """Convert [[slug]] → slug."""
    return re.sub(r"^\[\[(.+)\]\]$", r"\1", s.strip())


# ---------------------------------------------------------------------------
# Blog post lookup
# ---------------------------------------------------------------------------


def find_blog_post_file(vault_root: Path, slug: str) -> Path | None:
    """Resolve a slug or wikilink to a vault file path."""
    slug = _strip_wikilink(slug)
    # Direct glob search: name matches slug.md anywhere in vault
    matches = list(vault_root.glob(f"**/{slug}.md"))
    if matches:
        return matches[0]
    # Case-insensitive fallback
    slug_lower = slug.lower()
    for p in vault_root.rglob("*.md"):
        if p.stem.lower() == slug_lower:
            return p
    return None


def read_blog_post(file_path: Path) -> BlogPost:
    """Extract BlogPost metadata from a vault file."""
    post = frontmatter.load(str(file_path))
    title = (
        post.metadata.get("title")
        or post.metadata.get("Title")
        or _extract_h1(post.content)
        or file_path.stem
    )
    url = (
        post.metadata.get("canonical_url")
        or post.metadata.get("url")
        or post.metadata.get("permalink")
        or ""
    )
    excerpt = _extract_excerpt(post.content)
    return BlogPost(title=str(title), url=str(url), slug=file_path.stem, excerpt=excerpt)


def _extract_h1(content: str) -> str:
    """Pull the first H1 from markdown content."""
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return ""


def _extract_excerpt(content: str, max_chars: int = 200) -> str:
    """First non-heading, non-empty paragraph, truncated."""
    for para in content.split("\n\n"):
        stripped = para.strip()
        if stripped and not stripped.startswith("#") and not stripped.startswith("---"):
            text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", stripped)  # strip links
            text = re.sub(r"[*_`]", "", text)
            if len(text) > max_chars:
                text = text[:max_chars].rsplit(" ", 1)[0] + "…"
            return text
    return ""


# ---------------------------------------------------------------------------
# Content-discovery DB path resolution
# ---------------------------------------------------------------------------

# Candidate locations for .content-discovery.toml, in search order.
_TOML_SEARCH_PATHS = [
    Path("~/.content-discovery.toml"),
    Path("~/.config/content-discovery/.content-discovery.toml"),
]


def resolve_discovery_db_path(override: str | None = None) -> str:
    """Return the content-discovery DB path using the same priority chain as the agent itself.

    Priority:
    1. Explicit override (passed by caller / CLI flag)
    2. CONTENT_DISCOVERY_STORE env var  (matches content-discovery-agent)
    3. CONTENT_DISCOVERY_DB env var     (legacy alias used by older tools)
    4. [settings] store in ~/.content-discovery.toml
    5. Default: ~/.content-discovery.db
    """
    if override:
        return os.path.expanduser(override)

    env = os.environ.get("CONTENT_DISCOVERY_STORE") or os.environ.get("CONTENT_DISCOVERY_DB")
    if env:
        return os.path.expanduser(env)

    for candidate in _TOML_SEARCH_PATHS:
        toml_path = candidate.expanduser()
        if toml_path.exists():
            try:
                with open(toml_path, "rb") as f:
                    cfg = tomllib.load(f)
                store = cfg.get("settings", {}).get("store")
                if store:
                    return os.path.expanduser(store)
            except Exception:
                pass

    return os.path.expanduser("~/.content-discovery.db")


# ---------------------------------------------------------------------------
# Content-discovery kept finds
# ---------------------------------------------------------------------------


def get_kept_finds(db_path: str, limit: int = 5, since_days: int = 14) -> list[Find]:
    """Return recently kept items from the content-discovery DB, newest first."""
    if not Path(db_path).exists():
        return []

    cutoff = (date.today() - timedelta(days=since_days)).isoformat()
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT title, url, summary, source, reviewed_at
            FROM items
            WHERE status = 'kept'
              AND (reviewed_at >= ? OR fetched_at >= ?)
            ORDER BY reviewed_at DESC
            LIMIT ?
            """,
            (cutoff, cutoff, limit),
        ).fetchall()
        conn.close()
    except sqlite3.Error:
        return []

    return [
        Find(
            title=row["title"],
            url=row["url"],
            summary=row["summary"] or "",
            source=row["source"] or "",
            reviewed_at=row["reviewed_at"] or "",
        )
        for row in rows
    ]


# ---------------------------------------------------------------------------
# Daily note bullets
# ---------------------------------------------------------------------------


def get_daily_note_bullets(vault_root: Path, dates: list[date], subdir: str = "Timeline") -> list[str]:
    """Extract bullet-point lines from daily notes for the given dates."""
    bullets: list[str] = []
    notes_dir = vault_root / subdir

    for d in dates:
        note_path = notes_dir / f"{d.isoformat()}.md"
        if not note_path.exists():
            continue
        try:
            text = note_path.read_text(encoding="utf-8")
        except OSError:
            continue
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith(("- ", "* ", "+ ")) and len(stripped) > 4:
                # Skip bare checkbox stubs "- [ ] " with no content
                if re.match(r"^[-*+]\s+\[[ x]\]\s*$", stripped):
                    continue
                bullets.append(f"({d.isoformat()}) {stripped}")

    return bullets
