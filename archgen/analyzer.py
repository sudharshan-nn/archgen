"""Code analyzer - extracts structure and dependencies from repositories."""

import ast
import os
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class ComponentType(str, Enum):
    """System design component type inferred from code."""
    API = "api"           # Web/API layer (Flask, FastAPI, Express)
    APP = "app"           # Business logic / application
    DB = "database"       # Database / ORM
    CACHE = "cache"       # Redis, Memcached
    QUEUE = "queue"       # Message queue, Celery
    AUTH = "auth"         # Authentication
    CLIENT = "client"     # HTTP client, external API calls
    TEST = "test"         # Tests
    UNKNOWN = "unknown"


# Imports that indicate component type (lowercase for matching)
COMPONENT_SIGNATURES = {
    ComponentType.API: [
        "flask", "fastapi", "django", "starlette", "sanic", "aiohttp",
        "express", "koa", "hapi", "nest", "next",
    ],
    ComponentType.DB: [
        "sqlalchemy", "django.db", "psycopg2", "pymongo", "redis",
        "sqlite3", "mysql", "asyncpg", "prisma", "sequelize", "mongoose",
    ],
    ComponentType.CACHE: ["redis", "memcached", "aiocache"],
    ComponentType.QUEUE: [
        "celery", "rq", "kombu", "pika", "kafka", "confluent_kafka",
        "bull", "amqp", "sqs",
    ],
    ComponentType.AUTH: ["jwt", "oauth", "authlib", "passport", "bcrypt"],
    ComponentType.CLIENT: ["requests", "httpx", "aiohttp", "axios", "fetch"],
}


@dataclass
class ApiRoute:
    """An API endpoint with its handler and call flow."""
    path: str
    methods: list[str]
    handler_module: str
    handler_function: str
    handler_file: str
    calls: list[str]  # Functions/modules called from handler


@dataclass
class CallEdge:
    """A call from one function to another."""
    caller_module: str
    caller_func: str
    callee: str  # May be module.func or just func


@dataclass
class ModuleInfo:
    """Information about a module/file."""
    path: str
    name: str
    imports: list[str] = field(default_factory=list)
    classes: list[str] = field(default_factory=list)
    functions: list[str] = field(default_factory=list)
    entry_points: list[str] = field(default_factory=list)
    language: str = "unknown"
    component_type: ComponentType = field(default=ComponentType.UNKNOWN)


# Directories to skip when analyzing
SKIP_DIRS = {
    ".git", "__pycache__", "node_modules", "venv", ".venv", "env",
    "temp_repos",
    "dist", "build", "eggs", ".eggs", "*.egg-info", "site-packages",
    "vendor", ".tox", ".pytest_cache", ".mypy_cache", "coverage",
    ".idea", ".vscode", "target", "bin", "obj",
}

# File patterns to analyze
PYTHON_EXT = {".py"}
JS_EXT = {".js", ".ts", ".jsx", ".tsx"}
SUPPORTED_EXT = PYTHON_EXT | JS_EXT


def _should_skip(path: Path) -> bool:
    """Check if path should be skipped."""
    parts = path.parts
    for skip in SKIP_DIRS:
        if skip == "temp_repos":
            if path.name == "temp_repos":
                return True
            continue
        if skip in parts:
            return True
        if skip.startswith("*") and any(skip[1:] in p for p in parts):
            return True
    return False


def _path_to_module_name(path: Path, root: Path) -> str:
    """Convert file path to module name."""
    try:
        rel = path.relative_to(root)
    except ValueError:
        return path.stem
    parts = list(rel.parts[:-1]) + [rel.stem]
    return ".".join(parts).replace("-", "_")


def _infer_component_type(info: ModuleInfo) -> None:
    """Infer system design component type from imports and path."""
    imports_lower = {i.lower().split(".")[0] for i in info.imports}
    path_lower = info.path.lower()
    name_lower = info.name.lower()

    # Test files
    if "test" in path_lower or "test" in name_lower or "conftest" in name_lower:
        info.component_type = ComponentType.TEST
        return

    # Check imports against signatures (priority order)
    for comp_type, sigs in COMPONENT_SIGNATURES.items():
        for sig in sigs:
            if sig in imports_lower or sig.replace(".", "_") in imports_lower:
                info.component_type = comp_type
                return

    # Fallback: infer from path/name
    if any(x in path_lower for x in ["api", "routes", "views", "controller"]):
        info.component_type = ComponentType.API
    elif any(x in path_lower for x in ["model", "db", "repository", "dao"]):
        info.component_type = ComponentType.DB
    elif any(x in path_lower for x in ["auth", "login", "session"]):
        info.component_type = ComponentType.AUTH
    elif any(x in name_lower for x in ["main", "app", "__init__"]):
        info.component_type = ComponentType.APP


