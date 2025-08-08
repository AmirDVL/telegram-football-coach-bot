#!/usr/bin/env python3
"""
Manual admin sync fix - clean up the admins.json based on environment variables
"""

import json
import asyncio
from datetime import datetime
from config import Config
from data_manager import DataManager

async def manual_admin_sync():
    """Manually sync admins to fix the issue"""
    print("🔧 MANUAL ADMIN SYNC STARTING\n")
    
    # Get admin IDs from environment
    admin_ids = Config.get_admin_ids()
    config_super_admin = Config.ADMIN_ID
    
    print(f"📋 Environment Admin IDs: {admin_ids}")
    print(f"👤 Super Admin: {config_super_admin}")
    
    # Initialize data manager
    data_manager = DataManager()
    
    # Load current admins
    admins_data = await data_manager.load_data('admins')
    
    print(f"\n📄 Current admins.json:")
    print(f"   Super Admin: {admins_data.get('super_admin')}")
    print(f"   Admins: {admins_data.get('admins', [])}")
    
    # Create new clean structure
    new_admins_data = {
        'super_admin': config_super_admin,
        'admins': admin_ids.copy(),
        'admin_permissions': {}
    }
    
    # Add permissions for each admin
    for admin_id in admin_ids:
        is_super = (admin_id == config_super_admin)
        new_admins_data['admin_permissions'][str(admin_id)] = {
            'can_add_admins': is_super,
            'can_remove_admins': is_super,
            'can_view_users': True,
            'can_manage_payments': True,
            'is_super_admin': is_super,
            'added_by': 'manual_sync',
            'added_date': datetime.now().isoformat(),
            'synced_from_config': True
        }
    
    print(f"\n✅ New structure:")
    print(f"   Super Admin: {new_admins_data['super_admin']}")
    print(f"   Admins: {new_admins_data['admins']}")
    print(f"   Permissions Count: {len(new_admins_data['admin_permissions'])}")
    
    # Save the new structure
    await data_manager.save_data('admins', new_admins_data)
    
    print(f"\n🎉 Manual admin sync completed!")
    print(f"   Only admins from environment variables are now active")
    print(f"   Removed any extra admins that weren't in ADMIN_IDS")

if __name__ == "__main__":
    asyncio.run(manual_admin_sync())
