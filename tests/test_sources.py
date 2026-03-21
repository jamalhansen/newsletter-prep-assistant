"""Tests for newsletter_prep.sources."""

import sqlite3
from datetime import date, timedelta
from pathlib import Path

from newsletter_prep.sources import (
    _strip_wikilink,
    resolve_discovery_db_path,
    find_blog_post_file,
    find_issue_by_number,
    find_next_issue,
    get_daily_note_bullets,
    get_kept_finds,
    read_blog_post,
)

# ---------------------------------------------------------------------------
# Fixtures helpers
# ---------------------------------------------------------------------------


def _make_issue_folder(base: Path, number: int, send_date: str, content: str = "") -> Path:
    folder = base / f"Issue {number:03d} - {send_date}"
    folder.mkdir(parents=True)
    draft = folder / f"Select * from Jamal - Issue {number:03d}.md"
    draft.write_text(content, encoding="utf-8")
    return folder


def _make_vault(tmp_path: Path) -> Path:
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "Timeline").mkdir()
    (vault / "_newsletter").mkdir()
    return vault


# ---------------------------------------------------------------------------
# _strip_wikilink
# ---------------------------------------------------------------------------


class TestStripWikilink:
    def test_strips_brackets(self):
        assert _strip_wikilink("[[my-post]]") == "my-post"

    def test_passthrough_plain(self):
        assert _strip_wikilink("my-post") == "my-post"

    def test_strips_whitespace(self):
        assert _strip_wikilink("  [[slug]]  ") == "slug"


# ---------------------------------------------------------------------------
# find_next_issue
# ---------------------------------------------------------------------------


DRAFT_CONTENT = """\
---
issue_number: 2
status: draft
blog_post:
  - "[[my-sql-post]]"
finds_included: []
---
# Body
"""

PUBLISHED_CONTENT = """\
---
issue_number: 1
published_date: 2026-03-02
blog_post: "[[some-post]]"
---
# Published
"""


class TestFindNextIssue:
    def test_finds_unpublished_issue(self, tmp_path):
        vault = _make_vault(tmp_path)
        _make_issue_folder(vault / "_newsletter", 1, "2026-03-02", PUBLISHED_CONTENT)
        _make_issue_folder(vault / "_newsletter", 2, "2026-03-09", DRAFT_CONTENT)

        meta = find_next_issue(vault)
        assert meta is not None
        assert meta.issue_number == 2

    def test_skips_published_issue(self, tmp_path):
        vault = _make_vault(tmp_path)
        _make_issue_folder(vault / "_newsletter", 1, "2026-03-02", PUBLISHED_CONTENT)

        meta = find_next_issue(vault)
        # Falls back to last issue when all published
        assert meta is not None
        assert meta.issue_number == 1

    def test_returns_none_for_empty_dir(self, tmp_path):
        vault = _make_vault(tmp_path)
        meta = find_next_issue(vault)
        assert meta is None

    def test_parses_blog_post_wikilinks(self, tmp_path):
        vault = _make_vault(tmp_path)
        _make_issue_folder(vault / "_newsletter", 2, "2026-03-09", DRAFT_CONTENT)

        meta = find_next_issue(vault)
        assert meta is not None
        assert "my-sql-post" in meta.blog_post_wikilinks


ISSUE_3_CONTENT = """\
---
issue_number: 3
status: draft
blog_post: "[[another-post]]"
---
# Issue 3
"""


class TestFindIssueByNumber:
    def test_finds_by_number(self, tmp_path):
        vault = _make_vault(tmp_path)
        _make_issue_folder(vault / "_newsletter", 3, "2026-03-16", ISSUE_3_CONTENT)

        meta = find_issue_by_number(vault, 3)
        assert meta is not None
        assert meta.issue_number == 3

    def test_returns_none_for_missing(self, tmp_path):
        vault = _make_vault(tmp_path)
        meta = find_issue_by_number(vault, 99)
        assert meta is None


# ---------------------------------------------------------------------------
# find_blog_post_file + read_blog_post
# ---------------------------------------------------------------------------


