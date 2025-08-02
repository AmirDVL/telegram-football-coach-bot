#!/usr/bin/env python3
"""
Simple admin verification script
"""

import asyncio
from admin_manager import AdminManager

async def check_admin_status():
    """Check if user 293893885 is still an admin"""
    am = AdminManager()
    
    user_id = 293893885
    is_admin = await am.is_admin(user_id)
    is_super = await am.is_super_admin(user_id)
    
    print(f"User {user_id} admin status:")
    print(f"  Is admin: {is_admin}")
    print(f"  Is super admin: {is_super}")
    
    # Also check the environment-based admins
    from config import Config
    env_admins = Config.get_admin_ids()
    print(f"\nEnvironment admins: {env_admins}")
    print(f"User {user_id} in env admins: {user_id in env_admins}")

if __name__ == "__main__":
    asyncio.run(check_admin_status())
