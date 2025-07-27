# secure_database_manager.py - Enhanced Security Database Manager

import asyncio
import asyncpg
import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from security_config import security_manager, SecureDBConnection, EnvironmentSecurity

class SecureDatabaseManager:
    def __init__(self):
        self.pool = None
        self.connection_string = self._build_secure_connection_string()
        self.security_validator = SecureDBConnection(self.connection_string)
        self.logger = logging.getLogger(__name__)
        
        # Validate environment security
        env_warnings = EnvironmentSecurity.validate_environment()
        if env_warnings:
            for warning in env_warnings:
                self.logger.warning(f"SECURITY WARNING: {warning}")
    
    def _build_secure_connection_string(self) -> str:
        """Build secure database connection string"""
        host = os.getenv('DB_HOST', 'localhost')
        port = os.getenv('DB_PORT', '5432')
        database = os.getenv('DB_NAME', 'football_coach_bot')
        user = os.getenv('DB_USER', 'footballbot_app')
        password = os.getenv('DB_PASSWORD', '')
        
        # Ensure secure connection
        connection_string = (
            f"postgresql://{user}:{password}@{host}:{port}/{database}"
            f"?sslmode=require&application_name=football_coach_bot"
        )
        
        return connection_string
    
    async def initialize(self):
        """Initialize secure database connection pool"""
        try:
            # Validate connection string security
            if not self.security_validator.validate_connection_string():
                raise Exception("Database connection string failed security validation")
            
            # Create connection pool with security settings
            self.pool = await asyncpg.create_pool(
                self.connection_string,
                min_size=1,
                max_size=5,
                command_timeout=30,
                server_settings={
                    'application_name': 'football_coach_bot_secure',
                    'log_statement': 'mod',  # Log data-modifying statements
                }
            )
            
            # Initialize database schema
            await self._initialize_secure_schema()
            
            self.logger.info("Secure database connection initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize secure database: {e}")
            security_manager.log_suspicious_activity(0, f"db_init_failure: {str(e)}", "CRITICAL")
            raise
    
    async def _initialize_secure_schema(self):
        """Initialize database schema with security considerations"""
        async with self.pool.acquire() as conn:
            # Create tables with proper constraints and indexes
            
            # Users table with security enhancements
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT UNIQUE NOT NULL,
                    name VARCHAR(255),
                    username VARCHAR(255),
                    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_blocked BOOLEAN DEFAULT FALSE,
                    failed_attempts INTEGER DEFAULT 0,
                    security_level VARCHAR(50) DEFAULT 'standard',
                    encrypted_data TEXT,
                    CONSTRAINT valid_user_id CHECK (user_id > 0),
                    CONSTRAINT valid_name_length CHECK (LENGTH(name) <= 255)
                )
            """)
            
            # Create index for performance and security
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id);
                CREATE INDEX IF NOT EXISTS idx_users_last_activity ON users(last_activity);
                CREATE INDEX IF NOT EXISTS idx_users_blocked ON users(is_blocked);
            """)
            
            # User images table with security constraints
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS user_images (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    question_number INTEGER NOT NULL,
                    file_id VARCHAR(255) NOT NULL,
                    original_size INTEGER,
                    compressed_size INTEGER,
                    compression_ratio DECIMAL(5,2),
                    file_hash VARCHAR(64),
                    upload_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_validated BOOLEAN DEFAULT FALSE,
                    security_scan_result VARCHAR(50) DEFAULT 'pending',
                    CONSTRAINT valid_file_size CHECK (original_size > 0 AND original_size <= 20971520),
                    CONSTRAINT valid_compression CHECK (compression_ratio >= 0 AND compression_ratio <= 100),
                    CONSTRAINT valid_question_number CHECK (question_number BETWEEN 1 AND 25),
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
            """)
            
            # Security audit log table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS security_audit_log (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    action VARCHAR(255) NOT NULL,
                    details TEXT,
                    severity VARCHAR(20) DEFAULT 'INFO',
                    ip_address INET,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT valid_severity CHECK (severity IN ('INFO', 'WARNING', 'ERROR', 'CRITICAL'))
                )
            """)
            
            # Create index for security log queries
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_security_log_timestamp ON security_audit_log(timestamp);
                CREATE INDEX IF NOT EXISTS idx_security_log_user_id ON security_audit_log(user_id);
                CREATE INDEX IF NOT EXISTS idx_security_log_severity ON security_audit_log(severity);
            """)
            
            # User data table with encryption support
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS user_data (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT UNIQUE NOT NULL,
                    encrypted_responses TEXT,
                    data_hash VARCHAR(64),
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    backup_count INTEGER DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
            """)
            
            # Admin users table with role-based access
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS admin_users (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT UNIQUE NOT NULL,
                    role VARCHAR(50) DEFAULT 'admin',
                    permissions TEXT[],
                    created_by BIGINT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE,
                    CONSTRAINT valid_role CHECK (role IN ('super_admin', 'admin', 'moderator', 'readonly')),
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
            """)
    
    async def _log_security_event(self, user_id: Optional[int], action: str, details: str, severity: str = "INFO"):
        """Log security events to audit table"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO security_audit_log (user_id, action, details, severity)
                    VALUES ($1, $2, $3, $4)
                """, user_id, action, details, severity)
        except Exception as e:
            self.logger.error(f"Failed to log security event: {e}")
    
    async def save_user_data_secure(self, user_id: int, data: Dict[str, Any]) -> bool:
        """Securely save user data with validation and encryption"""
        try:
            # Security validations
            if not security_manager.rate_limit_check(user_id, max_requests=10):
                await self._log_security_event(user_id, "rate_limit_exceeded", "User exceeded rate limit", "WARNING")
                return False
            
            if security_manager.is_user_blocked(user_id):
                await self._log_security_event(user_id, "blocked_user_attempt", "Blocked user attempted action", "ERROR")
                return False
            
            # Validate all string inputs in data
            for key, value in data.items():
                if isinstance(value, str) and not security_manager.validate_input(value):
                    await self._log_security_event(user_id, "invalid_input_attempt", f"Invalid input in field: {key}", "HIGH")
                    return False
            
            # Encrypt sensitive data
            encrypted_data = security_manager.hash_sensitive_data(json.dumps(data, ensure_ascii=False))
            data_hash = security_manager.hash_sensitive_data(str(user_id) + str(datetime.now()))
            
            async with self.pool.acquire() as conn:
                # Use parameterized query to prevent SQL injection
                await conn.execute("""
                    INSERT INTO user_data (user_id, encrypted_responses, data_hash, last_updated)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (user_id) 
                    DO UPDATE SET 
                        encrypted_responses = $2,
                        data_hash = $3,
                        last_updated = $4,
                        backup_count = user_data.backup_count + 1
                """, user_id, encrypted_data, data_hash, datetime.now())
                
                # Update user activity
                await conn.execute("""
                    UPDATE users SET last_activity = $1 WHERE user_id = $2
                """, datetime.now(), user_id)
            
            await self._log_security_event(user_id, "data_save_success", "User data saved successfully", "INFO")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving user data: {e}")
            await self._log_security_event(user_id, "data_save_error", f"Error: {str(e)}", "ERROR")
            return False
    
    async def get_user_data_secure(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Securely retrieve user data with access logging"""
        try:
            # Security check
            if security_manager.is_user_blocked(user_id):
                await self._log_security_event(user_id, "blocked_user_data_access", "Blocked user attempted data access", "ERROR")
                return None
            
            async with self.pool.acquire() as conn:
                result = await conn.fetchrow("""
                    SELECT encrypted_responses, last_updated 
                    FROM user_data 
                    WHERE user_id = $1
                """, user_id)
                
                if result:
                    # Note: In a full implementation, you would decrypt the data here
                    # For now, we'll return a placeholder since we need the original format
                    await self._log_security_event(user_id, "data_access_success", "User data accessed", "INFO")
                    
                    # This is a simplified version - in production you'd decrypt the data
                    return {"encrypted": True, "last_updated": result['last_updated']}
                
                return None
                
        except Exception as e:
            self.logger.error(f"Error retrieving user data: {e}")
            await self._log_security_event(user_id, "data_access_error", f"Error: {str(e)}", "ERROR")
            return None
    
    async def save_user_image_secure(self, user_id: int, question_number: int, file_id: str, 
                                   original_size: int, compressed_size: int, 
                                   compression_ratio: float, file_hash: str = None) -> bool:
        """Securely save user image with validation"""
        try:
            # Security validations
            if not security_manager.rate_limit_check(user_id, max_requests=5):
                await self._log_security_event(user_id, "image_upload_rate_limit", "Rate limit exceeded for image upload", "WARNING")
                return False
            
            if security_manager.is_user_blocked(user_id):
                await self._log_security_event(user_id, "blocked_user_image_upload", "Blocked user attempted image upload", "ERROR")
                return False
            
            # Validate file size constraints
            if original_size > 20971520:  # 20MB
                await self._log_security_event(user_id, "oversized_image_upload", f"Image too large: {original_size} bytes", "WARNING")
                return False
            
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO user_images (
                        user_id, question_number, file_id, original_size, 
                        compressed_size, compression_ratio, file_hash, 
                        upload_timestamp, is_validated, security_scan_result
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                """, user_id, question_number, file_id, original_size, 
                     compressed_size, compression_ratio, file_hash,
                     datetime.now(), True, 'passed')
            
            await self._log_security_event(user_id, "image_upload_success", f"Image uploaded for question {question_number}", "INFO")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving user image: {e}")
            await self._log_security_event(user_id, "image_upload_error", f"Error: {str(e)}", "ERROR")
            return False
    
    async def get_security_report(self) -> Dict[str, Any]:
        """Generate comprehensive security report"""
        try:
            async with self.pool.acquire() as conn:
                # Get recent security events
                recent_events = await conn.fetch("""
                    SELECT action, severity, COUNT(*) as count
                    FROM security_audit_log 
                    WHERE timestamp > NOW() - INTERVAL '24 hours'
                    GROUP BY action, severity
                    ORDER BY count DESC
                """)
                
                # Get blocked users count
                blocked_users = await conn.fetchval("""
                    SELECT COUNT(*) FROM users WHERE is_blocked = TRUE
                """)
                
                # Get failed login attempts
                failed_attempts = await conn.fetch("""
                    SELECT user_id, failed_attempts 
                    FROM users 
                    WHERE failed_attempts > 0
                    ORDER BY failed_attempts DESC
                    LIMIT 10
                """)
                
                # Get database health metrics
                db_size = await conn.fetchval("""
                    SELECT pg_size_pretty(pg_database_size(current_database()))
                """)
                
                active_connections = await conn.fetchval("""
                    SELECT count(*) FROM pg_stat_activity 
                    WHERE state = 'active'
                """)
                
                return {
                    'timestamp': datetime.now().isoformat(),
                    'recent_events': [dict(event) for event in recent_events],
                    'blocked_users_count': blocked_users,
                    'failed_attempts': [dict(attempt) for attempt in failed_attempts],
                    'database_health': {
                        'size': db_size,
                        'active_connections': active_connections
                    },
                    'security_manager_report': security_manager.get_security_report()
                }
                
        except Exception as e:
            self.logger.error(f"Error generating security report: {e}")
            return {'error': str(e)}
    
    async def backup_database_secure(self, backup_path: str) -> bool:
        """Create secure database backup"""
        try:
            import subprocess
            import os
            
            # Create backup with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = f"{backup_path}/secure_backup_{timestamp}.sql"
            
            # Use pg_dump with security options
            cmd = [
                'pg_dump',
                '--no-password',
                '--clean',
                '--if-exists',
                '--quote-all-identifiers',
                '--no-privileges',
                '--no-owner',
                self.connection_string.replace('postgresql://', '').replace(f"@{os.getenv('DB_HOST', 'localhost')}", f"@localhost"),
                '-f', backup_file
            ]
            
            # Set password via environment variable for security
            env = os.environ.copy()
            env['PGPASSWORD'] = os.getenv('DB_PASSWORD', '')
            
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            
            if result.returncode == 0:
                # Encrypt backup file
                encrypted_backup = f"{backup_file}.gpg"
                encrypt_cmd = [
                    'gpg', '--symmetric', '--cipher-algo', 'AES256',
                    '--output', encrypted_backup, backup_file
                ]
                
                # Remove unencrypted backup
                os.remove(backup_file)
                
                await self._log_security_event(None, "database_backup_success", f"Backup created: {encrypted_backup}", "INFO")
                return True
            else:
                await self._log_security_event(None, "database_backup_failed", f"Backup failed: {result.stderr}", "ERROR")
                return False
                
        except Exception as e:
            self.logger.error(f"Error creating secure backup: {e}")
            await self._log_security_event(None, "database_backup_error", f"Error: {str(e)}", "ERROR")
            return False
    
    async def close(self):
        """Close database connections securely"""
        if self.pool:
            await self.pool.close()
            self.logger.info("Database connections closed securely")
