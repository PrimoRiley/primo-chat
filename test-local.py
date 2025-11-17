#!/usr/bin/env python3
"""
Local Development Test Script
Tests core functionality of the RAG system locally
"""

import os
import sys
import sqlite3
from pathlib import Path

def test_environment():
    """Test environment variables and configuration."""
    print("🔧 Testing Environment Configuration...")
    
    required_vars = ['ORGANIZATION_NAME', 'OPENAI_API_KEY']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        return False
    
    print("✅ Environment configuration looks good!")
    return True

def test_dependencies():
    """Test that required packages are installed."""
    print("📦 Testing Dependencies...")
    
    required_packages = [
        'chainlit',
        'openai', 
        'sqlite3'  # Built into Python
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            if package == 'sqlite3':
                import sqlite3
            else:
                __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Missing packages: {', '.join(missing_packages)}")
        print("Run: pip install -r requirements.txt")
        return False
    
    print("✅ All dependencies are installed!")
    return True

def test_database():
    """Test SQLite database creation and operations."""
    print("🗄️ Testing Database Operations...")
    
    try:
        # Import our database module
        sys.path.append(os.path.dirname(__file__))
        from database import ChatDatabase
        
        # Create test database
        db = ChatDatabase("test-local")
        
        # Test basic operations
        db.create_chat_session("test-session", "test-user")
        db.save_message("test-session", "user", "Test message")
        
        # Verify data
        stats = db.get_stats()
        assert stats['sessions'] >= 1
        assert stats['messages'] >= 1
        
        print("✅ Database operations working correctly!")
        return True
        
    except Exception as e:
        print(f"❌ Database test failed: {str(e)}")
        return False

def test_config():
    """Test configuration module."""
    print("⚙️ Testing Configuration Module...")
    
    try:
        from config import config
        
        # Test basic config properties
        assert config.organization_name
        assert config.openai_api_key
        assert config.is_configured
        
        print(f"✅ Configuration loaded for: {config.organization_name}")
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {str(e)}")
        return False

def test_openai_connection():
    """Test OpenAI API connection."""
    print("🤖 Testing OpenAI Connection...")
    
    try:
        from openai import OpenAI
        from config import config
        
        if not config.openai_api_key or config.openai_api_key == "your-openai-api-key-here":
            print("❌ OpenAI API key not set in .env file")
            return False
        
        client = OpenAI(api_key=config.openai_api_key)
        
        # Test API connection with a simple call
        try:
            models = client.models.list()
            print("✅ OpenAI API connection successful!")
            return True
        except Exception as api_error:
            print(f"❌ OpenAI API error: {str(api_error)}")
            print("Check your OPENAI_API_KEY in .env file")
            return False
        
    except Exception as e:
        print(f"❌ OpenAI connection test failed: {str(e)}")
        return False

def test_data_directory():
    """Test data directory creation and permissions."""
    print("📁 Testing Data Directory...")
    
    data_dir = Path("./data")
    
    try:
        # Create directory if it doesn't exist
        data_dir.mkdir(exist_ok=True)
        
        # Test write permissions
        test_file = data_dir / "test.txt"
        test_file.write_text("test")
        test_file.unlink()  # Delete test file
        
        print("✅ Data directory is accessible!")
        return True
        
    except Exception as e:
        print(f"❌ Data directory test failed: {str(e)}")
        return False

def run_all_tests():
    """Run all tests and return overall result."""
    print("🧪 Running Local Development Tests...\n")
    
    tests = [
        test_environment,
        test_dependencies,
        test_data_directory,
        test_config,
        test_database,
        test_openai_connection
    ]
    
    results = []
    
    for test in tests:
        try:
            result = test()
            results.append(result)
            print()
        except Exception as e:
            print(f"❌ Test failed with exception: {str(e)}\n")
            results.append(False)
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print("=" * 50)
    print(f"Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All tests passed! Your local environment is ready!")
        print("\nNext steps:")
        print("1. Run: chainlit run app.py")
        print("2. Open: http://localhost:8000")
        print("3. Upload some documents and start chatting!")
        return True
    else:
        print("❌ Some tests failed. Please fix the issues above.")
        return False

if __name__ == "__main__":
    # Load environment variables if .env file exists
    env_file = Path(".env")
    if env_file.exists():
        from dotenv import load_dotenv
        load_dotenv()
    
    success = run_all_tests()
    sys.exit(0 if success else 1)