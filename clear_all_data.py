#!/usr/bin/env python3
"""
Complete Data Clearing Script
Clears ALL data sources (PostgreSQL database AND JSON files)
"""

import os
import json
import asyncio
import asyncpg
from pathlib import Path
from config import Config

async def clear_postgresql_database():
    """Clear PostgreSQL database completely"""
    print("🗄️ Clearing PostgreSQL database...")
    
    try:
        # Connect to database
        conn = await asyncpg.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            database=Config.DB_NAME,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD
        )
        
        # List of tables to clear
        tables = [
            'payments', 'users', 'courses', 'admins', 'bot_settings',
            'user_interactions', 'daily_statistics', 'payment_analytics',
            'course_popularity', 'user_retention', 'questionnaire_analytics',
            'data_exports', 'bulk_imports', 'user_data_snapshots',
            'user_progress', 'user_availability', 'user_physical_data',
            'user_goals', 'user_training_history', 'user_profiles'
        ]
        
        # Clear all tables
        for table in tables:
            try:
                await conn.execute(f"DELETE FROM {table}")
                print(f"  ✅ Cleared table: {table}")
            except Exception as e:
                print(f"  ⚠️  Table not found or error: {table} ({e})")
        
        # Reset sequences
        sequences = [
            'users_id_seq', 'payments_id_seq', 'courses_id_seq', 
            'admins_id_seq', 'user_profiles_id_seq'
        ]
        
        for seq in sequences:
            try:
                await conn.execute(f"ALTER SEQUENCE {seq} RESTART WITH 1")
                print(f"  ✅ Reset sequence: {seq}")
            except Exception as e:
                print(f"  ⚠️  Sequence not found: {seq}")
        
        await conn.close()
        print("✅ PostgreSQL database cleared successfully!")
        
    except Exception as e:
        print(f"❌ Error clearing PostgreSQL database: {e}")

def clear_json_files():
    """Clear all JSON data files"""
    print("📄 Clearing JSON files...")
    
    # All possible JSON files
    json_files = [
        'bot_data.json',
        'questionnaire_data.json', 
        'admins.json',
        'users.json',
        'payments.json',
        'courses.json',
        'bot_settings.json',
        'user_profiles.json',
        'statistics.json',
        'analytics.json'
    ]
    
    cleared_count = 0
    
    for filename in json_files:
        filepath = Path(filename)
        if filepath.exists():
            # Create empty structure based on file type
            if filename == 'bot_data.json':
                empty_data = {
                    "users": {},
                    "payments": {},
                    "statistics": {
                        "total_users": 0,
                        "total_payments": 0,
                        "course_stats": {}
                    }
                }
            elif filename == 'questionnaire_data.json':
                empty_data = {}
            elif filename == 'admins.json':
                empty_data = {}
            else:
                empty_data = {}
            
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(empty_data, f, ensure_ascii=False, indent=2)
                print(f"  ✅ Cleared: {filename}")
                cleared_count += 1
            except Exception as e:
                print(f"  ❌ Error clearing {filename}: {e}")
        else:
            print(f"  ⚠️  Not found: {filename}")
    
    print(f"✅ Cleared {cleared_count} JSON files!")

async def main():
    """Main clearing function"""
    print("🚀 Complete Data Clearing Tool")
    print("=" * 50)
    print("⚠️  This will clear ALL data sources:")
    print("   • PostgreSQL Database")
    print("   • JSON Files")
    print("   • All user data, payments, analytics")
    print("=" * 50)
    
    response = input("❓ Are you sure you want to proceed? (yes/no): ").strip().lower()
    
    if response != 'yes':
        print("🚫 Operation cancelled.")
        return
    
    print("=" * 50)
    
    # Clear PostgreSQL database
    await clear_postgresql_database()
    
    print()
    
    # Clear JSON files
    clear_json_files()
    
    print()
    print("🎉 COMPLETE DATA CLEARING FINISHED!")
    print("✅ All data sources have been cleared")
    print("🔄 Bot is ready for fresh testing")
    print("💡 Admin access will be restored from .env file on next startup")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(main())
