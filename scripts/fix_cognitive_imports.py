import os
import re

def replace_cognitive_with_app(directory):
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Replace 'cognitive.' with 'app.'
                new_content = content.replace('cognitive.', 'app.')
                
                # Also replace 'from cognitive import' with 'from app import'
                new_content = re.sub(r'from cognitive\b', 'from app', new_content)
                new_content = re.sub(r'import cognitive\b', 'import app', new_content)

                if content != new_content:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    print(f"Updated: {file_path}")

if __name__ == "__main__":
    replace_cognitive_with_app('app')
    replace_cognitive_with_app('api')
    # Also update main.py
    with open('main.py', 'r', encoding='utf-8') as f:
        content = f.read()
    new_content = content.replace('cognitive.', 'app.')
    new_content = re.sub(r'from cognitive\b', 'from app', new_content)
    if content != new_content:
        with open('main.py', 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("Updated: main.py")
