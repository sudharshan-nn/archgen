"""Configuration loading from .archgen.yaml or defaults."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_CONFIG = {
    "include_tests": False,
    "max_depth": 4,
    "filter_paths": [],
    "skip_dirs": [],
    "output_format": "mermaid",  # mermaid | plantuml
    "export_html": True,
    "export_png": False,
    "export_svg": False,
    "max_modules": 30,
    "max_edges": 50,
    "max_api_routes": 20,
    "c4_level": "container",  # context | container | component
    "detect_circular": True,
}


@dataclass
class ArchGenConfig:
    """ArchGen configuration."""
    include_tests: bool = False
    max_depth: int = 4
    filter_paths: list[str] = field(default_factory=list)
    skip_dirs: list[str] = field(default_factory=list)
    output_format: str = "mermaid"
    export_html: bool = True
    export_png: bool = False
    export_svg: bool = False
    max_modules: int = 30
    max_edges: int = 50
    max_api_routes: int = 20
    c4_level: str = "container"
    detect_circular: bool = True

    @classmethod
    def load(cls, repo_path: Path | None = None) -> "ArchGenConfig":
        """Load config from .archgen.yaml or use defaults."""
        config_path: Path | None = None
        if repo_path:
            for name in (".archgen.yaml", ".archgen.yml", ".archgen.json"):
                p = Path(repo_path) / name
                if p.exists():
                    config_path = p
                    break
        if not config_path or not config_path.exists():
            return cls()

        data: dict = {}
        try:
            with open(config_path, encoding="utf-8") as f:
                raw = f.read()
            try:
                import yaml
                data = yaml.safe_load(raw) or {}
            except ImportError:
                import json
                data = json.loads(raw)
        except Exception:
            return cls()

        return cls(
            include_tests=data.get("include_tests", DEFAULT_CONFIG["include_tests"]),
            max_depth=data.get("max_depth", DEFAULT_CONFIG["max_depth"]),
            filter_paths=data.get("filter_paths", DEFAULT_CONFIG["filter_paths"]),
            skip_dirs=data.get("skip_dirs", DEFAULT_CONFIG["skip_dirs"]),
            output_format=data.get("output_format", DEFAULT_CONFIG["output_format"]),
            export_html=data.get("export_html", DEFAULT_CONFIG["export_html"]),
            export_png=data.get("export_png", DEFAULT_CONFIG["export_png"]),
            export_svg=data.get("export_svg", DEFAULT_CONFIG["export_svg"]),
            max_modules=data.get("max_modules", DEFAULT_CONFIG["max_modules"]),
            max_edges=data.get("max_edges", DEFAULT_CONFIG["max_edges"]),
            max_api_routes=data.get("max_api_routes", DEFAULT_CONFIG["max_api_routes"]),
            c4_level=data.get("c4_level", DEFAULT_CONFIG["c4_level"]),
            detect_circular=data.get("detect_circular", DEFAULT_CONFIG["detect_circular"]),
        )
