"""Typer CLI for newsletter-prep-assistant."""

from datetime import date, timedelta
from pathlib import Path
from typing import Optional

import typer

from local_first_common.obsidian import find_vault_root
from local_first_common.tracking import register_tool
from local_first_common.cli import init_config_option

from .cta import get_cta
from .renderer import render_prep_kit
from .sources import (
    find_issue_by_number,
    find_next_issue,
    find_blog_post_file,
    get_daily_note_bullets,
    get_kept_finds,
    read_blog_post,
    resolve_discovery_db_path,
)

TOOL_NAME = "newsletter-prep-assistant"
DEFAULTS = {"provider": "ollama", "model": "llama3"}
_TOOL = register_tool("newsletter-prep-assistant")

app = typer.Typer(help="Assemble raw materials for the weekly newsletter.")


def _week_dates(anchor: date) -> tuple[date, date]:
    """Return (monday, sunday) for the ISO week containing anchor."""
    monday = anchor - timedelta(days=anchor.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday


@app.command()
def prep(
    issue: Optional[int] = typer.Option(
        None, "--issue", "-i", help="Issue number. Default: auto-detect next unpublished issue."
    ),
    vault: Optional[str] = typer.Option(
        None,
        "--vault",
        "-V",
        help="Obsidian vault root path.",
        envvar="OBSIDIAN_VAULT_PATH",
    ),
    newsletter_dir: str = typer.Option(
        "_newsletter",
        "--newsletter-dir",
        help="Newsletter subfolder inside the vault.",
        envvar="NEWSLETTER_DIR",
    ),
    discovery_db: Optional[str] = typer.Option(
        None,
        "--discovery-db",
        "-d",
        help="Path to content-discovery SQLite DB. "
        "Defaults to CONTENT_DISCOVERY_STORE env var, then ~/.content-discovery.toml "
        "[settings] store, then ~/.content-discovery.db.",
        envvar="CONTENT_DISCOVERY_STORE",
    ),
    finds_limit: int = typer.Option(
        5,
        "--finds-limit",
        help="Max number of kept finds to include.",
        envvar="NEWSLETTER_FINDS_LIMIT",
    ),
    since_days: int = typer.Option(
        14,
        "--since-days",
        help="Look back N days for kept finds.",
        envvar="NEWSLETTER_FINDS_SINCE_DAYS",
    ),
    daily_notes_subdir: str = typer.Option(
        "Timeline",
        "--notes-subdir",
        help="Vault subdirectory containing daily notes.",
        envvar="DAILY_NOTES_SUBDIR",
    ),
    output: Optional[str] = typer.Option(
        None,
        "--output",
        "-o",
        help="Write prep kit to this file. Default: print to stdout.",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", "-n", help="Print prep kit to stdout, do not write files."
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show what each source found."
    ),
    init_config: bool = init_config_option(TOOL_NAME, DEFAULTS),
) -> None:
    """Assemble the newsletter prep kit for the next (or specified) issue.

    Pulls together: blog post metadata, recent kept finds from the content-discovery
    DB, daily note bullet points, and the next CTA in the rotation. Outputs an
    organized markdown file so you can start writing immediately.
    """

    # ── Resolve vault ────────────────────────────────────────────────────────
    if vault:
        vault_root = Path(vault).expanduser()
    else:
        try:
            vault_root = find_vault_root()
        except Exception as e:
            typer.secho(f"Error: could not locate Obsidian vault. Set OBSIDIAN_VAULT_PATH. ({e})",
                        fg=typer.colors.RED, err=True)
            raise typer.Exit(1)

    if not vault_root.exists():
        typer.secho(f"Error: vault path does not exist: {vault_root}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)

    # ── Find issue ───────────────────────────────────────────────────────────
    if issue is not None:
        issue_meta = find_issue_by_number(vault_root, issue, newsletter_dir)
        if issue_meta is None:
            typer.secho(f"Error: issue {issue} not found in {vault_root / newsletter_dir}",
                        fg=typer.colors.RED, err=True)
            raise typer.Exit(1)
    else:
        issue_meta = find_next_issue(vault_root, newsletter_dir)
        if issue_meta is None:
            typer.secho(f"Error: no issues found in {vault_root / newsletter_dir}",
                        fg=typer.colors.RED, err=True)
            raise typer.Exit(1)

    if verbose:
        typer.echo(f"Issue:  #{issue_meta.issue_number} — {issue_meta.draft_path.name}")
        typer.echo(f"Folder: {issue_meta.issue_folder}")

    # ── Blog posts ───────────────────────────────────────────────────────────
    blog_posts = []
    for slug in issue_meta.blog_post_wikilinks:
        bp_file = find_blog_post_file(vault_root, slug)
        if bp_file:
            bp = read_blog_post(bp_file)
            blog_posts.append(bp)
            if verbose:
                typer.echo(f"Blog post: {bp.title} ({bp.url or 'no URL'})")
        else:
            typer.secho(f"Warning: blog post file not found for [[{slug}]]",
                        fg=typer.colors.YELLOW, err=True)

    # ── Week dates ───────────────────────────────────────────────────────────
    week_start, week_end = _week_dates(date.today())

    # ── Kept finds ───────────────────────────────────────────────────────────
    db_path = resolve_discovery_db_path(discovery_db)
    finds = get_kept_finds(db_path, limit=finds_limit, since_days=since_days)
    if verbose:
        typer.echo(f"Kept finds: {len(finds)} (from {db_path})")

    # ── Daily note bullets ───────────────────────────────────────────────────
    dates = [week_start + timedelta(days=i) for i in range(7)]
    bullets = get_daily_note_bullets(vault_root, dates, subdir=daily_notes_subdir)
    if verbose:
        typer.echo(f"Daily note bullets: {len(bullets)}")

    # ── CTA ──────────────────────────────────────────────────────────────────
    cta = get_cta(issue_meta.issue_number)
    if verbose:
        typer.echo(f"CTA #{cta.index}: {cta.text[:60]}…")

    # ── Render ───────────────────────────────────────────────────────────────
    kit = render_prep_kit(
        issue=issue_meta,
        blog_posts=blog_posts,
        finds=finds,
        daily_bullets=bullets,
        cta=cta,
        week_start=week_start,
        week_end=week_end,
    )

    # ── Output ───────────────────────────────────────────────────────────────
    if dry_run or output is None and not _should_write_to_vault():
        typer.echo(kit)
        typer.echo(f"\nDone. Issue: {issue_meta.issue_number}, "
                   f"Blog posts: {len(blog_posts)}, Finds: {len(finds)}, "
                   f"Bullets: {len(bullets)}")
        return

    out_path = Path(output) if output else _default_output_path(issue_meta)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(kit, encoding="utf-8")
    typer.echo(f"Prep kit written to {out_path}")
    typer.echo(f"Done. Issue: {issue_meta.issue_number}, "
               f"Blog posts: {len(blog_posts)}, Finds: {len(finds)}, "
               f"Bullets: {len(bullets)}")


def _should_write_to_vault() -> bool:
    """Default behaviour: print to stdout unless --output is given."""
    return False


def _default_output_path(issue: "IssueMeta") -> Path:  # noqa: F821
    """Default output: prep-kit.md inside the issue folder."""
    return issue.issue_folder / "prep-kit.md"
