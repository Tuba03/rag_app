# setup_streamlit.py
import os
import shutil
import subprocess
import sys

def create_directory_structure():
    """Create necessary directories."""
    directories = [
        'data',
        '.streamlit'
    ]
    
    for dir_name in directories:
        os.makedirs(dir_name, exist_ok=True)
        print(f"✅ Created directory: {dir_name}")

def create_secrets_template():
    """Create secrets template file."""
    secrets_content = '''# .streamlit/secrets.toml'''
    
    secrets_path = '.streamlit/secrets.toml'
    if not os.path.exists(secrets_path):
        with open(secrets_path, 'w') as f:
            f.write(secrets_content)
        print(f"✅ Created secrets template: {secrets_path}")
    else:
        print(f"⚠️  Secrets file already exists: {secrets_path}")

def check_and_generate_data():
    """Check if data exists, generate if needed."""
    data_files = [
        'data/people.csv',
        'data/people.sqlite',
        'data/chroma_db'
    ]
    
    missing_files = [f for f in data_files if not os.path.exists(f)]
    
    if missing_files:
        print("⚠️  Missing data files. Generating now...")
        
        # Run data generator
        if os.path.exists('data_generator.py'):
            print("🔄 Running data_generator.py...")
            subprocess.run([sys.executable, 'data_generator.py'])
        elif os.path.exists('function/data_generator.py'):
            print("🔄 Running function/data_generator.py...")
            subprocess.run([sys.executable, 'function/data_generator.py'])
        else:
            print("❌ data_generator.py not found!")
            return False
        
        # Run indexing
        if os.path.exists('indexing.py'):
            print("🔄 Running indexing.py...")
            subprocess.run([sys.executable, 'indexing.py'])
        elif os.path.exists('src/indexing.py'):
            print("🔄 Running function/indexing.py...")
            subprocess.run([sys.executable, 'function/indexing.py'])
        else:
            print("❌ indexing.py not found!")
            return False
    else:
        print("✅ All data files exist")
    
    return True

def install_streamlit_requirements():
    """Install Streamlit requirements."""
    requirements = [
        "streamlit==1.28.1",
        "pandas",
        "langchain",
        "langchain-community", 
        "langchain-google-genai",
        "chromadb",
        "sentence-transformers",
        "sqlite-utils",
        "python-dotenv"
    ]
    
    print("🔄 Installing Streamlit requirements...")
    for req in requirements:
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", req], 
                         check=True, capture_output=True)
            print(f"✅ Installed: {req}")
        except subprocess.CalledProcessError:
            print(f"⚠️  Failed to install: {req}")

def create_gitignore():
    """Create .gitignore file."""
    gitignore_content = '''# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
env/
venv/
.env

# Streamlit
.streamlit/secrets.toml

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
    
    # Install requirements
    install_streamlit_requirements()
    
    # Check/generate data
    if not check_and_generate_data():
        print("❌ Data generation failed. Please fix and try again.")
        return
    
    print("\n🎉 Setup complete!")
    print("\n📝 Next steps:")
    print("1. Add your GEMINI_API_KEY to .streamlit/secrets.toml")
    print("2. Test locally: streamlit run streamlit_app.py")
    print("3. Commit to GitHub and deploy on Streamlit Cloud")
    print("\n🔗 Deployment guide: https://docs.streamlit.io/streamlit-community-cloud")

if __name__ == "__main__":
    main()