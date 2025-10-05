# setup_streamlit.py
import os
import shutil
import subprocess
import sys
import argparse

def create_directory_structure():
    """Create necessary directories."""
    directories = [
        'data',
        'backend',
        '.streamlit'
    ]
    
    for dir_name in directories:
        os.makedirs(dir_name, exist_ok=True)
        print(f"✅ Created directory: {dir_name}")

def create_secrets_template():
    """Create secrets template file."""
    secrets_content = '''# .streamlit/secrets.toml
# This file is used by Streamlit Cloud to set environment variables securely.
# In your code, load it using os.environ or st.secrets.
GEMINI_API_KEY = "YOUR_API_KEY_HERE"
'''
    
    secrets_path = '.streamlit/secrets.toml'
    if not os.path.exists(secrets_path):
        with open(secrets_path, 'w') as f:
            f.write(secrets_content)
        print(f"✅ Created secrets template: {secrets_path}")
    else:
        print(f"⚠️  Secrets file already exists: {secrets_path}")

def create_gitignore():
    """Create .gitignore file."""
    gitignore_content = '''# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
venv/
.env

# Streamlit/Data
.streamlit/secrets.toml
data/people.csv
data/people.sqlite
data/chroma_db/
.st-secrets.toml

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db
'''
    
    if not os.path.exists('.gitignore'):
        with open('.gitignore', 'w') as f:
            f.write(gitignore_content)
        print("✅ Created .gitignore")
    else:
        print("⚠️  .gitignore already exists")

def main():
    """Main setup function."""
    print("🚀 Setting up Streamlit RAG App...")
    
    # Create directories
    create_directory_structure()
    
    # Create secrets template
    create_secrets_template()
    
    # Create gitignore
    create_gitignore()
    
    print("\n🎉 Setup complete!")
    print("\n📝 Next steps:")
    print("1. **Crucial:** Add your `GEMINI_API_KEY` to **`.streamlit/secrets.toml`** or your environment variables.")
    print("2. Run the data pipeline locally (this generates the `data/` folder): `python indexing.py`")
    print("3. Test locally: `streamlit run streamlit_app.py`")

if __name__ == "__main__":
    main()