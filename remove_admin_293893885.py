#!/usr/bin/env python3
"""
Remove specific admin from database
This script removes user ID 293893885 from the admins table
"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def remove_admin_from_database():
    """Remove admin 293893885 from PostgreSQL database"""
    
    admin_id_to_remove = 293893885
    
    # Database connection parameters
    db_params = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 5432)),
        'database': os.getenv('DB_NAME', 'football_coach_bot'),
        'user': os.getenv('DB_USER', 'footballbot'),
        'password': os.getenv('DB_PASSWORD', 'SecureBot123!')
    }
    
    try:
        print("🔄 Connecting to PostgreSQL database...")
        conn = await asyncpg.connect(**db_params)
        
        # Check if admin exists first
        admin_exists = await conn.fetchval(
            "SELECT COUNT(*) FROM admins WHERE user_id = $1",
            admin_id_to_remove
        )
        
        if admin_exists > 0:
            print(f"🔍 Found admin {admin_id_to_remove} in database")
            
            # Remove the admin
            result = await conn.execute(
                "DELETE FROM admins WHERE user_id = $1",
                admin_id_to_remove
            )
            
            print(f"✅ Removed admin {admin_id_to_remove} from database")
            print(f"📊 Rows affected: {result}")
        else:
            print(f"❌ Admin {admin_id_to_remove} not found in database")
        
        # Show remaining admins
        remaining_admins = await conn.fetch("SELECT user_id, is_super_admin FROM admins ORDER BY user_id")
        print("\n📋 Remaining admins in database:")
        for admin in remaining_admins:
            role = "Super Admin" if admin['is_super_admin'] else "Admin"
            print(f"  • {admin['user_id']} ({role})")
        
        await conn.close()
        print("✅ Database connection closed")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(remove_admin_from_database())
