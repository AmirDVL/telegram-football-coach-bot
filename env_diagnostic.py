#!/usr/bin/env python3
"""
Environment Diagnostic Script
Use this on the server to diagnose .env file issues
"""

import os
import sys
from pathlib import Path

def diagnose_env_file():
    """Diagnose .env file loading issues"""
    
    print("🔍 Environment Diagnostic Starting...")
    print(f"📂 Working Directory: {os.getcwd()}")
    print(f"🐍 Python Executable: {sys.executable}")
    print(f"📄 Script Location: {__file__}")
    
    # Check if .env file exists
    env_files = ['.env', './.env', '/opt/football-bot/.env']
    
    for env_path in env_files:
        if os.path.exists(env_path):
            print(f"✅ Found .env file: {os.path.abspath(env_path)}")
            
            # Read the file contents
            try:
                with open(env_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                print(f"📝 File contents ({len(content)} chars):")
                print("-" * 50)
                print(content)
                print("-" * 50)
                
                # Check specific lines
                lines = content.strip().split('\n')
                for i, line in enumerate(lines, 1):
                    if 'ADMIN_IDS' in line:
                        print(f"🎯 Line {i}: {repr(line)}")
                        
                        # Check for hidden characters
                        if line.strip():
                            clean_line = ''.join(c if ord(c) < 128 else f'\\x{ord(c):02x}' for c in line)
                            if clean_line != line:
                                print(f"⚠️  Hidden chars detected: {clean_line}")
                
            except Exception as e:
                print(f"❌ Error reading file: {e}")
        else:
            print(f"❌ Not found: {env_path}")
    
    print("\n🌍 Raw Environment Variables:")
    for key in sorted(os.environ.keys()):
        if 'ADMIN' in key or 'BOT' in key:
            value = os.environ[key]
            # Hide sensitive parts of bot token
            if 'BOT_TOKEN' in key and len(value) > 10:
                value = value[:10] + "..." + value[-5:]
            print(f"   {key}={repr(value)}")
    
    print("\n📦 Testing dotenv loading...")
    try:
        from dotenv import load_dotenv
        result = load_dotenv()
        print(f"   load_dotenv() result: {result}")
        
        # Test specific variables after loading
        print(f"   ADMIN_ID after dotenv: {repr(os.getenv('ADMIN_ID'))}")
        print(f"   ADMIN_IDS after dotenv: {repr(os.getenv('ADMIN_IDS'))}")
        
    except ImportError:
        print("   ❌ python-dotenv not installed")
    except Exception as e:
        print(f"   ❌ Error loading dotenv: {e}")
    
    print("\n🔧 Testing Config class...")
    try:
        from config import Config
        admin_ids = Config.get_admin_ids()
        print(f"   Config.get_admin_ids(): {admin_ids}")
        print(f"   Config.ADMIN_ID: {getattr(Config, 'ADMIN_ID', 'NOT_SET')}")
        
    except Exception as e:
        print(f"   ❌ Error with Config: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    diagnose_env_file()
