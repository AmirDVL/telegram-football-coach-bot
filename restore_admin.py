#!/usr/bin/env python3
"""
Admin Restoration Script
Adds back the admin user after database clearing
"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def restore_admin():
    """Add the admin user back to the database"""
    
    # Database connection parameters
    db_params = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 5432)),
        'database': os.getenv('DB_NAME', 'football_coach_bot'),
        'user': os.getenv('DB_USER', 'footballbot'),
        'password': os.getenv('DB_PASSWORD', 'SecureBot123!')
    }
    
    # Admin ID from .env file
    admin_id = int(os.getenv('ADMIN_ID', 293893885))
    
    try:
        print("🔄 Connecting to PostgreSQL database...")
        conn = await asyncpg.connect(**db_params)
        
        print(f"👤 Adding admin user: {admin_id}")
        
        # Check if admin already exists
        existing_admin = await conn.fetchval(
            "SELECT user_id FROM admins WHERE user_id = $1", admin_id
        )
        
        if existing_admin:
            print(f"  ✅ Admin {admin_id} already exists!")
        else:
            # Insert admin record
            await conn.execute(
                "INSERT INTO admins (user_id, permissions) VALUES ($1, $2)",
                admin_id, 'full'
            )
            print(f"  ✅ Admin {admin_id} added successfully!")
        
        # Verify admin was added
        admin_count = await conn.fetchval("SELECT COUNT(*) FROM admins")
        print(f"📊 Total admins in database: {admin_count}")
        
        await conn.close()
        
        print("\n🎉 Admin restoration completed!")
        print("💡 You can now access the admin panel!")
        print("🔧 Try sending a message to your bot to test admin access.")
        
    except Exception as e:
        print(f"\n❌ Error connecting to database: {e}")
        return False
    
    return True

async def main():
    """Main function"""
    print("🚀 Football Coach Bot - Admin Restoration Tool")
    print("=" * 50)
    print("🔧 This will restore your admin access after database clearing")
    print("=" * 50)
    
    success = await restore_admin()
    
    if success:
        print("\n" + "=" * 50)
        print("✅ ADMIN RESTORATION COMPLETED!")
        print("\n🎯 Next steps:")
        print("1. Send /start to your bot")
        print("2. You should now have admin access")
        print("3. Try the admin panel features!")
        print("=" * 50)
    else:
        print("\n" + "=" * 50)
        print("❌ ADMIN RESTORATION FAILED!")
        print("Please check the error messages above.")
        print("=" * 50)

if __name__ == "__main__":
    asyncio.run(main())
