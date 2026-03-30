#!/usr/bin/env python3
"""
Comprehensive Import Path Refactoring Script
for SalesBoost Cognitive Architecture Migration
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Tuple


class ImportPathFixer:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.fixes_applied = 0
        self.errors = []

        # Define the import path mappings
        self.import_mappings = {
            # Old app.* imports -> New cognitive imports
            r"from app\.engine\.": "from cognitive.brain.",
            r"from app\.agents\.": "from cognitive.skills.",
            r"from app\.services\.": "from cognitive.",
            r"from app\.infra\.": "from cognitive.infra.",
            r"from app\.memory\.": "from cognitive.memory.",
            r"from app\.tools\.": "from cognitive.tools.",
            r"from app\.observability\.": "from cognitive.observability.",
            # Old app.* imports -> New root level imports
            r"from app\.api\.": "from api.",
            r"from app\.core\.": "from core.",
            r"from app\.models\.": "from models.",
            r"from app\.schemas\.": "from schemas.",
            r"from app\.main": "from main",
            # Specific cognitive component mappings
            r"cognitive\.brain\.coordinator\.": "cognitive.brain.coordinator.",
            r"cognitive\.brain\.intent\.": "cognitive.brain.intent.",
            r"cognitive\.brain\.state\.": "cognitive.brain.state.",
            r"cognitive\.skills\.study\.": "cognitive.skills.study.",
            r"cognitive\.skills\.ask\.": "cognitive.skills.ask.",
            r"cognitive\.skills\.practice\.": "cognitive.skills.practice.",
            r"cognitive\.skills\.evaluate\.": "cognitive.skills.evaluate.",
            r"cognitive\.memory\.context\.": "cognitive.memory.context.",
            r"cognitive\.memory\.tracking\.": "cognitive.memory.tracking.",
            r"cognitive\.memory\.storage\.": "cognitive.memory.storage.",
            r"cognitive\.infra\.gateway\.": "cognitive.infra.gateway.",
            r"cognitive\.infra\.guardrails\.": "cognitive.infra.guardrails.",
            r"cognitive\.infra\.providers\.": "cognitive.infra.providers.",
            r"cognitive\.tools\.parsers\.": "cognitive.tools.parsers.",
            r"cognitive\.tools\.connectors\.": "cognitive.tools.connectors.",
            r"cognitive\.observability\.tracing\.": "cognitive.observability.tracing.",
            r"cognitive\.observability\.metrics\.": "cognitive.observability.metrics.",
        }

        # File-specific imports that need special handling
        self.special_cases = {
            "main.py": [
                # Main.py specific fixes
                (r"from app\.", "from "),
            ],
        }

    def fix_file(self, file_path: Path) -> bool:
        """Fix import statements in a single file"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            original_content = content
            file_name = file_path.name

            # Apply special cases first
            if file_name in self.special_cases:
                for pattern, replacement in self.special_cases[file_name]:
                    content = re.sub(pattern, replacement, content)

            # Apply general mappings
            for old_pattern, new_import in self.import_mappings.items():
                content = re.sub(old_pattern, new_import, content)

            # Only write if changes were made
if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"Fixed imports in: {file_path.relative_to(self.project_root)}")
                self.fixes_applied += 1
                return True

            return False

        except Exception as e:
            error_msg = f"Error processing {file_path}: {str(e)}"
            print(f"{error_msg}")
            self.errors.append(error_msg)
            return False

def fix_directory(self, directory: Path) -> None:
        """Recursively fix all Python files in a directory"""
        if not directory.exists():
            print(f"Directory does not exist: {directory}")
            return
            
        print(f"Processing directory: {directory.relative_to(self.project_root)}")
        
        for file_path in directory.rglob("*.py"):
            if file_path.is_file():
                self.fix_file(file_path)

    def fix_all(self) -> Dict[str, any]:
        """Fix all Python files in the project"""
        print("🚀 Starting comprehensive import path refactoring...")

        # Fix main directories
        directories_to_fix = [
            self.project_root / "cognitive",
            self.project_root / "api",
            self.project_root / "core",
            self.project_root / "models",
            self.project_root / "schemas",
            self.project_root / "main.py",
            self.project_root / "tests",
            self.project_root / "scripts",
        ]

        for directory in directories_to_fix:
            if directory.is_file():
                self.fix_file(directory)
            else:
                self.fix_directory(directory)

        return {
            "fixes_applied": self.fixes_applied,
            "errors": self.errors,
            "status": "completed" if not self.errors else "completed_with_errors",
        }


def main():
    """Main execution function"""
    project_root = Path(__file__).parent
    fixer = ImportPathFixer(project_root)

    print("SalesBoost Import Path Refactoring Tool")
    print("=" * 50)

    result = fixer.fix_all()

    print("\n" + "=" * 50)
    print("REFACTORING SUMMARY")
    print("=" * 50)
    print(f"Files fixed: {result['fixes_applied']}")
    print(f"Errors: {len(result['errors'])}")

    if result["errors"]:
        print("\nERRORS:")
        for error in result["errors"]:
            print(f"  • {error}")

    print(f"\nStatus: {result['status']}")

    if result["fixes_applied"] > 0:
        print("\nNext steps:")
        print("  1. Run: python -m py_compile main.py")
        print("  2. Run: pytest tests/")
        print("  3. Verify application starts: uvicorn main:app --reload")


if __name__ == "__main__":
    main()