class TestFindBlogPostFile:
    def test_finds_by_name(self, tmp_path):
        vault = _make_vault(tmp_path)
        series = vault / "_series"
        series.mkdir()
        post = series / "my-sql-post.md"
        post.write_text("---\ntitle: My SQL Post\n---\nBody.", encoding="utf-8")

        result = find_blog_post_file(vault, "my-sql-post")
        assert result == post

    def test_resolves_wikilink(self, tmp_path):
        vault = _make_vault(tmp_path)
        (vault / "my-post.md").write_text("# Post", encoding="utf-8")

        result = find_blog_post_file(vault, "[[my-post]]")
        assert result is not None
        assert result.name == "my-post.md"

    def test_returns_none_when_not_found(self, tmp_path):
        vault = _make_vault(tmp_path)
        result = find_blog_post_file(vault, "nonexistent-post")
        assert result is None


class TestReadBlogPost:
    def test_reads_frontmatter_title_and_url(self, tmp_path):
        f = tmp_path / "post.md"
        f.write_text(
            "---\ntitle: SQL Joins\ncanonical_url: https://example.com/sql-joins\n---\nBody text here.",
            encoding="utf-8",
        )
        bp = read_blog_post(f)
        assert bp.title == "SQL Joins"
        assert bp.url == "https://example.com/sql-joins"

    def test_falls_back_to_h1(self, tmp_path):
        f = tmp_path / "post.md"
        f.write_text("# My Title\n\nBody paragraph.", encoding="utf-8")
        bp = read_blog_post(f)
        assert bp.title == "My Title"
        assert bp.url == ""

    def test_extracts_excerpt(self, tmp_path):
        f = tmp_path / "post.md"
        f.write_text("# Title\n\nThis is the first paragraph of the post.", encoding="utf-8")
        bp = read_blog_post(f)
        assert "first paragraph" in bp.excerpt


# ---------------------------------------------------------------------------
# get_kept_finds
# ---------------------------------------------------------------------------

def _make_discovery_db(path: Path, items: list[dict]) -> str:
    db = str(path / "discovery.db")
    conn = sqlite3.connect(db)
    conn.execute(
        """CREATE TABLE items (
            id INTEGER PRIMARY KEY,
            url TEXT UNIQUE,
            title TEXT,
            source TEXT,
            description TEXT DEFAULT '',
            score REAL,
            tags TEXT DEFAULT '[]',
            summary TEXT DEFAULT '',
            status TEXT DEFAULT 'new',
            fetched_at TEXT,
            published_at TEXT DEFAULT '',
            reviewed_at TEXT
        )"""
    )
    for item in items:
        conn.execute(
            "INSERT INTO items (url, title, source, score, summary, status, fetched_at, reviewed_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                item["url"],
                item["title"],
                item.get("source", "feed"),
                item.get("score", 0.9),
                item.get("summary", ""),
                item.get("status", "kept"),
                item.get("fetched_at", "2026-03-18"),
                item.get("reviewed_at", "2026-03-18T10:00:00+00:00"),
            ),
        )
    conn.commit()
    conn.close()
    return db


class TestGetKeptFinds:
    def test_returns_kept_items(self, tmp_path):
        db = _make_discovery_db(tmp_path, [
            {"url": "https://a.com", "title": "Post A", "summary": "About A"},
            {"url": "https://b.com", "title": "Post B", "summary": "About B"},
        ])
        finds = get_kept_finds(db, limit=5, since_days=30)
        assert len(finds) == 2
        titles = {f.title for f in finds}
        assert "Post A" in titles

    def test_excludes_dismissed(self, tmp_path):
        db = _make_discovery_db(tmp_path, [
            {"url": "https://a.com", "title": "Kept", "status": "kept"},
            {"url": "https://b.com", "title": "Dismissed", "status": "dismissed"},
        ])
        finds = get_kept_finds(db, limit=5, since_days=30)
        assert len(finds) == 1
        assert finds[0].title == "Kept"

    def test_respects_limit(self, tmp_path):
        db = _make_discovery_db(tmp_path, [
            {"url": f"https://item{i}.com", "title": f"Item {i}"}
            for i in range(10)
        ])
        finds = get_kept_finds(db, limit=3, since_days=30)
        assert len(finds) == 3

    def test_returns_empty_for_missing_db(self, tmp_path):
        finds = get_kept_finds(str(tmp_path / "nonexistent.db"), limit=5)
        assert finds == []


