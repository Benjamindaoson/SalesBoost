#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SalesBoost Project Reorganization Script

Reorganize project structure according to world-class open source standards

Author: Claude (Anthropic)
Date: 2026-02-05
"""

import os
import sys
from pathlib import Path

# Set UTF-8 encoding for Windows
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())


def main():
    """Main reorganization function"""

    print("=" * 70)
    print("SalesBoost Project Reorganization")
    print("=" * 70)
    print()

    # Get project root
    script_path = Path(__file__).resolve()
    project_root = script_path.parent.parent.parent

    print(f"Project root: {project_root}")
    print()

    # Check if --execute flag is present
    execute = "--execute" in sys.argv

    if not execute:
        print("[DRY RUN MODE] - Showing operations without executing")
        print()
    else:
        print("[EXECUTE MODE] - Will actually modify files")
        print()

    operations = []

    # ========================================
    # 1. Reorganize Documentation
    # ========================================
    print("=" * 70)
    print("1. Reorganizing Documentation")
    print("=" * 70)
    print()

    docs_root = project_root / "docs"

    # Create subdirectories
    subdirs_to_create = [
        docs_root / "guides",
        docs_root / "reports",
        docs_root / "architecture",
        docs_root / "api",
    ]

    for subdir in subdirs_to_create:
        if not subdir.exists():
            operations.append(("CREATE_DIR", str(subdir)))
            print(f"[CREATE DIR] {subdir.relative_to(project_root)}")
            if execute:
                subdir.mkdir(parents=True, exist_ok=True)

    # Move root-level docs to docs/
    root_docs_moves = [
        ("MCP_2026_COMPLETE_README.md", "docs/guides/mcp-2026-complete.md"),
        ("MCP_A2A_README.md", "docs/guides/mcp-a2a-integration.md"),
        ("INTEGRATION_COMPLETE.md", "docs/reports/integration-complete.md"),
        ("DEPLOYMENT_REPORT.md", "docs/reports/deployment-report.md"),
    ]

    for source_name, dest_path in root_docs_moves:
        source = project_root / source_name
        dest = project_root / dest_path

        if source.exists():
            operations.append(("MOVE", str(source), str(dest)))
            print(f"[MOVE] {source.name} -> {dest.relative_to(project_root)}")

            if execute:
                dest.parent.mkdir(parents=True, exist_ok=True)
                source.rename(dest)

    print()

    # ========================================
    # 2. Add Missing __init__.py Files
    # ========================================
    print("=" * 70)
    print("2. Adding Missing __init__.py Files")
    print("=" * 70)
    print()

    dirs_needing_init = [
        "app/ai_core",
        "app/ai_core/constitutional",
        "app/ai_core/curriculum",
        "app/ai_core/rlaif",
        "app/retrieval",
        "app/monitoring",
        "app/services",
        "app/agents/memory",
        "app/agents/rl",
        "app/agents/emotion",
        "app/infra/llm/moe",
    ]

    for dir_path in dirs_needing_init:
        full_path = project_root / dir_path
        init_file = full_path / "__init__.py"

        if full_path.exists() and not init_file.exists():
            operations.append(("CREATE", str(init_file)))
            print(f"[CREATE] {init_file.relative_to(project_root)}")

            if execute:
                module_name = full_path.name
                init_file.write_text(
                    f'"""\n{module_name}\n"""\n',
                    encoding="utf-8"
                )

    print()

    # ========================================
    # 3. Create Directory READMEs
    # ========================================
    print("=" * 70)
    print("3. Creating Directory READMEs")
    print("=" * 70)
    print()

    readme_contents = {
        "app/ai_core": "# AI Core Components\n\nAdvanced AI algorithms and models.\n",
        "app/agents": "# Agent System\n\nMulti-agent architecture and implementations.\n",
        "app/infra": "# Infrastructure\n\nCore infrastructure components.\n",
        "docs/guides": "# User Guides\n\nStep-by-step guides and tutorials.\n",
        "docs/reports": "# Reports\n\nImplementation reports and progress updates.\n",
        "docs/architecture": "# Architecture Documentation\n\nSystem architecture and design documents.\n",
    }

    for dir_path, content in readme_contents.items():
        full_path = project_root / dir_path
        readme_file = full_path / "README.md"

        if full_path.exists() and not readme_file.exists():
            operations.append(("CREATE", str(readme_file)))
            print(f"[CREATE] {readme_file.relative_to(project_root)}")

            if execute:
                full_path.mkdir(parents=True, exist_ok=True)
                readme_file.write_text(content, encoding="utf-8")

    print()

    # ========================================
    # 4. Archive Historical Scripts
    # ========================================
    print("=" * 70)
    print("4. Archiving Historical Scripts")
    print("=" * 70)
    print()

    scripts_root = project_root / "scripts"
    archive_dir = scripts_root / "archive"

    if not archive_dir.exists():
        operations.append(("CREATE_DIR", str(archive_dir)))
        print(f"[CREATE DIR] {archive_dir.relative_to(project_root)}")
        if execute:
            archive_dir.mkdir(parents=True, exist_ok=True)

    # Archive week* and phase* scripts
    for subdir_name in ["maintenance", "deployment"]:
        subdir = scripts_root / subdir_name
        if subdir.exists():
            for pattern in ["week*.py", "phase*.py"]:
                for file in subdir.glob(pattern):
                    dest = archive_dir / subdir_name / file.name
                    operations.append(("MOVE", str(file), str(dest)))
                    print(f"[ARCHIVE] {file.relative_to(project_root)} -> {dest.relative_to(project_root)}")

                    if execute:
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        file.rename(dest)

    print()

    # ========================================
    # Summary
    # ========================================
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    print()

    action_counts = {}
    for op in operations:
        action = op[0]
        action_counts[action] = action_counts.get(action, 0) + 1

    for action, count in sorted(action_counts.items()):
        print(f"{action}: {count} operations")

    print(f"\nTotal: {len(operations)} operations")
    print()

    if not execute:
        print("=" * 70)
        print("[DRY RUN] No actual changes were made")
        print()
        print("To execute these changes, run:")
        print("python scripts/ops/reorganize_project.py --execute")
        print("=" * 70)
    else:
        print("=" * 70)
        print("[SUCCESS] Reorganization completed!")
        print("=" * 70)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n[ERROR] {e}", file=sys.stderr)
        sys.exit(1)
