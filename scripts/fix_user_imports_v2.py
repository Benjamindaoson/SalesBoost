import os
import re

def fix_imports_v2(directory):
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Case 1: from api.auth_schemas import UserSchema as User, get_current_user_from_token
                new_content = re.sub(
                    r'from api\.auth_schemas import UserSchema as User,\s*get_current_user_from_token',
                    r'from api.auth_schemas import UserSchema as User\nfrom api.auth_utils import get_current_user_from_token',
                    content
                )
                
                # Case 2: from api.auth_schemas import UserSchema as User, verify_password, ...
                new_content = re.sub(
                    r'from api\.auth_schemas import UserSchema as User,\s*(.*)',
                    r'from api.auth_schemas import UserSchema as User\nfrom api.auth_utils import \1',
                    new_content
                )

                if content != new_content:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    print(f"Fixed imports in: {file_path}")

if __name__ == "__main__":
    fix_imports_v2('api')
