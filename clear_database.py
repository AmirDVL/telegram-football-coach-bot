#!/usr/bin/env python3
"""
Database Data Clearing Script
Clears all user data while preserving table structure for fresh testing
"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def clear_all_data():
    """Clear all data from PostgreSQL database tables"""
    
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
        
        print("🗑️  Clearing all data from tables...")
        
        # List of tables to clear (in order to handle foreign key constraints)
        tables_to_clear = [
            'user_interactions',
            'daily_statistics', 
            'payment_analytics',
            'course_popularity',
            'user_retention',
            'questionnaire_analytics',
            'data_exports',
            'bulk_imports',
            'user_data_snapshots',
            'user_progress',
            'user_availability',
            'user_physical_data',
            'user_goals',
            'user_training_history',
            'user_profiles',
            'payments',
            'users',
            'courses',
            'admins',
            'bot_settings'
        ]
        
        # Clear each table
        for table in tables_to_clear:
            try:
                # Check if table exists
                table_exists = await conn.fetchval(
                    "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = $1)",
                    table
                )
                
                if table_exists:
                    await conn.execute(f"DELETE FROM {table}")
                    print(f"  ✅ Cleared table: {table}")
                else:
                    print(f"  ⚠️  Table not found: {table}")
                    
            except Exception as e:
                print(f"  ❌ Error clearing table {table}: {e}")
        
        # Reset sequences (auto-increment counters)
        print("\n🔄 Resetting auto-increment sequences...")
        
        sequences_to_reset = [
            'users_id_seq',
            'payments_id_seq', 
            'courses_id_seq',
            'admins_id_seq'
        ]
        
        for sequence in sequences_to_reset:
            try:
                # Check if sequence exists
                seq_exists = await conn.fetchval(
                    "SELECT EXISTS (SELECT FROM information_schema.sequences WHERE sequence_name = $1)",
                    sequence
                )
                
                if seq_exists:
                    await conn.execute(f"ALTER SEQUENCE {sequence} RESTART WITH 1")
                    print(f"  ✅ Reset sequence: {sequence}")
                else:
                    print(f"  ⚠️  Sequence not found: {sequence}")
                    
            except Exception as e:
                print(f"  ❌ Error resetting sequence {sequence}: {e}")
        
        print("\n📊 Database statistics after clearing:")
        
        # Check remaining data in core tables
        core_tables = ['users', 'payments', 'courses', 'admins']
        for table in core_tables:
            try:
                count = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
                print(f"  {table}: {count} records")
            except:
                print(f"  {table}: table not found")
        
        await conn.close()
        
        print("\n🎉 Database successfully cleared!")
        print("💡 All user data, payments, and analytics have been removed.")
        print("🔄 Database is ready for fresh testing!")
        
    except Exception as e:
        print(f"\n❌ Error connecting to database: {e}")
        print("\n🔧 Troubleshooting tips:")
        print("1. Make sure PostgreSQL is running")
        print("2. Check your .env file database credentials")
        print("3. Verify database exists and user has permissions")
        
        return False
    
    return True

async def main():
    """Main function"""
    print("🚀 Football Coach Bot - Database Data Clearing Tool")
    print("=" * 60)
    print("⚠️  WARNING: This will delete ALL data from your database!")
    print("📋 This includes:")
    print("   • All user registrations and profiles")
    print("   • All payment records") 
    print("   • All questionnaire responses")
    print("   • All analytics and statistics")
    print("   • All admin data (except basic admin settings)")
    print("=" * 60)
    
    # Get user confirmation
    while True:
        confirm = input("\n❓ Are you sure you want to proceed? (yes/no): ").lower().strip()
        
        if confirm in ['yes', 'y']:
            break
        elif confirm in ['no', 'n']:
            print("❌ Operation cancelled. No data was deleted.")
            return
        else:
            print("Please enter 'yes' or 'no'")
    
    print("\n" + "=" * 60)
    
    # Perform the clearing
    success = await clear_all_data()
    
    if success:
        print("\n" + "=" * 60)
        print("✅ DATA CLEARING COMPLETED SUCCESSFULLY!")
        print("\n🎯 Next steps:")
        print("1. Restart your bot: python main.py")
        print("2. The database structure is preserved")
        print("3. Ready for fresh testing!")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ DATA CLEARING FAILED!")
        print("Please check the error messages above and try again.")
        print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
