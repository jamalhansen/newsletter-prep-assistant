from datetime import date, timedelta
from pathlib import Path
from typing import Optional, TYPE_CHECKING

from local_first_common.obsidian import find_vault_root

if TYPE_CHECKING:
    from .sources import IssueMeta


class NewsletterPrepError(Exception):
    """Base error for newsletter prep strict operations."""


class VaultResolutionError(NewsletterPrepError):
    """Raised when the vault root cannot be resolved or does not exist."""


def _week_dates(anchor: date) -> tuple[date, date]:
    """Return (monday, sunday) for the ISO week containing anchor."""
    monday = anchor - timedelta(days=anchor.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday


def _resolve_existing_vault_or_raise(vault: Optional[str]) -> Path:
    """Resolve the vault root and ensure it exists."""
    if vault:
        vault_root = Path(vault).expanduser()
    else:
        try:
            vault_root = find_vault_root()
        except Exception as e:  # noqa: BLE001
            raise VaultResolutionError(
                f"could not locate Obsidian vault. Set OBSIDIAN_VAULT_PATH. ({e})"
            ) from e

    if not vault_root.exists():
        raise VaultResolutionError(f"vault path does not exist: {vault_root}")
    return vault_root


def _should_write_to_vault() -> bool:
    """Default behaviour: print to stdout unless --output is given."""
    return False


def _default_output_path(issue: "IssueMeta") -> Path:
    """Default output: prep-kit.md inside the issue folder."""
    return issue.issue_folder / "prep-kit.md"
