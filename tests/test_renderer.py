"""Tests for newsletter_prep.renderer."""

from datetime import date
from pathlib import Path

from newsletter_prep.cta import get_cta
from newsletter_prep.renderer import render_prep_kit
from newsletter_prep.sources import BlogPost, Find, IssueMeta


def _make_issue(tmp_path: Path, number: int = 3) -> IssueMeta:
    folder = tmp_path / f"Issue {number:03d}"
    folder.mkdir()
    draft = folder / f"Issue {number:03d}.md"
    draft.write_text("", encoding="utf-8")
    return IssueMeta(
        issue_number=number,
        draft_path=draft,
        issue_folder=folder,
    )


class TestRenderPrepKit:
    def test_includes_issue_number(self, tmp_path):
        issue = _make_issue(tmp_path, 4)
        kit = render_prep_kit(
            issue=issue,
            blog_posts=[],
            finds=[],
            daily_bullets=[],
            cta=get_cta(4),
            week_start=date(2026, 3, 16),
            week_end=date(2026, 3, 22),
        )
        assert "Issue 4" in kit

    def test_includes_blog_post_title_and_url(self, tmp_path):
        issue = _make_issue(tmp_path)
        bp = BlogPost(title="SQL Joins", url="https://example.com/joins", slug="joins", excerpt="A great post.")
        kit = render_prep_kit(
            issue=issue,
            blog_posts=[bp],
            finds=[],
            daily_bullets=[],
            cta=get_cta(3),
            week_start=date(2026, 3, 16),
            week_end=date(2026, 3, 22),
        )
        assert "SQL Joins" in kit
        assert "https://example.com/joins" in kit
        assert "A great post." in kit

    def test_includes_finds(self, tmp_path):
        issue = _make_issue(tmp_path)
        find = Find(title="Cool Article", url="https://cool.com", summary="Very cool.", source="feed")
        kit = render_prep_kit(
            issue=issue,
            blog_posts=[],
            finds=[find],
            daily_bullets=[],
            cta=get_cta(3),
            week_start=date(2026, 3, 16),
            week_end=date(2026, 3, 22),
        )
        assert "Cool Article" in kit
        assert "https://cool.com" in kit
        assert "Very cool." in kit

    def test_includes_daily_bullets(self, tmp_path):
        issue = _make_issue(tmp_path)
        kit = render_prep_kit(
            issue=issue,
            blog_posts=[],
            finds=[],
            daily_bullets=["(2026-03-18) - Learned about DuckDB", "(2026-03-19) - Wrote a test"],
            cta=get_cta(3),
            week_start=date(2026, 3, 16),
            week_end=date(2026, 3, 22),
        )
        assert "DuckDB" in kit
        assert "Wrote a test" in kit

    def test_includes_cta(self, tmp_path):
        issue = _make_issue(tmp_path)
        cta = get_cta(2)
        kit = render_prep_kit(
            issue=issue,
            blog_posts=[],
            finds=[],
            daily_bullets=[],
            cta=cta,
            week_start=date(2026, 3, 16),
            week_end=date(2026, 3, 22),
        )
        assert cta.text in kit

    def test_placeholder_when_no_blog_post(self, tmp_path):
        issue = _make_issue(tmp_path)
        kit = render_prep_kit(
            issue=issue,
            blog_posts=[],
            finds=[],
            daily_bullets=[],
            cta=get_cta(1),
            week_start=date(2026, 3, 16),
            week_end=date(2026, 3, 22),
        )
        assert "No blog post linked" in kit

    def test_placeholder_when_no_finds(self, tmp_path):
        issue = _make_issue(tmp_path)
        kit = render_prep_kit(
            issue=issue,
            blog_posts=[],
            finds=[],
            daily_bullets=[],
            cta=get_cta(1),
            week_start=date(2026, 3, 16),
            week_end=date(2026, 3, 22),
        )
        assert "No recent kept items" in kit

    def test_blog_post_without_url_shows_note(self, tmp_path):
        issue = _make_issue(tmp_path)
        bp = BlogPost(title="Unpublished Post", url="", slug="unpublished", excerpt="")
        kit = render_prep_kit(
            issue=issue,
            blog_posts=[bp],
            finds=[],
            daily_bullets=[],
            cta=get_cta(1),
            week_start=date(2026, 3, 16),
            week_end=date(2026, 3, 22),
        )
        assert "URL not found" in kit

    def test_multiple_finds_shows_count(self, tmp_path):
        issue = _make_issue(tmp_path)
        finds = [
            Find(title=f"Article {i}", url=f"https://a{i}.com", summary="", source="feed")
            for i in range(3)
        ]
        kit = render_prep_kit(
            issue=issue,
            blog_posts=[],
            finds=finds,
            daily_bullets=[],
            cta=get_cta(1),
            week_start=date(2026, 3, 16),
            week_end=date(2026, 3, 22),
        )
        assert "3 candidates" in kit
