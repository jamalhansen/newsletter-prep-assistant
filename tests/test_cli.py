from datetime import date
from typer.testing import CliRunner
from newsletter_prep.cli import app
from tests.test_sources import _make_discovery_db, _make_vault, _make_issue_folder

runner = CliRunner()


def test_cli_prep_with_topics_and_tags(tmp_path):
    vault = _make_vault(tmp_path)
    today = date.today().isoformat()
    _make_issue_folder(
        vault / "_newsletter",
        1,
        today,
        content="---\nstatus: draft\nblog_post: [[my-post]]\n---\nDraft content",
    )

    db_path = _make_discovery_db(tmp_path, [
        {
            "url": "https://example.com/topic-match",
            "title": "Topic Matched Article",
            "tags": '["ai", "local-first"]',
            "summary": "Summary about local AI",
        },
        {
            "url": "https://example.com/other",
            "title": "Other Article",
            "tags": '["misc"]',
            "summary": "Other summary",
        },
    ])

    result = runner.invoke(
        app,
        [
            "--vault", str(vault),
            "--discovery-db", db_path,
            "--topic", "local",
            "--tag", "ai",
            "--dry-run",
        ],
    )
    assert result.exit_code == 0
    assert "Topic Matched Article" in result.output
    assert "#ai" in result.output
