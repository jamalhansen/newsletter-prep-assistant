"""Render the newsletter prep kit as markdown.

Output format mirrors the newsletter structure from Newsletter Strategy.md:
  1. Issue metadata header
  2. Blog post section
  3. Kept finds section
  4. Daily note highlights
  5. CTA suggestion
"""

from datetime import date

from .cta import CTA
from .sources import BlogPost, Find, IssueMeta


def render_prep_kit(
    issue: IssueMeta,
    blog_posts: list[BlogPost],
    finds: list[Find],
    daily_bullets: list[str],
    cta: CTA,
    week_start: date,
    week_end: date,
) -> str:
    sections: list[str] = []

    # ── Header ──────────────────────────────────────────────────────────────
    sections.append(
        f"# Newsletter Prep Kit — Issue {issue.issue_number}\n"
        f"Week of {week_start.isoformat()} → {week_end.isoformat()}\n"
        f"Generated: {date.today().isoformat()}"
    )

    # ── Blog post ────────────────────────────────────────────────────────────
    if blog_posts:
        lines = ["## This week on the blog"]
        for bp in blog_posts:
            if bp.url:
                lines.append(f"**[{bp.title}]({bp.url})**")
            else:
                lines.append(f"**{bp.title}** _(URL not found — add to frontmatter)_")
            if bp.excerpt:
                lines.append(f"> {bp.excerpt}")
        sections.append("\n".join(lines))
    else:
        sections.append(
            "## This week on the blog\n\n"
            "_No blog post linked in issue frontmatter (`blog_post:` field)._"
        )

    # ── Kept finds ───────────────────────────────────────────────────────────
    if finds:
        lines = [f"## Links worth your time ({len(finds)} candidates)"]
        for f in finds:
            line = f"- [{f.title}]({f.url})"
            if f.summary:
                line += f" — {f.summary}"
            lines.append(line)
        sections.append("\n".join(lines))
    else:
        sections.append(
            "## Links worth your time\n\n"
            "_No recent kept items found in content-discovery DB._"
        )

    # ── Daily note bullets ───────────────────────────────────────────────────
    if daily_bullets:
        lines = [f"## From your daily notes ({len(daily_bullets)} bullets)"]
        lines.extend(daily_bullets)
        sections.append("\n".join(lines))
    else:
        sections.append(
            "## From your daily notes\n\n"
            "_No daily notes found for this week._"
        )

    # ── CTA ──────────────────────────────────────────────────────────────────
    sections.append(
        f"## CTA suggestion (#{cta.index} of {cta.total})\n\n"
        f"{cta.text}"
    )

    # ── Footer ───────────────────────────────────────────────────────────────
    sections.append(
        "---\n"
        "_Prep kit assembled by newsletter-prep-assistant. "
        "Write the opening, story, and What I'm Learning sections yourself._"
    )

    return "\n\n".join(sections) + "\n"
