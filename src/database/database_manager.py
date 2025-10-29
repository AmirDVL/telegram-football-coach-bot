"""
PostgreSQL Database Manager for Football Coach Bot
Handles all database operations with proper async support
"""

import asyncio
import asyncpg
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from bot.config import Config

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self.pool = None
        self.connection_string = self._build_connection_string()
    
    def _build_connection_string(self) -> str:
        """Build PostgreSQL connection string from environment variables"""
        return (
            f"postgresql://{Config.DB_USER}:{Config.DB_PASSWORD}@"
            f"{Config.DB_HOST}:{Config.DB_PORT}/{Config.DB_NAME}"
        )
    
    async def initialize(self):
        """Initialize database connection pool"""
        try:
            self.pool = await asyncpg.create_pool(
                self.connection_string,
                min_size=1,
                max_size=10,
                command_timeout=60
            )
            logger.info("Database connection pool created successfully")
            await self.create_tables()
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    async def close(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection pool closed")
    
    async def create_tables(self):
        """Create all required tables"""
        async with self.pool.acquire() as conn:
            # Users table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    name VARCHAR(255),
                    username VARCHAR(255),
                    first_name VARCHAR(255),
                    language_code VARCHAR(10),
                    started_bot BOOLEAN DEFAULT FALSE,
                    registration_complete BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Courses table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS courses (
                    id SERIAL PRIMARY KEY,
                    course_key VARCHAR(50) UNIQUE NOT NULL,
                    title VARCHAR(255) NOT NULL,
                    description TEXT,
                    price INTEGER NOT NULL,
                    course_type VARCHAR(50),
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Payments table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS payments (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(user_id),
                    course_key VARCHAR(50) REFERENCES courses(course_key),
                    amount INTEGER NOT NULL,
                    status VARCHAR(50) DEFAULT 'pending',
                    payment_method VARCHAR(50),
                    receipt_file_id VARCHAR(255),
                    approved_by BIGINT,
                    approved_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # User responses (questionnaires)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS user_responses (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(user_id),
                    payment_id INTEGER REFERENCES payments(id),
                    questionnaire_data JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # User images table for questionnaire photos
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS user_images (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(user_id),
                    payment_id INTEGER REFERENCES payments(id),
                    question_step INTEGER NOT NULL,
                    file_id VARCHAR(255) NOT NULL,
                    compressed_file_id VARCHAR(255),
                    image_type VARCHAR(50) DEFAULT 'body_analysis',
                    image_order INTEGER DEFAULT 1,
                    file_size INTEGER,
                    compressed_size INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, payment_id, question_step, image_order)
                )
            """)
            
            # Admins table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS admins (
                    user_id BIGINT PRIMARY KEY,
                    is_super_admin BOOLEAN DEFAULT FALSE,
                    permissions JSONB DEFAULT '{}',
                    added_by BIGINT,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE
                )
            """)
            
            # Statistics table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS statistics (
                    id SERIAL PRIMARY KEY,
                    metric_name VARCHAR(100) NOT NULL,
                    metric_value INTEGER DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(metric_name)
                )
            """)
            
            # Bot settings table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS bot_settings (
                    key VARCHAR(100) PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes for better performance
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_payments_user_id ON payments(user_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_payments_created_at ON payments(created_at)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_user_images_user_id ON user_images(user_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_user_images_payment_id ON user_images(payment_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_user_images_question_step ON user_images(question_step)")
            
            logger.info("Database tables created successfully")
    
    async def insert_initial_data(self):
        """Insert initial courses and admin data"""
        async with self.pool.acquire() as conn:
            # Insert courses
            courses_data = [
                ('in_person_cardio', 'دوره تمرین حضوری: هوازی سرعتی چابکی کاربا توپ', 
                 Config.COURSE_DETAILS['in_person_cardio']['description'], 3000000, 'in_person'),
                ('in_person_weights', 'دوره تمرین حضوری: وزنه اختصاصی', 
                 Config.COURSE_DETAILS['in_person_weights']['description'], 3000000, 'in_person'),
                ('online_weights', 'دوره تمرین آنلاین: وزنه', 
                 Config.COURSE_DETAILS['online_weights']['description'], 599000, 'online'),
                ('online_cardio', 'دوره تمرین آنلاین: هوازی و کاربا توپ', 
                 Config.COURSE_DETAILS['online_cardio']['description'], 599000, 'online'),
                ('online_combo', 'دوره تمرین آنلاین: وزنه+ هوازی', 
                 Config.COURSE_DETAILS['online_combo']['description'], 999000, 'online')
            ]
            
            for course_key, title, description, price, course_type in courses_data:
                await conn.execute("""
                    INSERT INTO courses (course_key, title, description, price, course_type)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (course_key) 
                    DO UPDATE SET 
                        title = EXCLUDED.title,
                        description = EXCLUDED.description,
                        price = EXCLUDED.price,
                        course_type = EXCLUDED.course_type
                """, course_key, title, description, price, course_type)
            
            # Insert initial admin if specified in config
            if Config.ADMIN_ID:
                await conn.execute("""
                    INSERT INTO admins (user_id, is_super_admin, permissions)
                    VALUES ($1, TRUE, $2)
                    ON CONFLICT (user_id) 
                    DO UPDATE SET 
                        is_super_admin = TRUE,
                        permissions = EXCLUDED.permissions
                """, Config.ADMIN_ID, json.dumps({
                    "can_add_admins": True,
                    "can_remove_admins": True,
                    "can_view_users": True,
                    "can_manage_payments": True
                }))
            
            # Insert initial statistics
            initial_stats = [
                'total_users', 'total_payments', 'total_registrations',
                'course_in_person_cardio', 'course_in_person_weights',
                'course_online_weights', 'course_online_cardio', 'course_online_combo'
            ]
            
            for stat in initial_stats:
                await conn.execute("""
                    INSERT INTO statistics (metric_name, metric_value)
                    VALUES ($1, 0)
                    ON CONFLICT (metric_name) DO NOTHING
                """, stat)
            
            logger.info("Initial data inserted successfully")
    
    # User management methods
    async def save_user_data(self, user_id: int, user_data: Dict[str, Any]):
        """Save or update user data"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO users (
                    user_id, name, username, first_name, language_code, 
                    started_bot, registration_complete
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (user_id) 
                DO UPDATE SET 
                    name = COALESCE(EXCLUDED.name, users.name),
                    username = COALESCE(EXCLUDED.username, users.username),
                    first_name = COALESCE(EXCLUDED.first_name, users.first_name),
                    language_code = COALESCE(EXCLUDED.language_code, users.language_code),
                    started_bot = COALESCE(EXCLUDED.started_bot, users.started_bot),
                    registration_complete = COALESCE(EXCLUDED.registration_complete, users.registration_complete),
                    updated_at = CURRENT_TIMESTAMP
            """, 
            user_id,
            user_data.get('name'),
            user_data.get('username'),
            user_data.get('first_name'),
            user_data.get('language_code'),
            user_data.get('started_bot', False),
            user_data.get('registration_complete', False)
            )
    
    async def get_user_data(self, user_id: int) -> Dict[str, Any]:
        """Get user data"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM users WHERE user_id = $1
            """, user_id)
            
            if row:
                return dict(row)
            return {}
    
    # Payment management methods
    async def save_payment_data(self, user_id: int, payment_data: Dict[str, Any]):
        """Save payment data"""
        async with self.pool.acquire() as conn:
            return await conn.fetchval("""
                INSERT INTO payments (
                    user_id, course_key, amount, status, payment_method, receipt_file_id
                ) VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id
            """,
            user_id,
            payment_data.get('course_type'),
            payment_data.get('price', 0),
            payment_data.get('status', 'pending'),
            payment_data.get('payment_method', 'bank_transfer'),
            payment_data.get('receipt_file_id')
            )
    
    async def update_payment_status(self, payment_id: int, status: str, approved_by: Optional[int] = None):
        """Update payment status"""
        async with self.pool.acquire() as conn:
            if approved_by:
                await conn.execute("""
                    UPDATE payments 
                    SET status = $1, approved_by = $2, approved_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                    WHERE id = $3
                """, status, approved_by, payment_id)
            else:
                await conn.execute("""
                    UPDATE payments 
                    SET status = $1, updated_at = CURRENT_TIMESTAMP
                    WHERE id = $2
                """, status, payment_id)
    
    async def get_pending_payments(self) -> List[Dict[str, Any]]:
        """Get all pending payments"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT p.*, u.name, u.username, c.title as course_title
                FROM payments p
                JOIN users u ON p.user_id = u.user_id
                JOIN courses c ON p.course_key = c.course_key
                WHERE p.status = 'pending'
                ORDER BY p.created_at DESC
            """)
            return [dict(row) for row in rows]
    
    # Admin management methods
    async def is_admin(self, user_id: int) -> bool:
        """Check if user is admin"""
        async with self.pool.acquire() as conn:
            result = await conn.fetchval("""
                SELECT is_active FROM admins 
                WHERE user_id = $1 AND is_active = TRUE
            """, user_id)
            return bool(result)
    
    async def is_super_admin(self, user_id: int) -> bool:
        """Check if user is super admin"""
        async with self.pool.acquire() as conn:
            result = await conn.fetchval("""
                SELECT is_super_admin FROM admins 
                WHERE user_id = $1 AND is_active = TRUE
            """, user_id)
            return bool(result)
    
    async def add_admin(self, user_id: int, permissions: Dict[str, Any], added_by: int):
        """Add new admin"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO admins (user_id, permissions, added_by)
                VALUES ($1, $2, $3)
                ON CONFLICT (user_id) 
                DO UPDATE SET 
                    permissions = EXCLUDED.permissions,
                    added_by = EXCLUDED.added_by,
                    is_active = TRUE
            """, user_id, json.dumps(permissions), added_by)
    
    async def sync_admins_from_config(self):
        """Sync admins from environment config on startup"""
        from bot.config import Config
        
        admin_ids = Config.get_admin_ids()
        if not admin_ids:
            return
        
        print(f"🔄 Syncing {len(admin_ids)} admin(s) from configuration...")
        
        # Super admin permissions
        super_admin_permissions = {
            "can_add_admins": True,
            "can_remove_admins": True,
            "can_approve_payments": True,
            "can_view_users": True,
            "can_manage_courses": True,
            "can_export_data": True,
            "can_import_data": True,
            "can_view_analytics": True
        }
        
        async with self.pool.acquire() as conn:
            for admin_id in admin_ids:
                try:
                    # Check if admin already exists
                    exists = await conn.fetchval("""
                        SELECT user_id FROM admins WHERE user_id = $1
                    """, admin_id)
                    
                    if exists:
                        # Update existing admin to ensure they're active
                        await conn.execute("""
                            UPDATE admins SET 
                                is_active = TRUE,
                                is_super_admin = TRUE,
                                permissions = $2
                            WHERE user_id = $1
                        """, admin_id, json.dumps(super_admin_permissions))
                        print(f"  ✅ Updated admin: {admin_id}")
                    else:
                        # Add new admin
                        await conn.execute("""
                            INSERT INTO admins (user_id, is_super_admin, permissions, added_by)
                            VALUES ($1, TRUE, $2, $1)
                        """, admin_id, json.dumps(super_admin_permissions))
                        print(f"  ✅ Added new admin: {admin_id}")
                        
                except Exception as e:
                    print(f"  ❌ Error syncing admin {admin_id}: {e}")
        
        print(f"🎉 Admin sync completed! {len(admin_ids)} admins are now active.")
    
    # Statistics methods
    async def update_statistics(self, metric_name: str, increment: int = 1):
        """Update statistics"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO statistics (metric_name, metric_value)
                VALUES ($1, $2)
                ON CONFLICT (metric_name)
                DO UPDATE SET 
                    metric_value = statistics.metric_value + $2,
                    updated_at = CURRENT_TIMESTAMP
            """, metric_name, increment)
    
    async def get_statistics(self) -> Dict[str, int]:
        """Get all statistics"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT metric_name, metric_value FROM statistics")
            return {row['metric_name']: row['metric_value'] for row in rows}
    
    # Questionnaire methods
    async def save_questionnaire_response(self, user_id: int, payment_id: int, responses: str):
        """Save questionnaire responses"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO user_responses (user_id, payment_id, questionnaire_data)
                VALUES ($1, $2, $3)
            """, user_id, payment_id, json.dumps({"responses": responses}))

    # User image methods
    async def save_user_image(self, user_id: int, payment_id: int, question_step: int, 
                            file_id: str, image_order: int = 1, 
                            compressed_file_id: str = None, file_size: int = None, 
                            compressed_size: int = None) -> bool:
        """Save user image information"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO user_images (user_id, payment_id, question_step, file_id, 
                                           compressed_file_id, image_order, file_size, compressed_size)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    ON CONFLICT (user_id, payment_id, question_step, image_order) 
                    DO UPDATE SET 
                        file_id = EXCLUDED.file_id,
                        compressed_file_id = EXCLUDED.compressed_file_id,
                        file_size = EXCLUDED.file_size,
                        compressed_size = EXCLUDED.compressed_size,
                        created_at = CURRENT_TIMESTAMP
                """, user_id, payment_id, question_step, file_id, compressed_file_id, 
                     image_order, file_size, compressed_size)
            return True
        except Exception as e:
            logger.error(f"Error saving user image: {e}")
            return False

    async def get_user_images(self, user_id: int, payment_id: int = None) -> list:
        """Get user images"""
        async with self.pool.acquire() as conn:
            if payment_id:
                rows = await conn.fetch("""
                    SELECT * FROM user_images 
                    WHERE user_id = $1 AND payment_id = $2
                    ORDER BY question_step, image_order
                """, user_id, payment_id)
            else:
                rows = await conn.fetch("""
                    SELECT * FROM user_images 
                    WHERE user_id = $1
                    ORDER BY question_step, image_order
                """, user_id)
            
            return [dict(row) for row in rows]

    async def get_user_images_by_step(self, user_id: int, question_step: int, payment_id: int = None) -> list:
        """Get user images for specific question step"""
        async with self.pool.acquire() as conn:
            if payment_id:
                rows = await conn.fetch("""
                    SELECT * FROM user_images 
                    WHERE user_id = $1 AND question_step = $2 AND payment_id = $3
                    ORDER BY image_order
                """, user_id, question_step, payment_id)
            else:
                rows = await conn.fetch("""
                    SELECT * FROM user_images 
                    WHERE user_id = $1 AND question_step = $2
                    ORDER BY image_order
                """, user_id, question_step)
            
            return [dict(row) for row in rows]
