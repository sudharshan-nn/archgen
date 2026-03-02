"""Diagram generators - Mermaid architecture and flow charts."""

from pathlib import Path
from typing import TYPE_CHECKING

from .analyzer import ApiRoute, CallEdge, ComponentType, ModuleInfo

if TYPE_CHECKING:
    from .config import ArchGenConfig


def _sanitize_id(name: str) -> str:
    """Create safe Mermaid node ID (alphanumeric, underscores)."""
    return "".join(c if c.isalnum() or c in "._" else "_" for c in name).replace(".", "_")


def generate_architecture_diagram(modules: list[ModuleInfo], repo_name: str = "Repository") -> str:
    """
    Generate Mermaid architecture diagram showing modules and dependencies.
    """
    lines = [
        "flowchart TB",
        f"    subgraph {_sanitize_id(repo_name)}[\"📦 {repo_name}\"]",
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
        pkg_id = _sanitize_id(f"pkg_{pkg_name}")
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
        f"    subgraph EntryPoints[\"🚀 Entry Points\"]",
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
    lines.append("    subgraph Core[\"⚙️ Core Modules\"]")
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


def generate_system_design_diagram(modules: list[ModuleInfo], repo_name: str = "Repository") -> str:
    """
    Generate system design interview-style architecture diagram.
    Layered: Client -> API -> Application -> Data (DB, Cache, Queue)
    """
    prod_modules = [m for m in modules if m.component_type != ComponentType.TEST]

    by_type: dict[ComponentType, list[ModuleInfo]] = {}
    for m in prod_modules:
        ct = m.component_type if m.component_type != ComponentType.UNKNOWN else ComponentType.APP
        if ct not in by_type:
            by_type[ct] = []
        by_type[ct].append(m)

    layer_order = [
        (ComponentType.API, "🔌 API / Web Layer", "API_Web_Layer", "#4A90D9"),
        (ComponentType.APP, "⚙️ Application Layer", "Application_Layer", "#50C878"),
        (ComponentType.AUTH, "🔐 Authentication", "Authentication", "#9B59B6"),
        (ComponentType.DB, "🗄️ Database Layer", "Database_Layer", "#E67E22"),
        (ComponentType.CACHE, "⚡ Cache Layer", "Cache_Layer", "#F1C40F"),
        (ComponentType.QUEUE, "📨 Message Queue", "Message_Queue", "#E74C3C"),
        (ComponentType.CLIENT, "🌐 External Services", "External_Services", "#2ECC71"),
    ]

    lines = [
        "flowchart TB",
        "    %% System Design Architecture - Layered View",
        "    subgraph client[\"👤 Client Layer\"]",
        "        user((\"User / Client\"))",
        "    end",
        "",
    ]

    node_ids: set[str] = set()
    first_in_layer: dict[str, str] = {}

    for comp_type, layer_name, layer_id, color in layer_order:
        mods = by_type.get(comp_type, [])
        if not mods:
            continue

        lines.append(f"    subgraph {layer_id}[\"{layer_name}\"]")
        first_node = None
        for m in mods[:6]:
            nid = _sanitize_id(f"{comp_type.value}_{m.name}")
            if nid in node_ids:
                continue
            node_ids.add(nid)
            if first_node is None:
                first_node = nid
            display = m.name.split(".")[-1] if "." in m.name else m.name
            lines.append(f"        {nid}[\"{display}\"]")
        if first_node:
            first_in_layer[layer_id] = first_node
        lines.append("    end")
        lines.append(f"    style {layer_id} fill:{color}22,stroke:{color},stroke-width:2px")
        lines.append("")

    uncategorized = [
        m for m in prod_modules
        if m.component_type == ComponentType.UNKNOWN and "test" not in m.name.lower()
    ]
    if uncategorized and "Application_Layer" not in first_in_layer:
        lines.append('    subgraph Application_Layer["⚙️ Application Layer"]')
        for m in uncategorized[:6]:
            nid = _sanitize_id(f"app_{m.name}")
            if nid in node_ids:
                continue
            node_ids.add(nid)
            if "Application_Layer" not in first_in_layer:
                first_in_layer["Application_Layer"] = nid
            display = m.name.split(".")[-1] if "." in m.name else m.name
            lines.append(f"        {nid}[\"{display}\"]")
        lines.append("    end")
        lines.append("    style Application_Layer fill:#50C87822,stroke:#50C878,stroke-width:2px")
        lines.append("")

    lines.append("    style client fill:#3498db22,stroke:#3498db,stroke-width:2px")
    lines.append("    %% Data Flow: User -> API -> App -> Data")
    if "API_Web_Layer" in first_in_layer:
        lines.append(f"    user --> {first_in_layer['API_Web_Layer']}")
    if "Application_Layer" in first_in_layer and "API_Web_Layer" in first_in_layer:
        lines.append(f"    {first_in_layer['API_Web_Layer']} --> {first_in_layer['Application_Layer']}")
    if "Application_Layer" in first_in_layer:
        app_node = first_in_layer["Application_Layer"]
        for lid in ["Database_Layer", "Cache_Layer", "Message_Queue"]:
            if lid in first_in_layer:
                lines.append(f"    {app_node} --> {first_in_layer[lid]}")

    lines.append("")
    return "\n".join(lines)


def _safe_filename(route: ApiRoute, index: int | None = None) -> str:
    """Convert API route to safe filename. Use index for uniqueness when provided."""
    path_part = route.path.strip("/").replace("{", "").replace("}", "").replace("/", "_")
    method_part = "_".join(route.methods).lower()
    handler_part = route.handler_function
    base = f"{path_part or 'root'}_{method_part}_{handler_part}"
    s = _sanitize_id(base) or "api"
    return f"{s}_{index}" if index is not None else s


def generate_per_api_diagram(route: ApiRoute, repo_name: str = "Repository") -> str:
    """
    Generate a flow diagram for a single API endpoint.
    Request -> Handler -> Services -> Response
    """
    method_str = ", ".join(route.methods)
    prefix = _sanitize_id(f"{route.handler_module}_{route.handler_function}")
    handler_id = f"{prefix}_handler"

    lines = [
        "flowchart LR",
        f"    %% API: {method_str} {route.path}",
        "",
        "    subgraph Request[\"Request\"]",
        f"        {prefix}_req[\"HTTP {method_str}\"]",
        f"        {prefix}_path[\"{route.path}\"]",
        "    end",
        "",
        "    subgraph Handler[\"Handler\"]",
        f"        {handler_id}[\"{route.handler_function}\"]",
        "    end",
        "",
    ]

    service_ids: list[str] = []
    if route.calls:
        lines.append("    subgraph Services[\"Services / Dependencies\"]")
        for i, call in enumerate(route.calls[:8]):
            if not call.startswith("_"):
                nid = _sanitize_id(f"{prefix}_svc_{call}_{i}")
                service_ids.append(nid)
                lines.append(f"        {nid}[\"{call}\"]")
        lines.append("    end")
        lines.append("")

    resp_id = f"{prefix}_resp"
    lines.append("    subgraph Response[\"Response\"]")
    lines.append(f'        {resp_id}["JSON / Response"]')
    lines.append("    end")
    lines.append("")

    lines.append(f"    {prefix}_req --> {handler_id}")
    if service_ids:
        for sid in service_ids:
            lines.append(f"    {handler_id} --> {sid}")
            lines.append(f"    {sid} --> {resp_id}")
    else:
        lines.append(f"    {handler_id} --> {resp_id}")

    lines.append("")
    return "\n".join(lines)


def generate_api_sequence_diagram(route: ApiRoute) -> str:
    """Generate Mermaid sequence diagram for API request flow."""
    method_str = ", ".join(route.methods)
    lines = [
        "sequenceDiagram",
        f"    participant Client",
        f"    participant API as {route.path}",
        f"    participant Handler as {route.handler_function}",
        "",
        f"    Client->>+API: {method_str} Request",
        f"    API->>+Handler: invoke",
    ]
    for call in route.calls[:5]:
        if not call.startswith("_"):
            lines.append(f"    Handler->>Handler: {call}()")
    lines.append(f"    Handler-->>-API: response")
    lines.append(f"    API-->>-Client: HTTP Response")
    lines.append("")
    return "\n".join(lines)


def generate_per_api_diagrams(
    routes: list[ApiRoute],
    output_dir: Path,
    repo_name: str = "Repository",
) -> list[Path]:
    """Generate one flow diagram per API route. Returns list of written file paths."""
    output_dir = Path(output_dir)
    api_dir = output_dir / "api_flows"
    api_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    index_lines = ["# API Flows Index", "", "| Method | Path | Handler | Files |", "|--------|------|---------|-------|"]
    for i, route in enumerate(routes[:20]):  # Limit to 20 APIs
        fname = _safe_filename(route, index=i)
        flow_content = generate_per_api_diagram(route, repo_name)
        flow_path = api_dir / f"{fname}_flow.mmd"
        flow_path.write_text(flow_content, encoding="utf-8")
        written.append(flow_path)

        seq_content = generate_api_sequence_diagram(route)
        seq_path = api_dir / f"{fname}_sequence.mmd"
        seq_path.write_text(seq_content, encoding="utf-8")
        written.append(seq_path)

        index_lines.append(f"| {', '.join(route.methods)} | `{route.path}` | {route.handler_function} | [{fname}_flow.mmd]({fname}_flow.mmd), [{fname}_sequence.mmd]({fname}_sequence.mmd) |")

    index_path = api_dir / "README.md"
    index_path.write_text("\n".join(index_lines), encoding="utf-8")
    written.append(index_path)

    return written


def generate_c4_diagram(modules: list[ModuleInfo], repo_name: str = "Repository", level: str = "container") -> str:
    """Generate C4-style diagram (Context/Container/Component levels)."""
    prod = [m for m in modules if m.component_type != ComponentType.TEST]
    lines = [
        "flowchart TB",
        f"    subgraph Context[\"🏗️ C4 Context - {repo_name}\"]",
        "        user((\"👤 User\"))",
        f"        system[\"📦 {repo_name}\"]",
        "    end",
        "",
        f"    subgraph Containers[\"Containers\"]",
    ]
    for m in prod[:12]:
        nid = _sanitize_id(m.name)
        display = m.name.split(".")[-1] if "." in m.name else m.name
        lines.append(f"        {nid}[\"{display}\"]")
    lines.append("    end")
    lines.append("")
    lines.append("    user --> system")
    lines.append("    system --> Containers")
    return "\n".join(lines) + "\n"


def generate_call_graph_diagram(edges: list[CallEdge], modules: list[ModuleInfo], max_edges: int = 80) -> str:
    """Generate call graph flowchart."""
    lines = ["flowchart LR", "    %% Call Graph"]
    seen: set[tuple[str, str]] = set()
    count = 0
    for e in edges:
        if count >= max_edges:
            break
        key = (e.caller_module, e.callee)
        if key in seen:
            continue
        seen.add(key)
        src = _sanitize_id(f"{e.caller_module}_{e.caller_func}")
        tgt = _sanitize_id(f"{e.callee}")
        lines.append(f"    {src}[\"{e.caller_func}\"] --> {tgt}[\"{e.callee}\"]")
        count += 1
    return "\n".join(lines) + "\n"


def generate_circular_deps_diagram(cycles: list[list[str]]) -> str:
    """Generate diagram showing circular dependencies."""
    if not cycles:
        return "flowchart TB\n    subgraph NoCycles[\"No circular dependencies detected\"]\n        ok[\"✓ Clean\"]\n    end\n"
    lines = ["flowchart LR", "    %% Circular Dependencies - Consider Refactoring"]
    for i, cycle in enumerate(cycles[:5]):
        for j in range(len(cycle)):
            a, b = cycle[j], cycle[(j + 1) % len(cycle)]
            aid, bid = _sanitize_id(a), _sanitize_id(b)
            lines.append(f"    {aid}[\"{a}\"] --> {bid}[\"{b}\"]")
    return "\n".join(lines) + "\n"


def mermaid_to_plantuml(mermaid: str) -> str:
    """Convert simple Mermaid flowchart to PlantUML."""
    lines = ["@startuml", "skinparam backgroundColor #FFF"]
    for line in mermaid.split("\n"):
        line = line.strip()
        if line.startswith("%%") or not line:
            continue
        if " --> " in line and "subgraph" not in line:
            a, _, b = line.partition(" --> ")
            a = a.strip().split("[")[0].strip()
            b = b.strip().split("[")[0].strip()
            lines.append(f'"{a}" --> "{b}"')
        elif "subgraph" in line:
            label = line.split('"')[1] if '"' in line else "group"
            lines.append(f"package \"{label}\" {{")
        elif line == "end":
            lines.append("}")
    lines.append("@enduml")
    return "\n".join(lines) + "\n"


def generate_directory_diagram(structure: dict, repo_name: str = "Repository") -> str:
    """Generate a simple directory structure diagram."""
    lines = ["flowchart TB", f"    subgraph {_sanitize_id(repo_name)}[\"📁 {repo_name} Structure\"]"]
    
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
    repo_path: Path | None = None,
    config: "ArchGenConfig | None" = None,
    cycles: list[list[str]] | None = None,
    call_edges: list[CallEdge] | None = None,
) -> list[Path]:
    """Write all diagram files to output directory."""
    from .config import ArchGenConfig
    cfg = config or ArchGenConfig()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    arch_content = generate_architecture_diagram(modules, repo_name)
    arch_path = output_dir / "architecture.mmd"
    arch_path.write_text(arch_content, encoding="utf-8")
    written.append(arch_path)

    sysdesign_content = generate_system_design_diagram(modules, repo_name)
    sysdesign_path = output_dir / "system_design.mmd"
    sysdesign_path.write_text(sysdesign_content, encoding="utf-8")
    written.append(sysdesign_path)

    flow_content = generate_flowchart_diagram(modules, repo_name)
    flow_path = output_dir / "flowchart.mmd"
    flow_path.write_text(flow_content, encoding="utf-8")
    written.append(flow_path)

    dir_content = generate_directory_diagram(structure, repo_name)
    dir_path = output_dir / "directory_structure.mmd"
    dir_path.write_text(dir_content, encoding="utf-8")
    written.append(dir_path)

    c4_content = generate_c4_diagram(modules, repo_name, cfg.c4_level)
    c4_path = output_dir / "c4_diagram.mmd"
    c4_path.write_text(c4_content, encoding="utf-8")
    written.append(c4_path)

    if cfg.detect_circular and cycles:
        circ_content = generate_circular_deps_diagram(cycles)
        circ_path = output_dir / "circular_dependencies.mmd"
        circ_path.write_text(circ_content, encoding="utf-8")
        written.append(circ_path)

    if call_edges:
        cg_content = generate_call_graph_diagram(call_edges, modules, cfg.max_edges)
        cg_path = output_dir / "call_graph.mmd"
        cg_path.write_text(cg_content, encoding="utf-8")
        written.append(cg_path)

    if cfg.output_format == "plantuml":
        for mmd in list(output_dir.glob("*.mmd")):
            try:
                puml_content = mermaid_to_plantuml(mmd.read_text(encoding="utf-8"))
                puml_path = mmd.with_suffix(".puml")
                puml_path.write_text(puml_content, encoding="utf-8")
                written.append(puml_path)
            except Exception:
                pass

    if repo_path:
        from .analyzer import extract_api_routes
        routes = extract_api_routes(repo_path)
        if routes:
            api_written = generate_per_api_diagrams(
                routes[: cfg.max_api_routes], output_dir, repo_name
            )
            written.extend(api_written)

    if cfg.export_html:
        from .export import generate_html_report
        report_path = generate_html_report(
            output_dir, repo_name,
            [p for p in written if p.suffix == ".mmd"],
            cycles,
        )
        written.append(report_path)

    if cfg.export_png or cfg.export_svg:
        from .export import export_mermaid_to_image
        for mmd in output_dir.glob("*.mmd"):
            if cfg.export_png:
                png = mmd.with_suffix(".png")
                if export_mermaid_to_image(mmd, png, "png"):
                    written.append(png)
            if cfg.export_svg:
                svg = mmd.with_suffix(".svg")
                if export_mermaid_to_image(mmd, svg, "svg"):
                    written.append(svg)

    return written
