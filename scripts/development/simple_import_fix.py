#!/usr/bin/env python3
"""
Simple Import Path Fixer for SalesBoost
"""

import os
import re
from pathlib import Path


def fix_imports_in_file(file_path: Path) -> bool:
    """Fix import statements in a single file"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        original_content = content

        # Fix common import patterns
        content = re.sub(r"from app\.engine\.", "from cognitive.brain.", content)
        content = re.sub(r"from app\.agents\.", "from cognitive.skills.", content)
        content = re.sub(r"from app\.services\.", "from cognitive.", content)
        content = re.sub(r"from app\.infra\.", "from cognitive.infra.", content)
        content = re.sub(r"from app\.memory\.", "from cognitive.memory.", content)
        content = re.sub(r"from app\.tools\.", "from cognitive.tools.", content)
        content = re.sub(
            r"from app\.observability\.", "from cognitive.observability.", content
        )
        content = re.sub(r"from app\.api\.", "from api.", content)
        content = re.sub(r"from app\.core\.", "from core.", content)
        content = re.sub(r"from app\.models\.", "from models.", content)
        content = re.sub(r"from app\.schemas\.", "from schemas.", content)
        content = re.sub(r"from app\.main", "from main", content)

        # Only write if changes were made
        if content != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Fixed: {file_path.relative_to(Path.cwd())}")
            return True

        return False

    except Exception as e:
        print(f"Error: {file_path} - {e}")
        return False


def fix_all_imports():
    """Fix all Python files"""
    print("Starting import path fixes...")

    fix_count = 0
    project_root = Path.cwd()

    # Fix main directories
    for directory in [
        "cognitive",
        "api",
        "core",
        "models",
        "schemas",
        "tests",
        "scripts",
    ]:
        dir_path = project_root / directory
        if dir_path.exists():
            for py_file in dir_path.rglob("*.py"):
                if fix_imports_in_file(py_file):
                    fix_count += 1

    # Fix main.py
    main_py = project_root / "main.py"
    if main_py.exists():
        if fix_imports_in_file(main_py):
            fix_count += 1

    print(f"\nCompleted! Fixed {fix_count} files.")
    return fix_count


if __name__ == "__main__":
    fix_all_imports()
