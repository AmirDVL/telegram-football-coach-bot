# security_integration.py - Security Middleware for Main Bot

import functools
import logging
from typing import Callable, Any
from telegram import Update
from telegram.ext import ContextTypes
from security_config import security_manager

def security_check(max_requests_per_minute: int = 60):
    """Decorator for security checks on bot handlers"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs) -> Any:
            user_id = update.effective_user.id if update.effective_user else 0
            
            # Check if user is blocked
            if security_manager.is_user_blocked(user_id):
                await update.message.reply_text(
                    "⛔ دسترسی شما به دلیل فعالیت مشکوک محدود شده است.\n"
                    "برای رفع محدودیت با پشتیبانی تماس بگیرید."
                )
                return
            
            # Rate limiting check
            if not security_manager.rate_limit_check(user_id, max_requests_per_minute):
                await update.message.reply_text(
                    "⏱️ تعداد درخواست‌های شما بیش از حد مجاز است.\n"
                    "لطفاً چند دقیقه صبر کرده و دوباره تلاش کنید."
                )
                return
            
            # Input validation for text messages
            if update.message and update.message.text:
                if not security_manager.validate_input(update.message.text):
                    security_manager.log_suspicious_activity(user_id, "invalid_input", "HIGH")
                    await update.message.reply_text(
                        "❌ متن ارسالی نامعتبر است.\n"
                        "لطفاً از ارسال کاراکترهای خاص یا محتوای مشکوک خودداری کنید."
                    )
                    return
            
            # Call the original function
            return await func(self, update, context, *args, **kwargs)
        
        return wrapper
    return decorator


def admin_security_check(required_permission: str = "admin"):
    """Decorator for admin-only functions with enhanced security"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs) -> Any:
            user_id = update.effective_user.id if update.effective_user else 0
            
            # Check admin status
            if not await self.admin_panel.is_admin(user_id):
                security_manager.log_suspicious_activity(user_id, "unauthorized_admin_access", "HIGH")
                await update.message.reply_text(
                    "⛔ شما دسترسی ادمین ندارید."
                )
                return
            
            # Additional security checks for admin functions
            if not security_manager.rate_limit_check(user_id, max_requests=30):
                await update.message.reply_text(
                    "⏱️ تعداد درخواست‌های ادمین بیش از حد مجاز است."
                )
                return
            
            # Log admin action
            security_manager.security_logger.info(f"Admin action: {func.__name__} by user {user_id}")
            
            return await func(self, update, context, *args, **kwargs)
        
        return wrapper
    return decorator


def file_upload_security(allowed_types: list = None):
    """Decorator for secure file upload handling"""
    if allowed_types is None:
        allowed_types = ['photo', 'document']
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs) -> Any:
            user_id = update.effective_user.id if update.effective_user else 0
            
            # Check rate limiting for file uploads
            if not security_manager.rate_limit_check(user_id, max_requests=10):
                await update.message.reply_text(
                    "⏱️ تعداد آپلود فایل بیش از حد مجاز است.\n"
                    "لطفاً چند دقیقه صبر کنید."
                )
                return
            
            # Validate file type
            if update.message.photo and 'photo' not in allowed_types:
                security_manager.log_suspicious_activity(user_id, "invalid_file_type_photo", "MEDIUM")
                await update.message.reply_text(
                    "❌ نوع فایل مجاز نیست."
                )
                return
            
            if update.message.document and 'document' not in allowed_types:
                security_manager.log_suspicious_activity(user_id, "invalid_file_type_document", "MEDIUM")
                await update.message.reply_text(
                    "❌ نوع فایل مجاز نیست."
                )
                return
            
            # Validate file size for photos
            if update.message.photo:
                photo = update.message.photo[-1]  # Get largest size
                if photo.file_size and photo.file_size > 20 * 1024 * 1024:  # 20MB
                    security_manager.log_suspicious_activity(user_id, "oversized_file_upload", "MEDIUM")
                    await update.message.reply_text(
                        "❌ حجم فایل بیش از حد مجاز است (حداکثر ۲۰ مگابایت)."
                    )
                    return
            
            return await func(self, update, context, *args, **kwargs)
        
        return wrapper
    return decorator


class SecurityMiddleware:
    """Security middleware for the bot application"""
    
    def __init__(self, bot_instance):
        self.bot = bot_instance
        self.logger = logging.getLogger(__name__)
    
    async def log_user_activity(self, user_id: int, action: str, details: str = ""):
        """Log user activity for monitoring"""
        try:
            # This would integrate with your database manager
            if hasattr(self.bot, 'database_manager'):
                await self.bot.database_manager._log_security_event(
                    user_id, action, details, "INFO"
                )
        except Exception as e:
            self.logger.error(f"Failed to log user activity: {e}")
    
    async def check_user_permissions(self, user_id: int, action: str) -> bool:
        """Check if user has permission for specific action"""
        try:
            # Check if user is blocked
            if security_manager.is_user_blocked(user_id):
                return False
            
            # Check rate limits based on action type
            if action in ['message', 'command']:
                return security_manager.rate_limit_check(user_id, max_requests=60)
            elif action in ['file_upload', 'photo_upload']:
                return security_manager.rate_limit_check(user_id, max_requests=10)
            elif action in ['admin_action']:
                return security_manager.rate_limit_check(user_id, max_requests=30)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking user permissions: {e}")
            return False
    
    async def sanitize_user_input(self, text: str) -> str:
        """Sanitize user input"""
        if not text:
            return ""
        
        # Remove potentially dangerous characters
        import re
        
        # Remove control characters except newlines and tabs
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
        
        # Limit length
        if len(text) > 2000:
            text = text[:2000] + "..."
        
        return text
    
    async def generate_security_report(self) -> dict:
        """Generate security report for admin"""
        try:
            # Get security manager report
            sm_report = security_manager.get_security_report()
            
            # Get database security report if available
            db_report = {}
            if hasattr(self.bot, 'database_manager'):
                db_report = await self.bot.database_manager.get_security_report()
            
            return {
                'security_manager': sm_report,
                'database_security': db_report,
                'middleware_status': 'active'
            }
            
        except Exception as e:
            self.logger.error(f"Error generating security report: {e}")
            return {'error': str(e)}


# Example of how to apply security to your existing handlers
def secure_bot_handler(original_class):
    """Class decorator to add security to all bot handlers"""
    
    # List of methods that should have security checks
    secured_methods = [
        'start', 'handle_payment_receipt', 'handle_questionnaire_response',
        'handle_questionnaire_photo', 'handle_unsupported_file'
    ]
    
    for method_name in secured_methods:
        if hasattr(original_class, method_name):
            original_method = getattr(original_class, method_name)
            
            # Apply security decorator
            if method_name in ['handle_payment_receipt', 'handle_questionnaire_photo']:
                # File upload methods need file security
                secured_method = file_upload_security(['photo'])(
                    security_check(max_requests_per_minute=30)(original_method)
                )
            else:
                # Regular methods need basic security
                secured_method = security_check(max_requests_per_minute=60)(original_method)
            
            setattr(original_class, method_name, secured_method)
    
    return original_class


# Usage example for your main.py:
"""
from security_integration import secure_bot_handler, SecurityMiddleware

@secure_bot_handler
class FootballCoachBot:
    def __init__(self):
        # ... your existing initialization
        self.security_middleware = SecurityMiddleware(self)
    
    # Your existing methods will automatically have security applied
"""
