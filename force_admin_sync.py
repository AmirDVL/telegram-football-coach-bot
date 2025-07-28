#!/usr/bin/env python3
"""
Force Admin Sync Script
This script forces a complete re-sync of admin IDs from environment variables
Use this on the server to fix admin recognition issues
"""

import os
import json
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def force_admin_sync():
    """Force sync all admins from environment variables"""
    
    # Import after loading .env
    from config import Config
    from data_manager import DataManager
    
    print("🔄 Force Admin Sync Starting...")
    print(f"📋 Environment Variables:")
    print(f"   ADMIN_ID: {os.getenv('ADMIN_ID')}")
    print(f"   ADMIN_IDS: {os.getenv('ADMIN_IDS')}")
    
    # Get admin IDs from config
    admin_ids = Config.get_admin_ids()
    print(f"🎯 Parsed Admin IDs: {admin_ids}")
    
    if not admin_ids:
        print("❌ No admin IDs found in configuration!")
        return False
    
    # Initialize data manager
    dm = DataManager()
    
    try:
        # Load current data
        print("📂 Loading current bot data...")
        bot_data = await dm.load_data()
        
        # Clear existing admin data completely
        print("🧹 Clearing existing admin data...")
        if 'admins' in bot_data:
            old_admins = list(bot_data['admins'].keys())
            print(f"   Removing old admins: {old_admins}")
            bot_data['admins'] = {}
        else:
            bot_data['admins'] = {}
        
        # Add all admins from config
        print("➕ Adding new admins from config...")
        for admin_id in admin_ids:
            bot_data['admins'][str(admin_id)] = {
                'user_id': admin_id,
                'permissions': 'full',
                'added_at': '2025-07-28T18:50:00.000000',
                'synced_from_config': True,
                'force_synced': True
            }
            print(f"   ✅ Added admin: {admin_id}")
        
        # Save updated data
        print("💾 Saving updated data...")
        async with __import__('aiofiles').open(dm.data_file, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(bot_data, ensure_ascii=False, indent=2))
        
        print("🎉 Force admin sync completed successfully!")
        print(f"📊 Total admins synced: {len(admin_ids)}")
        
        # Verify the sync
        print("🔍 Verifying admin sync...")
        for admin_id in admin_ids:
            is_admin = await dm.is_admin(admin_id)
            status = "✅ SUCCESS" if is_admin else "❌ FAILED"
            print(f"   Admin {admin_id}: {status}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during force sync: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(force_admin_sync())
    exit(0 if success else 1)
