#!/usr/bin/env python3
"""
Environment Diagnostic Script
This script helps debug environment variable issues on the server
"""

import os
from dotenv import load_dotenv

def diagnose_environment():
    """Diagnose environment variable loading issues"""
    
    print("🔍 Environment Variable Diagnostic")
    print("=" * 50)
    
    # Check if .env file exists
    env_file = '.env'
    if os.path.exists(env_file):
        print(f"✅ .env file found: {os.path.abspath(env_file)}")
        
        # Read .env file content
        print("\n📄 .env file contents:")
        print("-" * 30)
        with open(env_file, 'r') as f:
            lines = f.readlines()
            for i, line in enumerate(lines, 1):
                print(f"{i:2d}: {line.rstrip()}")
        print("-" * 30)
    else:
        print(f"❌ .env file NOT found at: {os.path.abspath(env_file)}")
        return False
    
    # Check environment variables BEFORE loading .env
    print("\n🔍 Environment variables BEFORE loading .env:")
    print(f"   ADMIN_ID: {os.getenv('ADMIN_ID')}")
    print(f"   ADMIN_IDS: {os.getenv('ADMIN_IDS')}")
    print(f"   BOT_TOKEN: {'***HIDDEN***' if os.getenv('BOT_TOKEN') else 'None'}")
    
    # Load .env file
    print("\n🔄 Loading .env file...")
    load_dotenv()
    
    # Check environment variables AFTER loading .env
    print("\n✅ Environment variables AFTER loading .env:")
    admin_id = os.getenv('ADMIN_ID')
    admin_ids = os.getenv('ADMIN_IDS')
    bot_token = os.getenv('BOT_TOKEN')
    
    print(f"   ADMIN_ID: {admin_id}")
    print(f"   ADMIN_IDS: {admin_ids}")
    print(f"   BOT_TOKEN: {'***HIDDEN***' if bot_token else 'None'}")
    
    # Test Config class
    print("\n🧪 Testing Config class:")
    try:
        from config import Config
        print(f"   Config.ADMIN_ID: {Config.ADMIN_ID}")
        admin_ids_parsed = Config.get_admin_ids()
        print(f"   Config.get_admin_ids(): {admin_ids_parsed}")
        print(f"   Number of admins: {len(admin_ids_parsed)}")
        
        if len(admin_ids_parsed) == 1:
            print("⚠️  WARNING: Only 1 admin found. Expected 3 admins!")
            print("   This suggests ADMIN_IDS is not being read correctly.")
        elif len(admin_ids_parsed) == 3:
            print("✅ SUCCESS: All 3 admins found!")
        else:
            print(f"❓ Unexpected number of admins: {len(admin_ids_parsed)}")
            
    except Exception as e:
        print(f"❌ Error loading Config: {e}")
        import traceback
        traceback.print_exc()
    
    # Recommendations
    print("\n💡 Recommendations:")
    if admin_ids is None:
        print("   1. Add ADMIN_IDS line to .env file")
        print("   2. Make sure there are no extra spaces or special characters")
        print("   3. Restart the application after changes")
    elif admin_ids and ',' in admin_ids:
        print("   ✅ ADMIN_IDS appears to be correctly formatted")
    elif admin_ids:
        print("   ⚠️  ADMIN_IDS found but no commas - check if it contains multiple IDs")
    
    return True

if __name__ == "__main__":
    diagnose_environment()
