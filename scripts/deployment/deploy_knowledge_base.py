#!/usr/bin/env python3
"""
Knowledge Base Deployment Script
Automated deployment and verification

Usage:
    python scripts/deploy_knowledge_base.py --env production
    python scripts/deploy_knowledge_base.py --env development --skip-data
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class KnowledgeBaseDeployer:
    """Automated knowledge base deployment"""

    def __init__(self, environment: str = "development", skip_data: bool = False):
        self.environment = environment
        self.skip_data = skip_data
        self.deployment_log = []

    def log(self, message: str, level: str = "INFO"):
        """Log deployment message"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"
        self.deployment_log.append(log_entry)
        print(log_entry)

    def run_command(self, command: str, description: str) -> bool:
        """Run shell command and log result"""
        self.log(f"Running: {description}")
        self.log(f"Command: {command}", "DEBUG")

        try:
            result = subprocess.run(
                command,
                shell=True,
                check=True,
                capture_output=True,
                text=True
            )

            if result.stdout:
                self.log(result.stdout.strip(), "DEBUG")

            self.log(f"[OK] {description} completed", "SUCCESS")
            return True

        except subprocess.CalledProcessError as e:
            self.log(f"[X] {description} failed: {e}", "ERROR")
            if e.stderr:
                self.log(e.stderr.strip(), "ERROR")
            return False

    def check_prerequisites(self) -> bool:
        """Check deployment prerequisites"""
        self.log("=== Checking Prerequisites ===")

        checks = [
            ("python --version", "Python installation"),
            ("pip --version", "Pip installation"),
        ]

        all_passed = True
        for command, description in checks:
            if not self.run_command(command, f"Check {description}"):
                all_passed = False

        # Check required directories
        required_dirs = [
            "data/databases",
            "storage/chromadb",
            "data/processed",
            "storage/generated_data",
            "data/seeds"
        ]

        for directory in required_dirs:
            dir_path = Path(directory)
            if not dir_path.exists():
                self.log(f"Creating directory: {directory}")
                dir_path.mkdir(parents=True, exist_ok=True)

        return all_passed

    def install_dependencies(self) -> bool:
        """Install Python dependencies"""
        self.log("=== Installing Dependencies ===")

        return self.run_command(
            "pip install -r config/python/requirements.txt",
            "Install Python packages"
        )

    def setup_environment(self) -> bool:
        """Setup environment"""
        self.log("=== Setting Up Environment ===")

        return self.run_command(
            "python scripts/setup_local_environment.py",
            "Initialize SQLite and ChromaDB"
        )

    def process_data(self) -> bool:
        """Process sales data"""
        if self.skip_data:
            self.log("Skipping data processing (--skip-data flag)")
            return True

        self.log("=== Processing Sales Data ===")

        steps = [
            ("python scripts/process_sales_data.py", "Process sales data"),
            ("python scripts/smart_chunking.py", "Create semantic chunks"),
            ("python scripts/create_agent_interface.py", "Create agent interface"),
        ]

        for command, description in steps:
            if not self.run_command(command, description):
                return False

        return True

    def verify_deployment(self) -> bool:
        """Verify deployment"""
        self.log("=== Verifying Deployment ===")

        # Check if key files exist
        required_files = [
            "data/databases/salesboost_local.db",
            "data/processed/semantic_chunks.json",
            "data/processed/agent_interface_config.json",
        ]

        all_exist = True
        for file_path in required_files:
            if Path(file_path).exists():
                self.log(f"[OK] Found: {file_path}", "SUCCESS")
            else:
                self.log(f"[X] Missing: {file_path}", "ERROR")
                all_exist = False

        # Test knowledge integration
        if all_exist:
            return self.run_command(
                "python app/knowledge_integration.py",
                "Test knowledge integration"
            )

        return all_exist

    def save_deployment_log(self):
        """Save deployment log to file"""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        log_file = log_dir / f"deployment_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

        with open(log_file, 'w', encoding='utf-8') as f:
            f.write("\n".join(self.deployment_log))

        self.log(f"Deployment log saved to: {log_file}")

    def deploy(self) -> bool:
        """Execute full deployment"""
        self.log("="*70)
        self.log(f"Knowledge Base Deployment - {self.environment.upper()}")
        self.log("="*70)

        steps = [
            ("Prerequisites", self.check_prerequisites),
            ("Dependencies", self.install_dependencies),
            ("Environment", self.setup_environment),
            ("Data Processing", self.process_data),
            ("Verification", self.verify_deployment),
        ]

        for step_name, step_func in steps:
            self.log(f"\n{'='*70}")
            self.log(f"Step: {step_name}")
            self.log(f"{'='*70}")

            if not step_func():
                self.log(f"[X] Deployment failed at step: {step_name}", "ERROR")
                self.save_deployment_log()
                return False

        self.log("\n" + "="*70)
        self.log("[OK] Deployment completed successfully!", "SUCCESS")
        self.log("="*70)

        self.save_deployment_log()
        return True


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Deploy SalesBoost Knowledge Base")

    parser.add_argument(
        "--env",
        choices=["development", "production"],
        default="development",
        help="Deployment environment"
    )

    parser.add_argument(
        "--skip-data",
        action="store_true",
        help="Skip data processing (use existing data)"
    )

    args = parser.parse_args()

    deployer = KnowledgeBaseDeployer(
        environment=args.env,
        skip_data=args.skip_data
    )

    success = deployer.deploy()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
