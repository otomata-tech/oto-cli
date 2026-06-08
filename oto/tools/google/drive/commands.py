"""`oto google drive` command surface."""

import json

import typer
from typing import Optional

app = typer.Typer(help="Google Drive tools (list, download, upload, mkdir, move, rename, delete)")

@app.command("list")
def drive_list(
    folder_id: Optional[str] = typer.Option(None, help="Filter by parent folder ID"),
    query: Optional[str] = typer.Option(None, help="Custom query filter"),
    limit: int = typer.Option(100, help="Max results"),
    account: Optional[str] = typer.Option(None, "--account", "-a", help="Google account name"),
):
    """List files in Google Drive."""
    from oto.tools.google.drive.lib.drive_client import DriveClient

    client = DriveClient(account=account)
    files = client.list_files(folder_id=folder_id, query=query, page_size=limit)
    print(json.dumps({"count": len(files), "files": files}, indent=2))

@app.command("download")
def drive_download(
    file_id: str = typer.Argument(..., help="Google Drive file ID"),
    output: str = typer.Argument(..., help="Output path"),
    account: Optional[str] = typer.Option(None, "--account", "-a", help="Google account name"),
):
    """Download a file from Google Drive."""
    from oto.tools.google.drive.lib.drive_client import DriveClient

    client = DriveClient(account=account)
    result = client.download_file(file_id, output)
    print(f"Downloaded: {result['filename']} -> {result['output_path']}")

@app.command("upload")
def drive_upload(
    file_path: str = typer.Argument(..., help="Local file path to upload"),
    folder_id: Optional[str] = typer.Option(None, help="Target folder ID in Drive"),
    name: Optional[str] = typer.Option(None, help="Custom filename (defaults to local name)"),
    account: Optional[str] = typer.Option(None, "--account", "-a", help="Google account name"),
):
    """Upload a file to Google Drive."""
    from oto.tools.google.drive.lib.drive_client import DriveClient

    client = DriveClient(account=account)
    result = client.upload_file(local_path=file_path, folder_id=folder_id, file_name=name)
    print(json.dumps(result, indent=2))

@app.command("mkdir")
def drive_mkdir(
    name: str = typer.Argument(..., help="Folder name"),
    parent: Optional[str] = typer.Option(None, "--parent", "-p", help="Parent folder ID"),
    account: Optional[str] = typer.Option(None, "--account", "-a", help="Google account name"),
):
    """Create a folder in Google Drive."""
    from oto.tools.google.drive.lib.drive_client import DriveClient

    client = DriveClient(account=account)
    result = client.create_folder(name, parent_folder_id=parent)
    print(json.dumps(result, indent=2))

@app.command("move")
def drive_move(
    file_id: str = typer.Argument(..., help="Google Drive file ID to move"),
    folder_id: str = typer.Argument(..., help="Destination folder ID"),
    account: Optional[str] = typer.Option(None, "--account", "-a", help="Google account name"),
):
    """Move a file to a different folder in Google Drive."""
    from oto.tools.google.drive.lib.drive_client import DriveClient

    client = DriveClient(account=account)
    result = client.move_file(file_id, folder_id)
    print(json.dumps(result, indent=2))

@app.command("rename")
def drive_rename(
    file_id: str = typer.Argument(..., help="Google Drive file ID to rename"),
    name: str = typer.Argument(..., help="New name for the file"),
    account: Optional[str] = typer.Option(None, "--account", "-a", help="Google account name"),
):
    """Rename a file in Google Drive."""
    from oto.tools.google.drive.lib.drive_client import DriveClient

    client = DriveClient(account=account)
    result = client.rename_file(file_id, name)
    print(json.dumps(result, indent=2, ensure_ascii=False))

@app.command("delete")
def drive_delete(
    file_id: str = typer.Argument(..., help="Google Drive file ID to delete"),
    account: Optional[str] = typer.Option(None, "--account", "-a", help="Google account name"),
):
    """Permanently delete a file from Google Drive."""
    from oto.tools.google.drive.lib.drive_client import DriveClient

    client = DriveClient(account=account)
    result = client.delete_file(file_id)
    print(json.dumps(result, indent=2))

@app.command("share")
def drive_share(
    file_id: str = typer.Argument(..., help="Google Drive file or folder ID"),
    email: str = typer.Argument(..., help="Recipient email address"),
    role: str = typer.Option("reader", help="Permission role: reader, writer, commenter"),
    no_notify: bool = typer.Option(False, "--no-notify", help="Don't send email notification"),
    account: Optional[str] = typer.Option(None, "--account", "-a", help="Google account name"),
):
    """Share a file or folder with a user by email."""
    from oto.tools.google.drive.lib.drive_client import DriveClient

    client = DriveClient(account=account)
    result = client.share(file_id, email, role=role, notify=not no_notify)
    print(json.dumps(result, indent=2))

@app.command("unshare")
def drive_unshare(
    file_id: str = typer.Argument(..., help="Google Drive file or folder ID"),
    email: str = typer.Argument(..., help="Email address to remove"),
    account: Optional[str] = typer.Option(None, "--account", "-a", help="Google account name"),
):
    """Remove a user's access to a file or folder."""
    from oto.tools.google.drive.lib.drive_client import DriveClient

    client = DriveClient(account=account)
    result = client.unshare(file_id, email)
    print(json.dumps(result, indent=2))

@app.command("permissions")
def drive_permissions(
    file_id: str = typer.Argument(..., help="Google Drive file or folder ID"),
    account: Optional[str] = typer.Option(None, "--account", "-a", help="Google account name"),
):
    """List permissions on a file or folder."""
    from oto.tools.google.drive.lib.drive_client import DriveClient

    client = DriveClient(account=account)
    perms = client.list_permissions(file_id)
    print(json.dumps(perms, indent=2))
