"""Oto CLI - composable toolkit for AI agents."""

import importlib
import importlib.metadata
import sys
from pathlib import Path

import typer

app = typer.Typer(
    name="oto",
    help="CLI toolkit for AI agents. JSON on stdout, composable with pipes.",
    no_args_is_help=True,
)

# Auto-discover commands from oto/commands/*.py (connecteurs core, publics)
_commands_dir = Path(__file__).parent / "commands"
for _cmd_file in sorted(_commands_dir.glob("*.py")):
    if _cmd_file.name.startswith("_"):
        continue
    _module_name = _cmd_file.stem
    try:
        _module = importlib.import_module(f"oto.commands.{_module_name}")
    except ImportError:
        continue
    if hasattr(_module, "app"):
        app.add_typer(_module.app, name=_module_name)


# Connecteurs custom/client : packages séparés (souvent privés) qui déclarent
# leur Typer `app` via le groupe d'entry-points `oto.commands`. Permet à un
# connecteur spécifique-client de vivre HORS de ce core public sans patcher la
# CLI (cf. otomata-tech/oto-cli#9 ; symétrique au groupe `o_browser.sites`).
# Un plugin cassé est ignoré — il ne doit pas casser la CLI.
for _ep in importlib.metadata.entry_points(group="oto.commands"):
    try:
        _plugin_app = _ep.load()
    except Exception:
        continue
    app.add_typer(_plugin_app, name=_ep.name)


# Modules pulled by optional extras → which extra to install if missing.
_EXTRA_FOR_MODULE = {
    "googleapiclient": "google",
    "google.oauth2": "google",
    "google_auth_oauthlib": "google",
    "gkeepapi": "google",
    "markdown": "google",
    "o_browser": "browser",
    "anthropic": "anthropic",
    "pyarrow": "stock",
    "pandas": "stock",
}


def _extra_for(missing: str) -> str:
    for mod, extra in _EXTRA_FOR_MODULE.items():
        if missing == mod or missing.startswith(mod + "."):
            return extra
    return "all"


def main():
    try:
        app()
    except ValueError as e:
        if "not found. Set it via:" in str(e):
            print(f"Error: {e}", file=sys.stderr)
            raise SystemExit(1)
        raise
    except ModuleNotFoundError as e:
        extra = _extra_for(e.name or "")
        print(
            f"Error: missing dependency '{e.name}'. This command needs the "
            f"'{extra}' extra:\n"
            f"  pipx install 'oto-cli[{extra}]'   # or [all] for everything\n"
            f"  pipx inject oto-cli {e.name}      # if oto is already installed",
            file=sys.stderr,
        )
        raise SystemExit(1)


if __name__ == "__main__":
    main()
