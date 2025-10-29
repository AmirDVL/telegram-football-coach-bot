"""
Logging configuration for Football Coach Bot
Provides systematic logging with file rotation and different log levels
"""

import logging
import logging.handlers
import os
from datetime import datetime
from pathlib import Path

class BotLogger:
    """Enhanced logging system for the Football Coach Bot"""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Configure logging levels based on environment
        self.log_level = logging.DEBUG if os.getenv('DEBUG', 'false').lower() == 'true' else logging.INFO
        
        self._setup_loggers()
    
    def _setup_loggers(self):
        """Set up different loggers for different purposes"""
        
        # Root logger configuration
        root_logger = logging.getLogger()
        root_logger.setLevel(self.log_level)
        
        # Clear existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Create formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        simple_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        
        # 1. Main bot log file (rotating)
        main_handler = logging.handlers.RotatingFileHandler(
            filename=self.log_dir / "bot.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        main_handler.setLevel(logging.INFO)
        main_handler.setFormatter(detailed_formatter)
        
        # 2. Error-only log file
        error_handler = logging.handlers.RotatingFileHandler(
            filename=self.log_dir / "errors.log",
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(detailed_formatter)
        
        # 3. Debug log file (if debug mode is on)
        if self.log_level == logging.DEBUG:
            debug_handler = logging.handlers.RotatingFileHandler(
                filename=self.log_dir / "debug.log",
                maxBytes=20*1024*1024,  # 20MB
                backupCount=2,
                encoding='utf-8'
            )
            debug_handler.setLevel(logging.DEBUG)
            debug_handler.setFormatter(detailed_formatter)
            root_logger.addHandler(debug_handler)
        
        # 4. Console handler (simplified for terminal)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(simple_formatter)
        
        # 5. User interactions log (for analyzing user behavior)
        user_handler = logging.handlers.RotatingFileHandler(
            filename=self.log_dir / "user_interactions.log",
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3,
            encoding='utf-8'
        )
        user_handler.setLevel(logging.INFO)
        user_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))
        
        # Add handlers to root logger
        root_logger.addHandler(main_handler)
        root_logger.addHandler(error_handler)
        root_logger.addHandler(console_handler)
        
        # Create specialized loggers
        self.user_logger = logging.getLogger('user_interactions')
        self.user_logger.addHandler(user_handler)
        self.user_logger.setLevel(logging.INFO)
        
        # Payment logger for financial transactions
        payment_handler = logging.handlers.RotatingFileHandler(
            filename=self.log_dir / "payments.log",
            maxBytes=5*1024*1024,  # 5MB
            backupCount=5,  # Keep more payment logs
            encoding='utf-8'
        )
        payment_handler.setFormatter(detailed_formatter)
        
        self.payment_logger = logging.getLogger('payments')
        self.payment_logger.addHandler(payment_handler)
        self.payment_logger.setLevel(logging.INFO)
        
        # Admin actions logger
        admin_handler = logging.handlers.RotatingFileHandler(
            filename=self.log_dir / "admin_actions.log",
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3,
            encoding='utf-8'
        )
        admin_handler.setFormatter(detailed_formatter)
        
        self.admin_logger = logging.getLogger('admin_actions')
        self.admin_logger.addHandler(admin_handler)
        self.admin_logger.setLevel(logging.INFO)
        
        logging.info("🎯 Enhanced logging system initialized")
        logging.info(f"📁 Log files location: {self.log_dir.absolute()}")
        logging.info(f"📊 Log level: {logging.getLevelName(self.log_level)}")
    
    def log_user_interaction(self, user_id: int, username: str, action: str, details: str = ""):
        """Log user interactions for analysis"""
        message = f"USER:{user_id}(@{username}) - {action}"
        if details:
            message += f" - {details}"
        self.user_logger.info(message)
    
    def log_payment_action(self, user_id: int, action: str, amount: int = 0, course: str = "", admin_id: int = None):
        """Log payment-related actions"""
        message = f"PAYMENT - User:{user_id} - {action}"
        if amount:
            message += f" - Amount:{amount}"
        if course:
            message += f" - Course:{course}"
        if admin_id:
            message += f" - Admin:{admin_id}"
        self.payment_logger.info(message)
    
    def log_admin_action(self, admin_id: int, action: str, target_user: int = None, details: str = ""):
        """Log admin actions for audit trail"""
        message = f"ADMIN:{admin_id} - {action}"
        if target_user:
            message += f" - Target:{target_user}"
        if details:
            message += f" - {details}"
        self.admin_logger.info(message)
    
    def create_session_log(self):
        """Create a new session marker in logs"""
        session_start = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        separator = "=" * 80
        session_msg = f"BOT SESSION STARTED - {session_start}"
        
        logging.info(separator)
        logging.info(session_msg)
        logging.info(separator)
        
        return session_start
    
    def get_log_stats(self):
        """Get statistics about log files"""
        stats = {}
        for log_file in self.log_dir.glob("*.log"):
            if log_file.exists():
                size_mb = log_file.stat().st_size / (1024 * 1024)
                stats[log_file.name] = {
                    'size_mb': round(size_mb, 2),
                    'modified': datetime.fromtimestamp(log_file.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                }
        return stats

# Global logger instance
bot_logger = None

def setup_logging():
    """Initialize the enhanced logging system"""
    global bot_logger
    bot_logger = BotLogger()
    return bot_logger

def get_logger(name: str = None):
    """Get a logger instance"""
    return logging.getLogger(name) if name else logging.getLogger()

def log_user_action(user_id: int, username: str, action: str, details: str = ""):
    """Convenience function for logging user actions"""
    if bot_logger:
        bot_logger.log_user_interaction(user_id, username or "unknown", action, details)

def log_payment(user_id: int, action: str, **kwargs):
    """Convenience function for logging payments"""
    if bot_logger:
        bot_logger.log_payment_action(user_id, action, **kwargs)

def log_admin(admin_id: int, action: str, **kwargs):
    """Convenience function for logging admin actions"""
    if bot_logger:
        bot_logger.log_admin_action(admin_id, action, **kwargs)
