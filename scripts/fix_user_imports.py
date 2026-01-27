import os

def fix_user_imports(directory):
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Replace 'from api.endpoints.auth import User'
                new_content = content.replace(
                    'from api.endpoints.auth import User', 
                    'from api.auth_schemas import UserSchema as User'
                )
                
                # Also handle cases where it might be 'from api.endpoints.auth import User, ...'
                if 'from api.endpoints.auth import' in new_content and 'User' in new_content:
                    import re
                    new_content = re.sub(
                        r'from api\.endpoints\.auth import (.*)User(.*)',
                        r'from api.auth_schemas import UserSchema as User\nfrom api.endpoints.auth import \1\2',
                        new_content
                    )
                    # Clean up empty imports
                    new_content = re.sub(r'from api\.endpoints\.auth import \s*\n', '', new_content)

                if content != new_content:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    print(f"Fixed imports in: {file_path}")

if __name__ == "__main__":
    fix_user_imports('api')
