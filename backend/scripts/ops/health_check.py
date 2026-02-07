#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Critical Issues Fix Script

修复系统评估中发现的关键问题

Author: Claude (Anthropic)
Date: 2026-02-05
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent


def check_environment_variables():
    """检查必需的环境变量"""
    print("=" * 70)
    print("1. Checking Environment Variables")
    print("=" * 70)
    print()

    required_vars = [
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "GEMINI_API_KEY",
        "DATABASE_URL",
    ]

    missing_vars = []
    dummy_vars = []

    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
            print(f"[MISSING] {var}")
        elif value in ["dummy-key", "your-key-here", "changeme"]:
            dummy_vars.append(var)
            print(f"[DUMMY] {var} = {value}")
        else:
            print(f"[OK] {var} = {value[:10]}...")

    print()

    if missing_vars:
        print(f"[ERROR] Missing {len(missing_vars)} required environment variables")
        print("Please set them in your .env file")
        return False

    if dummy_vars:
        print(f"[WARNING] {len(dummy_vars)} variables have dummy values")
        print("These will cause errors in production")
        return False

    print("[SUCCESS] All environment variables are properly configured")
    return True


def check_authentication_config():
    """检查认证配置"""
    print("=" * 70)
    print("2. Checking Authentication Configuration")
    print("=" * 70)
    print()

    # Check backend auth
    backend_auth = PROJECT_ROOT / "app" / "api" / "endpoints" / "auth.py"
    if backend_auth.exists():
        content = backend_auth.read_text(encoding="utf-8")
        if "OAuth2PasswordRequestForm" in content:
            print("[FOUND] Backend uses FastAPI OAuth2")
            backend_type = "fastapi"
        elif "supabase" in content.lower():
            print("[FOUND] Backend uses Supabase")
            backend_type = "supabase"
        else:
            print("[UNKNOWN] Backend auth type unclear")
            backend_type = "unknown"
    else:
        print("[MISSING] Backend auth file not found")
        backend_type = "missing"

    # Check frontend auth
    frontend_auth = PROJECT_ROOT / "frontend" / "src" / "services" / "auth.service.ts"
    if frontend_auth.exists():
        content = frontend_auth.read_text(encoding="utf-8")
        if "supabase" in content.lower():
            print("[FOUND] Frontend uses Supabase")
            frontend_type = "supabase"
        elif "axios" in content.lower() and "/token" in content:
            print("[FOUND] Frontend uses FastAPI")
            frontend_type = "fastapi"
        else:
            print("[UNKNOWN] Frontend auth type unclear")
            frontend_type = "unknown"
    else:
        print("[MISSING] Frontend auth file not found")
        frontend_type = "missing"

    print()

    if backend_type == frontend_type:
        print(f"[SUCCESS] Auth is unified: {backend_type}")
        return True
    else:
        print(f"[ERROR] Auth mismatch: Backend={backend_type}, Frontend={frontend_type}")
        print()
        print("Recommendation:")
        print("  Option A: Use Supabase for both (recommended for quick setup)")
        print("  Option B: Use FastAPI OAuth2 for both (more control)")
        return False


def check_dead_code():
    """检查废弃代码"""
    print("=" * 70)
    print("3. Checking for Dead Code")
    print("=" * 70)
    print()

    dead_files = [
        "app/engine/coordinator/workflow_planner.py",
        "api/v1/endpoints/sales_coach.py",
    ]

    found_dead = []

    for file_path in dead_files:
        full_path = PROJECT_ROOT / file_path
        if full_path.exists():
            found_dead.append(file_path)
            print(f"[FOUND] Dead code: {file_path}")

    print()

    if found_dead:
        print(f"[WARNING] Found {len(found_dead)} dead code files")
        print("Run with --clean to remove them")
        return False
    else:
        print("[SUCCESS] No dead code found")
        return True


def check_imports():
    """检查关键导入"""
    print("=" * 70)
    print("4. Checking Critical Imports")
    print("=" * 70)
    print()

    try:
        # Test critical imports
        sys.path.insert(0, str(PROJECT_ROOT))

        print("[TEST] Importing app.agents.memory...")
        from app.agents.memory import AgentMemory
        print("[OK] AgentMemory imported")

        print("[TEST] Importing app.agents.rl...")
        from app.agents.rl import PPOPolicy
        print("[OK] PPOPolicy imported")

        print("[TEST] Importing app.ai_core.constitutional...")
        from app.ai_core.constitutional import ConstitutionalAI
        print("[OK] ConstitutionalAI imported")

        print("[TEST] Importing app.infra.llm.moe...")
        from app.infra.llm.moe import MixtureOfExpertsRouter
        print("[OK] MixtureOfExpertsRouter imported")

        print()
        print("[SUCCESS] All critical imports work")
        return True

    except ImportError as e:
        print(f"\n[ERROR] Import failed: {e}")
        return False


def clean_dead_code():
    """清理废弃代码"""
    print("=" * 70)
    print("Cleaning Dead Code")
    print("=" * 70)
    print()

    dead_files = [
        "app/engine/coordinator/workflow_planner.py",
        "api/v1/endpoints/sales_coach.py",
    ]

    removed = []

    for file_path in dead_files:
        full_path = PROJECT_ROOT / file_path
        if full_path.exists():
            full_path.unlink()
            removed.append(file_path)
            print(f"[REMOVED] {file_path}")

    print()

    if removed:
        print(f"[SUCCESS] Removed {len(removed)} dead code files")
    else:
        print("[INFO] No dead code to remove")


def generate_report(results):
    """生成报告"""
    print()
    print("=" * 70)
    print("System Health Check Summary")
    print("=" * 70)
    print()

    total_checks = len(results)
    passed_checks = sum(1 for r in results.values() if r)

    for check_name, passed in results.items():
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status} {check_name}")

    print()
    print(f"Score: {passed_checks}/{total_checks} checks passed")
    print()

    if passed_checks == total_checks:
        print("[SUCCESS] System is healthy!")
        return 0
    else:
        print("[WARNING] System has issues that need attention")
        print()
        print("See docs/reports/system-health-assessment.md for details")
        return 1


def main():
    """主函数"""
    print("=" * 70)
    print("SalesBoost System Health Check")
    print("=" * 70)
    print()

    # Check for --clean flag
    clean_mode = "--clean" in sys.argv

    if clean_mode:
        clean_dead_code()
        return

    # Run checks
    results = {
        "Environment Variables": check_environment_variables(),
        "Authentication Config": check_authentication_config(),
        "Dead Code": check_dead_code(),
        "Critical Imports": check_imports(),
    }

    # Generate report
    exit_code = generate_report(results)

    if not results["Dead Code"]:
        print()
        print("To remove dead code, run:")
        print("python scripts/ops/health_check.py --clean")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
