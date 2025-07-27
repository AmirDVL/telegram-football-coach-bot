# security_config.py - Enhanced Security Settings

import logging
import time
import hashlib
import secrets
from typing import Dict, Set, List
from datetime import datetime, timedelta
import re

class SecurityManager:
    def __init__(self):
        self.request_counts: Dict[int, List[float]] = {}
        self.blocked_users: Set[int] = set()
        self.suspicious_activity_log = []
        self.failed_login_attempts: Dict[int, int] = {}
        self.user_sessions: Dict[int, str] = {}
        
        # Configure security logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - SECURITY - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('security.log'),
                logging.StreamHandler()
            ]
        )
        self.security_logger = logging.getLogger('security')
    
    def rate_limit_check(self, user_id: int, max_requests: int = 60) -> bool:
        """Enhanced rate limiting with user tracking"""
        current_time = time.time()
        one_minute_ago = current_time - 60
        
        # Clean old requests
        if user_id in self.request_counts:
            self.request_counts[user_id] = [
                req_time for req_time in self.request_counts[user_id] 
                if req_time > one_minute_ago
            ]
        else:
            self.request_counts[user_id] = []
        
        # Check if user exceeded limit
        if len(self.request_counts[user_id]) >= max_requests:
            self.log_suspicious_activity(user_id, "rate_limit_exceeded", "HIGH")
            self.blocked_users.add(user_id)
            return False
        
        # Add current request
        self.request_counts[user_id].append(current_time)
        return True
    
    def validate_input(self, text: str) -> bool:
        """Comprehensive input validation to prevent injection attacks"""
        if not text or not isinstance(text, str):
            return False
        
        # Block SQL injection patterns
        sql_patterns = [
            r'DROP\s+TABLE', r'DELETE\s+FROM', r'INSERT\s+INTO', r'UPDATE\s+SET',
            r'UNION\s+SELECT', r'--', r';', r'CREATE\s+TABLE', r'ALTER\s+TABLE',
            r'EXEC\s*\(', r'EXECUTE\s*\(', r'xp_', r'sp_', r'SELECT\s+.*\s+FROM',
            r'<script', r'javascript:', r'vbscript:', r'onload=', r'onerror='
        ]
        
        text_upper = text.upper()
        for pattern in sql_patterns:
            if re.search(pattern, text_upper, re.IGNORECASE):
                self.log_suspicious_activity(0, f"injection_attempt: {pattern}", "CRITICAL")
                return False
        
        # Block excessively long inputs
        if len(text) > 2000:
            self.log_suspicious_activity(0, "oversized_input", "MEDIUM")
            return False
        
        # Block suspicious Unicode or control characters
        if any(ord(char) < 32 and char not in ['\n', '\r', '\t'] for char in text):
            self.log_suspicious_activity(0, "control_character_injection", "HIGH")
            return False
            
        return True
    
    def validate_file_upload(self, filename: str, file_content: bytes) -> bool:
        """Validate file uploads for security"""
        if not filename:
            return False
        
        # Allowed file extensions
        allowed_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.pdf'}
        file_extension = '.' + filename.lower().split('.')[-1] if '.' in filename else ''
        
        if file_extension not in allowed_extensions:
            self.log_suspicious_activity(0, f"invalid_file_type: {file_extension}", "MEDIUM")
            return False
        
        # Check file size (max 20MB)
        if len(file_content) > 20 * 1024 * 1024:
            self.log_suspicious_activity(0, "oversized_file", "MEDIUM")
            return False
        
        # Basic file header validation (magic numbers)
        file_signatures = {
            b'\xFF\xD8\xFF': 'jpg',
            b'\x89PNG\r\n\x1a\n': 'png',
            b'RIFF': 'webp',  # WebP files start with RIFF
            b'%PDF': 'pdf'
        }
        
        is_valid = False
        for signature, file_type in file_signatures.items():
            if file_content.startswith(signature):
                is_valid = True
                break
        
        if not is_valid:
            self.log_suspicious_activity(0, "invalid_file_signature", "HIGH")
            return False
        
        return True
    
    def generate_session_token(self, user_id: int) -> str:
        """Generate secure session token"""
        token = secrets.token_hex(32)
        self.user_sessions[user_id] = token
        return token
    
    def validate_session(self, user_id: int, token: str) -> bool:
        """Validate user session token"""
        return self.user_sessions.get(user_id) == token
    
    def hash_sensitive_data(self, data: str) -> str:
        """Hash sensitive data for storage"""
        salt = secrets.token_hex(16)
        hashed = hashlib.pbkdf2_hmac('sha256', data.encode(), salt.encode(), 100000)
        return f"{salt}:{hashed.hex()}"
    
    def verify_hashed_data(self, data: str, hashed: str) -> bool:
        """Verify hashed data"""
        try:
            salt, hash_value = hashed.split(':')
            expected_hash = hashlib.pbkdf2_hmac('sha256', data.encode(), salt.encode(), 100000)
            return hash_value == expected_hash.hex()
        except:
            return False
    
    def log_suspicious_activity(self, user_id: int, activity_type: str, severity: str = "MEDIUM"):
        """Log suspicious activities for monitoring"""
        log_entry = {
            'user_id': user_id,
            'activity': activity_type,
            'timestamp': datetime.now(),
            'severity': severity,
            'ip': 'telegram_api'  # Telegram doesn't provide IP
        }
        self.suspicious_activity_log.append(log_entry)
        
        # Log to file with appropriate level
        if severity == "CRITICAL":
            self.security_logger.critical(f"User {user_id} - {activity_type}")
        elif severity == "HIGH":
            self.security_logger.error(f"User {user_id} - {activity_type}")
        else:
            self.security_logger.warning(f"User {user_id} - {activity_type}")
        
        # Auto-block for critical activities
        if severity == "CRITICAL":
            self.blocked_users.add(user_id)
    
    def is_user_blocked(self, user_id: int) -> bool:
        """Check if user is blocked"""
        return user_id in self.blocked_users
    
    def unblock_user(self, user_id: int):
        """Unblock a user (admin function)"""
        self.blocked_users.discard(user_id)
        self.security_logger.info(f"User {user_id} unblocked by admin")
    
    def get_security_report(self) -> Dict:
        """Generate security activity report"""
        now = datetime.now()
        last_24h = now - timedelta(hours=24)
        
        recent_incidents = [
            incident for incident in self.suspicious_activity_log
            if incident['timestamp'] > last_24h
        ]
        
        return {
            'total_incidents_24h': len(recent_incidents),
            'critical_incidents': len([i for i in recent_incidents if i['severity'] == 'CRITICAL']),
            'high_incidents': len([i for i in recent_incidents if i['severity'] == 'HIGH']),
            'medium_incidents': len([i for i in recent_incidents if i['severity'] == 'MEDIUM']),
            'blocked_users_count': len(self.blocked_users),
            'active_sessions': len(self.user_sessions),
            'recent_incidents': recent_incidents[-10:]  # Last 10 incidents
        }


