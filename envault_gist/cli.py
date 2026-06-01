import json
import os
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from envault_gist import config, crypto, gist

app = typer.Typer(
    help="Securely sync encrypted .env files to GitHub Gists.",
    no_args_is_help=True,
)
console = Console()

PASSPHRASE_ENV = "ENVAULT_PASSPHRASE"


def validate_env_file(path: Path):
    """Basic validation to ensure file looks like an env file."""
    size = path.stat().st_size
    if size == 0:
        console.print("[red]Error: .env file is empty.[/red]")
        raise typer.Exit(code=1)
    if size > 1024 * 1024:  # 1MB limit
        console.print("[red]Error: .env file is too large (>1MB).[/red]")
        raise typer.Exit(code=1)
    # Check for binary content roughly
    try:
        path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        console.print("[red]Error: .env file is not valid UTF-8 text.[/red]")
        raise typer.Exit(code=1)


def _get_passphrase(prompt_text: str, confirm: bool = False) -> str:
    """Read a passphrase from ENVAULT_PASSPHRASE if set, else prompt.

    Setting the env var enables non-interactive use (CI, scripts) and skips
    confirmation since there is no risk of a typo.
    """
    env_passphrase = os.environ.get(PASSPHRASE_ENV)
    if env_passphrase:
        return env_passphrase

    passphrase = typer.prompt(prompt_text, hide_input=True)
    if confirm:
        confirm_passphrase = typer.prompt("Confirm passphrase", hide_input=True)
        if passphrase != confirm_passphrase:
            console.print("[red]Error: Passphrases do not match.[/red]")
            raise typer.Exit(code=1)
    return passphrase


def _resolve_gist_id(gist_id: Optional[str]) -> str:
    """Resolve a Gist ID from the flag, then the saved config."""
    resolved = gist_id or config.get_gist_id()
    if not resolved:
        console.print("[red]Error: No Gist ID provided and none saved in .envault.json.[/red]")
        console.print(
            "[yellow]Hint: run `envault-gist push` first, or pass --gist-id <id>.[/yellow]"
        )
        raise typer.Exit(code=1)
    return resolved


@app.command()
def init():
    """Initialize envault-gist configuration."""
    console.print("[bold]Welcome to envault-gist Initialization[/bold]")

    # Check/Setup GITHUB_TOKEN
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        console.print("[green]✓ GITHUB_TOKEN found in environment.[/green]")
    else:
        if Path(".envault_token").exists():
            console.print("[green]✓ .envault_token found locally.[/green]")
        else:
            console.print("[yellow]GITHUB_TOKEN not found.[/yellow]")
            token_input = typer.prompt("Enter your GitHub PAT (with gist scope)", hide_input=True)
            if token_input:
                Path(".envault_token").write_text(token_input.strip())
                console.print("[green]Saved to .envault_token (add this to .gitignore!)[/green]")

    # Check .env
    if not Path(".env").exists():
        console.print("[yellow]No .env file found. Creating an empty one.[/yellow]")
        Path(".env").touch()
    else:
        console.print("[green]✓ .env file found.[/green]")

    saved_id = config.get_gist_id()
    if saved_id:
        console.print(f"[green]✓ Saved Gist ID:[/green] [bold]{saved_id}[/bold]")

    console.print(
        "[bold green]Initialization complete! Run `envault-gist push` to sync.[/bold green]"
    )


@app.command()
def push(
    gist_id: Optional[str] = typer.Option(
        None,
        "--gist-id",
        help="Update this Gist instead of creating a new one (defaults to saved ID).",
    ),
    new: bool = typer.Option(
        False,
        "--new",
        help="Force creating a new Gist even if one is already saved.",
    ),
):
    """Encrypt local .env and push to a private Gist (creates or updates)."""
    env_path = Path(".env")
    if not env_path.exists():
        console.print("[red]Error: .env file not found in current directory.[/red]")
        raise typer.Exit(code=1)

    validate_env_file(env_path)

    target_id = None if new else (gist_id or config.get_gist_id())

    passphrase = _get_passphrase("Enter passphrase", confirm=True)

    try:
        data = env_path.read_bytes()
        encrypted_payload = crypto.encrypt(data, passphrase)
        payload_json = json.dumps(encrypted_payload)

        if target_id:
            gist.update_gist(target_id, payload_json)
            config.set_gist_id(target_id)
            console.print(f"[green]Success! Updated Gist:[/green] [bold]{target_id}[/bold]")
            console.print(f"[dim]{gist.gist_url(target_id)}[/dim]")
        else:
            new_id = gist.create_gist(payload_json)
            config.set_gist_id(new_id)
            console.print(f"[green]Success! Created Gist:[/green] [bold]{new_id}[/bold]")
            console.print(f"[dim]{gist.gist_url(new_id)}[/dim]")
            console.print(f"[dim]Saved Gist ID to {config.CONFIG_FILENAME}[/dim]")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)


