"""
Setup Script for Autism Support App
Helps users get the system up and running quickly.
"""

import os
import sys
import subprocess
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible."""
    print("🔍 Checking Python version...")
    version = sys.version_info
    if version.major == 3 and version.minor >= 8:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} - Compatible")
        return True
    else:
        print(f"❌ Python {version.major}.{version.minor}.{version.micro} - Requires Python 3.8+")
        return False

def install_dependencies():
    """Install required dependencies."""
    print("\n📦 Installing dependencies...")
    
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def create_directories():
    """Create required directories."""
    print("\n📁 Creating directories...")
    
    directories = [
        "data/admin_uploaded_docs",
        "data/user_docs",
        "data/processed_admin_docs",
        "app/services",
        "retrieval"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✅ Created: {directory}")

def check_streamlit_secrets():
    """Check if Streamlit secrets are configured."""
    print("\n🔐 Checking Streamlit configuration...")
    
    secrets_file = Path(".streamlit/secrets.toml")
    if secrets_file.exists():
        print("✅ Streamlit secrets file found")
        return True
    else:
        print("⚠️ Streamlit secrets file not found")
        print("   Create .streamlit/secrets.toml with your API keys:")
        print("   [secrets]")
        print("   OPENAI_API_KEY = 'your-openai-api-key'")
        print("   ADMIN_PASSWORD = 'your-admin-password'")
        return False

def check_qdrant():
    """Check if Qdrant is available."""
    print("\n🔍 Checking Qdrant availability...")
    
    try:
        from rag.qdrant_client import get_qdrant
        qdr = get_qdrant()
        if qdr:
            print("✅ Qdrant is running and accessible")
            return True
        else:
            print("⚠️ Qdrant is not running")
            print("   To start Qdrant, run: docker run -p 6333:6333 qdrant/qdrant")
            return False
    except Exception as e:
        print(f"❌ Qdrant check failed: {e}")
        return False

def run_tests():
    """Run system integration tests."""
    print("\n🧪 Running system tests...")
    
    try:
        result = subprocess.run([sys.executable, "test_system_integration.py"], 
                              capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("Errors:", result.stderr)
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        return False

def ingest_knowledge_base():
    """Ingest the knowledge base into Qdrant."""
    print("\n📚 Ingesting knowledge base...")
    
    try:
        from rag.ingest_shared_kb import main as ingest_main
        if ingest_main():
            print("✅ Knowledge base ingested successfully")
            return True
        else:
            print("❌ Knowledge base ingestion failed")
            return False
    except Exception as e:
        print(f"❌ Knowledge base ingestion error: {e}")
        return False

def main():
    """Main setup function."""
    print("🚀 Autism Support App Setup")
    print("=" * 50)
    
    # Check Python version
    if not check_python_version():
        return False
    
    # Install dependencies
    if not install_dependencies():
        return False
    
    # Create directories
    create_directories()
    
    # Check Streamlit secrets
    secrets_ok = check_streamlit_secrets()
    
    # Check Qdrant
    qdrant_ok = check_qdrant()
    
    # Run tests
    tests_ok = run_tests()
    
    # Ingest knowledge base if Qdrant is available
    if qdrant_ok:
        ingest_knowledge_base()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 SETUP SUMMARY")
    print("=" * 50)
    
    print(f"✅ Python version: Compatible")
    print(f"✅ Dependencies: Installed")
    print(f"✅ Directories: Created")
    print(f"{'✅' if secrets_ok else '❌'} Streamlit secrets: {'Configured' if secrets_ok else 'Missing'}")
    print(f"{'✅' if qdrant_ok else '⚠️'} Qdrant: {'Running' if qdrant_ok else 'Not running'}")
    print(f"{'✅' if tests_ok else '❌'} System tests: {'Passed' if tests_ok else 'Failed'}")
    
    print("\n🎯 Next Steps:")
    if not secrets_ok:
        print("1. Configure Streamlit secrets (.streamlit/secrets.toml)")
    if not qdrant_ok:
        print("2. Start Qdrant: docker run -p 6333:6333 qdrant/qdrant")
    print("3. Run the app: streamlit run app.py")
    
    return secrets_ok and tests_ok

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