# Database connection security wrapper
class SecureDBConnection:
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.connection_attempts = 0
        self.last_attempt = None
        self.max_retry_attempts = 3
        
    def validate_connection_string(self) -> bool:
        """Validate database connection string for security"""
        # Ensure using strong authentication
        if 'password=' not in self.connection_string.lower():
            return False
        
        # Ensure localhost only (no external connections)
        if 'host=localhost' not in self.connection_string.lower() and 'host=127.0.0.1' not in self.connection_string.lower():
            return False
        
        # Ensure using encrypted connection
        if 'sslmode=' not in self.connection_string.lower():
            # Add SSL requirement if not specified
            self.connection_string += " sslmode=require"
            
        return True
    
    def sanitize_query(self, query: str, params: tuple = None) -> bool:
        """Basic query sanitization check"""
        # This should be used with parameterized queries only
        dangerous_keywords = [
            'DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'CREATE', 'EXEC',
            'EXECUTE', 'INSERT', 'UPDATE'
        ]
        
        # Allow specific safe operations
        safe_operations = ['SELECT', 'INSERT INTO users', 'UPDATE users SET', 'INSERT INTO payments']
        
        query_upper = query.upper().strip()
        
        # Check if it's a safe operation
        for safe_op in safe_operations:
            if query_upper.startswith(safe_op):
                return True
        
        # Block dangerous operations
        for keyword in dangerous_keywords:
            if keyword in query_upper:
                return False
        
        return True


# Environment security validator
class EnvironmentSecurity:
    @staticmethod
    def validate_environment() -> List[str]:
        """Validate environment security settings"""
        warnings = []
        
        import os
        
        # Check critical environment variables
        required_vars = ['BOT_TOKEN', 'ADMIN_ID', 'DB_PASSWORD']
        for var in required_vars:
            if not os.getenv(var):
                warnings.append(f"Missing critical environment variable: {var}")
        
        # Check password strength
        db_password = os.getenv('DB_PASSWORD', '')
        if len(db_password) < 12:
            warnings.append("Database password too short (minimum 12 characters)")
        
        if not re.search(r'[A-Z]', db_password):
            warnings.append("Database password missing uppercase letters")
        
        if not re.search(r'[a-z]', db_password):
            warnings.append("Database password missing lowercase letters")
        
        if not re.search(r'[0-9]', db_password):
            warnings.append("Database password missing numbers")
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', db_password):
            warnings.append("Database password missing special characters")
        
        # Check debug mode
        if os.getenv('DEBUG', 'false').lower() == 'true':
            warnings.append("DEBUG mode is enabled in production")
        
        return warnings


# Initialize global security manager
security_manager = SecurityManager()
