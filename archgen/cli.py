"""CLI for ArchGen - Repository Architecture Diagram Generator."""

import sys
from pathlib import Path

import click

from . import __version__
from .analyzer import (
    analyze_repository,
    detect_circular_dependencies,
    extract_api_routes,
    extract_call_graph,
    get_directory_structure,
)
from .config import ArchGenConfig
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
@click.option(
    "--include-tests",
    is_flag=True,
    default=None,
    help="Include test modules in diagrams",
)
@click.option(
    "--no-include-tests",
    is_flag=True,
    default=None,
    help="Exclude test modules (default)",
)
@click.option(
    "--max-depth",
    type=int,
    default=None,
    help="Max depth for directory structure (default: 4)",
)
@click.option(
    "--filter",
    "filter_paths",
    multiple=True,
    help="Only analyze these paths (e.g. --filter src/ --filter lib/)",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["mermaid", "plantuml"]),
    default=None,
    help="Output format: mermaid or plantuml",
)
@click.option(
    "--no-html",
    is_flag=True,
    help="Skip HTML report generation",
)
@click.option(
    "--export-png",
    is_flag=True,
    help="Export diagrams as PNG (requires mermaid-cli)",
)
@click.option(
    "--export-svg",
    is_flag=True,
    help="Export diagrams as SVG (requires mermaid-cli)",
)
@click.option(
    "--no-circular-check",
    is_flag=True,
    help="Skip circular dependency detection",
)
@click.version_option(version=__version__)
def main(
    source: str,
    output: Path,
    name: str | None,
    include_tests: bool | None,
    no_include_tests: bool | None,
    max_depth: int | None,
    filter_paths: tuple[str, ...],
    output_format: str | None,
    no_html: bool,
    export_png: bool,
    export_svg: bool,
    no_circular_check: bool,
) -> None:
    """
    Generate architecture and flow diagrams from a repository.

    SOURCE can be:
    - Local path: /path/to/repo
    - GitHub URL: https://github.com/owner/repo
    """
    try:
        if is_github_url(source):
            repo_path = get_repo_path(source)
            repo_name = name or repo_path.name
        else:
            repo_path = Path(source).expanduser().resolve()
            if not repo_path.exists():
                click.echo(f"Error: Path does not exist: {repo_path}", err=True)
                sys.exit(1)
            repo_name = name or repo_path.name
            repo_path = get_repo_path(source)

        config = ArchGenConfig.load(repo_path)
        if include_tests is not None:
            config.include_tests = include_tests
        if no_include_tests is not None:
            config.include_tests = False
        if max_depth is not None:
            config.max_depth = max_depth
        if filter_paths:
            config.filter_paths = list(filter_paths)
        if output_format is not None:
            config.output_format = output_format
        if no_html:
            config.export_html = False
        if export_png:
            config.export_png = True
        if export_svg:
            config.export_svg = True
        if no_circular_check:
            config.detect_circular = False

        click.echo(f"Analyzing repository: {repo_path}")

        modules = analyze_repository(
            repo_path,
            include_tests=config.include_tests,
            filter_paths=config.filter_paths or None,
        )
        structure = get_directory_structure(repo_path, max_depth=config.max_depth)

        click.echo(f"Found {len(modules)} modules")

        cycles = []
        if config.detect_circular:
            cycles = detect_circular_dependencies(modules)
            if cycles:
                click.echo(f"⚠️  Found {len(cycles)} circular dependency cycle(s)")

        call_edges = []
        if repo_path.exists():
            call_edges = extract_call_graph(modules, repo_path)

        written = write_diagrams(
            output,
            modules,
            structure,
            repo_name,
            repo_path,
            config=config,
            cycles=cycles,
            call_edges=call_edges,
        )

        click.echo(f"\nGenerated {len(written)} files in {output}:")
        for p in written[:15]:
            click.echo(f"  - {p}")
        if len(written) > 15:
            click.echo(f"  ... and {len(written) - 15} more")

        if config.export_html:
            click.echo("\nOpen report.html in a browser to view all diagrams")
        click.echo("\nView .mmd files at https://mermaid.live or in VS Code with Mermaid extension")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    finally:
        pass


if __name__ == "__main__":
    main()