# ---------------------------------------------------------------------------
# get_daily_note_bullets
# ---------------------------------------------------------------------------


class TestResolveDiscoveryDbPath:
    def test_explicit_override_wins(self, tmp_path, monkeypatch):
        monkeypatch.delenv("CONTENT_DISCOVERY_STORE", raising=False)
        monkeypatch.delenv("CONTENT_DISCOVERY_DB", raising=False)
        db = str(tmp_path / "custom.db")
        assert resolve_discovery_db_path(db) == db

    def test_env_var_store_wins_over_default(self, monkeypatch, tmp_path):
        monkeypatch.setenv("CONTENT_DISCOVERY_STORE", str(tmp_path / "from-env.db"))
        monkeypatch.delenv("CONTENT_DISCOVERY_DB", raising=False)
        result = resolve_discovery_db_path(None)
        assert "from-env.db" in result

    def test_legacy_env_var_db_as_fallback(self, monkeypatch, tmp_path):
        monkeypatch.delenv("CONTENT_DISCOVERY_STORE", raising=False)
        monkeypatch.setenv("CONTENT_DISCOVERY_DB", str(tmp_path / "legacy.db"))
        result = resolve_discovery_db_path(None)
        assert "legacy.db" in result

    def test_reads_toml_store_setting(self, monkeypatch, tmp_path):
        monkeypatch.delenv("CONTENT_DISCOVERY_STORE", raising=False)
        monkeypatch.delenv("CONTENT_DISCOVERY_DB", raising=False)
        toml = tmp_path / ".content-discovery.toml"
        toml.write_text('[settings]\nstore = "~/sync/discovery.db"\n', encoding="utf-8")

        import newsletter_prep.sources as src_module
        orig = src_module._TOML_SEARCH_PATHS
        src_module._TOML_SEARCH_PATHS = [toml]
        try:
            result = resolve_discovery_db_path(None)
        finally:
            src_module._TOML_SEARCH_PATHS = orig

        assert "sync/discovery.db" in result

    def test_defaults_to_home_db(self, monkeypatch):
        monkeypatch.delenv("CONTENT_DISCOVERY_STORE", raising=False)
        monkeypatch.delenv("CONTENT_DISCOVERY_DB", raising=False)
        import newsletter_prep.sources as src_module
        orig = src_module._TOML_SEARCH_PATHS
        src_module._TOML_SEARCH_PATHS = []  # no toml files
        try:
            result = resolve_discovery_db_path(None)
        finally:
            src_module._TOML_SEARCH_PATHS = orig
        assert result.endswith(".content-discovery.db")


class TestGetDailyNoteBullets:
    def test_extracts_bullets(self, tmp_path):
        vault = _make_vault(tmp_path)
        today = date.today()
        note = vault / "Timeline" / f"{today.isoformat()}.md"
        note.write_text(
            "# Monday\n\n- Did some work\n- Learned something\n\n## Section\n\n- Another thing",
            encoding="utf-8",
        )
        bullets = get_daily_note_bullets(vault, [today])
        assert len(bullets) == 3
        assert any("Did some work" in b for b in bullets)

    def test_skips_bare_checkboxes(self, tmp_path):
        vault = _make_vault(tmp_path)
        today = date.today()
        note = vault / "Timeline" / f"{today.isoformat()}.md"
        note.write_text("- [ ] \n- [x] \n- Real bullet with content", encoding="utf-8")
        bullets = get_daily_note_bullets(vault, [today])
        assert len(bullets) == 1
        assert "Real bullet" in bullets[0]

    def test_skips_missing_notes(self, tmp_path):
        vault = _make_vault(tmp_path)
        yesterday = date.today() - timedelta(days=1)
        bullets = get_daily_note_bullets(vault, [yesterday])
        assert bullets == []

    def test_includes_date_prefix(self, tmp_path):
        vault = _make_vault(tmp_path)
        today = date.today()
        note = vault / "Timeline" / f"{today.isoformat()}.md"
        note.write_text("- A bullet point", encoding="utf-8")
        bullets = get_daily_note_bullets(vault, [today])
        assert bullets[0].startswith(f"({today.isoformat()})")
