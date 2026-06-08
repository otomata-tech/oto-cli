"""`oto google slides` command surface."""

import json

import typer
from typing import Optional

app = typer.Typer(help="Google Slides tools (layouts, convert-pptx, build, export-pdf)")

@app.command("layouts")
def slides_layouts(
    presentation_id: str = typer.Argument(..., help="Google Slides presentation ID"),
    account: Optional[str] = typer.Option(None, "--account", "-a", help="Google account name"),
):
    """List layouts (name + placeholders) of a presentation's master."""
    from oto.tools.google.slides.lib.slides_client import SlidesClient

    client = SlidesClient(account=account)
    layouts = client.get_layouts_map(presentation_id)
    out = {
        name: {
            "objectId": info["objectId"],
            "displayName": info["displayName"],
            "placeholders": [f"{t}#{i}" for (t, i) in info["placeholders"]],
        }
        for name, info in layouts.items()
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))

@app.command("convert-pptx")
def slides_convert_pptx(
    pptx_id: str = typer.Argument(..., help="Drive file ID of the .pptx"),
    name: str = typer.Argument(..., help="Name of the resulting Google Slides file"),
    folder_id: Optional[str] = typer.Option(None, "--folder-id", help="Target Drive folder ID"),
    account: Optional[str] = typer.Option(None, "--account", "-a", help="Google account name"),
):
    """Convert a .pptx (already on Drive) into a native Google Slides file."""
    from oto.tools.google.slides.lib.slides_client import SlidesClient

    client = SlidesClient(account=account)
    pres_id = client.convert_pptx_to_native(pptx_id, name, folder_id=folder_id)
    print(json.dumps({
        "presentationId": pres_id,
        "url": f"https://docs.google.com/presentation/d/{pres_id}/edit",
    }, indent=2))

@app.command("export-pdf")
def slides_export_pdf(
    presentation_id: str = typer.Argument(..., help="Google Slides presentation ID"),
    output: str = typer.Argument(..., help="Local output path for the PDF"),
    account: Optional[str] = typer.Option(None, "--account", "-a", help="Google account name"),
):
    """Export a presentation to PDF locally."""
    from oto.tools.google.slides.lib.slides_client import SlidesClient

    client = SlidesClient(account=account)
    path = client.export_pdf(presentation_id, output)
    print(json.dumps({"output": path}, indent=2))

@app.command("build")
def slides_build(
    presentation_id: str = typer.Argument(..., help="Target presentation ID (will be wiped)"),
    spec_path: str = typer.Argument(..., help="Path to YAML/JSON spec describing slides"),
    keep_existing: bool = typer.Option(False, "--keep-existing", help="Don't wipe existing slides first"),
    no_body_bold_override: bool = typer.Option(False, "--no-body-bold-override",
        help="Don't force bold:False on BODY placeholders (disable Otomata-style master override)"),
    account: Optional[str] = typer.Option(None, "--account", "-a", help="Google account name"),
):
    """Build slides from a spec file (YAML or JSON).

    Spec format:
        slides:
          - id: slide01                    # ≥ 5 chars
            layout: <layout_name_or_id>    # name from `oto google slides layouts`, or objectId
            fills:
              "CENTERED_TITLE#0": "Title"
              "SUBTITLE#0": "Subtitle"
              "BODY#0": "**Bold** then plain"
    """
    from pathlib import Path
    from oto.tools.google.slides.lib.slides_client import SlidesClient

    spec_text = Path(spec_path).read_text(encoding='utf-8')
    if spec_path.endswith(('.yaml', '.yml')):
        import yaml
        spec = yaml.safe_load(spec_text)
    else:
        spec = json.loads(spec_text)

    client = SlidesClient(account=account)

    # IMPORTANT : nettoyer AVANT de résoudre les layouts. Sur un pptx
    # fraîchement importé, supprimer les slides initiales peut renuméroter
    # les layoutIds — résoudre après garantit qu'on tape les bons IDs.
    keepalive_id = None
    if not keep_existing:
        keepalive_id = client.clear_all_slides(presentation_id)

    # Resolve layout names → objectIds
    layouts = client.get_layouts_map(presentation_id)
    name_to_id = {name: info["objectId"] for name, info in layouts.items()}
    valid_ids = set(name_to_id.values())

    slides_def = []
    for s in spec.get("slides", []):
        layout = s["layout"]
        layout_id = name_to_id.get(layout, layout if layout in valid_ids else None)
        if not layout_id:
            raise typer.BadParameter(
                f"Layout {layout!r} introuvable. Disponibles : {list(name_to_id)}"
            )
        # Parse fills keys "TYPE#index" → (type, index)
        fills = {}
        for k, v in s.get("fills", {}).items():
            if "#" in k:
                t, i = k.rsplit("#", 1)
                fills[(t.strip(), int(i))] = v
            else:
                fills[(k.strip(), 0)] = v
        slides_def.append((s["id"], layout_id, fills))

    created = client.build_from_layouts(
        presentation_id, slides_def,
        override_body_bold=not no_body_bold_override,
    )

    if keepalive_id:
        client.slides_service.presentations().batchUpdate(
            presentationId=presentation_id,
            body={'requests': [{'deleteObject': {'objectId': keepalive_id}}]},
        ).execute()

    print(json.dumps({
        "created": created,
        "url": f"https://docs.google.com/presentation/d/{presentation_id}/edit",
    }, indent=2))
