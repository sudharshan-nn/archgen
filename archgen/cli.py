"""CLI for ArchGen - Repository Architecture Diagram Generator."""

import sys
from pathlib import Path

import click

from . import __version__
from .analyzer import analyze_repository, get_directory_structure
from .diagrams import write_diagrams
from .repository import get_repo_path, is_github_url


@click.command()
@click.argument("source", type=str, required=True)
@click.option(
    "-o", "--output",
    type=click.Path(path_type=Path),
    default=Path("output"),
    help="Output directory for diagrams (default: output)",
)
@click.option(
    "--name",
    type=str,
    default=None,
    help="Repository name for diagram titles (default: auto-detected)",
)
@click.version_option(version=__version__)
def main(source: str, output: Path, name: str | None) -> None:
    """
    Generate architecture and flow diagrams from a repository.
    
    SOURCE can be:
    - Local path: /path/to/repo
    - GitHub URL: https://github.com/owner/repo
    """
    try:
        if is_github_url(source):
            # Clones to ./temp_repos/<repo_name> (works in sandboxed environments)
            repo_path = get_repo_path(source)
            repo_name = name or repo_path.name
        else:
            repo_path = Path(source).expanduser().resolve()
            if not repo_path.exists():
                click.echo(f"Error: Path does not exist: {repo_path}", err=True)
                sys.exit(1)
            repo_name = name or repo_path.name
            repo_path = get_repo_path(source)
        
        click.echo(f"Analyzing repository: {repo_path}")
        
        modules = analyze_repository(repo_path)
        structure = get_directory_structure(repo_path)
        
        click.echo(f"Found {len(modules)} modules")
        
        written = write_diagrams(output, modules, structure, repo_name)
        
        click.echo(f"\nGenerated {len(written)} diagrams in {output}:")
        for p in written:
            click.echo(f"  - {p}")
        
        click.echo("\nView diagrams at https://mermaid.live or in VS Code with Mermaid extension")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    finally:
        pass  # temp_repos/ is kept for potential reuse


if __name__ == "__main__":
    main()
