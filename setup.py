#!/usr/bin/env python3
"""
Setup script for Delivery Executive Chatbot
"""

import os
import sys
import subprocess

def main():
    print("🚀 Delivery Executive Chatbot - Project Setup")
    print("="*50)
    
    # Check Python version
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 3.8 or higher is required")
        print(f"Current version: {version.major}.{version.minor}.{version.micro}")
        return False
    print(f"✅ Python version {version.major}.{version.minor}.{version.micro} is compatible")
    
    # Check if required files exist
    required_files = [
        'requirements.txt',
        '.env',
        'database.py',
        'models.py',
        'schemas.py',
        'main.py'
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ Missing required files: {', '.join(missing_files)}")
        return False
    
    print("✅ All basic files found")
    
    # Try to install dependencies
    try:
        print("🔄 Installing Python dependencies...")
        result = subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], 
                              check=True, capture_output=True, text=True)
        print("✅ Dependencies installed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False
    
    print("\n🎉 Basic setup completed!")
    print("Next steps:")
    print("1. Make sure your .env file has your Claude API key")
    print("2. Run: python create_database.py")
    print("3. Run: python main.py")
    
    return True

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Setup failed with error: {e}")
        import traceback
        traceback.print_exc()