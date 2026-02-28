"""Code analyzer - extracts structure and dependencies from repositories."""

import ast
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


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


# Directories to skip when analyzing
SKIP_DIRS = {
    ".git", "__pycache__", "node_modules", "venv", ".venv", "env",
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
    
    return info


def analyze_repository(repo_path: Path) -> list[ModuleInfo]:
    """
    Analyze a repository and return module information.
    
    Walks the directory tree, parses supported files, and extracts
    structure and dependencies.
    """
    repo_path = Path(repo_path).resolve()
    if not repo_path.is_dir():
        return []
    
    modules: list[ModuleInfo] = []
    
    for root, dirs, files in os.walk(repo_path):
        root_path = Path(root)
        if _should_skip(root_path):
            dirs[:] = []
            continue
        
        # Filter dirs to skip
        dirs[:] = [d for d in dirs if not _should_skip(root_path / d)]
        
        for f in files:
            path = root_path / f
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
