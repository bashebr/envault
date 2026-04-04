import json
import typer
import sys
import os
import shutil
from pathlib import Path
from rich import print
from rich.console import Console

from envault import crypto, gist

app = typer.Typer(help="Securely sync encrypted .env files to GitHub Gists.")
console = Console()

def validate_env_file(path: Path):
    """Basic validation to ensure file looks like an env file."""
    if path.stat().st_size > 1024 * 1024: # 1MB limit
        console.print("[red]Error: .env file is too large (>1MB).[/red]")
        raise typer.Exit(code=1)
    # Check for binary content roughly
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        console.print("[red]Error: .env file is not valid UTF-8 text.[/red]")
        raise typer.Exit(code=1)

@app.command()
def init():
    """Initialize envault configuration."""
    console.print("[bold]Welcome to Envault Initialization[/bold]")
    
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

    console.print("[bold green]Initialization complete! Run `envault push` to sync.[/bold green]")


@app.command()
def push():
    """Encrypt local .env and push to a private Gist."""
    env_path = Path(".env")
    if not env_path.exists():
        console.print("[red]Error: .env file not found in current directory.[/red]")
        raise typer.Exit(code=1)

    validate_env_file(env_path)

    passphrase = typer.prompt("Enter passphrase", hide_input=True)
    confirm_passphrase = typer.prompt("Confirm passphrase", hide_input=True)

    if passphrase != confirm_passphrase:
        console.print("[red]Error: Passphrases do not match.[/red]")
        raise typer.Exit(code=1)

    try:
        data = env_path.read_bytes()
        encrypted_payload = crypto.encrypt(data, passphrase)
        payload_json = json.dumps(encrypted_payload)
        
        gist_id = gist.create_gist(payload_json)
        console.print(f"[green]Success! Encrypted .env pushed to Gist ID:[/green] [bold]{gist_id}[/bold]")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)


@app.command()
def pull(gist_id: str = typer.Option(..., "--gist-id", help="The ID of the Gist to pull from.")):
    """Fetch and decrypt .env from a Gist."""
    passphrase = typer.prompt("Enter passphrase", hide_input=True)
    
    try:
        content = gist.get_gist_content(gist_id)
        payload = json.loads(content)
        
        decrypted_data = crypto.decrypt(payload, passphrase)
        
        # Atomic Write
        env_path = Path(".env")
        tmp_path = env_path.with_suffix(".tmp")
        
        tmp_path.write_bytes(decrypted_data)
        
        # On POSIX, rename is atomic. Windows is ... complicated, but replace usually works for files.
        # generic solution:
        tmp_path.replace(env_path)
        
        console.print("[green]Success! .env file restored.[/green]")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        # In a real app we might differentiate auth errors vs corrupt data
        console.print("[yellow]Hint: Check your passphrase and Gist ID.[/yellow]")
        raise typer.Exit(code=1)


@app.command()
def rotate(gist_id: str = typer.Option(..., "--gist-id", help="The ID of the Gist to rotate.")):
    """Decrypt remote Gist with old passphrase and re-encrypt with a new one."""
    current_passphrase = typer.prompt("Enter CURRENT passphrase", hide_input=True)
    
    try:
        # 1. Fetch
        content = gist.get_gist_content(gist_id)
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
        gist.update_gist(gist_id, new_payload_json)
        console.print(f"[green]Success! Gist {gist_id} rotated to new passphrase.[/green]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)

@app.command()
def diff(gist_id: str = typer.Option(..., "--gist-id", help="The ID of the Gist to compare with.")):
    """Compare local .env with remote encrypted Gist."""
    passphrase = typer.prompt("Enter passphrase for REMOTE", hide_input=True)
    
    try:
        # Remote
        content = gist.get_gist_content(gist_id)
        payload = json.loads(content)
        remote_data = crypto.decrypt(payload, passphrase)
        remote_lines = set(remote_data.decode('utf-8').splitlines())
        
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
                console.print(f"[red]- {line.split('=')[0]}=***[/red] (In Remote only or different value)")
            for line in only_in_local:
                console.print(f"[green]+ {line.split('=')[0]}=***[/green] (In Local only or different value)")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)

def main():
    app()

if __name__ == "__main__":
    main()