def _analyze_python(content: str, path: Path, root: Path) -> ModuleInfo:
    """Analyze Python file using AST."""
    module_name = _path_to_module_name(path, root)
    info = ModuleInfo(path=str(path.relative_to(root)), name=module_name, language="python")
    
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return info
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                info.imports.append(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                info.imports.append(node.module.split(".")[0])
        elif isinstance(node, ast.ClassDef):
            info.classes.append(node.name)
        elif isinstance(node, ast.FunctionDef):
            if node.name == "main":
                info.entry_points.append(node.name)
            if not node.name.startswith("_"):
                info.functions.append(node.name)
    
    # Check for if __name__ == "__main__"
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            if _is_name_main_check(node):
                for stmt in node.body:
                    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                        if isinstance(stmt.value.func, ast.Name):
                            info.entry_points.append(stmt.value.func.id)
    
    _infer_component_type(info)
    return info


def _is_name_main_check(node: ast.If) -> bool:
    """Check if node is 'if __name__ == "__main__"'."""
    if not isinstance(node.test, ast.Compare):
        return False
    if len(node.test.ops) != 1 or not isinstance(node.test.ops[0], ast.Eq):
        return False
    if not isinstance(node.test.left, ast.Name) or node.test.left.id != "__name__":
        return False
    if not isinstance(node.test.comparators[0], ast.Constant):
        return False
    return node.test.comparators[0].value == "__main__"


def _analyze_javascript(content: str, path: Path, root: Path) -> ModuleInfo:
    """Basic analysis of JavaScript/TypeScript files."""
    module_name = _path_to_module_name(path, root)
    info = ModuleInfo(path=str(path.relative_to(root)), name=module_name, language="javascript")
    
    # Simple regex-based extraction (fallback when no proper parser)
    import re
    
    # Match: import X from 'Y' or require('Y')
    for match in re.finditer(r"(?:import .+ from|require)\s*\(\s*['\"]([^'\"]+)['\"]", content):
        mod = match.group(1).split("/")[0]
        if not mod.startswith("."):
            info.imports.append(mod)
    
    # Match: function name( or class Name
    for match in re.finditer(r"\b(?:function|async function)\s+(\w+)\s*\(", content):
        info.functions.append(match.group(1))
    for match in re.finditer(r"\bclass\s+(\w+)\s*(?:extends|\{)", content):
        info.classes.append(match.group(1))
    
    _infer_component_type(info)
    return info


def _matches_filter(path: Path, repo_path: Path, filter_paths: list[str]) -> bool:
    """Check if path matches filter_paths (include only these)."""
    if not filter_paths:
        return True
    try:
        rel = str(path.relative_to(repo_path))
    except ValueError:
        return False
    for fp in filter_paths:
        if rel.startswith(fp) or fp in rel:
            return True
    return False


def analyze_repository(
    repo_path: Path,
    include_tests: bool = False,
    filter_paths: list[str] | None = None,
) -> list[ModuleInfo]:
    """
    Analyze a repository and return module information.
    
    Walks the directory tree, parses supported files, and extracts
    structure and dependencies.
    """
    repo_path = Path(repo_path).resolve()
    if not repo_path.is_dir():
        return []
    filter_paths = filter_paths or []
    modules: list[ModuleInfo] = []
    
    for root, dirs, files in os.walk(repo_path):
        root_path = Path(root)
        if _should_skip(root_path):
            dirs[:] = []
            continue
        
        dirs[:] = [d for d in dirs if not _should_skip(root_path / d)]
        
        for f in files:
            path = root_path / f
            if filter_paths and not _matches_filter(path, repo_path, filter_paths):
                continue
            suffix = path.suffix.lower()
            
            if suffix not in SUPPORTED_EXT:
                continue
            
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
            except (OSError, UnicodeDecodeError):
                continue
            
            if suffix in PYTHON_EXT:
                info = _analyze_python(content, path, repo_path)
            else:
                info = _analyze_javascript(content, path, repo_path)
            
            if not include_tests and info.component_type == ComponentType.TEST:
                continue
            modules.append(info)
    
    return modules


def get_directory_structure(repo_path: Path, max_depth: int = 4) -> dict:
    """Get directory structure as a nested dict."""
    repo_path = Path(repo_path).resolve()
    structure: dict = {}
    
    for root, dirs, files in os.walk(repo_path):
        root_path = Path(root)
        if _should_skip(root_path):
            dirs[:] = []
            continue
        
        dirs[:] = [d for d in dirs if not _should_skip(root_path / d)]
        
        rel = root_path.relative_to(repo_path)
        depth = len(rel.parts)
        if depth >= max_depth:
            dirs[:] = []
            continue
        
        current = structure
        for part in rel.parts:
            if part not in current:
                current[part] = {}
            current = current[part]
        
        # Add key files
        key_files = [f for f in files if f.endswith((".py", ".js", ".ts", "package.json"))]
        if key_files:
            current["_files"] = key_files[:10]  # Limit to 10
    
    return structure


def _extract_route_from_decorator(decorator: ast.expr) -> tuple[str, list[str]] | None:
    """Extract (path, methods) from Flask/FastAPI decorator."""
    if isinstance(decorator, ast.Call):
        func = decorator.func
        if isinstance(func, ast.Attribute):
            name = func.attr
            if name == "route":
                path, methods = _parse_route_args(decorator)
                return (path, methods) if path else None
            if name in ("get", "post", "put", "patch", "delete"):
                path = _parse_path_arg(decorator)
                return (path, [name.upper()]) if path else None
    return None


def _parse_route_args(call: ast.Call) -> tuple[str | None, list[str]]:
    """Parse @app.route(path, methods=[...]) arguments."""
    args = call.args
    if not args or not isinstance(args[0], ast.Constant):
        return None, ["GET"]
    path = str(args[0].value)
    methods = ["GET"]
    for kw in call.keywords:
        if kw.arg == "methods" and isinstance(kw.value, ast.List):
            methods = []
            for elt in kw.value.elts:
                if isinstance(elt, ast.Constant):
                    methods.append(str(elt.value).upper())
    return path, methods or ["GET"]


def _parse_path_arg(call: ast.Call) -> str | None:
    """Parse path from @router.get(path) or @app.get(path)."""
    if call.args and isinstance(call.args[0], ast.Constant):
        return str(call.args[0].value)
    return None


def extract_call_graph(modules: list[ModuleInfo], repo_path: Path) -> list[CallEdge]:
    """Extract call graph: which functions call which (within same module)."""
    edges: list[CallEdge] = []
    for m in modules:
        path = repo_path / m.path
        if not path.exists() or not m.path.endswith(".py"):
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(content)
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                caller = node.name
                for n in ast.walk(node):
                    if isinstance(n, ast.Call):
                        if isinstance(n.func, ast.Name):
                            edges.append(CallEdge(m.name, caller, n.func.id))
                        elif isinstance(n.func, ast.Attribute):
                            edges.append(CallEdge(m.name, caller, n.func.attr))
    return edges


def _get_handler_calls(node: ast.AST) -> list[str]:
    """Extract called function/module names from function body."""
    calls: list[str] = []
    for n in ast.walk(node):
        if isinstance(n, ast.Call):
            func = n.func
            if isinstance(func, ast.Name):
                calls.append(func.id)
            elif isinstance(func, ast.Attribute):
                calls.append(func.attr)
    return list(dict.fromkeys(calls))


def detect_circular_dependencies(modules: list[ModuleInfo]) -> list[list[str]]:
    """Detect circular import dependencies. Returns list of cycles."""
    internal = {m.name.split(".")[0] for m in modules}
    graph: dict[str, set[str]] = {}
    for m in modules:
        mod = m.name.split(".")[0]
        if mod not in graph:
            graph[mod] = set()
        for imp in m.imports:
            if imp in internal and imp != mod:
                graph[mod].add(imp)

    cycles: list[list[str]] = []
    visited: set[str] = set()
    rec_stack: dict[str, int] = {}
    path: list[str] = []
    path_set: set[str] = set()

    def dfs(node: str) -> bool:
        visited.add(node)
        rec_stack[node] = len(path)
        path.append(node)
        path_set.add(node)
        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                if dfs(neighbor):
                    return True
            elif neighbor in path_set:
                cycle = path[rec_stack[neighbor]:] + [neighbor]
                if cycle not in cycles and len(cycle) > 1:
                    cycles.append(cycle)
        path.pop()
        path_set.discard(node)
        return False

    for node in graph:
        if node not in visited:
            dfs(node)
    return cycles


def _extract_express_routes(content: str, path: Path, root: Path) -> list[ApiRoute]:
    """Extract routes from Express/Node.js: app.get('/path', handler), router.post(...)."""
    routes: list[ApiRoute] = []
    module_name = _path_to_module_name(path, root)
    # Match: app.get('/path', fn), router.post("/path", handler), express().get('/x', ...)
    pattern = re.compile(
        r"(?:app|router|express\s*\(\s*\))\s*\.\s*(get|post|put|patch|delete|all)\s*\(\s*['\"]([^'\"]+)['\"]",
        re.IGNORECASE,
    )
    for match in pattern.finditer(content):
        method, path_str = match.group(1).upper(), match.group(2)
        routes.append(ApiRoute(
            path=path_str,
            methods=[method],
            handler_module=module_name,
            handler_function="<anonymous>",
            handler_file=str(path.relative_to(root)),
            calls=[],
        ))
    return routes


def _extract_django_routes(content: str, path: Path, root: Path) -> list[ApiRoute]:
    """Extract routes from Django urlpatterns."""
    routes: list[ApiRoute] = []
    module_name = _path_to_module_name(path, root)
    if "urlpatterns" not in content:
        return routes
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return routes
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "urlpatterns":
                    for elt in getattr(node.value, "elts", []):
                        path_str, view = None, "unknown"
                        if isinstance(elt, (ast.Tuple, ast.List)) and len(elt.elts) >= 2:
                            if isinstance(elt.elts[0], ast.Constant):
                                path_str = str(elt.elts[0].value)
                            if isinstance(elt.elts[1], ast.Name):
                                view = elt.elts[1].id
                            elif isinstance(elt.elts[1], ast.Attribute):
                                view = elt.elts[1].attr
                        elif hasattr(elt, "func") and isinstance(elt.func, ast.Name):
                            if elt.func.id == "path" and elt.args and isinstance(elt.args[0], ast.Constant):
                                path_str = str(elt.args[0].value)
                                if len(elt.args) >= 2 and isinstance(elt.args[1], ast.Name):
                                    view = elt.args[1].id
                        if path_str:
                            routes.append(ApiRoute(
                                path=path_str,
                                methods=["GET"],
                                handler_module=module_name,
                                handler_function=view,
                                handler_file=str(path.relative_to(root)),
                                calls=[],
                            ))
                    break
    return routes


def extract_api_routes(repo_path: Path) -> list[ApiRoute]:
    """Extract API routes from Flask/FastAPI/Django/Express files."""
    repo_path = Path(repo_path).resolve()
    routes: list[ApiRoute] = []

    for root, dirs, files in os.walk(repo_path):
        root_path = Path(root)
        if _should_skip(root_path):
            dirs[:] = []
            continue
        dirs[:] = [d for d in dirs if not _should_skip(root_path / d)]

        for f in files:
            path = root_path / f
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
            except (OSError, UnicodeDecodeError):
                continue

            if f.endswith(".py"):
                try:
                    tree = ast.parse(content)
                except SyntaxError:
                    pass
                else:
                    module_name = _path_to_module_name(path, repo_path)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            for dec in node.decorator_list:
                                result = _extract_route_from_decorator(dec)
                                if result:
                                    path_str, methods = result
                                    handler_calls = _get_handler_calls(node)
                                    routes.append(ApiRoute(
                                        path=path_str,
                                        methods=methods,
                                        handler_module=module_name,
                                        handler_function=node.name,
                                        handler_file=str(path.relative_to(repo_path)),
                                        calls=handler_calls,
                                    ))
                                    break
                routes.extend(_extract_django_routes(content, path, repo_path))
            elif f.endswith((".js", ".ts", ".jsx", ".tsx")):
                routes.extend(_extract_express_routes(content, path, repo_path))

    return routes
