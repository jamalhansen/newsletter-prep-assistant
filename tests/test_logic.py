from pathlib import Path
from unittest.mock import patch

import pytest

from newsletter_prep.logic import VaultResolutionError, _resolve_existing_vault_or_raise


class TestResolveExistingVaultOrRaise:
    def test_returns_explicit_existing_path(self, tmp_path):
        resolved = _resolve_existing_vault_or_raise(str(tmp_path))
        assert resolved == Path(tmp_path)

    def test_raises_when_find_vault_root_fails(self):
        with patch(
            "newsletter_prep.logic.find_vault_root",
            side_effect=RuntimeError("not found"),
        ):
            with pytest.raises(
                VaultResolutionError, match="could not locate Obsidian vault"
            ):
                _resolve_existing_vault_or_raise(None)

    def test_raises_when_resolved_path_missing(self, tmp_path):
        missing = tmp_path / "missing-vault"
        with patch("newsletter_prep.logic.find_vault_root", return_value=missing):
            with pytest.raises(VaultResolutionError, match="vault path does not exist"):
                _resolve_existing_vault_or_raise(None)
