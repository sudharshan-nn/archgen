#!/usr/bin/env python3
"""
Run ArchGen without installing. Usage:
    python run.py /path/to/repo
    python run.py https://github.com/owner/repo
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from archgen.cli import main

if __name__ == "__main__":
    main()
