# ArchGen - Repository Architecture & Flow Diagram Generator

Generate architecture diagrams and flow charts from any local repository or GitHub URL. Understand codebase structure at a glance.

## Quick Start

```bash
# 1. Clone and setup
git clone <repo-url>
cd archgen
python3 -m venv venv && source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. Generate diagrams (local or GitHub)
python run.py /path/to/local/repo
python run.py https://github.com/psf/requests
```

## Features

- **Local & GitHub support**: Analyze local repos or clone from GitHub URLs
- **Architecture diagram**: Visualize module structure and dependencies
- **Flow charts**: Generate flow diagrams for important use cases
- **CLI-first**: Simple command-line interface for quick usage
- **Mermaid output**: Diagrams in Mermaid format (viewable in GitHub, VS Code, online)

## Installation

```bash
# Clone the repository
git clone <this-repo-url>
cd archgen

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install in development mode (optional, for CLI)
pip install -e .
```

## Usage

**Option 1: Run directly (no install required)**
```bash
# Analyze a local repository
python run.py /path/to/your/repo

# Analyze from GitHub URL
python run.py https://github.com/psf/requests

# Specify output directory
python run.py /path/to/repo --output ./diagrams

# View help
python run.py --help
```

**Option 2: Install and use CLI**
```bash
pip install -e .
archgen /path/to/repo
archgen https://github.com/psf/requests
```

## CLI Options

| Option | Description |
|--------|-------------|
| `-o, --output PATH` | Output directory (default: output) |
| `--name TEXT` | Repository name for diagrams |
| `--include-tests` | Include test modules |
| `--max-depth N` | Directory structure depth (default: 4) |
| `--filter PATH` | Only analyze paths (repeatable) |
| `--format mermaid/plantuml` | Output format |
| `--no-html` | Skip HTML report |
| `--export-png` | Export PNG (requires mermaid-cli) |
| `--export-svg` | Export SVG (requires mermaid-cli) |
| `--no-circular-check` | Skip circular dependency detection |

## Configuration

Create `.archgen.yaml` or `.archgen.json` in your repo root. See `.archgen.example.yaml` for all options.

## Output

The tool generates:

1. **architecture.mmd** - Module structure and dependencies
2. **system_design.mmd** - System design layered diagram (Client → API → App → Data)
3. **flowchart.mmd** - Flow diagrams for key use cases and entry points
4. **directory_structure.mmd** - Directory layout
5. **c4_diagram.mmd** - C4-style architecture (Context/Container)
6. **call_graph.mmd** - Function call graph within modules
7. **circular_dependencies.mmd** - Circular import cycles (if detected)
8. **api_flows/** - Per-API flow and sequence diagrams (Flask/FastAPI/Django/Express)
9. **report.html** - Standalone HTML report with all diagrams (open in browser)

View Mermaid files:
- **GitHub**: Paste content in a `.md` file or use GitHub's Mermaid support
- **VS Code**: Install "Mermaid" extension
- **Online**: [mermaid.live](https://mermaid.live)

## Supported Languages & Frameworks

- **Python**: Flask, FastAPI, Django (routes + AST analysis)
- **JavaScript/TypeScript**: Express, Koa (routes + structure)
- **Other**: Directory structure and file relationships

## Future Improvements

- **Watch mode**: Regenerate on file changes
- **Optional LLM**: Add descriptions (requires API key)

## License

MIT
