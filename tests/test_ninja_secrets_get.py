"""`oto ninja secrets get` pour le groupe <provider>_API_KEY (oto-cli#11).

Depuis le durcissement du coffre (oto-backend#671), une clé posée n'est plus
JAMAIS relisible côté serveur. `get` doit échouer NOMMÉMENT et IMMÉDIATEMENT
pour ce groupe — jamais un `None` pris pour « pas configuré », jamais un appel
réseau pour le découvrir, et jamais un octet sur stdout (l'usage documenté
`export FOO=$(oto ninja secrets get FOO)` jetterait le code de sortie et
poserait FOO vide en silence).
"""
from typer.testing import CliRunner

from oto.commands import ninja as ninja_cmd

runner = CliRunner()


def _explode(*_a, **_kw):
    raise AssertionError("_client() must not be called for an api_key: get")


def test_get_api_key_fails_immediately_without_network_call(monkeypatch):
    monkeypatch.setattr(ninja_cmd, "_client", _explode)

    result = runner.invoke(ninja_cmd.secrets_app, ["get", "SERPER_API_KEY"])

    assert result.exit_code == 1
    assert result.stdout == ""
    assert "oto-backend#671" in result.output
    assert "n'est plus lisible" in result.output


def test_get_unconfigured_api_key_also_fails_before_any_call(monkeypatch):
    """Configurée ou non, `get` sur ce groupe n'a plus de réponse à donner —
    le message ne doit pas dépendre d'un aller-retour réseau pour le savoir."""
    monkeypatch.setattr(ninja_cmd, "_client", _explode)

    result = runner.invoke(ninja_cmd.secrets_app, ["get", "HUNTER_API_KEY"])

    assert result.exit_code == 1
    assert result.stdout == ""


def test_get_linkedin_cookie_is_unaffected(monkeypatch):
    """Le garde-fou vise UNIQUEMENT le groupe api_key: — linkedin/crunchbase
    restent hors périmètre de ce correctif (cf. issue, section « hors
    périmètre, à ne pas durcir en même temps »)."""

    class _FakeClient:
        def get_linkedin(self):
            return {"cookie": "COOKIE-VALUE"}

    monkeypatch.setattr(ninja_cmd, "_client", lambda: _FakeClient())

    result = runner.invoke(ninja_cmd.secrets_app, ["get", "LINKEDIN_COOKIE"])

    assert result.exit_code == 0, result.output
    assert result.stdout == "COOKIE-VALUE"


def test_unknown_secret_name_still_rejected():
    result = runner.invoke(ninja_cmd.secrets_app, ["get", "NOT_A_REAL_SECRET"])
    assert result.exit_code != 0
