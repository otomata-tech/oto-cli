"""`oto config` / `oto config provider secrets` — régression sur les imports
cassés par le split oto-core (2026-06-11 : `_find_project_secrets` et
`_get_user_secrets` ont déménagé dans `oto.secrets.file`, `oto.scaleway_secrets`
est devenu `oto.secrets.scaleway`) et sur le setter qui rejetait 'sops', le
défaut même de `oto.config.get_provider()` (oto-core#63).

Toutes les commandes tournent sur un HOME isolé (tmp_path) : ni config.yaml,
ni secrets.env, ni store SOPS — le cas qui faisait planter `oto config` pour
n'importe quel provider, pas seulement 'sops'.
"""
from pathlib import Path

import pytest
from typer.testing import CliRunner

import oto.config as config
from oto.commands.config import app as config_app, provider_app

runner = CliRunner()


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    config._oto_config_cache = None
    yield
    config._oto_config_cache = None


def test_show_does_not_crash_on_a_fresh_install():
    """`oto config` (sans sous-commande) levait ImportError avant ce correctif
    — sur CE chemin, pour n'importe quel provider."""
    result = runner.invoke(config_app, [])
    assert result.exit_code == 0, result.output
    assert "Secret provider: sops" in result.output


def test_show_file_provider_branch():
    result = runner.invoke(provider_app, ["secrets", "file"])
    assert result.exit_code == 0, result.output

    result = runner.invoke(config_app, [])
    assert result.exit_code == 0, result.output
    assert "Secrets files:" in result.output


def test_provider_secrets_accepts_sops():
    """`sops` est le défaut de `get_provider()` — son propre setter le
    rejetait (`Must be 'file' or 'scaleway'`)."""
    result = runner.invoke(provider_app, ["secrets", "sops"])
    assert result.exit_code == 0, result.output
    assert config._get_oto_config()["secret_provider"] == "sops"


def test_provider_secrets_accepts_file():
    result = runner.invoke(provider_app, ["secrets", "file"])
    assert result.exit_code == 0, result.output
    assert config._get_oto_config()["secret_provider"] == "file"


def test_provider_secrets_rejects_unknown():
    result = runner.invoke(provider_app, ["secrets", "bogus"])
    assert result.exit_code != 0


def test_secrets_push_import_paths_resolve():
    """`from oto.scaleway_secrets import push_secrets` n'existe plus — ça
    plantait (ModuleNotFoundError) dès l'exécution de la commande."""
    result = runner.invoke(config_app, ["secrets-push"])
    assert not isinstance(result.exception, ImportError)
    assert "No secrets file at" in result.output


def test_secrets_pull_import_paths_resolve():
    result = runner.invoke(config_app, ["secrets-pull"])
    assert not isinstance(result.exception, ImportError)
