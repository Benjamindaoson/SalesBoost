import os
import re

def fix_imports(directory):
    replacements = {
        r'app\.brain\b': 'app.engine',
        r'app\.skills\b': 'app.agents',
        r'from app\.brain\b': 'from app.engine',
        r'from app\.skills\b': 'from app.agents',
        r'import app\.brain\b': 'import app.engine',
        r'import app\.skills\b': 'import app.agents',
    }
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                new_content = content
                for pattern, replacement in replacements.items():
                    new_content = re.sub(pattern, replacement, new_content)

                if content != new_content:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    print(f"Updated: {file_path}")

if __name__ == "__main__":
    fix_imports('app')
    fix_imports('api')
    # Also update main.py
    with open('main.py', 'r', encoding='utf-8') as f:
        content = f.read()
    new_content = content
    replacements = {
        r'app\.brain\b': 'app.engine',
        r'app\.skills\b': 'app.agents',
    }
    for pattern, replacement in replacements.items():
        new_content = re.sub(pattern, replacement, new_content)
    if content != new_content:
        with open('main.py', 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("Updated: main.py")
