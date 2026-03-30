#!/usr/bin/env python3
"""
SalesBoost Project Reorganization Script

按照世界级开源项目标准重组文件结构

Author: Claude (Anthropic)
Date: 2026-02-05
"""

import os
import shutil
from pathlib import Path
from typing import List, Tuple

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent


class ProjectReorganizer:
    """项目重组器"""

    def __init__(self, dry_run: bool = True):
        """
        初始化

        Args:
            dry_run: 如果为True，只打印操作不实际执行
        """
        self.dry_run = dry_run
        self.operations: List[Tuple[str, str, str]] = []  # (action, source, dest)

    def log_operation(self, action: str, source: str, dest: str = ""):
        """记录操作"""
        self.operations.append((action, source, dest))
        if dest:
            print(f"[{action}] {source} -> {dest}")
        else:
            print(f"[{action}] {source}")

    def move_file(self, source: Path, dest: Path):
        """移动文件"""
        if not source.exists():
            print(f"[SKIP] Source not found: {source}")
            return

        self.log_operation("MOVE", str(source), str(dest))

        if not self.dry_run:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(dest))

    def delete_file(self, path: Path):
        """删除文件"""
        if not path.exists():
            print(f"[SKIP] File not found: {path}")
            return

        self.log_operation("DELETE", str(path))

        if not self.dry_run:
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()

    def create_init_py(self, directory: Path):
        """创建__init__.py"""
        init_file = directory / "__init__.py"

        if init_file.exists():
            return

        self.log_operation("CREATE", str(init_file))

        if not self.dry_run:
            directory.mkdir(parents=True, exist_ok=True)
            init_file.write_text('"""\n' + directory.name + '\n"""\n')

    def reorganize_docs(self):
        """重组文档目录"""
        print("\n=== 重组文档目录 ===\n")

        docs_root = PROJECT_ROOT / "docs"

        # 创建子目录
        subdirs = {
            "guides": docs_root / "guides",
            "reports": docs_root / "reports",
            "architecture": docs_root / "architecture",
            "api": docs_root / "api",
        }

        for subdir in subdirs.values():
            if not self.dry_run:
                subdir.mkdir(parents=True, exist_ok=True)

        # 移动根目录的文档到docs/
        root_docs_to_move = [
            ("MCP_2026_COMPLETE_README.md", "guides/mcp-2026-complete.md"),
            ("MCP_A2A_README.md", "guides/mcp-a2a-integration.md"),
            ("INTEGRATION_COMPLETE.md", "reports/integration-complete.md"),
            ("DEPLOYMENT_REPORT.md", "reports/deployment-report.md"),
        ]

        for source_name, dest_name in root_docs_to_move:
            source = PROJECT_ROOT / source_name
            dest = docs_root / dest_name
            if source.exists():
                self.move_file(source, dest)

        # 重组docs/内的文件
        if docs_root.exists():
            for file in docs_root.glob("*.md"):
                filename = file.name.lower()

                # 报告类文档
                if any(keyword in filename for keyword in [
                    "complete", "report", "week", "phase", "implementation"
                ]):
                    dest = subdirs["reports"] / file.name.lower().replace("_", "-")
                    self.move_file(file, dest)

                # 指南类文档
                elif any(keyword in filename for keyword in [
                    "guide", "quickstart", "tutorial", "howto"
                ]):
                    dest = subdirs["guides"] / file.name.lower().replace("_", "-")
                    self.move_file(file, dest)

                # 架构类文档
                elif any(keyword in filename for keyword in [
                    "architecture", "design", "system"
                ]):
                    dest = subdirs["architecture"] / file.name.lower().replace("_", "-")
                    self.move_file(file, dest)

        # 移动Python脚本到examples/
        for py_file in docs_root.glob("*.py"):
            dest = PROJECT_ROOT / "examples" / "demos" / py_file.name
            self.move_file(py_file, dest)

    def reorganize_scripts(self):
        """重组脚本目录"""
        print("\n=== 重组脚本目录 ===\n")

        scripts_root = PROJECT_ROOT / "scripts"
        archive_dir = scripts_root / "archive"

        if not self.dry_run:
            archive_dir.mkdir(parents=True, exist_ok=True)

        # 归档历史脚本
        for subdir in ["maintenance", "deployment"]:
            subdir_path = scripts_root / subdir
            if subdir_path.exists():
                for file in subdir_path.glob("week*.py"):
                    dest = archive_dir / subdir / file.name
                    self.move_file(file, dest)

                for file in subdir_path.glob("phase*.py"):
                    dest = archive_dir / subdir / file.name
                    self.move_file(file, dest)

    def add_missing_init_files(self):
        """添加缺失的__init__.py文件"""
        print("\n=== 添加缺失的__init__.py ===\n")

        app_root = PROJECT_ROOT / "app"

        # 需要添加__init__.py的目录
        directories_needing_init = [
            app_root / "ai_core",
            app_root / "ai_core" / "constitutional",
            app_root / "ai_core" / "curriculum",
            app_root / "ai_core" / "rlaif",
            app_root / "retrieval",
            app_root / "monitoring",
            app_root / "services",
            app_root / "agents" / "memory",
            app_root / "agents" / "rl",
            app_root / "agents" / "emotion",
            app_root / "infra" / "llm" / "moe",
        ]

        for directory in directories_needing_init:
            if directory.exists():
                self.create_init_py(directory)

    def clean_duplicates(self):
        """清理重复文件"""
        print("\n=== 清理重复文件 ===\n")

        # 删除README_NEW.md（应该合并到README.md）
        readme_new = PROJECT_ROOT / "README_NEW.md"
        if readme_new.exists():
            self.delete_file(readme_new)

    def rename_files(self):
        """重命名不规范的文件"""
        print("\n=== 重命名文件 ===\n")

        # 重命名app/mcp/orchestrator_enhanced.py
        old_name = PROJECT_ROOT / "app" / "mcp" / "orchestrator_enhanced.py"
        new_name = PROJECT_ROOT / "app" / "mcp" / "dynamic_orchestrator.py"
        if old_name.exists():
            self.move_file(old_name, new_name)

    def create_directory_readmes(self):
        """为主要目录创建README"""
        print("\n=== 创建目录README ===\n")

        readmes = {
            "app/ai_core": "AI Core Components\n\nAdvanced AI algorithms and models.",
            "app/agents": "Agent System\n\nMulti-agent architecture and implementations.",
            "app/infra": "Infrastructure\n\nCore infrastructure components.",
            "docs/guides": "User Guides\n\nStep-by-step guides and tutorials.",
            "docs/reports": "Reports\n\nImplementation reports and progress updates.",
            "docs/architecture": "Architecture Documentation\n\nSystem architecture and design documents.",
        }

        for path, content in readmes.items():
            readme_path = PROJECT_ROOT / path / "README.md"
            if not readme_path.exists():
                self.log_operation("CREATE", str(readme_path))
                if not self.dry_run:
                    readme_path.parent.mkdir(parents=True, exist_ok=True)
                    readme_path.write_text(f"# {content}\n")

    def generate_report(self):
        """生成重组报告"""
        print("\n" + "=" * 60)
        print("重组操作总结")
        print("=" * 60 + "\n")

        action_counts = {}
        for action, _, _ in self.operations:
            action_counts[action] = action_counts.get(action, 0) + 1

        for action, count in sorted(action_counts.items()):
            print(f"{action}: {count} 个操作")

        print(f"\n总计: {len(self.operations)} 个操作")

        if self.dry_run:
            print("\n[WARNING] This is DRY RUN mode, no actual operations were performed")
            print("Add --execute parameter to actually execute the operations")

    def run(self):
        """执行重组"""
        print("=" * 60)
        print("SalesBoost 项目重组")
        print("=" * 60)

        if self.dry_run:
            print("\n[DRY RUN] Mode - Only showing operations, not executing\n")
        else:
            print("\n[EXECUTE] Mode - Will actually modify files\n")

        # 执行各项重组任务
        self.reorganize_docs()
        self.reorganize_scripts()
        self.add_missing_init_files()
        self.clean_duplicates()
        self.rename_files()
        self.create_directory_readmes()

        # 生成报告
        self.generate_report()


def main():
    """主函数"""
    import sys

    # 检查是否为执行模式
    execute = "--execute" in sys.argv

    reorganizer = ProjectReorganizer(dry_run=not execute)
    reorganizer.run()

    if not execute:
        print("\n" + "=" * 60)
        print("To actually execute the reorganization, run:")
        print("python scripts/ops/reorganize_project.py --execute")
        print("=" * 60)


if __name__ == "__main__":
    main()