@app.command()
def pull(
    gist_id: Optional[str] = typer.Option(
        None, "--gist-id", help="The ID of the Gist to pull from (defaults to saved ID)."
    ),
):
    """Fetch and decrypt .env from a Gist."""
    resolved_id = _resolve_gist_id(gist_id)
    passphrase = _get_passphrase("Enter passphrase")

    try:
        content = gist.get_gist_content(resolved_id)
        payload = json.loads(content)

        decrypted_data = crypto.decrypt(payload, passphrase)

        # Atomic Write
        env_path = Path(".env")
        tmp_path = env_path.with_suffix(".tmp")

        tmp_path.write_bytes(decrypted_data)
        tmp_path.replace(env_path)

        config.set_gist_id(resolved_id)
        console.print("[green]Success! .env file restored.[/green]")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        # In a real app we might differentiate auth errors vs corrupt data
        console.print("[yellow]Hint: Check your passphrase and Gist ID.[/yellow]")
        raise typer.Exit(code=1)


@app.command()
def rotate(
    gist_id: Optional[str] = typer.Option(
        None, "--gist-id", help="The ID of the Gist to rotate (defaults to saved ID)."
    ),
):
    """Decrypt remote Gist with old passphrase and re-encrypt with a new one."""
    resolved_id = _resolve_gist_id(gist_id)
    current_passphrase = _get_passphrase("Enter CURRENT passphrase")

    try:
        # 1. Fetch
        content = gist.get_gist_content(resolved_id)
        payload = json.loads(content)

        # 2. Decrypt
        decrypted_data = crypto.decrypt(payload, current_passphrase)
        console.print("[blue]Successfully decrypted current payload.[/blue]")

        # 3. New Passphrase
        new_passphrase = typer.prompt("Enter NEW passphrase", hide_input=True)
        confirm_passphrase = typer.prompt("Confirm NEW passphrase", hide_input=True)

        if new_passphrase != confirm_passphrase:
            console.print("[red]Error: New passphrases do not match.[/red]")
            raise typer.Exit(code=1)

        # 4. Encrypt
        new_encrypted_payload = crypto.encrypt(decrypted_data, new_passphrase)
        new_payload_json = json.dumps(new_encrypted_payload)

        # 5. Update
        gist.update_gist(resolved_id, new_payload_json)
        console.print(f"[green]Success! Gist {resolved_id} rotated to new passphrase.[/green]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)


@app.command()
def diff(
    gist_id: Optional[str] = typer.Option(
        None, "--gist-id", help="The ID of the Gist to compare with (defaults to saved ID)."
    ),
):
    """Compare local .env with remote encrypted Gist."""
    resolved_id = _resolve_gist_id(gist_id)
    passphrase = _get_passphrase("Enter passphrase for REMOTE")

    try:
        # Remote
        content = gist.get_gist_content(resolved_id)
        payload = json.loads(content)
        remote_data = crypto.decrypt(payload, passphrase)
        remote_lines = set(remote_data.decode("utf-8").splitlines())

        # Local
        local_path = Path(".env")
        if not local_path.exists():
            console.print("[red]Local .env does not exist.[/red]")
            return

        local_lines = set(local_path.read_text().splitlines())

        # Simple set diff (key=value level)
        # Ideally we parse env keys, but line-based is a good start
        only_in_remote = remote_lines - local_lines
        only_in_local = local_lines - remote_lines

        if not only_in_remote and not only_in_local:
            console.print("[green]No differences found.[/green]")
        else:
            console.print("[bold]Differences Found:[/bold]")
            for line in only_in_remote:
                key = line.split("=")[0]
                console.print(f"[red]- {key}=***[/red] (In Remote only)")
            for line in only_in_local:
                key = line.split("=")[0]
                console.print(f"[green]+ {key}=***[/green] (In Local only)")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)


def main():
    app()


if __name__ == "__main__":
    main()
