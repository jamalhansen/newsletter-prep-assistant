# newsletter-prep-assistant

Assembles the raw materials for your weekly newsletter in one pass — no file-hopping required.

**Not a newsletter writer.** Every word of the newsletter is yours. This tool saves ~10 minutes of hunting through vault folders by pulling everything together into a single prep kit markdown file.

## What it assembles

| Section | Source |
|---------|--------|
| This week's blog post | Issue draft frontmatter → vault file (`canonical_url`, title, excerpt) |
| Links worth your time | `kept` items from content-discovery DB (last 14 days) |
| Daily note highlights | Bullet points from this week's Timeline notes |
| CTA suggestion | Rotating list from Newsletter Strategy, keyed by issue number |

## Installation

```bash
git clone git@github.com:jamalhansen/newsletter-prep-assistant.git
cd newsletter-prep-assistant
uv sync
```

## Usage

```bash
# Auto-detect next unpublished issue, print to stdout
uv run newsletter-prep prep

# Specific issue number
uv run newsletter-prep prep --issue 5

# Write prep kit into the issue folder
uv run newsletter-prep prep --output path/to/prep-kit.md

# Preview without writing anything
uv run newsletter-prep prep --dry-run

# Verbose: show what each source found
uv run newsletter-prep prep --verbose
```

## Configuration

All settings are via environment variables (no config file needed).

| Variable | Default | Description |
|----------|---------|-------------|
| `OBSIDIAN_VAULT_PATH` | auto-detect | Path to your Obsidian vault root |
| `NEWSLETTER_DIR` | `_newsletter` | Newsletter subfolder inside the vault |
| `CONTENT_DISCOVERY_DB` | `~/.content-discovery.db` | Path to content-discovery SQLite DB |
| `NEWSLETTER_FINDS_LIMIT` | `5` | Max kept finds to include |
| `NEWSLETTER_FINDS_SINCE_DAYS` | `14` | Look-back window for kept finds |
| `DAILY_NOTES_SUBDIR` | `Timeline` | Vault subdirectory containing daily notes |

Set them in your shell profile or `.envrc`:

```bash
export OBSIDIAN_VAULT_PATH="$HOME/vaults/BrainSync"
export CONTENT_DISCOVERY_DB="$HOME/.content-discovery.db"
```

## CLI Reference

### `prep`

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--issue` | `-i` | auto | Issue number. Defaults to next unpublished issue. |
| `--vault` | `-V` | `$OBSIDIAN_VAULT_PATH` | Obsidian vault root path |
| `--newsletter-dir` | — | `$NEWSLETTER_DIR` / `_newsletter` | Newsletter subfolder |
| `--discovery-db` | `-d` | `$CONTENT_DISCOVERY_DB` | Path to content-discovery SQLite DB |
| `--finds-limit` | — | `$NEWSLETTER_FINDS_LIMIT` / `5` | Max kept finds to include |
| `--since-days` | — | `$NEWSLETTER_FINDS_SINCE_DAYS` / `14` | Look-back window for finds |
| `--notes-subdir` | — | `$DAILY_NOTES_SUBDIR` / `Timeline` | Daily notes subdirectory |
| `--output` | `-o` | stdout | Write prep kit to file |
| `--dry-run` | `-n` | false | Print to stdout, no file writes |
| `--verbose` | `-v` | false | Show what each source found |

## Issue folder conventions

Issue folders must match: `Issue NNN - YYYY-MM-DD/`

Draft files inside must match: `* Issue NNN.md` (e.g. `Select * from Jamal - Issue 005.md`)

The draft frontmatter drives what's included:

```yaml
---
issue_number: 5
blog_post:
  - "[[subqueries-when-sql-needs-helper-functions]]"
finds_included: []
---
```

A blog post wikilink resolves to any `.md` file in the vault with that name. The tool reads `canonical_url` (or `url`/`permalink`) from its frontmatter for the link.

## CTA rotation

Five CTAs cycle by issue number (issue 1 → CTA 1, issue 6 → CTA 1 again):

1. Reply and tell me: [question]
2. Know a Python dev who'd benefit? Forward this along.
3. Follow me on LinkedIn for tips between issues.
4. Got a question about [topic]? Reply to this email.
5. If you're enjoying the newsletter, share it with a colleague.

## Project structure

```
newsletter-prep-assistant/
├── src/
│   ├── main.py
│   └── newsletter_prep/
│       ├── cta.py        # CTA rotation
│       ├── sources.py    # Vault, DB, and daily note readers
│       ├── renderer.py   # Prep kit markdown formatter
│       └── logic.py      # Typer CLI
├── tests/
│   ├── test_cta.py
│   ├── test_sources.py
│   └── test_renderer.py
├── pyproject.toml
└── README.md
```
