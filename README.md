# ArchGen - Repository Architecture & Flow Diagram Generator

Generate architecture diagrams and flow charts from any local repository or GitHub URL. Understand codebase structure at a glance.

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

## Output

The tool generates:

1. **architecture.mmd** - High-level architecture showing modules and their relationships
2. **flowchart.mmd** - Flow diagrams for key use cases and entry points

View Mermaid files:
- **GitHub**: Paste content in a `.md` file or use GitHub's Mermaid support
- **VS Code**: Install "Mermaid" extension
- **Online**: [mermaid.live](https://mermaid.live)

## Supported Languages

- **Python**: Full AST analysis (imports, classes, functions)
- **JavaScript/TypeScript**: Basic structure analysis
- **Other**: Directory structure and file relationships

## License

MIT
