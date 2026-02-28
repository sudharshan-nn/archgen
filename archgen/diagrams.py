"""Diagram generators - Mermaid architecture and flow charts."""

from pathlib import Path
from typing import TYPE_CHECKING

from .analyzer import ModuleInfo

if TYPE_CHECKING:
    pass


def _sanitize_id(name: str) -> str:
    """Create safe Mermaid node ID (alphanumeric, underscores)."""
    return "".join(c if c.isalnum() or c in "._" else "_" for c in name)


def generate_architecture_diagram(modules: list[ModuleInfo], repo_name: str = "Repository") -> str:
    """
    Generate Mermaid architecture diagram showing modules and dependencies.
    """
    lines = [
        "flowchart TB",
        f"    subgraph {_sanitize_id(repo_name)}[\"{repo_name}\"]",
    ]
    
    # Group modules by top-level package
    packages: dict[str, list[ModuleInfo]] = {}
    for m in modules:
        top = m.name.split(".")[0] if "." in m.name else "root"
        if top not in packages:
            packages[top] = []
        packages[top].append(m)
    
    # Limit modules shown to avoid huge diagrams
    max_modules = 30
    shown = 0
    node_ids: set[str] = set()
    
    for pkg_name, pkg_modules in packages.items():
        if shown >= max_modules:
            break
        pkg_id = _sanitize_id(pkg_name)
        lines.append(f"        subgraph {pkg_id}[\"{pkg_name}\"]")
        for m in pkg_modules[:5]:  # Max 5 per package
            if shown >= max_modules:
                break
            node_id = _sanitize_id(m.name)
            if node_id in node_ids:
                continue
            node_ids.add(node_id)
            display_name = m.name.split(".")[-1] if "." in m.name else m.name
            lines.append(f"            {node_id}[\"{display_name}\"]")
            shown += 1
        lines.append("        end")
    
    lines.append("    end")
    
    # Add dependency edges (internal only, limit to avoid clutter)
    internal_names = {m.name.split(".")[0] for m in modules}
    added_edges: set[tuple[str, str]] = set()
    edge_count = 0
    max_edges = 50
    
    for m in modules:
        if edge_count >= max_edges:
            break
        target_id = _sanitize_id(m.name)
        if target_id not in node_ids:
            continue
        for imp in m.imports:
            if imp in internal_names:
                source_id = _sanitize_id(imp)
                if source_id in node_ids and (source_id, target_id) not in added_edges:
                    if source_id != target_id:
                        lines.append(f"    {source_id} --> {target_id}")
                        added_edges.add((source_id, target_id))
                        edge_count += 1
                        if edge_count >= max_edges:
                            break
    
    lines.append("")
    return "\n".join(lines)


def generate_flowchart_diagram(modules: list[ModuleInfo], repo_name: str = "Repository") -> str:
    """
    Generate Mermaid flowchart for important use cases and entry points.
    """
    lines = [
        "flowchart LR",
        f"    subgraph EntryPoints[\"Entry Points\"]",
    ]
    
    entry_modules = [m for m in modules if m.entry_points or m.functions]
    
    # Add entry points (deduplicated)
    entry_count = 0
    seen_entry_ids: set[str] = set()
    for m in entry_modules[:10]:
        for ep in m.entry_points[:2]:
            node_id = _sanitize_id(f"{m.name}_{ep}")
            if node_id in seen_entry_ids:
                continue
            seen_entry_ids.add(node_id)
            lines.append(f"        {node_id}[\"{m.name}.{ep}\"]")
            entry_count += 1
            if entry_count >= 8:
                break
        if entry_count >= 8:
            break
    
    if entry_count == 0:
        # Use main modules as fallback (prefer src/ over tests/)
        sorted_modules = sorted(modules, key=lambda m: (0 if "test" in m.name.lower() else 1, m.name))
        for m in sorted_modules[:8]:
            if m.functions and _sanitize_id(m.name) not in seen_entry_ids:
                node_id = _sanitize_id(m.name)
                seen_entry_ids.add(node_id)
                lines.append(f"        {node_id}[\"{m.name}\"]")
                entry_count += 1
                if entry_count >= 5:
                    break
    
    lines.append("    end")
    
    # Add key modules/functions
    lines.append("")
    lines.append("    subgraph Core[\"Core Modules\"]")
    core_count = 0
    for m in modules:
        if core_count >= 10:
            break
        if m.classes or len(m.functions) >= 2:
            node_id = _sanitize_id(m.name + "_core")
            display = m.name.split(".")[-1] if "." in m.name else m.name
            lines.append(f"        {node_id}[\"{display}\"]")
            core_count += 1
    lines.append("    end")
    
    # Add connections
    lines.append("")
    lines.append("    EntryPoints --> Core")
    
    lines.append("")
    return "\n".join(lines)


def generate_directory_diagram(structure: dict, repo_name: str = "Repository") -> str:
    """Generate a simple directory structure diagram."""
    lines = ["flowchart TB", f"    subgraph {_sanitize_id(repo_name)}[\"{repo_name} Structure\"]"]
    
    def add_nodes(d: dict, prefix: str = "") -> None:
        for key, value in d.items():
            if key == "_files":
                continue
            node_id = _sanitize_id(prefix + key)
            lines.append(f"        {node_id}[\"{key}/\"]")
            if isinstance(value, dict):
                add_nodes(value, prefix + key + "_")
    
    add_nodes(structure)
    lines.append("    end")
    lines.append("")
    return "\n".join(lines)


def write_diagrams(
    output_dir: Path,
    modules: list[ModuleInfo],
    structure: dict,
    repo_name: str = "Repository",
) -> list[Path]:
    """Write all diagram files to output directory."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    written: list[Path] = []
    
    arch_content = generate_architecture_diagram(modules, repo_name)
    arch_path = output_dir / "architecture.mmd"
    arch_path.write_text(arch_content, encoding="utf-8")
    written.append(arch_path)
    
    flow_content = generate_flowchart_diagram(modules, repo_name)
    flow_path = output_dir / "flowchart.mmd"
    flow_path.write_text(flow_content, encoding="utf-8")
    written.append(flow_path)
    
    dir_content = generate_directory_diagram(structure, repo_name)
    dir_path = output_dir / "directory_structure.mmd"
    dir_path.write_text(dir_content, encoding="utf-8")
    written.append(dir_path)
    
    return written
