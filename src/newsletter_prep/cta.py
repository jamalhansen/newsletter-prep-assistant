"""CTA rotation for the newsletter.

Cycles through a fixed list keyed by (issue_number - 1) % len(CTAS).
The list matches the order in Newsletter Strategy.md.
"""

from dataclasses import dataclass

CTAS = [
    "Reply and tell me: [question related to this week's topic]",
    "Know a Python dev who'd benefit? Forward this along.",
    "Follow me on [LinkedIn](https://www.linkedin.com/in/jamalhansen/) for tips between issues.",
    "Got a question about [topic]? Reply to this email.",
    "If you're enjoying the newsletter, share it with a colleague.",
]


@dataclass
class CTA:
    index: int
    text: str
    total: int


def get_cta(issue_number: int) -> CTA:
    """Return the CTA for a given issue number (1-based).

    Cycles deterministically: issue 1 → CTA 0, issue 2 → CTA 1, etc.
    """
    idx = (issue_number - 1) % len(CTAS)
    return CTA(index=idx + 1, text=CTAS[idx], total=len(CTAS))
