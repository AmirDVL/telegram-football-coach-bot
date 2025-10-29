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
import tempfile
import zipfile

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
        """Save admin log entry to file with enhanced error recovery"""
        try:
            log_file = 'logs/admin_audit.json'
            
            # First, try to load existing logs with error recovery
            logs = []
            if os.path.exists(log_file):
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                        if content:
                            logs = json.loads(content)
                except json.JSONDecodeError as e:
                    self.admin_logger.error(f"Corrupted JSON in admin_audit.json at position {e.pos}: {e}")
                    # Try to recover by creating a backup and starting fresh
                    backup_file = f'logs/admin_audit_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
                    try:
                        # Move corrupted file to backup
                        if os.path.exists(log_file):
                            os.rename(log_file, backup_file)
                        self.admin_logger.warning(f"Corrupted log file backed up to {backup_file}, starting with fresh logs")
                    except Exception as backup_error:
                        self.admin_logger.error(f"Failed to backup corrupted log file: {backup_error}")
                    logs = []
                except Exception as read_error:
                    self.admin_logger.error(f"Error reading admin log file: {read_error}")
                    logs = []
            
            # Add new log entry
            logs.append(log_entry)
            
            # Keep only last 1000 entries to prevent file from growing too large
            if len(logs) > 1000:
                logs = logs[-1000:]
            
            # Save back to file with atomic write operation
            temp_file = f"{log_file}.tmp"
            try:
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(logs, f, ensure_ascii=False, indent=2)
                
                # Atomic move - only replace the original file if write succeeded
                if os.path.exists(temp_file):
                    if os.path.exists(log_file):
                        os.remove(log_file)
                    os.rename(temp_file, log_file)
            except Exception as write_error:
                # Clean up temp file if write failed
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except:
                        pass
                raise write_error
                
        except Exception as e:
            self.admin_logger.error(f"Failed to save admin log: {e}")
            # Don't re-raise the exception to prevent recursive logging errors

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
        elif "There is no text in the message to edit" in str(error):
            user_message = "📝 خطای ویرایش پیام: نمی‌توان پیام تصویری را با متن جایگزین کرد"
        elif "BadRequest" in str(error):
            user_message = "📡 خطای درخواست: درخواست نامعتبر به تلگرام"
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

    async def repair_corrupted_logs(self):
        """Repair corrupted admin log files"""
        log_file = 'logs/admin_audit.json'
        repaired = False
        
        if not os.path.exists(log_file):
            self.admin_logger.info("No admin log file to repair")
            return False
            
        try:
            # Try to read the file
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content:
                    json.loads(content)
                    self.admin_logger.info("Admin log file is valid, no repair needed")
                    return False
        except json.JSONDecodeError as e:
            self.admin_logger.error(f"Detected corrupted JSON in admin logs at position {e.pos}")
            
            # Create backup of corrupted file
            backup_file = f'logs/admin_audit_corrupted_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            try:
                os.rename(log_file, backup_file)
                self.admin_logger.info(f"Corrupted log file backed up to {backup_file}")
            except Exception as backup_error:
                self.admin_logger.error(f"Failed to backup corrupted file: {backup_error}")
            
            # Create fresh log file
            try:
                with open(log_file, 'w', encoding='utf-8') as f:
                    json.dump([], f, ensure_ascii=False, indent=2)
                self.admin_logger.info("Created fresh admin log file")
                repaired = True
            except Exception as create_error:
                self.admin_logger.error(f"Failed to create fresh log file: {create_error}")
                
        except Exception as e:
            self.admin_logger.error(f"Error checking admin log file: {e}")
            
        return repaired

    async def clear_error_logs(self):
        """Clear error logs (for admin use)"""
        try:
            self.error_logs.clear()
            
            # Also clear the file  
            log_file = 'logs/admin_audit.json'
            if os.path.exists(log_file):
                with open(log_file, 'w', encoding='utf-8') as f:
                    json.dump([], f, ensure_ascii=False, indent=2)
            
            self.admin_logger.info("Admin error logs cleared")
            return True
        except Exception as e:
            self.admin_logger.error(f"Failed to clear error logs: {e}")
            return False

    async def log_document_export_debug(self, user_id: int, export_user_id: str, 
                                      questionnaire_data: Dict, documents_found: int,
                                      export_result: Dict = None):
        """Enhanced logging specifically for document export operations"""
        debug_entry = {
            'timestamp': datetime.now().isoformat(),
            'admin_id': user_id,
            'action': 'document_export_debug',
            'export_user_id': export_user_id,
            'questionnaire_data_structure': {
                'has_answers': 'answers' in questionnaire_data,
                'answer_keys': list(questionnaire_data.get('answers', {}).keys()) if questionnaire_data.get('answers') else [],
                'has_documents_key': 'documents' in questionnaire_data.get('answers', {}),
                'documents_data_type': str(type(questionnaire_data.get('answers', {}).get('documents', {}))),
                'documents_data_content': questionnaire_data.get('answers', {}).get('documents', {}),
                'completed': questionnaire_data.get('completed', False),
                'completion_timestamp': questionnaire_data.get('completion_timestamp', 'None')
            },
            'documents_found': documents_found,
            'export_result': export_result or {},
            'type': 'document_export_debug'
        }
        
        # Detailed logging
        self.admin_logger.info(
            f"DOCUMENT EXPORT DEBUG - Admin {user_id} exporting user {export_user_id} | "
            f"Documents found: {documents_found} | "
            f"Questionnaire completed: {questionnaire_data.get('completed', False)} | "
            f"Answer keys: {list(questionnaire_data.get('answers', {}).keys())}"
        )
        
        # Save detailed debug info
        await self.save_admin_log(debug_entry)
        
        return debug_entry

    async def log_file_operation(self, operation: str, file_type: str, file_id: str = None,
                                local_path: str = None, success: bool = True, 
                                error_message: str = None, admin_id: int = None):
        """Log file operations (download, zip creation, etc.)"""
        operation_entry = {
            'timestamp': datetime.now().isoformat(),
            'admin_id': admin_id,
            'action': 'file_operation',
            'operation': operation,  # 'download', 'zip_create', 'zip_add_file', etc.
            'file_type': file_type,  # 'document', 'photo', 'zip'
            'file_id': file_id,
            'local_path': local_path,
            'success': success,
            'error_message': error_message,
            'type': 'file_operation'
        }
        
        if success:
            self.admin_logger.info(
                f"FILE OPERATION SUCCESS - {operation} {file_type} | "
                f"File ID: {file_id} | Path: {local_path}"
            )
        else:
            self.admin_logger.error(
                f"FILE OPERATION FAILED - {operation} {file_type} | "
                f"File ID: {file_id} | Error: {error_message}"
            )
        
        await self.save_admin_log(operation_entry)

    async def log_questionnaire_data_analysis(self, user_id: str, questionnaire_data: Dict):
        """Detailed analysis of questionnaire data structure for debugging"""
        analysis = {
            'timestamp': datetime.now().isoformat(),
            'action': 'questionnaire_data_analysis',
            'user_id': user_id,
            'type': 'questionnaire_analysis'
        }
        
        if not questionnaire_data:
            analysis['status'] = 'no_data'
            analysis['message'] = 'No questionnaire data found'
        else:
            answers = questionnaire_data.get('answers', {})
            analysis.update({
                'status': 'data_found',
                'completed': questionnaire_data.get('completed', False),
                'total_answer_keys': len(answers),
                'answer_keys': list(answers.keys()),
                'documents_analysis': {},
                'photos_analysis': {}
            })
            
            # Analyze documents
            documents_data = answers.get('documents', {})
            analysis['documents_analysis'] = {
                'exists': 'documents' in answers,
                'type': str(type(documents_data)),
                'content': documents_data if isinstance(documents_data, dict) else str(documents_data),
                'keys': list(documents_data.keys()) if isinstance(documents_data, dict) else []
            }
            
            # Analyze photos
            photos_data = answers.get('photos', {})
            analysis['photos_analysis'] = {
                'exists': 'photos' in answers,
                'type': str(type(photos_data)),
                'keys': list(photos_data.keys()) if isinstance(photos_data, dict) else [],
                'total_photos': sum(len(p) if isinstance(p, list) else 1 for p in photos_data.values()) if isinstance(photos_data, dict) else 0
            }
            
            # Check for document-type answers in individual steps
            document_type_answers = {}
            for step, answer in answers.items():
                if isinstance(answer, dict) and answer.get('type') == 'document':
                    document_type_answers[step] = answer
            analysis['document_type_answers'] = document_type_answers
        
        self.admin_logger.info(f"QUESTIONNAIRE ANALYSIS - User {user_id} | Status: {analysis.get('status')} | Documents: {analysis.get('documents_analysis', {}).get('exists', False)}")
        await self.save_admin_log(analysis)
        
        return analysis

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

    async def log_plan_upload_workflow(self, admin_id: int, step: str, plan_data: dict = None, 
                                     success: bool = None, error_message: str = None):
        """Enhanced logging for plan upload workflow"""
        workflow_entry = {
            'timestamp': datetime.now().isoformat(),
            'admin_id': admin_id,
            'action': 'plan_upload_workflow',
            'step': step,  # 'start', 'file_received', 'description_received', 'save_attempt', 'save_success', 'save_failed'
            'plan_data': plan_data or {},
            'success': success,
            'error_message': error_message,
            'type': 'plan_workflow'
        }
        
        if success is True:
            self.admin_logger.info(f"PLAN WORKFLOW SUCCESS - Admin {admin_id} | Step: {step} | Plan: {plan_data.get('title', 'N/A')}")
        elif success is False:
            self.admin_logger.error(f"PLAN WORKFLOW FAILED - Admin {admin_id} | Step: {step} | Error: {error_message}")
        else:
            self.admin_logger.info(f"PLAN WORKFLOW STEP - Admin {admin_id} | Step: {step}")
        
        await self.save_admin_log(workflow_entry)

    async def log_navigation_action(self, admin_id: int, current_menu: str, action: str, 
                                  destination: str = None, context_data: dict = None):
        """Log admin navigation for debugging flow issues"""
        nav_entry = {
            'timestamp': datetime.now().isoformat(),
            'admin_id': admin_id,
            'action': 'admin_navigation',
            'current_menu': current_menu,
            'navigation_action': action,
            'destination': destination,
            'context_data': context_data or {},
            'type': 'admin_navigation'
        }
        
        self.admin_logger.info(
            f"ADMIN NAVIGATION - Admin {admin_id} | From: {current_menu} | Action: {action} | To: {destination}"
        )
        
        await self.save_admin_log(nav_entry)

    async def log_input_state_issue(self, user_id: int, expected_state: str, actual_input: str,
                                  problematic_flag: str = None):
        """Log input state confusion issues (like coupon input bug)"""
        state_entry = {
            'timestamp': datetime.now().isoformat(),
            'user_id': user_id,
            'action': 'input_state_issue',
            'expected_state': expected_state,
            'actual_input': actual_input,
            'problematic_flag': problematic_flag,
            'type': 'input_state_bug'
        }
        
        self.admin_logger.warning(
            f"INPUT STATE BUG - User {user_id} | Expected: {expected_state} | Input: {actual_input} | Flag: {problematic_flag}"
        )
        
        await self.save_admin_log(state_entry)

    async def log_plan_management_debug(self, admin_id: int, operation: str, 
                                      course_type: str = None, user_id: str = None,
                                      plans_before: int = None, plans_after: int = None,
                                      success: bool = None, details: dict = None):
        """Comprehensive logging for plan management operations"""
        debug_entry = {
            'timestamp': datetime.now().isoformat(),
            'admin_id': admin_id,
            'action': 'plan_management_debug',
            'operation': operation,  # 'load_plans', 'save_plans', 'filter_plans', 'display_plans'
            'course_type': course_type,
            'target_user_id': user_id,
            'plans_before_count': plans_before,
            'plans_after_count': plans_after,
            'success': success,
            'details': details or {},
            'type': 'plan_management_debug'
        }
        
        status = "SUCCESS" if success else "FAILED" if success is False else "INFO"
        self.admin_logger.info(
            f"PLAN MANAGEMENT {status} - Admin {admin_id} | Operation: {operation} | "
            f"Course: {course_type} | User: {user_id} | Plans: {plans_before}→{plans_after}"
        )
        
        await self.save_admin_log(debug_entry)
        return debug_entry

    async def clear_all_input_states(self, context, user_id: int, navigation_context: str = "unknown"):
        """
        Clear ALL possible input waiting states for a user - COMPREHENSIVE VERSION
        This is called when user navigates away from input panels or uses /start
        """
        states_cleared = []
        
        # COMPREHENSIVE list of ALL possible input waiting states in the entire bot
        input_states = [
            # Core input states
            'waiting_for_coupon',
            'coupon_course',
            'current_course_selection',
            'course_selected',
            'buying_additional_course',
            
            # Payment related states  
            'awaiting_payment_receipt',
            'payment_pending',
            'payment_receipt_uploaded',
            'payment_course',
            
            # Admin upload states
            'uploading_plan',
            'uploading_user_plan', 
            'plan_course_type',
            'plan_course_code', 
            'plan_user_id',
            'plan_upload_step',
            'plan_title',
            'plan_content',
            'plan_content_type',
            'plan_filename',
            'plan_description',
            
            # Admin workflow states
            'awaiting_admin_input',
            'creating_coupon',
            'editing_user_data',
            'exporting_data',
            'admin_awaiting_input',
            
            # Questionnaire states
            'questionnaire_active',
            'questionnaire_step',
            'questionnaire_course',
            'awaiting_questionnaire_response',
            'current_step',
            'questionnaire_started',
            
            # Form and workflow states
            'awaiting_form',
            'form_step',
            'current_question_step',
            
            # Document and file states
            'awaiting_document',
            'awaiting_photo',
            'document_upload_pending',
            'photo_upload_pending',
            
            # Navigation states that might persist
            'menu_state',
            'current_menu',
            'previous_menu',
            'navigation_stack',
            
            # Any other potential stuck states
            'input_mode',
            'waiting_mode',
            'processing_mode',
            'temp_state',
            'callback_waiting'
        ]
        
        # Clear all input states from user-specific data
        if user_id in context.user_data:
            for state in input_states:
                if state in context.user_data[user_id]:
                    context.user_data[user_id].pop(state, None)
                    states_cleared.append(f"user_{state}")
        
        # Clear global context states (some states are stored globally)
        for state in input_states:
            if state in context.user_data:
                context.user_data.pop(state, None)
                states_cleared.append(f"global_{state}")
        
        # Clear the entire user context if it's mostly empty to prevent stale references
        if user_id in context.user_data:
            user_context = context.user_data[user_id]
            # Count non-essential keys
            essential_keys = {'user_id', 'name', 'username', 'last_interaction'}
            non_essential_keys = set(user_context.keys()) - essential_keys
            
            if len(non_essential_keys) > 0:
                # Clear non-essential keys to ensure clean state
                for key in list(non_essential_keys):
                    if key in user_context:
                        user_context.pop(key, None)
                        states_cleared.append(f"cleanup_{key}")
        
        # Log the state clearing for debugging
        if states_cleared:
            await self.log_input_state_issue(
                user_id=user_id,
                expected_state="navigation_away",
                actual_input=navigation_context,
                problematic_flag=f"cleared_states: {', '.join(states_cleared[:10])}..."  # Limit log size
            )
            
            self.admin_logger.info(
                f"COMPREHENSIVE STATE CLEARING - User {user_id} | Context: {navigation_context} | "
                f"Cleared: {len(states_cleared)} states"
            )
        
        return states_cleared

    async def setup_admin_directories(self):
        """Create organized directory structure for admin operations"""
        directories = [
            'admin_data',
            'admin_data/course_plans',
            'admin_data/uploads',
            'admin_data/exports',
            'admin_data/backups'
        ]
        
        created_dirs = []
        for directory in directories:
            try:
                os.makedirs(directory, exist_ok=True)
                created_dirs.append(directory)
            except Exception as e:
                self.admin_logger.error(f"Failed to create directory {directory}: {e}")
        
        if created_dirs:
            self.admin_logger.info(f"✅ Admin directory structure created: {', '.join(created_dirs)}")
        
        return created_dirs

    async def migrate_legacy_admin_files(self):
        """Migrate legacy admin files to organized structure"""
        import shutil
        migration_results = []
        
        # Define legacy file mappings to new locations
        legacy_mappings = [
            ('course_plans_*.json', 'admin_data/course_plans/'),
            ('admin_audit.json', 'admin_data/'),
            ('admin_operations.log', 'logs/'),
            ('admin_errors.log', 'logs/')
        ]
        
        for pattern, target_dir in legacy_mappings:
            try:
                import glob
                if '*' in pattern:
                    # Handle wildcard patterns
                    files = glob.glob(pattern)
                    for file_path in files:
                        if os.path.exists(file_path):
                            filename = os.path.basename(file_path)
                            # Remove prefix for course plans
                            if 'course_plans_' in filename:
                                new_filename = filename.replace('course_plans_', '').replace('.json', '.json')
                            else:
                                new_filename = filename
                            
                            target_path = os.path.join(target_dir, new_filename)
                            os.makedirs(target_dir, exist_ok=True)
                            shutil.move(file_path, target_path)
                            migration_results.append(f"✅ {file_path} → {target_path}")
                            self.admin_logger.info(f"Migrated {file_path} to {target_path}")
                else:
                    # Handle single files
                    if os.path.exists(pattern):
                        filename = os.path.basename(pattern)
                        target_path = os.path.join(target_dir, filename)
                        os.makedirs(target_dir, exist_ok=True)
                        shutil.move(pattern, target_path)
                        migration_results.append(f"✅ {pattern} → {target_path}")
                        self.admin_logger.info(f"Migrated {pattern} to {target_path}")
                        
            except Exception as e:
                migration_results.append(f"❌ Failed to migrate {pattern}: {e}")
                self.admin_logger.error(f"Failed to migrate {pattern}: {e}")
        
        return migration_results

    async def reset_questionnaire_state(self, user_id: int, questionnaire_manager, reason: str = "user_navigation"):
        """
        Reset questionnaire progress for a user
        This is called when user wants to completely restart or abandon questionnaire
        """
        try:
            # Log the questionnaire reset
            self.admin_logger.info(
                f"QUESTIONNAIRE RESET - User {user_id} | Reason: {reason}"
            )
            
            # Reset questionnaire progress in questionnaire_manager
            await questionnaire_manager.reset_user_progress(user_id)
            
            # Log the reset action
            await self.log_input_state_issue(
                user_id=user_id,
                expected_state="questionnaire_reset",
                actual_input=reason,
                problematic_flag="questionnaire_progress_reset"
            )
            
            return True
            
        except Exception as e:
            self.admin_logger.error(f"Failed to reset questionnaire state for user {user_id}: {e}")
            return False

    async def clear_admin_input_states(self, admin_panel_instance, user_id: int, navigation_context: str = "unknown"):
        """
        Clear admin-specific input states from admin panel and context.user_data
        """
        admin_states_cleared = []
        
        # Clear admin coupon creation state
        if user_id in admin_panel_instance.admin_creating_coupons:
            admin_panel_instance.admin_creating_coupons.discard(user_id)
            admin_states_cleared.append("admin_creating_coupons")
        
        # Log admin state clearing
        if admin_states_cleared:
            self.admin_logger.info(
                f"ADMIN STATE CLEARING - Admin {user_id} | Context: {navigation_context} | "
                f"Cleared: {', '.join(admin_states_cleared)}"
            )
            
            await self.log_input_state_issue(
                user_id=user_id,
                expected_state="admin_navigation_away",
                actual_input=navigation_context,
                problematic_flag=f"admin_states_cleared: {', '.join(admin_states_cleared)}"
            )
        
        return admin_states_cleared
    
    async def clear_admin_plan_upload_states(self, context, user_id: int, reason: str = "navigation"):
        """
        Clear plan upload states from context.user_data to prevent stuck upload modes
        Should be called when admin navigates away (e.g., /start command)
        """
        states_cleared = []
        
        if user_id in context.user_data:
            upload_states = [
                'uploading_plan',
                'uploading_user_plan', 
                'plan_course_type',
                'plan_course_code',
                'plan_user_id',
                'plan_upload_step',
                'plan_title',
                'plan_content',
                'plan_content_type',
                'plan_filename',
                'plan_description',
                'plan_local_path',
                'plan_file_size'
            ]
            
            for state in upload_states:
                if state in context.user_data[user_id]:
                    context.user_data[user_id].pop(state, None)
                    states_cleared.append(state)
        
        if states_cleared:
            self.admin_logger.info(
                f"PLAN UPLOAD STATE CLEARING - Admin {user_id} | Reason: {reason} | "
                f"Cleared {len(states_cleared)} states: {', '.join(states_cleared)}"
            )
        
        return states_cleared

    async def log_questionnaire_flow_debug(self, user_id: int, context: str, questionnaire_data: dict, 
                                          flow_decision: str, details: dict = None):
        """Log questionnaire flow decisions for debugging edge cases"""
        flow_entry = {
            'timestamp': datetime.now().isoformat(),
            'user_id': user_id,
            'action': 'questionnaire_flow_debug',
            'context': context,  # 'payment_approved', 'start_command', 'resume_questionnaire', etc.
            'questionnaire_data': {
                'current_step': questionnaire_data.get('current_step', 0),
                'completed': questionnaire_data.get('completed', False),
                'has_answers': bool(questionnaire_data.get('answers', {})),
                'answer_count': len(questionnaire_data.get('answers', {})),
                'started_at': questionnaire_data.get('started_at', 'unknown')
            },
            'flow_decision': flow_decision,  # 'resume_existing', 'start_fresh', 'show_completed', etc.
            'details': details or {},
            'type': 'questionnaire_flow_debug'
        }
        
        self.admin_logger.info(
            f"QUESTIONNAIRE FLOW - User {user_id} | Context: {context} | "
            f"Step: {questionnaire_data.get('current_step', 0)} | "
            f"Completed: {questionnaire_data.get('completed', False)} | "
            f"Decision: {flow_decision}"
        )
        
        await self.save_admin_log(flow_entry)
        return flow_entry

    async def log_state_clearing_debug(self, user_id: int, navigation_action: str, 
                                     states_before: dict, states_after: dict):
        """Log detailed state clearing information for debugging"""
        clearing_entry = {
            'timestamp': datetime.now().isoformat(),
            'user_id': user_id,
            'action': 'state_clearing_debug',
            'navigation_action': navigation_action,
            'states_before': states_before,
            'states_after': states_after,
            'states_cleared': list(set(states_before.keys()) - set(states_after.keys())),
            'type': 'state_clearing_debug'
        }
        
        self.admin_logger.info(
            f"STATE CLEARING DEBUG - User {user_id} | Action: {navigation_action} | "
            f"Cleared: {clearing_entry['states_cleared']}"
        )
        
        await self.save_admin_log(clearing_entry)
        return clearing_entry

# Create global instance
admin_error_handler = AdminErrorHandler()
