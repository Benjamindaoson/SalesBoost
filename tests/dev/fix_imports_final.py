#!/usr/bin/env python3
"""
最终修复 import 路径和目录结构
"""
import shutil
import re
from pathlib import Path

def fix_providers_structure():
    """修复 providers 目录结构"""
    providers_nested = Path('app/infra/providers/providers')
    providers_target = Path('app/infra/providers')
    
    if providers_nested.exists():
        for item in providers_nested.iterdir():
            if item.name != '__pycache__':
                shutil.move(str(item), str(providers_target / item.name))
        try:
            providers_nested.rmdir()
        except:
            pass
        print("Fixed providers structure")

def fix_gateway_structure():
    """修复 gateway 目录结构"""
    gateway_nested = Path('app/infra/gateway/model_gateway')
    gateway_target = Path('app/infra/gateway')
    
    if gateway_nested.exists():
        for item in gateway_nested.iterdir():
            if item.name != '__pycache__' and item.name != 'providers':
                target = gateway_target / item.name
                if target.exists():
                    # 如果目标已存在，跳过
                    continue
                shutil.move(str(item), str(target))
        try:
            gateway_nested.rmdir()
        except:
            pass
        print("Fixed gateway structure")

# 更完整的 import 映射
IMPORT_FIXES = [
    # Gateway 相关
    (r'from app\.infra\.gateway\.model_gateway\.', 'from cognitive.infra.gateway.'),
    (r'from app\.infra\.gateway\.providers\.', 'from cognitive.infra.providers.'),
    (r'from app\.infra\.gateway\.model_gateway import', 'from cognitive.infra.gateway import'),
    (r'import app\.infra\.gateway\.model_gateway', 'import app.infra.gateway'),
    
    # Providers
    (r'from app\.infra\.providers\.providers\.', 'from cognitive.infra.providers.'),
    
    # 其他修复
    (r'from app\.services\.state_recovery', 'from cognitive.brain.state.recovery'),
    (r'from app\.observability\.tracing import trace_manager', 'from cognitive.observability.tracing.execution_tracer import trace_manager'),
]

def fix_file_imports(file_path: Path):
    """修复单个文件的 import"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original = content
        for pattern, replacement in IMPORT_FIXES:
            content = re.sub(pattern, replacement, content)
        
        if content != original:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False
    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
        return False

def main():
    """主函数"""
    # 1. 修复目录结构
    fix_providers_structure()
    fix_gateway_structure()
    
    # 2. 修复所有文件的 import
    app_dir = Path('app')
    updated = 0
    
    for py_file in app_dir.rglob('*.py'):
        if fix_file_imports(py_file):
            updated += 1
    
    print(f"\nFixed {updated} files")

if __name__ == '__main__':
    main()
