"""
Enhanced Error Handling and Logging System for Admin Operations
"""

import logging
import json
import traceback
from datetime import datetime
from typing import Dict, Any, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import os

class AdminErrorHandler:
    """Comprehensive error handling and logging for admin operations"""
    
    def __init__(self):
        self.setup_admin_logger()
        self.error_logs = []
        self.max_error_logs = 100  # Keep last 100 errors
        
    def setup_admin_logger(self):
        """Set up dedicated logger for admin operations"""
        # Create logs directory if it doesn't exist
        os.makedirs('logs', exist_ok=True)
        
        # Create admin-specific logger
        self.admin_logger = logging.getLogger('admin_operations')
        self.admin_logger.setLevel(logging.DEBUG)
        
        # Remove existing handlers to avoid duplicates
        for handler in self.admin_logger.handlers[:]:
            self.admin_logger.removeHandler(handler)
        
        # File handler for admin operations
        admin_file_handler = logging.FileHandler(
            'logs/admin_operations.log', 
            encoding='utf-8'
        )
        admin_file_handler.setLevel(logging.DEBUG)
        
        # Error-specific file handler
        error_file_handler = logging.FileHandler(
            'logs/admin_errors.log', 
            encoding='utf-8'
        )
        error_file_handler.setLevel(logging.ERROR)
        
        # Formatter for admin logs
        admin_formatter = logging.Formatter(
            '%(asctime)s - [ADMIN] - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        admin_file_handler.setFormatter(admin_formatter)
        error_file_handler.setFormatter(admin_formatter)
        
        self.admin_logger.addHandler(admin_file_handler)
        self.admin_logger.addHandler(error_file_handler)
        
        # Don't propagate to root logger to avoid duplicate messages
        self.admin_logger.propagate = False
        
        self.admin_logger.info("🚀 Admin Error Handler initialized successfully")

    async def log_admin_action(self, user_id: int, action: str, details: Dict[str, Any] = None):
        """Log admin actions for audit trail"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'admin_id': user_id,
            'action': action,
            'details': details or {},
            'type': 'admin_action'
        }
        
        self.admin_logger.info(f"Admin {user_id} performed action: {action} | Details: {details}")
        
        # Save to JSON file for easy querying
        await self.save_admin_log(log_entry)

    async def log_admin_error(self, user_id: int, error: Exception, context: str, 
                             update: Update = None, callback_data: str = None):
        """Log admin errors with full context"""
        error_entry = {
            'timestamp': datetime.now().isoformat(),
            'admin_id': user_id,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context,
            'callback_data': callback_data,
            'traceback': traceback.format_exc(),
            'type': 'admin_error'
        }
        
        # Add update context if available
        if update:
            error_entry['update_info'] = {
                'user_id': update.effective_user.id if update.effective_user else None,
                'chat_id': update.effective_chat.id if update.effective_chat else None,
                'message_id': update.effective_message.message_id if update.effective_message else None
            }
        
        self.admin_logger.error(
            f"ADMIN ERROR - User {user_id} | Context: {context} | "
            f"Error: {type(error).__name__}: {str(error)} | "
            f"Callback: {callback_data}"
        )
        
        # Store in memory for quick access
        self.error_logs.append(error_entry)
        if len(self.error_logs) > self.max_error_logs:
            self.error_logs.pop(0)
        
        # Save to persistent storage
        await self.save_admin_log(error_entry)

    async def save_admin_log(self, log_entry: Dict[str, Any]):
        """Save admin log entry to file"""
        try:
            log_file = 'logs/admin_audit.json'
            
            # Load existing logs
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
            else:
                logs = []
            
            # Add new log entry
            logs.append(log_entry)
            
            # Keep only last 1000 entries to prevent file from growing too large
            if len(logs) > 1000:
                logs = logs[-1000:]
            
            # Save back to file
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            self.admin_logger.error(f"Failed to save admin log: {e}")

    async def handle_admin_error(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                                error: Exception, operation_context: str, 
                                admin_id: int = None) -> bool:
        """
        Handle admin errors gracefully with user feedback
        Returns True if error was handled, False if it needs to be re-raised
        """
        try:
            # Get admin ID from update if not provided
            if not admin_id and update and update.effective_user:
                admin_id = update.effective_user.id
            
            # Log the error with full context
            callback_data = None
            if update and update.callback_query:
                callback_data = update.callback_query.data
            
            await self.log_admin_error(admin_id, error, operation_context, update, callback_data)
            
            # Create user-friendly error message
            error_message = self.create_user_error_message(error, operation_context)
            
            # Try to send error message to admin
            if update:
                try:
                    if update.callback_query:
                        await update.callback_query.answer("❌ خطا رخ داد! جزئیات در پیام ارسال شد.")
                        await update.callback_query.message.reply_text(error_message)
                    else:
                        await update.message.reply_text(error_message)
                except Exception as send_error:
                    self.admin_logger.error(f"Failed to send error message to admin: {send_error}")
            
            return True  # Error handled
            
        except Exception as handler_error:
            self.admin_logger.critical(f"ERROR HANDLER FAILED: {handler_error}")
            return False  # Let the error bubble up

    def create_user_error_message(self, error: Exception, context: str) -> str:
        """Create user-friendly error message for admins"""
        error_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Specific error messages based on error type
        if isinstance(error, KeyError):
            user_message = "🔑 خطای داده‌ای: کلید مورد نظر یافت نشد"
        elif isinstance(error, FileNotFoundError):
            user_message = "📁 خطای فایل: فایل مورد نظر یافت نشد"
        elif isinstance(error, json.JSONDecodeError):
            user_message = "📋 خطای JSON: فرمت داده نامعتبر"
        elif isinstance(error, PermissionError):
            user_message = "🔒 خطای دسترسی: عدم مجوز برای انجام عملیات"
        elif "timeout" in str(error).lower():
            user_message = "⏰ خطای زمان: عملیات بیش از حد طول کشید"
        else:
            user_message = f"❌ خطای سیستم: {type(error).__name__}"
        
        return f"""🚨 خطا در عملیات ادمین

🆔 کد خطا: {error_id}
📍 بخش: {context}
🔍 نوع خطا: {user_message}

💡 راهکارهای پیشنهادی:
• صفحه را رفرش کنید (/admin)
• چند ثانیه صبر کرده و مجددا تلاش کنید
• در صورت تکرار، با پشتیبانی تماس بگیرید

📊 جزئیات تکنیکی برای پشتیبانی:
• زمان: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
• خطا: {str(error)[:100]}"""

    async def get_error_summary(self, admin_id: int = None, limit: int = 10) -> str:
        """Get summary of recent errors for admin dashboard"""
        try:
            # Filter errors by admin if specified
            recent_errors = self.error_logs[-limit:]
            if admin_id:
                recent_errors = [e for e in recent_errors if e.get('admin_id') == admin_id]
            
            if not recent_errors:
                return "✅ هیچ خطای اخیری برای نمایش وجود ندارد"
            
            summary = "📊 خلاصه خطاهای اخیر:\n\n"
            
            for i, error in enumerate(recent_errors[-5:], 1):  # Last 5 errors
                timestamp = error['timestamp'][:16].replace('T', ' ')  # Format: YYYY-MM-DD HH:MM
                error_type = error['error_type']
                context = error['context']
                
                summary += f"{i}. {timestamp} | {error_type} | {context}\n"
            
            summary += f"\n📈 تعداد کل خطاها: {len(self.error_logs)}"
            summary += f"\n🔄 نمایش {len(recent_errors)} خطای اخیر"
            
            return summary
            
        except Exception as e:
            self.admin_logger.error(f"Failed to generate error summary: {e}")
            return "❌ خطا در تولید گزارش خطاها"

    async def clear_error_logs(self):
        """Clear error logs (for admin use)"""
        try:
            self.error_logs.clear()
            
            # Also clear the file
            log_file = 'logs/admin_audit.json'
            if os.path.exists(log_file):
                with open(log_file, 'w', encoding='utf-8') as f:
                    json.dump([], f)
            
            self.admin_logger.info("Admin error logs cleared")
            return True
        except Exception as e:
            self.admin_logger.error(f"Failed to clear error logs: {e}")
            return False

    def get_callback_debug_info(self, callback_data: str) -> str:
        """Get debug information for callback data"""
        debug_info = f"""🔍 Callback Debug Info:
        
📋 Raw Callback Data: {callback_data}
📏 Length: {len(callback_data)}
🎯 Type: {type(callback_data).__name__}

🔗 Pattern Matching:
• Starts with 'admin_': {callback_data.startswith('admin_')}
• Starts with 'plan_': {callback_data.startswith('plan_')}
• Starts with 'upload_': {callback_data.startswith('upload_')}
• Starts with 'send_': {callback_data.startswith('send_')}
• Starts with 'view_': {callback_data.startswith('view_')}

📊 Pattern Analysis:
• Contains underscore: {'_' in callback_data}
• Split by underscore: {callback_data.split('_')}
"""
        return debug_info

# Create global instance
admin_error_handler = AdminErrorHandler()
