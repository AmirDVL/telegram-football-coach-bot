import logging
import logging.handlers
import asyncio
import os
import json
import csv
import io
import traceback
from datetime import datetime
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

from config import Config
from data_manager import DataManager
from database_manager import DatabaseManager
from admin_panel import AdminPanel
from questionnaire_manager import QuestionnaireManager
from image_processor import ImageProcessor
from coupon_manager import CouponManager
from admin_error_handler import admin_error_handler
from input_validator import sanitize_text

# Enhanced logging configuration
def setup_enhanced_logging():
    """Set up comprehensive logging with file rotation and multiple log files"""
    # Create logs directory if it doesn't exist
    logs_dir = "logs"
    os.makedirs(logs_dir, exist_ok=True)
    
    # Remove all existing handlers to start fresh
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Set root logger level based on debug mode
    log_level = logging.DEBUG if Config.DEBUG else logging.INFO
    root_logger.setLevel(log_level)
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # 1. Main application log (rotating)
    main_handler = logging.handlers.RotatingFileHandler(
        filename=os.path.join(logs_dir, "bot.log"),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    main_handler.setLevel(logging.INFO)
    main_handler.setFormatter(detailed_formatter)
    
    # 2. Error-only log
    error_handler = logging.handlers.RotatingFileHandler(
        filename=os.path.join(logs_dir, "errors.log"),
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    
    # 3. Debug log (if debug mode is on)
    if Config.DEBUG:
        debug_handler = logging.handlers.RotatingFileHandler(
            filename=os.path.join(logs_dir, "debug.log"),
            maxBytes=20*1024*1024,  # 20MB
            backupCount=2,
            encoding='utf-8'
        )
        debug_handler.setLevel(logging.DEBUG)
        debug_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(debug_handler)
    
    # 4. Console handler (for terminal output)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    
    # 5. User interactions log (for analytics)
    user_handler = logging.handlers.RotatingFileHandler(
        filename=os.path.join(logs_dir, "user_interactions.log"),
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3,
        encoding='utf-8'
    )
    user_handler.setLevel(logging.INFO)
    user_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    
    # 6. Admin actions log (for audit trail)
    admin_handler = logging.handlers.RotatingFileHandler(
        filename=os.path.join(logs_dir, "admin_actions.log"),
        maxBytes=5*1024*1024,  # 5MB
        backupCount=5,
        encoding='utf-8'
    )
    admin_handler.setLevel(logging.INFO)
    admin_handler.setFormatter(detailed_formatter)
    
    # 7. Payment transactions log (for financial audit)
    payment_handler = logging.handlers.RotatingFileHandler(
        filename=os.path.join(logs_dir, "payments.log"),
        maxBytes=5*1024*1024,  # 5MB
        backupCount=10,  # Keep more payment logs
        encoding='utf-8'
    )
    payment_handler.setLevel(logging.INFO)
    payment_handler.setFormatter(detailed_formatter)
    
    # Add all handlers to root logger
    root_logger.addHandler(main_handler)
    root_logger.addHandler(error_handler)
    root_logger.addHandler(console_handler)
    
    # Create specialized loggers
    user_logger = logging.getLogger('user_interactions')
    user_logger.addHandler(user_handler)
    user_logger.setLevel(logging.INFO)
    
    admin_logger = logging.getLogger('admin_actions')
    admin_logger.addHandler(admin_handler)
    admin_logger.setLevel(logging.INFO)
    
    payment_logger = logging.getLogger('payments')
    payment_logger.addHandler(payment_handler)
    payment_logger.setLevel(logging.INFO)
    
    error_logger = logging.getLogger('errors')
    error_logger.addHandler(error_handler)
    error_logger.setLevel(logging.ERROR)
    
    # Log startup information
    logging.info("=" * 80)
    logging.info("🤖 Football Coach Bot Enhanced Logging System Initialized")
    logging.info(f"📁 Log files location: {os.path.abspath(logs_dir)}")
    logging.info(f"📊 Log level: {logging.getLevelName(log_level)}")
    logging.info(f"🔧 Debug mode: {'ON' if Config.DEBUG else 'OFF'}")
    logging.info("=" * 80)
    
    return {
        'main': logging.getLogger(__name__),
        'user': user_logger,
        'admin': admin_logger,
        'payment': payment_logger,
        'error': error_logger
    }

# Initialize enhanced logging
loggers = setup_enhanced_logging()
logger = loggers['main']
user_logger = loggers['user']
admin_logger = loggers['admin']
payment_logger = loggers['payment']
error_logger = loggers['error']

# Convenience functions for logging
def log_user_action(user_id: int, username: str, action: str, details: str = ""):
    """Log user interactions for analytics"""
    message = f"USER:{user_id}(@{username}) - {action}"
    if details:
        message += f" - {details}"
    user_logger.info(message)

def log_admin_action(admin_id: int, action: str, details: str = ""):
    """Log admin actions for audit trail"""
    message = f"ADMIN:{admin_id} - {action}"
    if details:
        message += f" - {details}"
    admin_logger.info(message)

def log_payment_action(user_id: int, action: str, amount: int = 0, course: str = "", admin_id: int = None):
    """Log payment-related actions"""
    message = f"PAYMENT - User:{user_id} - {action}"
    if amount:
        message += f" - Amount:{amount}"
    if course:
        message += f" - Course:{course}"
    if admin_id:
        message += f" - Admin:{admin_id}"
    payment_logger.info(message)

class FootballCoachBot:
    def __init__(self):
        # Initialize data manager based on USE_DATABASE setting
        if Config.USE_DATABASE:
            self.data_manager = DatabaseManager()
            logger.info("🗄️ Using PostgreSQL Database Manager")
        else:
            self.data_manager = DataManager()
            logger.info("📁 Using JSON File Data Manager")
            
        self.admin_panel = AdminPanel()
        self.questionnaire_manager = QuestionnaireManager()
        self.image_processor = ImageProcessor()
        self.coupon_manager = CouponManager()
        self.payment_pending = {}
        self.user_coupon_codes = {}  # Store coupon codes entered by users
        self.user_last_action = {}  # Cooldown protection - track last action time per user
        self.processing_payments = set()  # Track payments currently being processed to prevent race conditions
    
    async def check_cooldown(self, user_id: int) -> bool:
        """Check if user is in cooldown period (0.5s). Returns True if should skip action."""
        current_time = time.time()
        last_action = self.user_last_action.get(user_id, 0)
        
        if current_time - last_action < 0.5:  # 0.5 second cooldown
            logger.debug(f"🕐 COOLDOWN - User {user_id} action skipped (too fast)")
            return True
            
        self.user_last_action[user_id] = current_time
        return False
    
    async def safe_edit_message(self, query, text, reply_markup=None, parse_mode=None):
        """Safely edit message to prevent 'Message is not modified' errors"""
        try:
            # Check if current message text is different
            if hasattr(query.message, 'text') and query.message.text == text:
                logger.debug("🔄 Message content identical, skipping edit to prevent 'Message is not modified' error")
                return
                
            await query.edit_message_text(
                text, 
                reply_markup=reply_markup, 
                parse_mode=parse_mode
            )
        except Exception as e:
            if "message is not modified" in str(e).lower():
                logger.debug(f"⚠️ Message not modified: {e}")
            elif "can't parse entities" in str(e).lower():
                logger.error(f"❌ Markdown parsing error: {e}")
                # Try to send without parse_mode as fallback
                try:
                    await query.edit_message_text(text, reply_markup=reply_markup)
                except Exception as fallback_error:
                    logger.error(f"❌ Fallback edit also failed: {fallback_error}")
            else:
                logger.error(f"❌ Unexpected error editing message: {e}")
                raise

    async def initialize(self):
        """Initialize bot on startup - comprehensive admin sync"""
        try:
            logger.info("🔧 Initializing admin sync from environment variables...")
            
            # Initialize database connection if using PostgreSQL
            if Config.USE_DATABASE:
                logger.info("🗄️ Initializing PostgreSQL database connection...")
                await self.data_manager.initialize()
            
            # Setup admin directory structure
            from admin_error_handler import admin_error_handler
            await admin_error_handler.setup_admin_directories()
            
            # Migrate legacy admin files to organized structure
            migration_results = await admin_error_handler.migrate_legacy_admin_files()
            if migration_results:
                logger.info(f"📁 Admin file migration completed: {len(migration_results)} operations")
            
            # Check if using database mode
            if Config.USE_DATABASE:
                await self._sync_admins_database()
            else:
                await self._sync_admins_json()
        except Exception as e:
            logger.warning(f"⚠️  Warning: Failed to sync admins: {e}")
    
    async def notify_all_admins_payment_update(self, bot, payment_user_id: int, action: str, acting_admin_name: str, course_title: str = "", price: int = 0, user_name: str = ""):
        """Notify all admins when a payment status changes"""
        try:
            # Get all admin IDs
            admin_ids = []
            if Config.USE_DATABASE:
                admin_ids = await self.admin_panel.admin_manager.get_all_admin_ids()
            else:
                admins_data = await self.data_manager.load_data('admins')
                admin_ids = []
                if admins_data:
                    # Extract admin IDs properly, avoiding non-numeric keys like 'super_admin'
                    if 'admins' in admins_data:
                        admin_ids = admins_data['admins']  # Use the admins list
                    else:
                        # Fallback: filter keys that are numeric
                        admin_ids = [int(admin_id) for admin_id in admins_data.keys() 
                                   if admin_id.isdigit() or (isinstance(admin_id, (int, str)) and str(admin_id).isdigit())]
            
            # Create message based on action
            if action == 'approve':
                message = f"""✅ پرداخت تایید شد:
👤 کاربر: {user_name or 'ناشناس'}
🆔 User ID: {payment_user_id}
📚 دوره: {course_title}
💰 مبلغ: {Config.format_price(price)}
⏰ تایید شده توسط: {acting_admin_name}"""
            elif action == 'reject':
                message = f"""❌ پرداخت رد شد:
👤 کاربر: {user_name or 'ناشناس'}
🆔 User ID: {payment_user_id}
⏰ رد شده توسط: {acting_admin_name}"""
            else:
                return
            
            # Send notification to all admins
            for admin_id in admin_ids:
                try:
                    await bot.send_message(
                        chat_id=admin_id,
                        text=f"🔔 به‌روزرسانی وضعیت پرداخت:\n\n{message}"
                    )
                except Exception as e:
                    logger.warning(f"Failed to notify admin {admin_id}: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to notify admins about payment update: {e}")
    
    async def _sync_admins_json(self):
        """Comprehensive admin sync for JSON mode - all ADMIN_IDS are super admins"""
        admin_ids = Config.get_admin_ids()
        if not admin_ids:
            return
        
        log_admin_action(0, f"Syncing {len(admin_ids)} super admin(s) to JSON mode...")
        
        # Load existing admins - handle current format with 'admins' array and 'admin_permissions' dict
        admins_data = await self.data_manager.load_data('admins')
        
        # Initialize structure if empty or wrong format
        if not admins_data or not isinstance(admins_data, dict):
            admins_data = {
                'super_admin': admin_ids[0] if admin_ids else None,  # First admin as primary super admin
                'admins': [],
                'admin_permissions': {}
            }
        
        # Ensure required keys exist
        if 'admins' not in admins_data:
            admins_data['admins'] = []
        if 'admin_permissions' not in admins_data:
            admins_data['admin_permissions'] = {}
        if 'super_admin' not in admins_data:
            admins_data['super_admin'] = admin_ids[0] if admin_ids else None
        
        # Update super admin to first admin in list
        admins_data['super_admin'] = admin_ids[0] if admin_ids else None
        
        # Track changes
        added_count = 0
        updated_count = 0
        removed_count = 0
        
        # Current admins in the data
        current_admin_ids = set(admins_data['admins'])
        env_admin_ids = set(admin_ids)
        
        # Add new admins from environment - ALL are super admins
        for admin_id in admin_ids:
            if admin_id not in current_admin_ids:
                # Add to admins array
                admins_data['admins'].append(admin_id)
                # Add permissions - ALL are super admins now
                admins_data['admin_permissions'][str(admin_id)] = {
                    'can_add_admins': True,  # All ADMIN_IDS are super admins
                    'can_remove_admins': True,  # All ADMIN_IDS are super admins
                    'can_view_users': True,
                    'can_manage_payments': True,
                    'is_super_admin': True,  # All ADMIN_IDS are super admins
                    'added_by': 'env_sync',
                    'added_date': datetime.now().isoformat(),
                    'synced_from_config': True
                }
                log_admin_action(0, f"Added super admin to JSON: {admin_id}")
                added_count += 1
            else:
                # Update existing admin's permissions - ensure they're super admin
                admin_perms = admins_data['admin_permissions'].get(str(admin_id), {})
                current_is_super = admin_perms.get('is_super_admin', False)
                
                if not current_is_super:
                    # Promote to super admin
                    admins_data['admin_permissions'][str(admin_id)]['is_super_admin'] = True
                    admins_data['admin_permissions'][str(admin_id)]['can_add_admins'] = True
                    admins_data['admin_permissions'][str(admin_id)]['can_remove_admins'] = True
                    admins_data['admin_permissions'][str(admin_id)]['updated_date'] = datetime.now().isoformat()
                    log_admin_action(0, f"Admin {admin_id} promoted to super admin (all ADMIN_IDS are super)")
                    updated_count += 1
        
        # Remove admins who are no longer in environment (AGGRESSIVE SYNC - removes ALL non-env admins)
        admins_to_remove = current_admin_ids - env_admin_ids
        for admin_id_to_remove in admins_to_remove:
            # Remove from admins array
            if admin_id_to_remove in admins_data['admins']:
                admins_data['admins'].remove(admin_id_to_remove)
            # Remove permissions
            if str(admin_id_to_remove) in admins_data['admin_permissions']:
                del admins_data['admin_permissions'][str(admin_id_to_remove)]
            log_admin_action(0, f"Removed admin from JSON: {admin_id_to_remove} (aggressive sync)")
            removed_count += 1
        
        # Save updated admins data
        await self.data_manager.save_data('admins', admins_data)
        
        total_changes = added_count + updated_count + removed_count
        if total_changes > 0:
            log_admin_action(0, f"JSON admin sync completed! {len(admin_ids)} env super admins active, {added_count} added, {updated_count} updated, {removed_count} removed")
        else:
            log_admin_action(0, f"JSON admin sync verified! {len(admin_ids)} env super admins are properly synced")
    
    async def _sync_admins_database(self):
        """Comprehensive admin sync for database mode using admin_manager - all ADMIN_IDS are super admins"""
        admin_ids = Config.get_admin_ids()
        if not admin_ids:
            return
        
        log_admin_action(0, f"Syncing {len(admin_ids)} super admin(s) to database mode...")
        
        # Use the comprehensive sync method from admin_manager
        success = await self.admin_panel.admin_manager.sync_admins_from_config()
        
        if success:
            log_admin_action(0, "Database admin sync completed! All ADMIN_IDS are super admins. Manual cleanup available via /admin_panel.")
        else:
            logger.warning(f"⚠️ Database admin sync encountered issues.")
    
    async def notify_all_admins(self, context, message, reply_markup=None, photo=None):
        """Send notification to all admins"""
        admin_ids = Config.get_admin_ids()
        if not admin_ids:
            return 0
        
        sent_count = 0
        for admin_id in admin_ids:
            try:
                if photo:
                    await context.bot.send_photo(
                        chat_id=admin_id,
                        photo=photo,
                        caption=message,
                        reply_markup=reply_markup
                    )
                else:
                    await context.bot.send_message(
                        chat_id=admin_id,
                        text=message,
                        reply_markup=reply_markup,
                        parse_mode='HTML'
                    )
                sent_count += 1
            except Exception as e:
                logger.warning(f"Failed to send notification to admin {admin_id}: {e}")
        
        logger.info(f"Notification sent to {sent_count}/{len(admin_ids)} admins")
        return sent_count
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Start command handler - ALWAYS takes users to their appropriate main hub"""
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name or "کاربر"
        
        # Add cooldown protection for /start command  
        if await self.check_cooldown(user_id):
            return
        
        # Log user interaction
        log_user_action(user_id, user_name, "executed /start command - MAIN HUB REDIRECT")
        
        # CRITICAL: /start should ALWAYS be a complete reset and redirect to main hub
        # This prevents ANY stuck input states regardless of where user was
        
        # Clear any stale payment_pending data when user runs /start
        if user_id in self.payment_pending:
            user_logger.info(f"Clearing stale payment_pending data for user {user_id} on /start")
            del self.payment_pending[user_id]
        
        # COMPREHENSIVE STATE CLEARING - clear ALL possible input states
        states_cleared = await admin_error_handler.clear_all_input_states(
            context, user_id, "/start command - FORCE MAIN HUB"
        )
        
        # CRITICAL FIX: Clear questionnaire_active flag so random text won't be processed as questionnaire
        if user_id in context.user_data and 'questionnaire_active' in context.user_data[user_id]:
            context.user_data[user_id]['questionnaire_active'] = False
            user_logger.info(f"CLEARED QUESTIONNAIRE_ACTIVE FLAG for User {user_id} via /start")
        
        # CRITICAL: Also clear PERSISTENT payment states from user data AND payments table
        # This prevents rejected payments from persisting after /start navigation
        user_data_before_clear = await self.data_manager.get_user_data(user_id)
        payment_states_to_clear = [
            'payment_status',  # CRITICAL: Clear rejected/pending payment status
            'receipt_submitted',
            'payment_verified', 
            'awaiting_payment_receipt',
            'course_selected',  # Clear course selection to force fresh selection
            'receipt_file_id',
            'receipt_attempts',
            'awaiting_form'  # Clear form waiting state
        ]
        
        persistent_payment_data = {}
        for state in payment_states_to_clear:
            if state in user_data_before_clear:
                persistent_payment_data[state] = None  # Clear the state
        
        # CRITICAL: Also clear payment records from payments table
        # This prevents get_user_status from finding old rejected payments
        payments_data = await self.data_manager.load_data('payments')
        payments_cleared = []
        for payment_id, payment_data in list(payments_data.items()):
            if payment_data.get('user_id') == user_id:
                # Keep approved payments, but clear pending/rejected ones
                payment_status = payment_data.get('status')
                if payment_status in ['pending_approval', 'rejected', 'pending']:
                    del payments_data[payment_id]
                    payments_cleared.append(payment_id)
                    log_payment_action(user_id, f"CLEARED PAYMENT RECORD - Payment: {payment_id} | Status: {payment_status}")
        
        # Save cleared payments data
        if payments_cleared:
            await self.data_manager.save_data('payments', payments_data)
        
        if persistent_payment_data:
            payment_logger.info(f"Clearing persistent payment states for User {user_id}: {list(persistent_payment_data.keys())}")
            await self.data_manager.save_user_data(user_id, persistent_payment_data)
        
        # DON'T RESET QUESTIONNAIRE PROGRESS ON /start
        # Instead, preserve questionnaire state and let user continue or restart if they want
        # questionnaire_reset = await admin_error_handler.reset_questionnaire_state(
        #     user_id, self.questionnaire_manager, "/start command - FORCE RESET"
        # )
        
        user_logger.info(f"Preserving questionnaire state for User {user_id} on /start")
        
        # Clear admin-specific states if user is admin
        is_admin_result = await self.admin_panel.admin_manager.is_admin(user_id)
        
        if is_admin_result:
            admin_states_cleared = await admin_error_handler.clear_admin_input_states(
                self.admin_panel, user_id, "/start command - ADMIN HUB REDIRECT"
            )
            
            # ALWAYS redirect admins to admin hub - no exceptions
            log_admin_action(user_id, "executed /start command", f"Redirected to admin hub | Context states: {states_cleared} | Admin states: {admin_states_cleared} | Persistent states: {list(persistent_payment_data.keys())} | Payments cleared: {payments_cleared} | Questionnaire preserved")
            await self.admin_panel.show_admin_hub_for_command(update, context, user_id)
            return
        
        # For regular users, always show the same simple unified menu
        # This ensures /start always has consistent behavior regardless of user state
        user_data = await self.data_manager.get_user_data(user_id)
        
        # Update user interaction data
        await self.data_manager.save_user_data(user_id, {
            'name': user_name,
            'username': update.effective_user.username,
            'started_bot': True,
            'last_interaction': asyncio.get_event_loop().time()
        })
        
        # Refresh user_data after save and ensure user_id is set
        user_data = await self.data_manager.get_user_data(user_id)
        user_data['user_id'] = user_id
        
        # SIMPLE, UNIFIED MENU - always the same layout (questionnaire preserved)
        user_logger.info(f"User {user_id} redirected to simple unified menu. States cleared: {states_cleared}, Persistent states cleared: {list(persistent_payment_data.keys())}, Payments cleared: {payments_cleared}")
        await self.show_simple_unified_menu(update, context, user_data, user_name)

    async def show_simple_unified_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_data: dict, user_name: str) -> None:
        """Show simple, unified menu that's always the same - no status complexity"""
        user_id = update.effective_user.id
        
        # SIMPLE MENU - Always the same 4 buttons regardless of status
        keyboard = [
            [InlineKeyboardButton("🛒 خرید دوره", callback_data='new_course')],
            [InlineKeyboardButton("📊 مشاهده وضعیت", callback_data='my_status')],
            [InlineKeyboardButton("📞 پشتیبانی", callback_data='contact_support')],
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Simple welcome message - no status complexity
        welcome_text = f"""سلام {user_name}! 👋

🤖 به ربات مربی فوتبال خوش آمدید

💪 دوره‌های تمرینی حرفه‌ای
🥗 برنامه‌های غذایی تخصصی  
📊 پیگیری و مشاوره

چه کاری می‌تونم برات انجام بدم؟"""
        
        if hasattr(update, 'message') and update.message:
            await update.message.reply_text(welcome_text, reply_markup=reply_markup)
        else:
            await update.callback_query.edit_message_text(welcome_text, reply_markup=reply_markup)
    
    async def show_status_based_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_data: dict, user_name: str, admin_mode: bool = False) -> None:
        """Show menu based on user's current status"""
        user_id = update.effective_user.id
        
        # Check if user is admin first (but skip if in admin_mode)
        if not admin_mode:
            is_admin = await self.admin_panel.admin_manager.is_admin(user_id)
            if is_admin:
                # Redirect admins directly to the unified admin hub
                await self.show_admin_hub_for_start(update, context, user_id)
                return
        
        # Determine user status
        try:
            status = await self.get_user_status(user_data)
        except Exception as e:
            error_logger.error(f"Error determining user status for user {user_id}: {e}", exc_info=True)
            # Default to returning user if status determination fails
            status = 'returning_user'
        
        if status == 'new_user':
            # First-time user - show welcome and course selection
            reply_markup = await self.create_course_selection_keyboard(user_id)
            welcome_text = Config.WELCOME_MESSAGE
            
        elif status == 'payment_pending':
            # User has submitted payment, waiting for approval
            course_code = user_data.get('course_selected', 'نامشخص')
            course_name = self.get_course_name_farsi(course_code)
            keyboard = [
                [InlineKeyboardButton("📊 وضعیت پرداخت", callback_data='check_payment_status')],
                [InlineKeyboardButton("📞 تماس با پشتیبانی", callback_data='contact_support')],
                [InlineKeyboardButton("🔄 دوره جدید", callback_data='new_course')]
            ]
            if admin_mode:
                keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی ادمین", callback_data='admin_back_main')])
            reply_markup = InlineKeyboardMarkup(keyboard)
            welcome_text = f"سلام {user_name}! 👋\n\n⏳ پرداخت شما برای دوره **{course_name}** در انتظار تایید است.\n\nمی‌توانید وضعیت پرداخت خود را بررسی کنید:"
            
        elif status == 'payment_approved':
            # User payment approved - use comprehensive questionnaire requirement analysis
            quest_req_status = await self.get_user_questionnaire_requirement_status(user_id)
            purchased_courses = quest_req_status['purchased_courses']
            course_count = len(purchased_courses)
            
            # DEBUG LOGGING for questionnaire flow
            questionnaire_status = quest_req_status['questionnaire_status']
            from admin_error_handler import admin_error_handler
            await admin_error_handler.log_questionnaire_flow_debug(
                user_id=user_id,
                context='payment_approved_status_menu',
                questionnaire_data=questionnaire_status or {},
                flow_decision='analyzing_requirements',
                details={
                    'purchased_courses': list(purchased_courses),
                    'requires_questionnaire': quest_req_status['requires_questionnaire'],
                    'can_access_programs': quest_req_status['can_access_programs'],
                    'questionnaire_completed': quest_req_status['questionnaire_completed'],
                    'questionnaire_in_progress': quest_req_status['questionnaire_in_progress']
                }
            )
            
            # Get primary course for display (most recent or default)
            course_code = user_data.get('course', 'نامشخص')
            course_name = self.get_course_name_farsi(course_code)
            
            if quest_req_status['can_access_programs']:
                # User can access programs (either no questionnaire needed or questionnaire completed)
                keyboard = [
                    [InlineKeyboardButton("📋 مشاهده برنامه تمرینی", callback_data='view_program')],
                    [InlineKeyboardButton("📊 وضعیت من", callback_data='my_status')],
                ]
                
                # Only show questionnaire options if questionnaire is required for their courses
                if quest_req_status['requires_questionnaire']:
                    keyboard.extend([
                        [InlineKeyboardButton("✏️ ویرایش پرسشنامه", callback_data='edit_questionnaire')],
                        [InlineKeyboardButton("🔄 بروزرسانی پرسشنامه", callback_data='restart_questionnaire')],
                    ])
                
                keyboard.append([InlineKeyboardButton("🛒 دوره جدید", callback_data='new_course')])
                
                if admin_mode:
                    keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی ادمین", callback_data='admin_back_main')])
                
                # Enhanced welcome message showing completion status and purchased courses
                nutrition_info = ""
                
                # Only show nutrition info if user purchased nutrition plan
                if 'nutrition_plan' in purchased_courses:
                    nutrition_info = """

🥗 برنامه غذایی شخصی‌سازی شده

با توجه به اهداف و شرایط جسمانی شما، یک برنامه غذایی کاملاً شخصی‌سازی شده تهیه می‌شود.

برای دریافت برنامه غذایی، لطفاً روی لینک زیر کلیک کنید:

👈 https://fitava.ir/coach/drbohloul/question

✨ این برنامه شامل:
• برنامه غذایی کامل بر اساس نیازهای شما
• راهنمایی تخصصی تغذیه ورزشی
• پیگیری و تنظیم برنامه
❌توجه داشته باشید همه فیلدهای فرم رو پر کنید وبرای قسمت اعداد، کیورد اعداد انگلیسی رو وارد کنید"""

                if course_count > 1:
                    welcome_text = f"سلام {user_name}! 👋\n\n✅ شما دارای {course_count} دوره فعال هستید!\n🎯 برنامه‌های تمرینی شخصی‌سازی شده شما آماده است!{nutrition_info}\n\n💪 برای دسترسی به برنامه تمرینی، از منو استفاده کنید:"
                else:
                    welcome_text = f"سلام {user_name}! 👋\n\n✅ برنامه تمرینی شما برای دوره **{course_name}** آماده است!\n🎯 برنامه شخصی‌سازی شده شما آماده است!{nutrition_info}\n\n💪 برای دسترسی به برنامه تمرینی، از منو استفاده کنید:"
            else:
                # User needs to complete questionnaire - check if questionnaire already exists
                questionnaire_status = quest_req_status['questionnaire_status']
                current_step = questionnaire_status.get('current_step', 0)
                total_steps = questionnaire_status.get('total_steps', 21)
                
                # CRITICAL DEBUG: Log questionnaire_status raw data for edge case debugging
                user_logger.info(f"QUESTIONNAIRE STATUS DEBUG for User {user_id}: Raw status: {questionnaire_status}, Step: {current_step}, Answers: {len(questionnaire_status.get('answers', {}))}")
                
                # ENHANCED DETECTION: Check for existing questionnaire progress
                has_existing_questionnaire = (
                    questionnaire_status and 
                    (current_step > 0 or len(questionnaire_status.get('answers', {})) > 0)
                )
                
                # DEBUG LOGGING for questionnaire detection
                await admin_error_handler.log_questionnaire_flow_debug(
                    user_id=user_id,
                    context='payment_approved_questionnaire_detection',
                    questionnaire_data=questionnaire_status or {},
                    flow_decision=f'has_existing: {has_existing_questionnaire}, step: {current_step}',
                    details={
                        'current_step': current_step,
                        'total_steps': total_steps,
                        'has_existing_questionnaire': has_existing_questionnaire,
                        'answer_count': len(questionnaire_status.get('answers', {})),
                        'questionnaire_status_raw': questionnaire_status,
                        'decision_path_debug': f'step_check: current_step({current_step}) > 1 = {current_step > 1}, step_equals_1: {current_step == 1}',
                        'expected_branch': (
                            'resume_step_gt_1' if (has_existing_questionnaire and current_step > 1) 
                            else 'existing_step_1' if (has_existing_questionnaire and current_step == 1)
                            else 'fresh_start'
                        )
                    }
                )
                
                if has_existing_questionnaire and current_step > 1:
                    # Resume existing questionnaire from saved progress
                    current_question = await self.questionnaire_manager.get_current_question(user_id)
                    if current_question:
                        # COMPREHENSIVE DEBUG: Track branch execution
                        user_logger.info(f"BRANCH: resume_step_gt_1 - User {user_id} | Step: {current_step} | Question: {current_question.get('step', 'unknown')}")
                        
                        # CRITICAL FIX: Set questionnaire_active flag so text input will be processed
                        if user_id not in context.user_data:
                            context.user_data[user_id] = {}
                        context.user_data[user_id]['questionnaire_active'] = True
                        user_logger.info(f"SET questionnaire_active flag for User {user_id} resuming at step {current_step}")
                        
                        # ROBUST FIX: Also set a timestamp to track when flag was set
                        context.user_data[user_id]['questionnaire_activated_at'] = datetime.now().isoformat()
                        
                        # ADDITIONAL FIX: Verify questionnaire data is immediately available
                        verification_progress = await self.questionnaire_manager.load_user_progress(user_id)
                        verification_question = await self.questionnaire_manager.get_current_question(user_id)
                        user_logger.info(f"QUESTIONNAIRE VERIFICATION for User {user_id}: progress={verification_progress is not None}, question={verification_question is not None}")
                        
                        # If verification fails, force questionnaire readiness
                        if not verification_progress or not verification_question:
                            error_logger.warning(f"QUESTIONNAIRE DATA NOT READY for User {user_id} - attempting to fix")
                            # Force refresh questionnaire data
                            await self.questionnaire_manager.start_questionnaire(user_id)
                            verification_progress = await self.questionnaire_manager.load_user_progress(user_id)
                            user_logger.info(f"AFTER FIX for User {user_id}: progress available = {verification_progress is not None}")
                        
                        # DEBUG: Log questionnaire resume activation
                        await admin_error_handler.log_questionnaire_flow_debug(
                            user_id=user_id,
                            context="questionnaire_activated_payment_approved_resume",
                            questionnaire_data=questionnaire_status,
                            flow_decision="set_questionnaire_active_flag_resume",
                            details={
                                'step': current_step,
                                'has_question': bool(current_question),
                                'question_type': current_question.get('type', 'unknown') if current_question else None,
                                'context_flag_set': True,
                                'resume_from_step': current_step,
                                'branch_taken': 'resume_step_gt_1',
                                'question_step_from_manager': current_question.get('step', 'unknown'),
                                'question_progress_text_from_manager': current_question.get('progress_text', 'none'),
                                'verification_progress_available': verification_progress is not None,
                                'verification_question_available': verification_question is not None
                            }
                        )
                        
                        # Show current question directly - USE PROGRESS TEXT FROM QUESTION MANAGER
                        # POTENTIAL FIX: Use progress text from questionnaire manager instead of recalculating
                        if current_question.get('progress_text'):
                            progress_text = current_question['progress_text']
                        else:
                            progress_text = f"سوال {current_step} از {total_steps}"
                        message = f"{progress_text}\n\n{current_question['text']}"
                        
                        keyboard = []
                        if current_question.get('type') == 'choice':
                            choices = current_question.get('choices', [])
                            for choice in choices:
                                keyboard.append([InlineKeyboardButton(choice, callback_data=f'q_answer_{choice}')])
                        keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data='back_to_user_menu')])
                        
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        welcome_text = f"سلام {user_name}! 👋\n\n✅ پرداخت شما تایید شده است.\n📝 بازگشت به پرسشنامه از جایی که رها کردید\n\n{message}"
                    else:
                        # Fallback to continue button if question not found
                        keyboard = [
                            [InlineKeyboardButton("📝 ادامه پرسشنامه", callback_data='continue_questionnaire')]
                        ]
                        if admin_mode:
                            keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی ادمین", callback_data='admin_back_main')])
                        welcome_text = f"سلام {user_name}! 👋\n\n✅ پرداخت شما تایید شده است.\n📝 پرسشنامه: مرحله {current_step} از {total_steps}\n\nلطفاً پرسشنامه شخصی را تکمیل کنید تا برنامه شخصی‌سازی شده شما آماده شود:"
                        reply_markup = InlineKeyboardMarkup(keyboard)
                elif has_existing_questionnaire and current_step == 1:
                    # User has a questionnaire at step 1 - show first question
                    first_question = self.questionnaire_manager.get_question(1, questionnaire_status.get('answers', {}))
                    if first_question:
                        # COMPREHENSIVE DEBUG: Track branch execution  
                        user_logger.info(f"BRANCH: existing_step_1 - User {user_id} | Step: {current_step} | Question for step 1")
                        
                        # CRITICAL FIX: Set questionnaire_active flag so text input will be processed
                        if user_id not in context.user_data:
                            context.user_data[user_id] = {}
                        context.user_data[user_id]['questionnaire_active'] = True
                        user_logger.info(f"SET questionnaire_active flag for User {user_id} in payment_approved flow (existing questionnaire at step 1)")
                        
                        # ROBUST FIX: Also set a timestamp to track when flag was set
                        context.user_data[user_id]['questionnaire_activated_at'] = datetime.now().isoformat()
                        
                        # ADDITIONAL FIX: Verify questionnaire data is immediately available for step 1
                        verification_progress = await self.questionnaire_manager.load_user_progress(user_id)
                        verification_question = await self.questionnaire_manager.get_current_question(user_id)
                        user_logger.info(f"QUESTIONNAIRE VERIFICATION STEP 1 for User {user_id}: progress={verification_progress is not None}, question={verification_question is not None}")
                        
                        # DEBUG: Log comprehensive questionnaire activation state
                        await admin_error_handler.log_questionnaire_flow_debug(
                            user_id=user_id,
                            context="questionnaire_activated_payment_approved_existing",
                            questionnaire_data=questionnaire_status,
                            flow_decision="set_questionnaire_active_flag",
                            details={
                                'step': 1,
                                'has_question': bool(first_question),
                                'question_type': first_question.get('type', 'unknown') if first_question else None,
                                'context_flag_set': True,
                                'branch_taken': 'existing_step_1',
                                'verification_progress_available': verification_progress is not None,
                                'verification_question_available': verification_question is not None
                            }
                        )
                        
                        progress_text = "سوال 1 از 21"
                        # POTENTIAL FIX: If the question returned doesn't match step 1, use its actual progress
                        if first_question.get('progress_text'):
                            error_logger.warning(f"PROGRESS TEXT MISMATCH for User {user_id} - Expected step 1, got: {first_question.get('progress_text')}")
                            progress_text = first_question['progress_text']
                        
                        message = f"{progress_text}\n\n{first_question['text']}"
                        
                        keyboard = []
                        if first_question.get('type') == 'choice':
                            choices = first_question.get('choices', [])
                            for choice in choices:
                                keyboard.append([InlineKeyboardButton(choice, callback_data=f'q_answer_{choice}')])
                        keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data='back_to_user_menu')])
                        
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        welcome_text = f"سلام {user_name}! 👋\n\n✅ پرداخت شما تایید شده است.\n📝 بازگشت به پرسشنامه شخصی‌تان\n\n{message}"
                    else:
                        # Fallback if first question not found
                        keyboard = [
                            [InlineKeyboardButton("📝 شروع پرسشنامه", callback_data='continue_questionnaire')]
                        ]
                        if admin_mode:
                            keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی ادمین", callback_data='admin_back_main')])
                        welcome_text = f"سلام {user_name}! 👋\n\n✅ پرداخت شما تایید شده است.\n📝 لطفاً پرسشنامه شخصی را شروع کنید:"
                        reply_markup = InlineKeyboardMarkup(keyboard)
                else:
                    # No existing questionnaire - start fresh
                    first_question = self.questionnaire_manager.get_question(1, {})
                    if first_question:
                        # COMPREHENSIVE DEBUG: Track branch execution
                        user_logger.info(f"BRANCH: fresh_start - User {user_id} | Starting fresh questionnaire")
                        
                        # Initialize questionnaire for user
                        await self.questionnaire_manager.start_questionnaire(user_id)
                        
                        # CRITICAL FIX: Set questionnaire_active flag so text input will be processed
                        if user_id not in context.user_data:
                            context.user_data[user_id] = {}
                        context.user_data[user_id]['questionnaire_active'] = True
                        user_logger.info(f"SET questionnaire_active flag for User {user_id} in fresh questionnaire flow")
                        
                        # ROBUST FIX: Also set a timestamp to track when flag was set
                        context.user_data[user_id]['questionnaire_activated_at'] = datetime.now().isoformat()
                        
                        # ADDITIONAL FIX: Verify questionnaire data is immediately available after start
                        verification_progress = await self.questionnaire_manager.load_user_progress(user_id)
                        verification_question = await self.questionnaire_manager.get_current_question(user_id)
                        user_logger.info(f"QUESTIONNAIRE VERIFICATION FRESH for User {user_id}: progress={verification_progress is not None}, question={verification_question is not None}")
                        
                        # DEBUG: Log comprehensive questionnaire activation state
                        await admin_error_handler.log_questionnaire_flow_debug(
                            user_id=user_id,
                            context="questionnaire_activated_payment_approved_fresh",
                            questionnaire_data={'current_step': 1, 'started': True},
                            flow_decision="set_questionnaire_active_flag_fresh_start",
                            details={
                                'step': 1,
                                'has_question': bool(first_question),
                                'question_type': first_question.get('type', 'unknown') if first_question else None,
                                'context_flag_set': True,
                                'questionnaire_manager_started': True,
                                'branch_taken': 'fresh_start',
                                'verification_progress_available': verification_progress is not None,
                                'verification_question_available': verification_question is not None
                            }
                        )
                        
                        progress_text = "سوال 1 از 21"
                        # POTENTIAL FIX: If the question returned doesn't match step 1, use its actual progress  
                        if first_question.get('progress_text'):
                            error_logger.warning(f"PROGRESS TEXT MISMATCH for User {user_id} - Expected step 1, got: {first_question.get('progress_text')}")
                            progress_text = first_question['progress_text']
                            
                        message = f"{progress_text}\n\n{first_question['text']}"
                        
                        keyboard = []
                        if first_question.get('type') == 'choice':
                            choices = first_question.get('choices', [])
                            for choice in choices:
                                keyboard.append([InlineKeyboardButton(choice, callback_data=f'q_answer_{choice}')])
                        keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data='back_to_user_menu')])
                        
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        welcome_text = f"سلام {user_name}! 👋\n\n✅ پرداخت شما تایید شده است.\n\n📝 حالا وقت تکمیل پرسشنامه است!\n\n{message}"
                    else:
                        # Fallback if first question not found
                        keyboard = [
                            [InlineKeyboardButton("📝 شروع پرسشنامه", callback_data='start_questionnaire')]
                        ]
                        if admin_mode:
                            keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی ادمین", callback_data='admin_back_main')])
                        welcome_text = f"سلام {user_name}! 👋\n\n✅ پرداخت شما تایید شده است.\n📝 برای دریافت برنامه تمرینی، لطفاً پرسشنامه را تکمیل کنید:"
                        reply_markup = InlineKeyboardMarkup(keyboard)
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
        elif status == 'payment_rejected':
            # Payment was rejected
            course_code = user_data.get('course_selected', 'نامشخص')
            course_name = self.get_course_name_farsi(course_code)
            keyboard = [
                [InlineKeyboardButton("💳 پرداخت مجدد", callback_data=f'payment_{user_data.get("course_selected", "")}')],
                [InlineKeyboardButton("📞 تماس با پشتیبانی", callback_data='contact_support')],
                [InlineKeyboardButton("🔄 دوره جدید", callback_data='new_course')]
            ]
            if admin_mode:
                keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی ادمین", callback_data='admin_back_main')])
            reply_markup = InlineKeyboardMarkup(keyboard)
            welcome_text = f"سلام {user_name}! 👋\n\n❌ متاسفانه پرداخت شما برای دوره **{course_name}** تایید نشد.\n\nمی‌توانید مجدداً پرداخت کنید یا با پشتیبانی @DrBohloul تماس بگیرید:"
            
        elif status == 'course_selected':
            # User has selected a course but hasn't paid yet - show course details and payment option
            course_code = user_data.get('course_selected', 'نامشخص')
            course_name = self.get_course_name_farsi(course_code)
            course_details = Config.COURSE_DETAILS.get(course_code, {})
            price = Config.PRICES.get(course_code, 0)
            price_text = Config.format_price(price)
            
            keyboard = [
                [InlineKeyboardButton(f"💳 پرداخت و ثبت نام ({price_text})", callback_data=f'payment_{course_code}')],
                [InlineKeyboardButton("🏷️ کد تخفیف", callback_data=f'coupon_{course_code}')],
                [InlineKeyboardButton("🔄 تغییر دوره", callback_data='new_course')],
                [InlineKeyboardButton("📊 وضعیت من", callback_data='my_status')]
            ]
            if admin_mode:
                keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی ادمین", callback_data='admin_back_main')])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Show course details
            course_title = course_details.get('title', course_name)
            course_description = course_details.get('description', 'توضیحات در دسترس نیست')
            
            welcome_text = f"""سلام {user_name}! 👋

📚 *{course_title}*

{course_description}

💰 قیمت: {price_text}

برای ثبت نام و پرداخت، روی دکمه زیر کلیک کنید:"""
            
        else:
            # Returning user without active course - show course selection
            course_keyboard = await self.create_course_selection_keyboard(user_id)
            # Add status button to the existing keyboard
            additional_buttons = [
                [InlineKeyboardButton("📊 وضعیت من", callback_data='my_status')]
            ]
            if admin_mode:
                additional_buttons.append([InlineKeyboardButton("🔙 بازگشت به منوی ادمین", callback_data='admin_back_main')])
            
            keyboard = list(course_keyboard.inline_keyboard) + additional_buttons
            reply_markup = InlineKeyboardMarkup(keyboard)
            welcome_text = f"سلام {user_name}! 👋\n\nخوش برگشتی! چه کاری می‌تونم برات انجام بدم؟"
        
        if hasattr(update, 'message') and update.message:
            await update.message.reply_text(welcome_text, reply_markup=reply_markup)
        else:
            await update.callback_query.edit_message_text(welcome_text, reply_markup=reply_markup)
    
    async def show_admin_hub_for_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int) -> None:
        """Show the unified admin hub when admin uses /start command"""
        is_super = await self.admin_panel.admin_manager.is_super_admin(user_id)
        can_manage_admins = await self.admin_panel.admin_manager.can_add_admins(user_id)
        user_name = update.effective_user.first_name or "ادمین"
        
        keyboard = [
            [InlineKeyboardButton("📊 آمار و گزارشات", callback_data='admin_stats'),
             InlineKeyboardButton("👥 مدیریت کاربران", callback_data='admin_users')],
            [InlineKeyboardButton("💳 مدیریت پرداخت‌ها", callback_data='admin_payments'),
             InlineKeyboardButton("📤 اکسپورت داده‌ها", callback_data='admin_export_menu')],
            [InlineKeyboardButton("🎟️ مدیریت کوپن", callback_data='admin_coupons'),
             InlineKeyboardButton("📋 مدیریت برنامه‌ها", callback_data='admin_plans')]
        ]
        
        if can_manage_admins:
            keyboard.append([InlineKeyboardButton("🔐 مدیریت ادمین‌ها", callback_data='admin_manage_admins')])
        
        keyboard.append([InlineKeyboardButton("👤 حالت کاربر", callback_data='admin_user_mode')])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        admin_type = "🔥 سوپر ادمین" if is_super else "👤 ادمین"
        welcome_text = f"🎛️ پنل مدیریت\n\nسلام {user_name}! 👋\n{admin_type} - مرکز فرماندهی ربات:\n\n📋 همه ابزارهای مدیریت در یک مکان"
        
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)
    
    async def get_user_status(self, user_data: dict) -> str:
        """Determine user's current status based on their data"""
        user_id = user_data.get('user_id')
        
        # Debug logging
        user_logger.debug(f"get_user_status for user {user_id}")
        user_logger.debug(f"user_data: {user_data}")
        payment_logger.debug(f"payment_pending dict has user: {user_id in self.payment_pending}")
        
        if not user_data or not user_data.get('started_bot'):
            user_logger.debug(f"Status for {user_id}: new_user")
            return 'new_user'
        
        # Check payment status from the payments table
        payments_data = await self.data_manager.load_data('payments')
        user_payment = None
        
        # Find the most recent payment for this user
        for payment_id, payment_data in payments_data.items():
            if payment_data.get('user_id') == user_id:
                if user_payment is None or payment_data.get('timestamp', '') > user_payment.get('timestamp', ''):
                    user_payment = payment_data
        
        payment_logger.debug(f"User {user_id} payment from DB: {user_payment}")
        
        if user_payment:
            payment_status = user_payment.get('status')
            payment_logger.debug(f"Payment status for user {user_id} from DB: {payment_status}")
            if payment_status == 'pending_approval':  # Changed from 'pending' to 'pending_approval'
                user_logger.debug(f"Status for {user_id}: payment_pending (from DB)")
                return 'payment_pending'
            elif payment_status == 'approved':
                user_logger.debug(f"Status for {user_id}: payment_approved (from DB)")
                return 'payment_approved'
            # REMOVED: payment_rejected check - after /start, rejected payments don't affect status
        
        # Fallback to user_data payment_status (for backward compatibility)
        payment_status = user_data.get('payment_status')
        payment_logger.debug(f"Fallback payment_status for user {user_id} from user_data: {payment_status}")
        
        if payment_status == 'pending_approval':
            user_logger.debug(f"Status for {user_id}: payment_pending (from user_data)")
            return 'payment_pending'
        elif payment_status == 'approved':
            user_logger.debug(f"Status for {user_id}: payment_approved (from user_data)")
            return 'payment_approved'
        # REMOVED: payment_rejected check - after /start, rejected payments don't affect status
        elif user_data.get('course_selected') and not payment_status:
            user_logger.debug(f"Status for {user_id}: course_selected (course: {user_data.get('course_selected')})")
            return 'course_selected'
        else:
            user_logger.debug(f"Status for {user_id}: returning_user")
            return 'returning_user'

    async def get_user_purchased_courses(self, user_id: int) -> set:
        """Get set of course types that user has approved payments for"""
        payments_data = await self.data_manager.load_data('payments')
        purchased_courses = set()
        
        for payment_id, payment_data in payments_data.items():
            if (payment_data.get('user_id') == user_id and 
                payment_data.get('status') == 'approved'):
                course_type = payment_data.get('course_type')
                if course_type:
                    purchased_courses.add(course_type)
        
        return purchased_courses

    async def get_user_questionnaire_requirement_status(self, user_id: int) -> dict:
        """
        Determine questionnaire requirement status for a user
        Returns comprehensive status for multi-course scenarios
        """
        purchased_courses = await self.get_user_purchased_courses(user_id)
        questionnaire_status = await self.questionnaire_manager.get_user_questionnaire_status(user_id)
        
        # Courses that require questionnaire completion (ALL courses need questionnaire for personalization)
        courses_requiring_questionnaire = {'in_person_cardio', 'in_person_weights', 'online_cardio', 'online_weights', 'nutrition_plan'}
        
        # Check if user has any courses that require questionnaire
        requires_questionnaire = bool(purchased_courses & courses_requiring_questionnaire)
        
        questionnaire_completed = questionnaire_status.get('completed', False)
        questionnaire_in_progress = (questionnaire_status.get('current_step', 0) > 0 and 
                                    not questionnaire_completed)
        
        return {
            'purchased_courses': purchased_courses,
            'requires_questionnaire': requires_questionnaire,
            'questionnaire_completed': questionnaire_completed,
            'questionnaire_in_progress': questionnaire_in_progress,
            'questionnaire_status': questionnaire_status,
            'can_access_programs': (not requires_questionnaire) or questionnaire_completed,
            'needs_to_complete_questionnaire': requires_questionnaire and not questionnaire_completed
        }

    async def has_purchased_course(self, user_id: int, course_type: str) -> bool:
        """Check if user has purchased a specific course"""
        purchased_courses = await self.get_user_purchased_courses(user_id)
        return course_type in purchased_courses

    async def create_course_selection_keyboard(self, user_id: int = None) -> InlineKeyboardMarkup:
        """Create course selection keyboard with tick marks for purchased courses"""
        # If no user_id provided, show basic menu without tick marks
        if user_id is None:
            keyboard = [
                [InlineKeyboardButton("1️⃣ دوره تمرین حضوری", callback_data='in_person')],
                [InlineKeyboardButton("2️⃣ دوره تمرین آنلاین", callback_data='online')],
                [InlineKeyboardButton("3️⃣ برنامه غذایی", callback_data='nutrition_plan')]
            ]
        else:
            # Get purchased courses to add tick marks only for specific purchased courses
            purchased_courses = await self.get_user_purchased_courses(user_id)
            
            in_person_text = "1️⃣ دوره تمرین حضوری"
            online_text = "2️⃣ دوره تمرین آنلاین"
            nutrition_text = "3️⃣ برنامه غذایی"
            
            # Add checkmarks for purchased courses
            if 'nutrition_plan' in purchased_courses:
                nutrition_text += " ✅"
            
            keyboard = [
                [InlineKeyboardButton(in_person_text, callback_data='in_person')],
                [InlineKeyboardButton(online_text, callback_data='online')],
                [InlineKeyboardButton(nutrition_text, callback_data='nutrition_plan')]
            ]
        
        return InlineKeyboardMarkup(keyboard)

    async def handle_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle main menu selections"""
        query = update.callback_query
        await query.answer()
        user_id = update.effective_user.id
        if await self.check_cooldown(user_id):
            return
        user_name = update.effective_user.first_name or "کاربر"
        
        # Clear all input states when navigating to main menu categories
        states_cleared = await admin_error_handler.clear_all_input_states(
            context, user_id, "handle_main_menu"
        )
        
        log_user_action(user_id, user_name, f"selected menu option: {query.data}")
        
        if query.data == 'in_person':
            # Check which courses user has purchased
            purchased_courses = await self.get_user_purchased_courses(user_id)
            
            # Create buttons with tick marks for purchased courses
            cardio_text = "1️⃣ تمرین هوازی سرعتی چابکی کار با توپ"
            weights_text = "2️⃣ تمرین وزنه"
            
            if 'in_person_cardio' in purchased_courses:
                cardio_text += " ✅"
            if 'in_person_weights' in purchased_courses:
                weights_text += " ✅"
            
            keyboard = [
                [InlineKeyboardButton(cardio_text, callback_data='in_person_cardio')],
                [InlineKeyboardButton(weights_text, callback_data='in_person_weights')],
                [InlineKeyboardButton("🔙 بازگشت به انتخاب دوره", callback_data='back_to_course_selection')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("انتخاب کنید:", reply_markup=reply_markup)
            
        elif query.data == 'online':
            # Check which courses user has purchased
            purchased_courses = await self.get_user_purchased_courses(user_id)
            
            # Create buttons with tick marks for purchased courses
            weights_text = "1️⃣ برنامه وزنه"
            cardio_text = "2️⃣ برنامه هوازی و کار با توپ"
            combo_text = "3️⃣ برنامه وزنه + برنامه هوازی (با تخفیف بیشتر)"
            
            if 'online_weights' in purchased_courses:
                weights_text += " ✅"
            if 'online_cardio' in purchased_courses:
                cardio_text += " ✅"
            if 'online_combo' in purchased_courses:
                combo_text += " ✅"
            
            keyboard = [
                [InlineKeyboardButton(weights_text, callback_data='online_weights')],
                [InlineKeyboardButton(cardio_text, callback_data='online_cardio')],
                [InlineKeyboardButton(combo_text, callback_data='online_combo')],
                [InlineKeyboardButton("🔙 بازگشت به انتخاب دوره", callback_data='back_to_course_selection')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("انتخاب کنید:", reply_markup=reply_markup)
            
        elif query.data == 'nutrition_plan':
            # Handle nutrition plan selection directly 
            await query.answer()
            # Check if user already owns this course
            user_id = update.effective_user.id
            if await self.has_purchased_course(user_id, 'nutrition_plan'):
                await query.answer(
                    "✅ شما قبلاً این دوره را خریداری کرده‌اید!\n"
                    "برای دسترسی به برنامه تغذیه خود از منو استفاده کنید.",
                    show_alert=True
                )
                return
                
            course = Config.COURSE_DETAILS['nutrition_plan']
            price = Config.PRICES['nutrition_plan']
            
            # Format price properly using the utility function
            price_text = Config.format_price(price)
            
            message_text = f"{course['title']}👇👇👇👇👇\n\n{course['description']}"
            
            keyboard = [
                [InlineKeyboardButton(f"💳 پرداخت و ثبت نام ({price_text})", callback_data='payment_nutrition_plan')],
                [InlineKeyboardButton("🏷️ کد تخفیف دارم", callback_data='coupon_nutrition_plan')],
                [InlineKeyboardButton("🔙 بازگشت به انتخاب دوره", callback_data='back_to_course_selection')],
                [InlineKeyboardButton("🏠 منوی اصلی", callback_data='back_to_user_menu')]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(message_text, reply_markup=reply_markup)

    async def handle_course_details(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle detailed course information"""
        query = update.callback_query
        user_id = update.effective_user.id
        if await self.check_cooldown(user_id):
            await query.answer()
            return
        
        # Clear all input states when navigating to course details (this includes navigation back from coupon panel)
        states_cleared = await admin_error_handler.clear_all_input_states(
            context, user_id, "handle_course_details"
        )
        
        if query.data in Config.COURSE_DETAILS:
            # Check if user already owns this course
            if await self.has_purchased_course(user_id, query.data):
                await query.answer(
                    "✅ شما قبلاً این دوره را خریداری کرده‌اید!\n"
                    "برای دسترسی به برنامه تمرینی خود از منو استفاده کنید.",
                    show_alert=True
                )
                return
            
            await query.answer()
            
            course = Config.COURSE_DETAILS[query.data]
            price = Config.PRICES[query.data]
            
            # Format price properly using the utility function
            price_text = Config.format_price(price)
            
            message_text = f"{course['title']}👇👇👇👇👇\n\n{course['description']}"
            
            keyboard = [
                [InlineKeyboardButton(f"💳 پرداخت و ثبت نام ({price_text})", callback_data=f'payment_{query.data}')],
                [InlineKeyboardButton("🏷️ کد تخفیف دارم", callback_data=f'coupon_{query.data}')]
            ]
            
            # Add appropriate back button based on course type
            if query.data == 'nutrition_plan':
                keyboard.append([InlineKeyboardButton("🔙 بازگشت به انتخاب دوره", callback_data='back_to_course_selection')])
            elif query.data.startswith('online'):
                keyboard.append([InlineKeyboardButton("🔙 بازگشت به دوره‌های آنلاین", callback_data='back_to_online')])
            elif query.data.startswith('in_person'):
                keyboard.append([InlineKeyboardButton("🔙 بازگشت به دوره‌های حضوری", callback_data='back_to_in_person')])
                
            keyboard.append([InlineKeyboardButton("🏠 منوی اصلی", callback_data='back_to_user_menu')])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(message_text, reply_markup=reply_markup)

    async def handle_coupon_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle coupon code request"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        if await self.check_cooldown(user_id):
            return
        course_type = query.data.replace('coupon_', '')
        
        # Store course type for later use
        self.payment_pending[user_id] = course_type
        
        await query.edit_message_text(
            "🏷️ لطفاً کد تخفیف خود را وارد کنید:\n\n"
            "💡 کد تخفیف را دقیقاً همانطور که دریافت کردید تایپ کنید.\n"
            "❌ برای لغو، /start را تایپ کنید.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 بازگشت", callback_data=f'{course_type}')]
            ])
        )
        
        # Store that we're waiting for coupon code
        if user_id not in context.user_data:
            context.user_data[user_id] = {}
        context.user_data[user_id]['waiting_for_coupon'] = True
        context.user_data[user_id]['coupon_course'] = course_type

    async def handle_coupon_code(self, update: Update, context: ContextTypes.DEFAULT_TYPE, coupon_code: str) -> None:
        """Handle coupon code validation and processing"""
        user_id = update.effective_user.id
        user_context = context.user_data.get(user_id, {})
        course_type = user_context.get('coupon_course')
        
        # Safety check: Ensure we have valid coupon context
        if not course_type:
            # Invalid coupon state - clear everything and redirect to main menu
            await admin_error_handler.clear_all_input_states(
                context, user_id, "invalid_coupon_state"
            )
            await update.message.reply_text(
                "❌ خطایی در حالت کد تخفیف رخ داده است.\n\n"
                "🏠 به منوی اصلی بازگردید و مجددا تلاش کنید.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🏠 منوی اصلی", callback_data='back_to_user_menu')]
                ])
            )
            return
        
        # Clear coupon waiting state for this specific user
        if user_id not in context.user_data:
            context.user_data[user_id] = {}
        context.user_data[user_id]['waiting_for_coupon'] = False
        if 'coupon_course' in context.user_data[user_id]:
            del context.user_data[user_id]['coupon_course']
        
        if not course_type:
            await update.message.reply_text(
                "❌ خطایی رخ داده است. لطفاً مجدداً دوره را انتخاب کنید.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🏠 منوی اصلی", callback_data='back_to_user_menu')]
                ])
            )
            return
        
        # SANITIZE and validate coupon
        sanitized_code = sanitize_text(coupon_code).strip().upper()
        is_valid, message, discount_percent = self.coupon_manager.validate_coupon(sanitized_code)
        
        if not is_valid:
            # Show error and offer to continue without coupon
            course_details = Config.COURSE_DETAILS.get(course_type, {})
            original_price = Config.PRICES.get(course_type, 0)
            price_text = Config.format_price(original_price)
            
            keyboard = [
                [InlineKeyboardButton(f"💳 ادامه بدون تخفیف ({price_text})", callback_data=f'payment_{course_type}')],
                [InlineKeyboardButton("🏷️ کد تخفیف جدید", callback_data=f'coupon_{course_type}')],
                [InlineKeyboardButton("🔙 بازگشت", callback_data=f'{course_type}')]
            ]
            
            await update.message.reply_text(
                f"❌ {message}\n\n"
                f"💡 می‌توانید بدون کد تخفیف ادامه دهید یا کد تخفیف دیگری وارد کنید.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
        
        # Calculate discounted price
        original_price = Config.PRICES.get(course_type, 0)
        final_price, discount_amount = self.coupon_manager.calculate_discounted_price(original_price, sanitized_code)
        
        # Store coupon for this user
        self.user_coupon_codes[user_id] = {
            'code': sanitized_code,
            'discount_percent': discount_percent,
            'discount_amount': discount_amount,
            'course_type': course_type
        }
        
        # Show discounted price and payment option
        original_price_text = Config.format_price(original_price)
        final_price_text = Config.format_price(final_price)
        discount_amount_text = Config.format_price(discount_amount)
        
        keyboard = [
            [InlineKeyboardButton(f"💳 پرداخت ({final_price_text})", callback_data=f'payment_coupon_{course_type}')],
            [InlineKeyboardButton("🔙 بازگشت", callback_data=f'{course_type}')]
        ]
        
        await update.message.reply_text(
            f"✅ {message}\n\n"
            f"💰 قیمت اصلی: {original_price_text}\n"
            f"🏷️ تخفیف ({discount_percent}%): -{discount_amount_text}\n"
            f"💳 قیمت نهایی: {final_price_text}\n\n"
            f"🎉 شما {discount_amount_text} صرفه‌جویی کردید!",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # =====================================
    # ADMIN PLAN UPLOAD HANDLERS
    # =====================================
    
    async def handle_plan_upload_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
        """Handle text input during plan upload process"""
        user_id = update.effective_user.id
        admin_context = context.user_data.get(user_id, {})
        
        # UNIFIED INPUT TYPE VALIDATION for admin operations
        from input_validator import input_validator
        
        upload_step = admin_context.get('plan_upload_step')
        
        # Validate that text input is appropriate for this step
        expected_input_types = {
            'title': 'plan_description',
            'description': 'plan_description'
        }
        
        if upload_step in expected_input_types:
            is_valid = await input_validator.validate_and_reject_wrong_input_type(
                update, expected_input_types[upload_step], f"آپلود برنامه - مرحله {upload_step}", is_admin=True
            )
            if not is_valid:
                return
        
        upload_step = admin_context.get('plan_upload_step')
        
        # Support both old and new upload workflows
        course_type = admin_context.get('plan_course_type') or admin_context.get('plan_course_code')
        target_user_id = admin_context.get('plan_user_id')  # For user-specific plans
        
        if upload_step == 'title':
            sanitized_text = sanitize_text(text)
            # Store the title and ask for file
            context.user_data[user_id]['plan_title'] = sanitized_text
            context.user_data[user_id]['plan_upload_step'] = 'file'
            
            course_names = {
                'online_weights': '🏋️ وزنه آنلاین',
                'online_cardio': '🏃 هوازی آنلاین',
                'online_combo': '💪 ترکیبی آنلاین',
                'in_person_cardio': '🏃‍♂️ هوازی حضوری',
                'in_person_weights': '🏋️‍♀️ وزنه حضوری'
            }
            
            course_name = course_names.get(course_type, course_type)
            
            # Add target user info if uploading for specific user
            user_info = ""
            if target_user_id:
                try:
                    with open('bot_data.json', 'r', encoding='utf-8') as f:
                        bot_data = json.load(f)
                    user_data = bot_data.get('users', {}).get(target_user_id, {})
                    user_name = user_data.get('name', 'نامشخص')
                    user_info = f"\n👤 برای کاربر: {user_name}"
                except:
                    pass
            
            await update.message.reply_text(
                f"✅ عنوان برنامه ثبت شد: {sanitized_text}{user_info}\n\n"
                f"📁 حال لطفاً فایل برنامه {course_name} را ارسال کنید:\n\n"
                f"📋 فرمت‌های قابل قبول:\n"
                f"• فایل PDF\n"
                f"• تصاویر (JPG, PNG)\n"
                f"• متن (فایل TXT)\n\n"
                f"💡 یا می‌توانید متن برنامه را مستقیماً بنویسید."
            )
            
        elif upload_step == 'description':
            sanitized_text = sanitize_text(text)
            # Store the description and complete upload
            context.user_data[user_id]['plan_description'] = sanitized_text
            
            # Log description received
            await admin_error_handler.log_plan_upload_workflow(
                admin_id=user_id, 
                step='description_received',
                plan_data={'description': sanitized_text[:50] + '...' if len(sanitized_text) > 50 else sanitized_text}
            )
            
            await self.complete_plan_upload(update, context)
            
        elif upload_step == 'file' and text:
            sanitized_text = sanitize_text(text)
            # Handle direct text input as plan content
            context.user_data[user_id]['plan_content'] = sanitized_text
            context.user_data[user_id]['plan_content_type'] = 'text'
            context.user_data[user_id]['plan_upload_step'] = 'description'
            
            # Log text content received
            await admin_error_handler.log_plan_upload_workflow(
                admin_id=user_id, 
                step='text_content_received',
                plan_data={'content_type': 'text', 'content_length': len(sanitized_text)}
            )
            
            keyboard = [[InlineKeyboardButton("⏩ رد کردن توضیحات", callback_data='skip_plan_description')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "✅ محتوای برنامه دریافت شد!\n\n"
                "📝 حال توضیحات اضافی برنامه را بنویسید (اختیاری):\n\n"
                "💡 مثال: مناسب برای مبتدیان، دوره 8 هفته‌ای، نیاز به تجهیزات ورزشی",
                reply_markup=reply_markup
            )

    async def handle_plan_upload_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Handle document upload during plan upload process"""
        user_id = update.effective_user.id
        admin_context = context.user_data.get(user_id, {})
        
        # Check both old and new upload workflows
        if not (admin_context.get('uploading_plan') or admin_context.get('uploading_user_plan')):
            return False  # Not in upload mode
            
        upload_step = admin_context.get('plan_upload_step')
        
        if upload_step == 'file':
            document = update.message.document
            filename = document.file_name or "plan_file"
            
            # Validate file type (similar to questionnaire system)
            if filename.lower().endswith(('.pdf', '.txt', '.doc', '.docx')):
                # Log successful file upload
                await admin_error_handler.log_file_operation(
                    operation='plan_upload',
                    file_type='document',
                    file_id=document.file_id,
                    local_path=filename,
                    success=True,
                    admin_id=user_id
                )
                
                # Store document info
                context.user_data[user_id]['plan_content'] = document.file_id
                context.user_data[user_id]['plan_content_type'] = 'document'
                context.user_data[user_id]['plan_filename'] = filename
                context.user_data[user_id]['plan_upload_step'] = 'description'
                
                # Get file type for user feedback
                file_extension = filename.split('.')[-1].upper()
                
                keyboard = [[InlineKeyboardButton("⏩ رد کردن توضیحات", callback_data='skip_plan_description')]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    f"✅ فایل {file_extension} دریافت شد: {filename}\n\n"
                    f"📝 حال توضیحات اضافی برنامه را بنویسید (اختیاری):\n\n"
                    f"💡 مثال: مناسب برای مبتدیان، دوره 8 هفته‌ای، نیاز به تجهیزات ورزشی",
                    reply_markup=reply_markup
                )
                return True
            else:
                # Log failed file upload attempt
                await admin_error_handler.log_file_operation(
                    operation='plan_upload',
                    file_type='document',
                    file_id=document.file_id,
                    local_path=filename,
                    success=False,
                    error_message=f"Unsupported file type: {filename}",
                    admin_id=user_id
                )
                
                # Invalid file type - provide helpful error message
                await update.message.reply_text(
                    "❌ فرمت فایل پشتیبانی نمی‌شود!\n\n"
                    "📋 فرمت‌های قابل قبول:\n"
                    "• فایل PDF (.pdf)\n"
                    "• فایل متنی (.txt)\n"
                    "• فایل Word (.doc, .docx)\n\n"
                    "💡 یا می‌توانید:\n"
                    "📝 متن برنامه را مستقیماً بنویسید\n"
                    "📸 عکس برنامه را ارسال کنید (JPG, PNG)\n\n"
                    "🔄 لطفاً فایل مناسب ارسال کنید یا متن برنامه را بنویسید."
                )
                return True  # We handled the upload, even though it was invalid
            
        return False

    async def handle_plan_upload_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Handle photo upload during plan upload process"""
        user_id = update.effective_user.id
        admin_context = context.user_data.get(user_id, {})
        
        # Check both old and new upload workflows
        if not (admin_context.get('uploading_plan') or admin_context.get('uploading_user_plan')):
            return False  # Not in upload mode
            
        upload_step = admin_context.get('plan_upload_step')
        
        if upload_step == 'file':
            photo = update.message.photo[-1]  # Get highest resolution
            
            # Store photo info
            context.user_data[user_id]['plan_content'] = photo.file_id
            context.user_data[user_id]['plan_content_type'] = 'photo'
            context.user_data[user_id]['plan_upload_step'] = 'description'
            
            keyboard = [[InlineKeyboardButton("⏩ رد کردن توضیحات", callback_data='skip_plan_description')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"✅ تصویر برنامه دریافت شد!\n\n"
                f"📝 حال توضیحات اضافی برنامه را بنویسید (اختیاری):\n\n"
                f"💡 مثال: مناسب برای مبتدیان، دوره 8 هفته‌ای، نیاز به تجهیزات ورزشی",
                reply_markup=reply_markup
            )
            return True
            
        return False

    async def complete_plan_upload(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Complete the plan upload process"""
        user_id = update.effective_user.id
        admin_context = context.user_data.get(user_id, {})
        
        # Support both old and new upload workflows
        course_type = admin_context.get('plan_course_type') or admin_context.get('plan_course_code')
        target_user_id = admin_context.get('plan_user_id')  # For user-specific plans
        title = admin_context.get('plan_title')
        content = admin_context.get('plan_content')
        content_type = admin_context.get('plan_content_type')
        filename = admin_context.get('plan_filename', '')
        description = admin_context.get('plan_description', '')
        
        # Create plan data with improved plan_id generation
        existing_plans = await self.admin_panel.load_course_plans(course_type)
        
        # Generate unique plan_id with duplicate checking
        import uuid
        plan_id = None
        max_attempts = 10
        attempt = 0
        
        while plan_id is None and attempt < max_attempts:
            # Generate candidate ID
            candidate_id = str(uuid.uuid4())[:8]
            
            # Check if this ID already exists
            id_exists = any(plan.get('id') == candidate_id for plan in existing_plans)
            
            if not id_exists:
                plan_id = candidate_id
            else:
                attempt += 1
        
        # Fallback if all attempts failed
        if plan_id is None:
            plan_id = f"{course_type}_{int(time.time())}"
        
        plan_data = {
            'id': plan_id,
            'title': title,
            'content': content,
            'content_type': content_type,
            'filename': filename,
            'description': description,
            'created_at': datetime.now().isoformat(),
            'created_by': user_id
        }
        
        # If uploading for specific user, add user-specific info
        if target_user_id:
            plan_data['target_user_id'] = target_user_id
            plan_data['is_user_specific'] = True
        
        # Load existing plans and add new one
        plans_before = await self.admin_panel.load_course_plans(course_type)
        plans_before_count = len(plans_before)
        
        # Log save attempt
        await admin_error_handler.log_plan_upload_workflow(
            admin_id=user_id,
            step='save_attempt',
            plan_data={'title': title, 'course_type': course_type, 'target_user_id': target_user_id}
        )
        
        plans_before.append(plan_data)
        
        # Save plans
        success = await self.admin_panel.save_course_plans(course_type, plans_before)
        
        # Verify save by loading again
        plans_after = await self.admin_panel.load_course_plans(course_type)
        plans_after_count = len(plans_after)
        
        # Log save result
        await admin_error_handler.log_plan_upload_workflow(
            admin_id=user_id,
            step='save_result',
            plan_data={
                'title': title, 
                'course_type': course_type, 
                'plans_before': plans_before_count,
                'plans_after': plans_after_count,
                'plan_id': plan_id
            },
            success=success and (plans_after_count > plans_before_count)
        )
        
        if success:
            course_names = {
                'online_weights': '🏋️ وزنه آنلاین',
                'online_cardio': '🏃 هوازی آنلاین',
                'online_combo': '💪 ترکیبی آنلاین',
                'in_person_cardio': '🏃‍♂️ هوازی حضوری',
                'in_person_weights': '🏋️‍♀️ وزنه حضوری'
            }
            
            course_name = course_names.get(course_type, course_type)
            
            # Different back button based on workflow with better navigation options
            if target_user_id:
                keyboard = [
                    [InlineKeyboardButton("🔙 بازگشت به مدیریت این کاربر", callback_data=f'manage_user_course_{target_user_id}_{course_type}')],
                    [InlineKeyboardButton("📋 مدیریت کلیه برنامه‌ها", callback_data='admin_plans')],
                    [InlineKeyboardButton("🏠 بازگشت به پنل اصلی", callback_data='admin_back_main')]
                ]
                user_info = f"\n👤 برای کاربر: {target_user_id}"
            else:
                keyboard = [
                    [InlineKeyboardButton("🔧 مدیریت برنامه‌های این دوره", callback_data=f'plan_course_{course_type}')],
                    [InlineKeyboardButton("📂 مدیریت کلیه برنامه‌ها", callback_data='admin_plans')],
                    [InlineKeyboardButton("🏠 بازگشت به پنل اصلی", callback_data='admin_back_main')]
                ]
                user_info = ""
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"✅ برنامه با موفقیت آپلود شد!\n\n"
                f"📋 عنوان: {title}\n"
                f"🎯 دوره: {course_name}{user_info}\n"
                f"📄 نوع محتوا: {content_type}\n"
                f"📝 توضیحات: {description or 'ندارد'}\n\n"
                f"🎉 اکنون می‌توانید این برنامه را برای کاربران ارسال کنید!",
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                "❌ خطا در ذخیره برنامه! لطفاً مجددا تلاش کنید."
            )
        
        # Clear upload state (both old and new workflow fields)
        if user_id in context.user_data:
            context.user_data[user_id].pop('uploading_plan', None)
            context.user_data[user_id].pop('uploading_user_plan', None)
            context.user_data[user_id].pop('plan_course_type', None)
            context.user_data[user_id].pop('plan_course_code', None)
            context.user_data[user_id].pop('plan_user_id', None)
            context.user_data[user_id].pop('plan_upload_step', None)
            context.user_data[user_id].pop('plan_title', None)
            context.user_data[user_id].pop('plan_content', None)
            context.user_data[user_id].pop('plan_content_type', None)
            context.user_data[user_id].pop('plan_filename', None)
            context.user_data[user_id].pop('plan_description', None)

    async def handle_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle payment process - go directly to payment"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        
        # Add cooldown protection for payment actions
        if await self.check_cooldown(user_id):
            return
        
        # Handle both regular payment and coupon payment
        if query.data.startswith('payment_coupon_'):
            course_type = query.data.replace('payment_coupon_', '')
        else:
            course_type = query.data.replace('payment_', '')
        
        # 🚫 DUPLICATE PURCHASE PREVENTION (only for same course)
        # Check if user already has an approved payment for this course
        if await self.check_duplicate_purchase(user_id, course_type):
            await query.edit_message_text(
                "⚠️ شما قبلاً این دوره را خریداری کرده‌اید!\n\n"
                "✅ پرداخت شما تایید شده و دسترسی فعال است.\n\n"
                "📋 اگر پرسشنامه را تکمیل نکرده‌اید، لطفاً تکمیل کنید.\n"
                "📞 برای سوالات بیشتر با پشتیبانی @DrBohloul تماس بگیرید.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 بازگشت به انتخاب دوره", callback_data='back_to_course_selection')]
                ])
            )
            return
        
        # Check if user has a pending payment for this specific course
        if await self.check_pending_purchase(user_id, course_type):
            await query.edit_message_text(
                "⏳ شما قبلاً برای این دوره پرداخت کرده‌اید!\n\n"
                "🔍 پرداخت شما در حال بررسی توسط ادمین است.\n"
                "📱 از نتیجه بررسی مطلع خواهید شد.\n\n"
                "💡 اگر نیاز به پرداخت مجدد دارید، ابتدا با پشتیبانی @DrBohloul تماس بگیرید.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 بازگشت به انتخاب دوره", callback_data='back_to_course_selection')]
                ])
            )
            return
        
        # Store the course type for this user in context (not in payment_pending yet)
        # payment_pending will be set in show_payment_details with full pricing info
        
        # For additional course purchases, store in context
        user_context = context.user_data.get(user_id, {})
        if user_context.get('buying_additional_course'):
            context.user_data[user_id]['current_course_selection'] = course_type
        
        # Go directly to payment details (questionnaire comes after approval)
        await self.show_payment_details(update, context, course_type)

    async def check_duplicate_purchase(self, user_id: int, course_type: str) -> bool:
        """Check if user already has an approved payment for this course"""
        try:
            with open('bot_data.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            payments = data.get('payments', {})
            
            for payment_data in payments.values():
                if (payment_data.get('user_id') == user_id and 
                    payment_data.get('course_type') == course_type and 
                    payment_data.get('status') == 'approved'):
                    return True
            
            return False
        except Exception as e:
            error_logger.error(f"Error checking duplicate purchase for user {user_id}: {e}", exc_info=True)
            return False

    async def check_pending_purchase(self, user_id: int, course_type: str) -> bool:
        """Check if user has a pending payment for this course"""
        try:
            with open('bot_data.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            payments = data.get('payments', {})
            
            for payment_data in payments.values():
                if (payment_data.get('user_id') == user_id and 
                    payment_data.get('course_type') == course_type and 
                    payment_data.get('status') == 'pending_approval'):
                    return True
            
            return False
        except Exception as e:
            error_logger.error(f"Error checking pending purchase for user {user_id}: {e}", exc_info=True)
            return False

    async def handle_csv_import(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle CSV file imports for admins"""
        user_id = update.effective_user.id
        
        # Check if user is admin
        if not await self.admin_panel.admin_manager.is_admin(user_id):
            await update.message.reply_text("❌ شما دسترسی ادمین ندارید.")
            return
        
        document = update.message.document
        
        # Check if it's a CSV file
        if not (document.file_name.endswith('.csv') or document.mime_type == 'text/csv'):
            await update.message.reply_text(
                "❌ فقط فایل‌های CSV پذیرفته می‌شوند!\n\n"
                "📋 برای راهنمای واردات، از منوی ادمین > واردات/صادرات استفاده کنید."
            )
            return
        
        # Check file size (max 5MB)
        if document.file_size > 5 * 1024 * 1024:
            await update.message.reply_text("❌ حجم فایل نباید بیشتر از ۵ مگابایت باشد!")
            return
        
        try:
            # Download file
            file = await context.bot.get_file(document.file_id)
            file_content = await file.download_as_bytearray()
            
            # Decode CSV content
            csv_content = file_content.decode('utf-8')
            
            # Determine import type based on headers
            lines = csv_content.strip().split('\n')
            if len(lines) < 2:
                await update.message.reply_text("❌ فایل CSV خالی است یا فرمت صحیح ندارد!")
                return
            
            headers = lines[0].lower().split(',')
            
            # Check if it's users or payments import
            if 'user_id' in headers and 'name' in headers:
                await self.import_users_csv(update, csv_content)
            elif 'user_id' in headers and 'course_type' in headers and 'price' in headers:
                await self.import_payments_csv(update, csv_content)
            else:
                await update.message.reply_text(
                    "❌ فرمت CSV شناخته نشده!\n\n"
                    "🔍 فرمت‌های پشتیبانی شده:\n"
                    "• کاربران: user_id,name,username,course_selected,payment_status\n"
                    "• پرداخت‌ها: user_id,course_type,price,status"
                )
        
        except Exception as e:
            error_logger.error(f"Error processing CSV import for admin {user_id}: {e}", exc_info=True)
            await update.message.reply_text(f"❌ خطا در پردازش فایل: {str(e)}")

    async def import_users_csv(self, update: Update, csv_content: str) -> None:
        """Import users from CSV content"""
        try:
            csv_reader = csv.DictReader(io.StringIO(csv_content))
            
            imported_count = 0
            errors = []
            
            for row_num, row in enumerate(csv_reader, 2):  # Start from row 2 (after header)
                try:
                    user_id = int(row.get('user_id', '').strip())
                    name = row.get('name', '').strip()
                    username = row.get('username', '').strip()
                    course_selected = row.get('course_selected', '').strip()
                    payment_status = row.get('payment_status', '').strip()
                    
                    if not user_id or not name:
                        errors.append(f"سطر {row_num}: user_id و name ضروری هستند")
                        continue
                    
                    # Validate course type
                    valid_courses = ['in_person_weights', 'in_person_cardio', 'online_weights', 'online_cardio', 'online_combo', 'nutrition_plan']
                    if course_selected and course_selected not in valid_courses:
                        errors.append(f"سطر {row_num}: نوع دوره نامعتبر: {course_selected}")
                        continue
                    
                    # Validate payment status
                    valid_statuses = ['pending_approval', 'approved', 'rejected', '']
                    if payment_status and payment_status not in valid_statuses:
                        errors.append(f"سطر {row_num}: وضعیت پرداخت نامعتبر: {payment_status}")
                        continue
                    
                    # Save user data
                    user_data = {
                        'name': name,
                        'username': username,
                        'course_selected': course_selected,
                        'payment_status': payment_status,
                        'imported_at': datetime.now().isoformat(),
                        'imported_by': update.effective_user.id
                    }
                    
                    await self.data_manager.save_user_data(user_id, user_data)
                    imported_count += 1
                    
                except ValueError:
                    errors.append(f"سطر {row_num}: user_id باید عدد باشد")
                except Exception as e:
                    errors.append(f"سطر {row_num}: {str(e)}")
            
            # Send result
            result_text = f"✅ واردات کاربران تکمیل شد!\n\n"
            result_text += f"📊 تعداد وارد شده: {imported_count} کاربر\n"
            
            if errors:
                result_text += f"⚠️ تعداد خطا: {len(errors)}\n\n"
                result_text += "🔸 خطاها:\n"
                for error in errors[:10]:  # Show max 10 errors
                    result_text += f"• {error}\n"
                if len(errors) > 10:
                    result_text += f"... و {len(errors) - 10} خطای دیگر"
            
            await update.message.reply_text(result_text)
            
        except Exception as e:
            await update.message.reply_text(f"❌ خطا در واردات کاربران: {str(e)}")

    async def import_payments_csv(self, update: Update, csv_content: str) -> None:
        """Import payments from CSV content"""
        try:
            csv_reader = csv.DictReader(io.StringIO(csv_content))
            
            imported_count = 0
            errors = []
            
            for row_num, row in enumerate(csv_reader, 2):  # Start from row 2 (after header)
                try:
                    user_id = int(row.get('user_id', '').strip())
                    course_type = row.get('course_type', '').strip()
                    price = int(row.get('price', '').strip())
                    status = row.get('status', '').strip()
                    
                    if not user_id or not course_type or not price:
                        errors.append(f"سطر {row_num}: user_id، course_type و price ضروری هستند")
                        continue
                    
                    # Validate course type
                    valid_courses = ['in_person_weights', 'in_person_cardio', 'online_weights', 'online_cardio', 'online_combo', 'nutrition_plan']
                    if course_type not in valid_courses:
                        errors.append(f"سطر {row_num}: نوع دوره نامعتبر: {course_type}")
                        continue
                    
                    # Validate status
                    valid_statuses = ['pending_approval', 'approved', 'rejected', 'pending']
                    if status and status not in valid_statuses:
                        errors.append(f"سطر {row_num}: وضعیت نامعتبر: {status}")
                        continue
                    
                    # Save payment data
                    payment_data = {
                        'course_type': course_type,
                        'price': price,
                        'status': status if status else 'pending_approval',
                        'imported_at': datetime.now().isoformat(),
                        'imported_by': update.effective_user.id
                    }
                    
                    await self.data_manager.save_payment_data(user_id, payment_data)
                    imported_count += 1
                    
                except ValueError:
                    errors.append(f"سطر {row_num}: user_id و price باید عدد باشند")
                except Exception as e:
                    errors.append(f"سطر {row_num}: {str(e)}")
            
            # Send result
            result_text = f"✅ واردات پرداخت‌ها تکمیل شد!\n\n"
            result_text += f"📊 تعداد وارد شده: {imported_count} پرداخت\n"
            
            if errors:
                result_text += f"⚠️ تعداد خطا: {len(errors)}\n\n"
                result_text += "🔸 خطاها:\n"
                for error in errors[:10]:  # Show max 10 errors
                    result_text += f"• {error}\n"
                if len(errors) > 10:
                    result_text += f"... و {len(errors) - 10} خطای دیگر"
            
            await update.message.reply_text(result_text)
            
        except Exception as e:
            await update.message.reply_text(f"❌ خطا در واردات پرداخت‌ها: {str(e)}")

    async def start_questionnaire(self, update: Update, context: ContextTypes.DEFAULT_TYPE, course_type: str = None) -> None:
        """
        Start the questionnaire process (PERSON-SPECIFIC, not course-specific)
        
        The questionnaire is tied to the PERSON, not the course they're purchasing.
        Once completed, it applies to ALL their future course purchases.
        """
        query = update.callback_query
        user_id = update.effective_user.id
        
        # Check if user already has completed questionnaire
        existing_progress = await self.questionnaire_manager.load_user_progress(user_id)
        if existing_progress and existing_progress.get('completed', False):
            # User already has completed questionnaire - show confirmation and redirect to course payment
            
            # Check if user is buying additional course
            user_context = context.user_data.get(user_id, {})
            is_additional_purchase = user_context.get('buying_additional_course', False)
            
            if is_additional_purchase:
                # Show confirmation message for additional course purchase
                confirmation_message = """✅ عالی! شما قبلاً پرسشنامه را تکمیل کرده‌اید

🎯 اطلاعات شخصی شما در سیستم موجود است و برای این دوره جدید نیز استفاده خواهد شد.

💡 دیگر نیازی به تکمیل مجدد پرسشنامه نیست.

📚 حالا می‌توانید برای دوره جدیدتان پرداخت کنید."""
                
                keyboard = [
                    [InlineKeyboardButton("💳 ادامه به پرداخت", callback_data=f'payment_{course_type}')],
                    [InlineKeyboardButton("🔙 بازگشت", callback_data='back_to_user_menu')]
                ]
                
                await query.edit_message_text(
                    confirmation_message,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                return
            else:
                # Regular flow - redirect to payment
                await self.show_payment_details(update, context, course_type)
                return
        
        # Start or resume questionnaire (regardless of course type)
        if not existing_progress:
            # Start fresh questionnaire
            await self.questionnaire_manager.start_questionnaire(user_id)
        
        # Get current question
        question = await self.questionnaire_manager.get_current_question(user_id)
        
        if question:
            intro_message = f"""✨ عالی! قبل از پرداخت باید اطلاعاتت رو تکمیل کنیم

📋 این پرسشنامه شخصی شماست و برای همه دوره‌هایتان استفاده می‌شود
⭐ فقط یک بار تکمیل کنید، برای همه خریدهای بعدی استفاده می‌شود

🔢 این فرآیند فقط {17} سوال ساده داره تا بتونم بهترین برنامه تمرینی رو برات طراحی کنم

⏱️ زمان تقریبی: 3-5 دقیقه

آماده‌ای؟ بیا شروع کنیم! 🚀

───────────────────
{question['progress_text']}

{question['text']}"""
            
            # Add choices as buttons if it's a choice question
            keyboard = []
            if question.get('type') == 'choice':
                choices = question.get('choices', [])
                for choice in choices:
                    keyboard.append([InlineKeyboardButton(choice, callback_data=f'q_answer_{choice}')])
                keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data='back_to_user_menu')])
            else:
                keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data='back_to_user_menu')]]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(intro_message, reply_markup=reply_markup)
        else:
            # Something went wrong, proceed to payment if course_type provided
            if course_type:
                await self.show_payment_details(update, context, course_type)
            else:
                await query.answer("خطا در بارگذاری پرسشنامه")
                await self.show_status_based_menu(update, context, await self.data_manager.get_user_data(user_id), update.effective_user.first_name or "کاربر")

    async def show_payment_details(self, update: Update, context: ContextTypes.DEFAULT_TYPE, course_type: str) -> None:
        """Show payment details with coupon support"""
        user_id = update.effective_user.id
        
        # Check if user has applied a coupon
        coupon_info = self.user_coupon_codes.get(user_id)
        original_price = Config.PRICES[course_type]
        final_price = original_price
        
        if coupon_info and coupon_info.get('course_type') == course_type:
            final_price = original_price - coupon_info.get('discount_amount', 0)
            
            # Mark coupon as used
            self.coupon_manager.use_coupon(coupon_info['code'])
            
            # Clear coupon from user session
            del self.user_coupon_codes[user_id]
        
        # Save course selection in user data (but NOT payment status yet)
        await self.data_manager.save_user_data(user_id, {
            'course_selected': course_type
        })
        
        # Store course selection and pricing info for when receipt is uploaded
        # but do NOT create payment record yet - that happens only on receipt upload
        self.payment_pending[user_id] = {
            'course_type': course_type,
            'price': final_price,
            'original_price': original_price,
            'coupon_info': coupon_info
        }
        
        # EXPLICIT PAYMENT FLOW STATE - Set awaiting receipt flag
        if user_id not in context.user_data:
            context.user_data[user_id] = {}
        context.user_data[user_id]['awaiting_payment_receipt'] = True
        context.user_data[user_id]['payment_course'] = course_type
        
        payment_logger.info(f"User {user_id} entering payment flow for course: {course_type}")
        
        # Format prices properly
        final_price_text = Config.format_price(final_price)
        
        # Special message for nutrition plan
        if course_type == 'nutrition_plan':
            payment_message = f"""✨ این برنامه شامل:
• برنامه غذایی کامل بر اساس نیازهای شما
• راهنمایی تخصصی تغذیه ورزشی
• پیگیری و تنظیم برنامه
❌توجه داشته باشید همه فیلدهای فرم رو پر کنید وبرای قسمت اعداد، کیورد اعداد انگلیسی رو وارد کنید 

برای پرداخت به شماره کارت زیر واریز کنید:

💡 برای کپی کردن شماره کارت، روی آن کلیک کنید
💳 شماره کارت: {Config.format_card_number(Config.PAYMENT_CARD_NUMBER)}
👤 نام صاحب حساب: {Config.PAYMENT_CARD_HOLDER}
💰 مبلغ: {final_price_text}"""
        else:
            # Generic payment message for other courses
            course_title = Config.COURSE_DETAILS.get(course_type, {}).get('title', 'دوره انتخابی')
            payment_message = f"""📚 {course_title}

برای پرداخت به شماره کارت زیر واریز کنید:

💡 برای کپی کردن شماره کارت، روی آن کلیک کنید
💳 شماره کارت: {Config.format_card_number(Config.PAYMENT_CARD_NUMBER)}
👤 نام صاحب حساب: {Config.PAYMENT_CARD_HOLDER}
💰 مبلغ: {final_price_text}"""
        
        if coupon_info:
            original_price_text = Config.format_price(original_price)
            discount_amount_text = Config.format_price(coupon_info['discount_amount'])
            payment_message += f"""

🏷️ کد تخفیف: {coupon_info['code']}
💰 قیمت اصلی: {original_price_text}
🎯 تخفیف: -{discount_amount_text}
✅ قیمت نهایی: {final_price_text}"""
        
        payment_message += """

بعد از واریز، فیش یا اسکرین شات رو همینجا ارسال کنید تا بررسی شه ✅

⚠️ توجه: فقط فیش واریز رو ارسال کنید"""
        
        # Add contextual back button based on course type
        if course_type == 'nutrition_plan':
            back_button_text = "🔙 بازگشت به انتخاب دوره"
            back_callback = 'back_to_course_selection'
        else:
            back_button_text = "🔙 بازگشت به منو اصلی"
            back_callback = 'back_to_user_menu'
            
        keyboard = [
            [InlineKeyboardButton(back_button_text, callback_data=back_callback)]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.edit_message_text(payment_message, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.message.reply_text(payment_message, reply_markup=reply_markup, parse_mode='Markdown')

    async def handle_photo_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        MASTER PHOTO ROUTER - Routes photos to appropriate handlers based on user state
        This ensures photos are processed correctly based on context, not blindly as payment receipts
        """
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name or "کاربر"
        
        user_logger.debug(f"Photo received from user {user_id} ({user_name})")
        
        # First, validate that this is actually a photo message
        if not update.message or not update.message.photo:
            error_logger.warning(f"Non-photo message received from user {user_id}")
            await update.message.reply_text(
                "❌ فقط تصاویر قابل پردازش هستند!\n\n"
                "لطفاً یک عکس ارسال کنید (نه فایل یا متن)."
            )
            return

        # PRIORITY 1: Check if admin is uploading a plan
        if await self.admin_panel.admin_manager.is_admin(user_id):
            admin_context = context.user_data.get(user_id, {})
            if admin_context.get('uploading_plan') or admin_context.get('uploading_user_plan'):
                admin_logger.debug(f"Admin {user_id} uploading plan photo")
                if await self.handle_plan_upload_photo(update, context):
                    return
        
        # PRIORITY 2: Check if user is in questionnaire mode
        user_data = await self.data_manager.get_user_data(user_id)
        payment_status = user_data.get('payment_status')
        user_context = context.user_data.get(user_id, {})
        
        user_logger.debug(f"PHOTO DEBUG for User {user_id} | Payment: {payment_status} | Active: {user_context.get('questionnaire_active', False)}")
        
        # ENHANCED QUESTIONNAIRE DETECTION: Check multiple conditions
        in_questionnaire_mode = False
        
        # Method 1: Check if questionnaire_active flag is set
        if user_context.get('questionnaire_active', False):
            in_questionnaire_mode = True
            user_logger.debug(f"QUESTIONNAIRE MODE for User {user_id} detected via active flag")
        
        # Method 2: Check if user has approved payment and unfinished questionnaire
        elif payment_status == 'approved':
            # Check if user has questionnaire progress 
            questionnaire_progress = await self.questionnaire_manager.load_user_progress(user_id)
            if (questionnaire_progress and 
                not questionnaire_progress.get("completed", False) and 
                questionnaire_progress.get("current_step", 0) > 0):
                in_questionnaire_mode = True
                user_logger.debug(f"QUESTIONNAIRE MODE for User {user_id} detected via payment+progress")
                
                # AUTO-SET questionnaire_active flag for consistency
                if user_id not in context.user_data:
                    context.user_data[user_id] = {}
                context.user_data[user_id]['questionnaire_active'] = True
                user_logger.debug(f"AUTO-SET questionnaire_active flag for user {user_id}")
        
        if in_questionnaire_mode:
            current_question = await self.questionnaire_manager.get_current_question(user_id)
            
            user_logger.debug(f"PHOTO DEBUG for User {user_id} | Current question: {current_question is not None}")
            if current_question:
                user_logger.debug(f"PHOTO DEBUG for User {user_id} | Question type: {current_question.get('type')} | Step: {current_question.get('step')}")
            
            if current_question:
                question_type = current_question.get("type")
                
                if question_type == "photo":
                    user_logger.debug(f"PHOTO ROUTER - User {user_id} in questionnaire photo step")
                    await self.handle_questionnaire_photo(update, context)
                    return
                else:
                    # User sent photo but different input type is expected (text, number, etc.)
                    user_logger.debug(f"PHOTO ROUTER - User {user_id} sent photo for {question_type} question - showing error")
                    from input_validator import input_validator
                    
                    is_valid = await input_validator.validate_and_reject_wrong_input_type(
                        update, question_type, f"پرسشنامه - سوال {current_question.get('step', '?')}", is_admin=False
                    )
                    return  # Error message already sent by validator
        
        # PRIORITY 3: Check if user is waiting for coupon code (not photo)
        if user_context.get('waiting_for_coupon'):
            user_logger.debug(f"PHOTO ROUTER - User {user_id} sent photo while waiting for coupon - showing error")
            from input_validator import input_validator
            
            await input_validator.validate_and_reject_wrong_input_type(
                update, 'coupon_code', "ورود کد تخفیف", is_admin=False
            )
            return
        
        # PRIORITY 4: Check if user is actively in payment flow
        user_context = context.user_data.get(user_id, {})
        actively_in_payment_flow = (
            user_context.get('buying_additional_course') or
            user_id in self.payment_pending or
            user_context.get('awaiting_payment_receipt')
        )
        
        # DEBUG: Log payment flow state
        payment_logger.debug(f"PHOTO ROUTER DEBUG - User {user_id}:")
        payment_logger.debug(f"  - buying_additional_course: {user_context.get('buying_additional_course')}")
        payment_logger.debug(f"  - in payment_pending: {user_id in self.payment_pending}")
        payment_logger.debug(f"  - awaiting_payment_receipt: {user_context.get('awaiting_payment_receipt')}")
        payment_logger.debug(f"  - actively_in_payment_flow: {actively_in_payment_flow}")
        
        if actively_in_payment_flow:
            payment_logger.debug(f"PHOTO ROUTER - User {user_id} in payment flow")
            await self.handle_payment_receipt(update, context)
            return
        
        # FALLBACK: Photo sent outside valid context - PROVIDE DEBUG INFO
        # User requested complete silence when no input is expected (like in main menu)
        user_logger.debug(f"PHOTO ROUTER - User {user_id} sent photo outside valid context")
        
        # DEBUG: For troubleshooting, let's show what we found
        await update.message.reply_text(
            f"🔍 DEBUG: تصویر در زمینه نامعتبر ارسال شد\n\n"
            f"وضعیت فعلی:\n"
            f"📊 در حال پرسشنامه: {in_questionnaire_mode}\n"
            f"💳 در جریان پرداخت: {actively_in_payment_flow}\n"
            f"🎯 انتظار کوپن: {user_context.get('waiting_for_coupon', False)}\n\n"
            f"برای شروع مجدد: /start"
        )

    async def handle_payment_receipt(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle ONLY payment receipt photos - called after photo router validation"""
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name or "کاربر"
        
        payment_logger.debug(f"Processing payment receipt from user {user_id} ({user_name})")
        
        # At this point, the photo router has already validated this is a payment receipt context
        # So we can proceed directly with payment processing
        
        # Get user data and context
        user_data = await self.data_manager.get_user_data(user_id)
        user_context = context.user_data.get(user_id, {})
        course_selected = user_context.get('current_course_selection') or user_data.get('course_selected')
        
        if not course_selected:
            await update.message.reply_text(
                "❌ ابتدا یک دوره انتخاب کنید!\n\n"
                "برای شروع /start را بزنید."
            )
            return

        # Handle different payment states
        payment_status = user_data.get('payment_status')
        
        if payment_status == 'pending_approval':
            payment_logger.warning(f"User {user_id} sent duplicate receipt - already pending")
            await update.message.reply_text(
                "✅ فیش واریز شما قبلاً دریافت شده است!\n\n"
                "⏳ در حال بررسی توسط ادمین...\n"
                "📱 از وضعیت پرداخت مطلع خواهید شد.\n\n"
                "🔄 برای بازگشت به منو: /start"
            )
            return

        # Process new payment receipt
        await self.process_new_course_payment(update, context)

    async def process_new_course_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Process payment receipt for new course purchase"""
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name or "کاربر"
        
        # Get selected course for this payment
        user_context = context.user_data.get(user_id, {})
        course_selected = user_context.get('current_course_selection')
        
        if not course_selected:
            # Fall back to user's main course selection
            user_data = await self.data_manager.get_user_data(user_id)
            course_selected = user_data.get('course_selected')
        
        if not course_selected:
            await update.message.reply_text(
                "❌ ابتدا یک دوره انتخاب کنید!\n\n"
                "برای شروع /start را بزنید."
            )
            return
        
        # CHECK RECEIPT SUBMISSION LIMITS
        receipt_status = await self.check_receipt_submission_limits(user_id, course_selected)
        if not receipt_status or not receipt_status.get('allowed', False):
            error_message = receipt_status.get('message', "❌ خطا در بررسی محدودیت ارسال فیش") if receipt_status else "❌ خطا در بررسی محدودیت ارسال فیش"
            await update.message.reply_text(error_message)
            return
        
        # Validate photo size and format
        photo = update.message.photo[-1]  # Get highest resolution
        
        # Check file size (Telegram API limit)
        if photo.file_size and photo.file_size > 20 * 1024 * 1024:  # 20MB
            await update.message.reply_text(
                "❌ حجم فایل بیش از حد مجاز است!\n"
                "لطفاً تصویری با حجم کمتر از 20 مگابایت ارسال کنید."
            )
            return

        try:
            # Get course details and pricing info from pending payment
            pending_info = self.payment_pending.get(user_id, {})
            
            # Get course details with safe lookup
            course_details = Config.COURSE_DETAILS.get(course_selected, {})
            if not course_details or not isinstance(course_details, dict):
                error_logger.error(f"Missing or invalid course details for {course_selected}")
                course_title = f"دوره: {course_selected}"
            else:
                course_title = course_details.get('title', f"دوره: {course_selected}")
            
            # Use pending payment info if available, otherwise fall back to config
            if pending_info:
                price = pending_info.get('price', Config.PRICES.get(course_selected, 0))
                original_price = pending_info.get('original_price', price)
                coupon_info = pending_info.get('coupon_info')
            else:
                price = Config.PRICES.get(course_selected, 0)
                original_price = price
                coupon_info = None
            
            # Note: Minimum dimension check removed for payment receipts to allow any size receipt images
            
            # Create payment record
            payment_id = f"{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Log payment receipt submission
            log_payment_action(user_id, "submitted payment receipt", price, course_selected)
            
            # Save payment record with coupon info if applicable
            payment_data = {
                'course_type': course_selected,
                'price': price,
                'original_price': original_price,
                'status': 'pending_approval',
                'timestamp': datetime.now().isoformat(),
                'user_id': user_id,
                'payment_id': payment_id,
                'receipt_file_id': photo.file_id
            }
            
            # Add coupon information if used
            if coupon_info:
                payment_data.update({
                    'coupon_code': coupon_info['code'],
                    'discount_percent': coupon_info['discount_percent'],
                    'discount_amount': coupon_info['discount_amount']
                })
            
            await self.data_manager.save_payment_data(user_id, payment_data)
            
            # Clear pending payment info since receipt is now submitted
            if user_id in self.payment_pending:
                del self.payment_pending[user_id]
            
            # UPDATE RECEIPT SUBMISSION COUNT
            await self.increment_receipt_submission_count(user_id, course_selected)
            
            # Update user data (but don't change their main course selection)
            user_updates = {
                'receipt_submitted': True,
                'receipt_file_id': photo.file_id,
                'payment_status': 'pending_approval'
            }
            
            # If this is their first course purchase, set as main course
            user_data = await self.data_manager.get_user_data(user_id)
            if not user_data:
                error_logger.error(f"Failed to get user data for user {user_id}")
                user_data = {}
            
            if not user_data.get('course_selected'):
                user_updates['course_selected'] = course_selected
            
            await self.data_manager.save_user_data(user_id, user_updates)
            
            # Clear additional course purchase context AND payment receipt state
            if user_id in context.user_data:
                context.user_data[user_id].pop('buying_additional_course', None)
                context.user_data[user_id].pop('current_course_selection', None)
                context.user_data[user_id].pop('awaiting_payment_receipt', None)  # CLEAR PAYMENT STATE
                context.user_data[user_id].pop('payment_course', None)
                
            payment_logger.info(f"Payment receipt processed for user {user_id} - PAYMENT FLOW STATE CLEARED")
            
            # Show submission count to user (with safe calculation)
            current_submission_count = receipt_status.get('submission_count', 0) if receipt_status else 0
            remaining_attempts = 3 - current_submission_count - 1
            submission_info = f"\n\n📊 تعداد ارسال فیش: {current_submission_count + 1}/3"
            if remaining_attempts > 0:
                submission_info += f"\n🔄 تعداد باقی‌مانده: {remaining_attempts}"
            else:
                submission_info += f"\n⚠️ این آخرین فرصت ارسال فیش برای این دوره بود"
            
            await update.message.reply_text(
                f"✅ فیش واریز برای دوره **{course_title}** با موفقیت دریافت شد!\n\n"
                f"⏳ در حال بررسی توسط ادمین...\n"
                f"📱 از طریق همین بات از وضعیت پرداخت مطلع خواهید شد.\n\n"
                f"⏱️ زمان تقریبی بررسی: تا ۲۴ ساعت{submission_info}"
            )
            
            # Notify admins with TIMEOUT PROTECTION
            await self.notify_admins_about_payment(update, context, photo, course_title, price, user_id)
                
        except Exception as e:
            payment_logger.error(f"Error processing payment receipt for user {user_id}: {e}", exc_info=True)
            # Use error handler for better error reporting
            await admin_error_handler.handle_admin_error(
                update, context, e, "process_new_course_payment", user_id
            )

    async def check_receipt_submission_limits(self, user_id: int, course_code: str) -> dict:
        """Check if user can submit more receipt attempts for a course"""
        try:
            user_data = await self.data_manager.get_user_data(user_id)
            if not user_data:
                user_data = {}
                
            receipt_attempts = user_data.get('receipt_attempts')
            if receipt_attempts is None:
                receipt_attempts = {}
                
            course_attempts = receipt_attempts.get(course_code, 0)
            
            # Check if admin has allowed additional attempts
            admin_overrides = user_data.get('admin_receipt_overrides', {})
            admin_allowed = admin_overrides.get(course_code, 0)
            
            max_attempts = 3 + admin_allowed
            
            if course_attempts >= max_attempts:
                if admin_allowed > 0:
                    message = f"""❌ شما حداکثر {max_attempts} فیش برای این دوره ارسال کرده‌اید!

📊 ارسال شده: {course_attempts}/{max_attempts}
🔧 تعداد اضافی از ادمین: {admin_allowed}

💡 برای ارسال فیش بیشتر با پشتیبانی @DrBohloul تماس بگیرید."""
                else:
                    message = f"""❌ شما حداکثر 3 فیش برای این دوره ارسال کرده‌اید!

📊 ارسال شده: {course_attempts}/3

💡 برای ارسال فیش بیشتر با پشتیبانی @DrBohloul تماس بگیرید.
📞 ادمین‌ها می‌توانند فرصت اضافی به شما بدهند."""
                
                return {
                    'allowed': False,
                    'message': message,
                    'submission_count': course_attempts,
                    'max_attempts': max_attempts
                }
            
            return {
                'allowed': True,
                'submission_count': course_attempts,
                'max_attempts': max_attempts
            }
            
        except Exception as e:
            payment_logger.error(f"Error checking receipt limits for user {user_id}, course {course_code}: {e}", exc_info=True)
            # Allow submission if there's an error (fail safe)
            return {
                'allowed': True,
                'submission_count': 0,
                'max_attempts': 3
            }

    async def increment_receipt_submission_count(self, user_id: int, course_code: str):
        """Increment the receipt submission count for a user/course"""
        try:
            user_data = await self.data_manager.get_user_data(user_id)
            if not user_data:
                error_logger.error(f"Failed to get user data for user {user_id} in increment_receipt_submission_count")
                user_data = {}
            
            receipt_attempts = user_data.get('receipt_attempts', {})
            if not isinstance(receipt_attempts, dict):
                receipt_attempts = {}
            
            receipt_attempts[course_code] = receipt_attempts.get(course_code, 0) + 1
            
            await self.data_manager.save_user_data(user_id, {'receipt_attempts': receipt_attempts})
            
            payment_logger.info(f"User {user_id} receipt attempt #{receipt_attempts[course_code]} for course {course_code}")
            
        except Exception as e:
            error_logger.error(f"Error incrementing receipt count for user {user_id}, course {course_code}: {e}", exc_info=True)

    async def notify_admins_about_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                        photo, course_title: str, price: int, user_id: int):
        """Notify admins about payment with timeout protection"""
        admin_ids = Config.get_admin_ids()
        if not admin_ids:
            error_logger.warning("No admin IDs found for payment notification")
            return
        
        # Get receipt attempt info
        user_data = await self.data_manager.get_user_data(user_id)
        receipt_attempts = user_data.get('receipt_attempts', {})
        course_code = user_data.get('course_selected', 'unknown')
        attempt_count = receipt_attempts.get(course_code, 1)
        
        admin_message = (f"🔔 درخواست تایید پرداخت جدید\n\n"
                       f"👤 کاربر: {update.effective_user.first_name}\n"
                       f"📱 نام کاربری: @{update.effective_user.username or 'ندارد'}\n"
                       f"🆔 User ID: {user_id}\n"
                       f"📚 دوره: {course_title}\n"
                       f"💰 مبلغ: {price:,} تومان\n"
                       f"📊 تلاش ارسال فیش: {attempt_count}/3\n\n"
                       f"⬇️ فیش واریز ارسالی:")
        
        # Create enhanced approval buttons
        keyboard = [
            [
                InlineKeyboardButton("✅ تایید", callback_data=f'approve_payment_{user_id}'),
                InlineKeyboardButton("❌ رد", callback_data=f'reject_payment_{user_id}')
            ],
            [InlineKeyboardButton("👤 مشاهده پروفایل", callback_data=f'view_user_{user_id}')],
            [InlineKeyboardButton("🔄 اجازه فیش اضافی", callback_data=f'allow_extra_receipt_{user_id}')],
            [InlineKeyboardButton("🎛️ مدیریت پرداخت‌ها", callback_data='admin_pending_payments')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Send to admins with timeout protection
        sent_count = 0
        failed_admins = []
        
        for admin_id in admin_ids:
            try:
                # Use asyncio.wait_for to add timeout protection
                await asyncio.wait_for(
                    context.bot.send_photo(
                        chat_id=admin_id,
                        photo=photo.file_id,
                        caption=admin_message,
                        reply_markup=reply_markup
                    ),
                    timeout=10.0  # 10 second timeout per admin
                )
                sent_count += 1
                
            except asyncio.TimeoutError:
                error_logger.warning(f"Timeout sending payment notification to admin {admin_id}")
                failed_admins.append(admin_id)
                
            except Exception as e:
                error_logger.warning(f"Failed to send payment notification to admin {admin_id}: {e}")
                failed_admins.append(admin_id)
        
        admin_logger.info(f"Payment notification sent to {sent_count}/{len(admin_ids)} admins")
        
        if failed_admins:
            error_logger.warning(f"Failed to notify admins: {failed_admins}")
            # Try to send a fallback text message to failed admins
            for admin_id in failed_admins:
                try:
                    await asyncio.wait_for(
                        context.bot.send_message(
                            chat_id=admin_id,
                            text=f"⚠️ فیش پرداخت جدید دریافت شد ولی ارسال عکس ناموفق بود.\n\n{admin_message}",
                            reply_markup=reply_markup
                        ),
                        timeout=5.0
                    )
                except Exception as e:
                    error_logger.error(f"Failed to send fallback notification to admin {admin_id}: {e}", exc_info=True)

    async def handle_questionnaire_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle photo submission for questionnaire questions"""
        user_id = update.effective_user.id
        
        try:
            # Get the photo
            photo = update.message.photo[-1]  # Get highest resolution
            
            # Basic validation
            if photo.file_size and photo.file_size > 20 * 1024 * 1024:  # 20MB
                await update.message.reply_text(
                    "❌ تصویر خیلی بزرگ است!\n\n"
                    "حداکثر سایز مجاز: ۲۰ مگابایت\n"
                    "لطفاً تصویر کوچک‌تری ارسال کنید."
                )
                return
            
            # Check minimum dimensions
            if photo.width < 200 or photo.height < 200:
                await update.message.reply_text(
                    "❌ تصویر خیلی کوچک است!\n\n"
                    "حداقل ابعاد مورد نیاز: ۲۰۰×۲۰۰ پیکسل\n"
                    "لطفاً تصویر با کیفیت بهتر ارسال کنید."
                )
                return
            
            # Process the photo through questionnaire manager
            result = await self.questionnaire_manager.process_photo_answer(user_id, photo.file_id, context.bot)
            
            if result["status"] == "error":
                await update.message.reply_text(result["message"])
                return
            elif result["status"] == "need_more_photos":
                await update.message.reply_text(result["message"])
                return
            elif result["status"] == "can_continue_or_add_more":
                # User can continue or add more photos
                from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                keyboard = [
                    [InlineKeyboardButton("➡️ ادامه به سوال بعد", callback_data='continue_photo_question')],
                    [InlineKeyboardButton("📷 ارسال عکس بیشتر", callback_data='add_more_photos')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(result["message"], reply_markup=reply_markup)
                return
            elif result["status"] == "next_question":
                # Send confirmation and next question
                await update.message.reply_text("✅ عکس دریافت شد!")
                await self.questionnaire_manager.send_question(
                    context.bot,
                    user_id,
                    result["question"]
                )
                return
            elif result["status"] == "completed":
                # Questionnaire completed
                await self.handle_questionnaire_completion(update, context)
                return
            else:
                await update.message.reply_text("❌ خطا در پردازش عکس!")
                
        except Exception as e:
            error_logger.error(f"Error processing questionnaire photo for user {user_id}: {e}", exc_info=True)
            await update.message.reply_text(
                "❌ خطا در پردازش تصویر!\n\n"
                "لطفاً دوباره تلاش کنید یا با پشتیبانی تماس بگیرید."
            )

    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle document uploads (PDF files for questionnaire, CSV for admin, plan uploads)"""
        user_id = update.effective_user.id
        
        # Check if admin is uploading a plan
        if await self.admin_panel.admin_manager.is_admin(user_id):
            if await self.handle_plan_upload_document(update, context):
                return  # Plan upload handled
        
        # Check if it's a CSV file and user is admin
        if update.message.document and update.message.document.file_name:
            filename = update.message.document.file_name.lower()
            if filename.endswith('.csv') and await self.admin_panel.admin_manager.is_admin(user_id):
                await self.handle_csv_import(update, context)
                return
        
        # Check if user is in questionnaire mode
        current_question = await self.questionnaire_manager.get_current_question(user_id)
        
        if current_question:
            question_type = current_question.get("type")
            
            # UNIFIED INPUT TYPE VALIDATION for questionnaire documents
            from input_validator import input_validator
            
            if question_type == "photo":
                # User sent document but photo is expected
                is_valid = await input_validator.validate_and_reject_wrong_input_type(
                    update, question_type, f"پرسشنامه - سوال {current_question.get('step', '?')}", is_admin=False
                )
                return  # Error message already sent
                
            elif question_type == "text":
                # User sent document but text is expected
                is_valid = await input_validator.validate_and_reject_wrong_input_type(
                    update, question_type, f"پرسشنامه - سوال {current_question.get('step', '?')}", is_admin=False
                )
                return  # Error message already sent
                
            elif question_type == "number":
                # User sent document but number is expected
                is_valid = await input_validator.validate_and_reject_wrong_input_type(
                    update, question_type, f"پرسشنامه - سوال {current_question.get('step', '?')}", is_admin=False
                )
                return  # Error message already sent
            elif question_type == "text_or_document":
                # Handle PDF documents for training program questions
                if update.message.document:
                    document = update.message.document
                    filename = document.file_name or ""
                    
                    # Check if it's a PDF file
                    if filename.lower().endswith('.pdf'):
                        try:
                            # Process the document
                            result = await self.questionnaire_manager.process_document_answer(
                                user_id, 
                                document.file_id, 
                                filename
                            )
                            
                            if result["status"] == "next_question":
                                # Send next question
                                await self.questionnaire_manager.send_question(
                                    context.bot, 
                                    user_id, 
                                    result["question"]
                                )
                            elif result["status"] == "completed":
                                await self.handle_questionnaire_completion(update, context)
                            else:
                                await update.message.reply_text(result.get("message", "خطا در پردازش فایل"))
                                
                        except Exception as e:
                            error_logger.error(f"Error processing document for user {user_id}: {e}", exc_info=True)
                            await update.message.reply_text(
                                "❌ خطا در پردازش فایل!\n\n"
                                "می‌توانید متن پاسخ خود را بنویسید یا فایل PDF دیگری ارسال کنید."
                            )
                        return
                    else:
                        await update.message.reply_text(
                            "❌ فقط فایل‌های PDF قابل قبول هستند!\n\n"
                            "💡 می‌توانید:\n"
                            "📝 متن پاسخ خود را بنویسید\n"
                            "📄 یا فایل PDF ارسال کنید"
                        )
                        return
                        
        # Handle other document types
        # Check if user is in questionnaire mode for text_or_document questions
        current_question = await self.questionnaire_manager.get_current_question(user_id)
        if current_question and current_question.get("type") == "text_or_document":
            await update.message.reply_text(
                "❌ فقط فایل‌های PDF قابل قبول هستند!\n\n"
                "💡 می‌توانید:\n"
                "📝 متن پاسخ خود را بنویسید\n"
                "📄 یا فایل PDF ارسال کنید"
            )
        # Handle other document types that are not in questionnaire mode
        # For documents sent outside of questionnaire or admin context - remain silent
        # (This matches the requirement for complete silence when no input expected)

    async def handle_unsupported_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle non-document file uploads (video, audio, stickers, etc.)"""
        user_id = update.effective_user.id
        
        # ENHANCED QUESTIONNAIRE DETECTION - Same as photo handler
        user_data = await self.data_manager.get_user_data(user_id)
        payment_status = user_data.get('payment_status')
        user_context = context.user_data.get(user_id, {})
        
        user_logger.debug(f"UNSUPPORTED FILE DEBUG for User {user_id} | Payment: {payment_status} | Active: {user_context.get('questionnaire_active', False)}")
        
        # Check if user is in questionnaire mode using enhanced detection
        in_questionnaire_mode = False
        
        # Method 1: Check if questionnaire_active flag is set
        if user_context.get('questionnaire_active', False):
            in_questionnaire_mode = True
            user_logger.debug(f"QUESTIONNAIRE MODE for User {user_id} detected via active flag")
        
        # Method 2: Check if user has approved payment and unfinished questionnaire
        elif payment_status == 'approved':
            # Check if user has questionnaire progress 
            questionnaire_progress = await self.questionnaire_manager.load_user_progress(user_id)
            if (questionnaire_progress and 
                not questionnaire_progress.get("completed", False) and 
                questionnaire_progress.get("current_step", 0) > 0):
                in_questionnaire_mode = True
                user_logger.debug(f"QUESTIONNAIRE MODE for User {user_id} detected via payment+progress")
                
                # AUTO-SET questionnaire_active flag for consistency
                if user_id not in context.user_data:
                    context.user_data[user_id] = {}
                context.user_data[user_id]['questionnaire_active'] = True
                user_logger.debug(f"AUTO-SET questionnaire_active flag for user {user_id}")
        
        if in_questionnaire_mode:
            current_question = await self.questionnaire_manager.get_current_question(user_id)
            
            if current_question:
                question_type = current_question.get("type")
                
                user_logger.debug(f"UNSUPPORTED FILE - User {user_id} sent unsupported file for {question_type} question - showing error")
                
                # UNIFIED INPUT TYPE VALIDATION for unsupported files
                from input_validator import input_validator
                
                is_valid = await input_validator.validate_and_reject_wrong_input_type(
                    update, question_type, f"پرسشنامه - سوال {current_question.get('step', '?')}", is_admin=False
                )
                return  # Error message already sent by validator
        
        # For unsupported files sent outside questionnaire mode - remain silent
        # (This matches the requirement for complete silence when no input expected)

    async def _safe_edit_message_or_alert(self, query, message: str) -> None:
        """
        Safely edit message text or show alert popup if editing fails.
        This handles cases where the original message is a photo without text.
        """
        try:
            await query.edit_message_text(message)
        except Exception as e:
            # If editing fails (e.g., message is a photo), show popup alert instead
            if "no text in the message" in str(e).lower():
                await query.answer(message, show_alert=True)
            else:
                # For other errors, still try to show alert
                await query.answer("❌ خطای غیرمنتظره رخ داد", show_alert=True)

    async def handle_payment_approval(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle admin payment approval/rejection and user profile viewing"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        if await self.check_cooldown(user_id):
            return
        admin_name = update.effective_user.first_name or "Unknown Admin"
        
        # Log admin action attempt
        log_admin_action(user_id, "attempted payment approval", f"Data: {query.data}")
        
        # Check if user is admin
        is_admin = await self.admin_panel.admin_manager.is_admin(user_id)
        
        if not is_admin:
            admin_logger.warning(f"Non-admin user {user_id} ({admin_name}) attempted payment approval")
            log_admin_action(user_id, "attempted payment approval - BLOCKED (not an admin)")
            await query.answer("❌ شما دسترسی ادمین ندارید.", show_alert=True)
            return
        
        admin_logger.info(f"Admin access confirmed for user {user_id} ({admin_name})")
        
        # Handle user profile viewing
        if query.data.startswith('view_user_'):
            target_user_id = int(query.data.replace('view_user_', ''))
            log_admin_action(user_id, f"viewing profile of user {target_user_id}")
            await self.show_user_profile(query, target_user_id)
            return
        
        # Extract user_id and action from callback data
        if query.data.startswith('approve_payment_'):
            target_user_id = int(query.data.replace('approve_payment_', ''))
            action = 'approve'
        elif query.data.startswith('reject_payment_'):
            target_user_id = int(query.data.replace('reject_payment_', ''))
            action = 'reject'
        else:
            await self._safe_edit_message_or_alert(query, "❌ داده نامعتبر.")
            return

        # Race condition protection - check if payment is already being processed
        payment_lock_key = f"{action}_{target_user_id}"
        if payment_lock_key in self.processing_payments:
            admin_logger.warning(f"RACE CONDITION BLOCKED - Payment {payment_lock_key} already being processed by another admin")
            await query.answer("⚠️ این پرداخت در حال پردازش توسط ادمین دیگری است", show_alert=True)
            return
        
        # Set lock to prevent duplicate processing
        self.processing_payments.add(payment_lock_key)
        admin_logger.info(f"Payment processing lock acquired: {payment_lock_key}")
        
        # Get user data
        user_data = await self.data_manager.get_user_data(target_user_id)
        
        if not user_data.get('receipt_submitted'):
            # Release lock before returning error
            if payment_lock_key in self.processing_payments:
                self.processing_payments.remove(payment_lock_key)
                admin_logger.info(f"Payment processing lock released due to missing receipt: {payment_lock_key}")
            await self._safe_edit_message_or_alert(query, "❌ هیچ فیش واریزی برای این کاربر یافت نشد.")
            return
        
        if action == 'approve':
            # Find and approve the most recent payment for this user
            payments_data = await self.data_manager.load_data('payments')
            user_payment = None
            payment_id = None
            
            # Find the most recent pending payment for this user
            for pid, payment_data in payments_data.items():
                if (payment_data.get('user_id') == target_user_id and 
                    payment_data.get('status') == 'pending_approval'):
                    if user_payment is None or payment_data.get('timestamp', '') > user_payment.get('timestamp', ''):
                        user_payment = payment_data
                        payment_id = pid
            
            if not user_payment:
                # Release lock before returning error
                if payment_lock_key in self.processing_payments:
                    self.processing_payments.remove(payment_lock_key)
                    admin_logger.info(f"Payment processing lock released due to no pending payment found: {payment_lock_key}")
                await self._safe_edit_message_or_alert(query, "❌ هیچ پرداخت معلقی برای این کاربر یافت نشد.")
                return
            
            course_type = user_payment.get('course_type')
            if not course_type:
                # Release lock before returning error
                if payment_lock_key in self.processing_payments:
                    self.processing_payments.remove(payment_lock_key)
                    admin_logger.info(f"Payment processing lock released due to missing course type: {payment_lock_key}")
                await self._safe_edit_message_or_alert(query, "❌ نوع دوره برای این کاربر مشخص نیست.")
                return
            
            # Log the approval action
            course_title = Config.COURSE_DETAILS.get(course_type, {}).get('title', 'نامشخص')
            price = user_payment.get('price', 0)
            
            log_payment_action(target_user_id, "PAYMENT APPROVED", price, course_type, admin_id=user_id)
            
            # Update payment status in payments table
            user_payment['status'] = 'approved'
            user_payment['approved_by'] = update.effective_user.id
            user_payment['approved_at'] = datetime.now().isoformat()
            payments_data[payment_id] = user_payment
            await self.data_manager.save_data('payments', payments_data)
            
            payment_logger.info(f"Payment data updated for user {target_user_id}")
            
            # Update user data
            await self.data_manager.save_user_data(target_user_id, {
                'payment_verified': True,
                'awaiting_form': True,
                'course': course_type,
                'payment_status': 'approved'
            })
            
            user_logger.info(f"User data updated for user {target_user_id} after payment approval")
            
            # Update statistics
            await self.data_manager.update_statistics('total_payments')
            if course_type:
                await self.data_manager.update_statistics(f'course_{course_type}')
            
            # Remove from pending payments
            if target_user_id in self.payment_pending:
                del self.payment_pending[target_user_id]

            # Check questionnaire status before sending questionnaire 
            log_admin_action(user_id, "Checking questionnaire status before notification", f"User: {target_user_id}")
            quest_status = await self.get_user_questionnaire_requirement_status(target_user_id)
            
            # Notify user and start questionnaire automatically
            log_admin_action(user_id, "Starting automatic questionnaire notification", f"User: {target_user_id}")
            
            notification_sent = False
            notification_error = None
            
            try:
                # Special handling for nutrition plan
                if course_type == 'nutrition_plan':
                    message = """✅ پرداخت شما تایید شد!

🥗 برای دریافت برنامه غذایی شخصی‌سازی شده، لطفاً روی لینک زیر کلیک کنید:

👈 https://fitava.ir/coach/drbohloul/question

❌ توجه داشته باشید همه فیلدهای فرم را پر کنید و برای قسمت اعداد، کیورد اعداد انگلیسی را وارد کنید

آیا متوجه شدید که باید روی لینک کلیک کنید و فرم را پر کنید؟"""
                    
                    keyboard = [
                        [InlineKeyboardButton("✅ بله، متوجه شدم", callback_data='nutrition_form_understood')],
                        [InlineKeyboardButton("❓ سوال دارم", callback_data='nutrition_form_question')]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await context.bot.send_message(
                        chat_id=target_user_id,
                        text=message,
                        reply_markup=reply_markup
                    )
                    
                    notification_sent = True
                    log_user_action(target_user_id, user_data.get('name', 'Unknown'), "Received nutrition plan form notification")
                    
                elif quest_status['questionnaire_completed']:
                    # User already completed questionnaire - show menu with edit option
                    message = """✅ پرداخت شما تایید شد!

🎉 شما قبلاً پرسشنامه را تکمیل کرده‌اید و می‌توانید از برنامه‌های تمرینی خود استفاده کنید.

📝 اگر می‌خواهید پرسشنامه خود را ویرایش کنید، از گزینه زیر استفاده کنید:"""
                    
                    keyboard = [
                        [InlineKeyboardButton("✏️ ویرایش پرسشنامه", callback_data='edit_questionnaire')],
                        [InlineKeyboardButton("📋 مشاهده وضعیت", callback_data='my_status')],
                        [InlineKeyboardButton("🏠 بازگشت به منوی اصلی", callback_data='back_to_user_menu')]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await context.bot.send_message(
                        chat_id=target_user_id,
                        text=message,
                        reply_markup=reply_markup
                    )
                    
                    notification_sent = True
                    log_user_action(target_user_id, user_data.get('name', 'Unknown'), "Received completed questionnaire menu")
                    
                elif quest_status['questionnaire_in_progress']:
                    # User has questionnaire in progress - give option to continue or restart
                    current_step = quest_status['questionnaire_status'].get('current_step', 1)
                    message = f"""✅ پرداخت شما تایید شد!

📝 شما پرسشنامه را شروع کرده‌اید و در سوال {current_step} هستید.

می‌خواهید ادامه دهید یا از نو شروع کنید؟"""
                    
                    keyboard = [
                        [InlineKeyboardButton("➡️ ادامه پرسشنامه", callback_data='continue_questionnaire')],
                        [InlineKeyboardButton("🔄 شروع مجدد پرسشنامه", callback_data='restart_questionnaire')],
                        [InlineKeyboardButton("🏠 بازگشت به منوی اصلی", callback_data='back_to_user_menu')]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await context.bot.send_message(
                        chat_id=target_user_id,
                        text=message,
                        reply_markup=reply_markup
                    )
                    
                    notification_sent = True
                    log_user_action(target_user_id, user_data.get('name', 'Unknown'), "Received in-progress questionnaire menu")
                    
                else:
                    # User needs to start questionnaire - existing logic
                    # Get first question to start questionnaire immediately
                    user_logger.debug(f"Starting questionnaire for user {target_user_id}")
                    await self.questionnaire_manager.start_questionnaire(target_user_id)
                    
                    user_logger.debug(f"Getting first question for user {target_user_id}")
                    first_question = await self.questionnaire_manager.get_current_question(target_user_id)
                    
                    if first_question:
                        # Send approval message with first question directly
                        progress_text = "سوال 1 از 21"
                        message = f"✅ پرداخت شما تایید شد!\n\n📝 حالا برای شخصی‌سازی برنامه تمرینتان، چند سوال کوتاه از شما می‌پرسیم:\n\n{progress_text}\n\n{first_question['text']}"
                        
                        keyboard = []
                        if first_question.get('type') == 'choice':
                            choices = first_question.get('choices', [])
                            for choice in choices:
                                keyboard.append([InlineKeyboardButton(choice, callback_data=f'q_answer_{choice}')])
                        keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data='back_to_user_menu')])
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        
                        log_admin_action(user_id, "Sending questionnaire with first question", f"User: {target_user_id}")
                        
                        await context.bot.send_message(
                            chat_id=target_user_id,
                            text=message,
                            reply_markup=reply_markup
                        )
                        
                        notification_sent = True
                        log_user_action(target_user_id, user_data.get('name', 'Unknown'), "Received questionnaire message")
                        
                    else:
                        # Fallback to button if question not found
                        error_logger.warning(f"First question not found for user {target_user_id}, using fallback button")
                        
                        keyboard = [[InlineKeyboardButton("🎯 شروع پرسشنامه", callback_data='start_questionnaire')]]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        
                        await context.bot.send_message(
                        chat_id=target_user_id,
                        text="✅ پرداخت شما تایید شد!\n\nحالا برای شخصی‌سازی برنامه تمرینتان، چند سوال کوتاه از شما می‌پرسیم:",
                        reply_markup=reply_markup
                    )
                    
                    notification_sent = True
                    log_user_action(target_user_id, user_data.get('name', 'Unknown'), "Received fallback questionnaire message")
                
            except Exception as e:
                notification_error = str(e)
                error_logger.error(f"FAILED to send questionnaire message to user {target_user_id}: {e}", exc_info=True)
                
                # Try to at least notify them of approval
                try:
                    log_admin_action(user_id, "Attempting fallback notification", f"User: {target_user_id}")
                    
                    await context.bot.send_message(
                        chat_id=target_user_id,
                        text="✅ پرداخت شما تایید شد! برای ادامه از دستور /start استفاده کنید."
                    )
                    
                    notification_sent = True
                    log_user_action(target_user_id, user_data.get('name', 'Unknown'), "Received fallback approval notification")
                    
                except Exception as e2:
                    notification_error = f"{e} | Fallback also failed: {e2}"
                    error_logger.error(f"EVEN FALLBACK FAILED for user {target_user_id}: {e2}", exc_info=True)
            
            # Final notification status log
            if notification_sent:
                log_admin_action(user_id, "PAYMENT APPROVAL COMPLETE", f"User {target_user_id} notified successfully")
            else:
                log_admin_action(user_id, "PAYMENT APPROVAL INCOMPLETE", f"User {target_user_id} NOT notified - Error: {notification_error}")
            
            # Update admin message
            updated_message = f"""✅ پرداخت تایید شد:
👤 کاربر: {user_data.get('name', 'ناشناس')}
🆔 User ID: {target_user_id}
📚 دوره: {course_title}
💰 مبلغ: {Config.format_price(price)}
⏰ تایید شده توسط: {admin_name}
📧 اطلاع‌رسانی: {'✅ موفق' if notification_sent else '❌ ناموفق'}"""
            
            # Edit caption for photo messages, text for text messages
            try:
                await query.edit_message_caption(caption=updated_message, reply_markup=None)
            except Exception:
                # Fallback to edit_message_text if it's not a photo message
                await query.edit_message_text(updated_message, reply_markup=None)
            
            # Notify all admins about the approval
            await self.notify_all_admins_payment_update(
                bot=context.bot,
                payment_user_id=target_user_id,
                action='approve',
                acting_admin_name=update.effective_user.first_name or "ادمین",
                course_title=course_title,
                price=price,
                user_name=user_data.get('name', 'ناشناس')
            )
            
            # Release payment processing lock after successful approval
            if payment_lock_key in self.processing_payments:
                self.processing_payments.remove(payment_lock_key)
                admin_logger.info(f"Payment processing lock released after approval: {payment_lock_key}")
            
        elif action == 'reject':
            # Find and reject the most recent payment for this user
            payments_data = await self.data_manager.load_data('payments')
            user_payment = None
            payment_id = None
            
            # Find the most recent pending payment for this user
            for pid, payment_data in payments_data.items():
                if (payment_data.get('user_id') == target_user_id and 
                    payment_data.get('status') == 'pending_approval'):
                    if user_payment is None or payment_data.get('timestamp', '') > user_payment.get('timestamp', ''):
                        user_payment = payment_data
                        payment_id = pid
            
            if not user_payment:
                # Release lock before returning error
                if payment_lock_key in self.processing_payments:
                    self.processing_payments.remove(payment_lock_key)
                    admin_logger.info(f"Payment processing lock released due to no pending payment found in rejection: {payment_lock_key}")
                await self._safe_edit_message_or_alert(query, "❌ هیچ پرداخت معلقی برای این کاربر یافت نشد.")
                return
            
            course_type = user_payment.get('course_type', user_data.get('course_selected', 'Unknown'))
            course_title = Config.COURSE_DETAILS.get(course_type, {}).get('title', 'نامشخص')
            
            # Log the rejection action
            log_payment_action(target_user_id, "PAYMENT REJECTED", admin_id=user_id)
            
            # Update payment status in payments table
            user_payment['status'] = 'rejected'
            user_payment['rejected_by'] = update.effective_user.id
            user_payment['rejected_at'] = datetime.now().isoformat()
            payments_data[payment_id] = user_payment
            await self.data_manager.save_data('payments', payments_data)
            
            # Also update user data for backward compatibility
            await self.data_manager.save_user_data(target_user_id, {
                'payment_status': 'rejected'
            })
            
            payment_logger.info(f"Payment rejected for user {target_user_id}")
            
            # Remove from pending payments
            if target_user_id in self.payment_pending:
                del self.payment_pending[target_user_id]
            
            # Notify user
            notification_sent = False
            notification_error = None
            
            try:
                log_admin_action(user_id, "Sending rejection notification", f"User: {target_user_id}")
                
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text="❌ متاسفانه پرداخت شما تایید نشد. لطفا با پشتیبانی تماس بگیرید یا فیش صحیح را ارسال کنید."
                )
                
                notification_sent = True
                log_user_action(target_user_id, user_data.get('name', 'Unknown'), "Received rejection notification")
                
            except Exception as e:
                notification_error = str(e)
                error_logger.error(f"FAILED to notify user {target_user_id} about rejection: {e}", exc_info=True)
            
            # Final notification status log
            if notification_sent:
                log_admin_action(user_id, "PAYMENT REJECTION COMPLETE", f"User {target_user_id} notified successfully")
            else:
                log_admin_action(user_id, "PAYMENT REJECTION INCOMPLETE", f"User {target_user_id} NOT notified - Error: {notification_error}")
            
            # Update admin message
            updated_message = f"""❌ پرداخت رد شد:
👤 کاربر: {user_data.get('name', 'ناشناس')}
🆔 User ID: {target_user_id}
📚 دوره: {course_title}
⏰ رد شده توسط: {admin_name}
📧 اطلاع‌رسانی: {'✅ موفق' if notification_sent else '❌ ناموفق'}"""
            
            # Edit caption for photo messages, text for text messages
            try:
                await query.edit_message_caption(caption=updated_message, reply_markup=None)
            except Exception:
                # Fallback to edit_message_text if it's not a photo message
                await query.edit_message_text(updated_message, reply_markup=None)
            
            # Notify all admins about the rejection
            await self.notify_all_admins_payment_update(
                bot=context.bot,
                payment_user_id=target_user_id,
                action='reject',
                acting_admin_name=update.effective_user.first_name or "ادمین",
                user_name=user_data.get('name', 'ناشناس')
            )

            # Release payment processing lock after successful rejection
            if payment_lock_key in self.processing_payments:
                self.processing_payments.remove(payment_lock_key)
                admin_logger.info(f"Payment processing lock released after rejection: {payment_lock_key}")

        elif query.data.startswith('allow_extra_receipt_'):
            # Handle admin allowing extra receipt submission
            target_user_id = int(query.data.replace('allow_extra_receipt_', ''))
            await self.handle_allow_extra_receipt(query, context, target_user_id, user_id)
            return

    async def handle_allow_extra_receipt(self, query, context: ContextTypes.DEFAULT_TYPE, 
                                       target_user_id: int, admin_id: int):
        """Allow a user to submit additional receipt attempts"""
        try:
            admin_name = query.from_user.first_name or "ادمین"
            
            # Get user data
            user_data = await self.data_manager.get_user_data(target_user_id)
            if not user_data:
                await query.edit_message_text(f"❌ کاربر با ID {target_user_id} یافت نشد.")
                return
            
            # Get user's course
            course_code = user_data.get('course_selected')
            if not course_code:
                await query.edit_message_text("❌ دوره کاربر مشخص نیست.")
                return
            
            # Get current receipt attempts
            receipt_attempts = user_data.get('receipt_attempts', {})
            current_attempts = receipt_attempts.get(course_code, 0)
            
            # Get current admin overrides
            admin_overrides = user_data.get('admin_receipt_overrides', {})
            current_overrides = admin_overrides.get(course_code, 0)
            
            # Show selection buttons for number of extra attempts
            keyboard = [
                [
                    InlineKeyboardButton("1️⃣ +1 فرصت", callback_data=f'grant_receipt_1_{target_user_id}'),
                    InlineKeyboardButton("2️⃣ +2 فرصت", callback_data=f'grant_receipt_2_{target_user_id}')
                ],
                [
                    InlineKeyboardButton("3️⃣ +3 فرصت", callback_data=f'grant_receipt_3_{target_user_id}'),
                    InlineKeyboardButton("♾️ نامحدود", callback_data=f'grant_receipt_unlimited_{target_user_id}')
                ],
                [InlineKeyboardButton("🔙 بازگشت", callback_data=f'view_user_{target_user_id}')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            course_title = Config.COURSE_DETAILS.get(course_code, {}).get('title', course_code)
            user_name = user_data.get('name', 'ناشناس')
            
            message = f"""🔄 اجازه ارسال فیش اضافی

👤 کاربر: {user_name}
🆔 User ID: {target_user_id}
📚 دوره: {course_title}

📊 وضعیت فعلی:
• تعداد ارسال شده: {current_attempts}
• فرصت‌های اضافی قبلی: {current_overrides}
• مجموع مجاز: {3 + current_overrides}

💡 چند فرصت اضافی می‌خواهید به این کاربر بدهید؟"""
            
            await query.edit_message_text(message, reply_markup=reply_markup)
            
            # Log admin action
            log_admin_action(admin_id, f"requested_extra_receipt_options", f"Target user: {target_user_id}, Course: {course_code}")
            
        except Exception as e:
            error_logger.error(f"Error in handle_allow_extra_receipt: {e}", exc_info=True)
            await admin_error_handler.handle_admin_error(
                query, context, e, "handle_allow_extra_receipt", admin_id
            )

    async def handle_grant_receipt_approval(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle granting extra receipt attempts to users"""
        query = update.callback_query
        await query.answer()
        
        admin_id = update.effective_user.id
        if await self.check_cooldown(admin_id):
            return
        admin_name = update.effective_user.first_name or "ادمین"
        
        # Check admin access
        if not await self.admin_panel.admin_manager.is_admin(admin_id):
            await query.edit_message_text("❌ شما دسترسی ادمین ندارید.")
            return
        
        try:
            # Parse callback data
            callback_parts = query.data.split('_')
            if len(callback_parts) < 4:
                await query.edit_message_text("❌ داده نامعتبر.")
                return
            
            extra_attempts = callback_parts[2]  # grant_receipt_X_userid
            target_user_id = int(callback_parts[3])
            
            # Get user data
            user_data = await self.data_manager.get_user_data(target_user_id)
            if not user_data:
                await query.edit_message_text(f"❌ کاربر با ID {target_user_id} یافت نشد.")
                return
            
            course_code = user_data.get('course_selected')
            if not course_code:
                await query.edit_message_text("❌ دوره کاربر مشخص نیست.")
                return
            
            # Get current overrides
            admin_overrides = user_data.get('admin_receipt_overrides', {})
            
            # Apply the new override
            if extra_attempts == 'unlimited':
                admin_overrides[course_code] = 999  # Effectively unlimited
                attempts_text = "نامحدود"
            else:
                additional = int(extra_attempts)
                admin_overrides[course_code] = admin_overrides.get(course_code, 0) + additional
                attempts_text = f"+{additional}"
            
            # Save the updated overrides
            await self.data_manager.save_user_data(target_user_id, {
                'admin_receipt_overrides': admin_overrides
            })
            
            # Get updated totals
            receipt_attempts = user_data.get('receipt_attempts', {})
            current_attempts = receipt_attempts.get(course_code, 0)
            new_max = 3 + admin_overrides[course_code]
            
            course_title = Config.COURSE_DETAILS.get(course_code, {}).get('title', course_code)
            user_name = user_data.get('name', 'ناشناس')
            
            # Notify user about the extra attempts
            try:
                user_message = f"""🎉 فرصت اضافی برای ارسال فیش!

📚 دوره: {course_title}
🔄 فرصت‌های اضافی: {attempts_text}
📊 مجموع مجاز: {new_max} فیش

💡 حالا می‌توانید فیش جدید ارسال کنید."""
                
                await context.bot.send_message(chat_id=target_user_id, text=user_message)
                user_notified = "✅ موفق"
            except Exception as e:
                error_logger.error(f"Failed to notify user {target_user_id} about extra receipt: {e}", exc_info=True)
                user_notified = "❌ ناموفق"
            
            # Update admin message
            success_message = f"""✅ فرصت اضافی اعطا شد

👤 کاربر: {user_name}
🆔 User ID: {target_user_id}
📚 دوره: {course_title}
🔄 فرصت اضافی: {attempts_text}
📊 جمع فرصت‌ها: {new_max}
👨‍💼 توسط: {admin_name}
📧 اطلاع‌رسانی: {user_notified}"""
            
            keyboard = [
                [InlineKeyboardButton("👤 مشاهده پروفایل", callback_data=f'view_user_{target_user_id}')],
                [InlineKeyboardButton("🔙 بازگشت به منوی ادمین", callback_data='admin_back_main')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(success_message, reply_markup=reply_markup)
            
            # Log admin action
            log_admin_action(admin_id, "granted_extra_receipt", f"Target user: {target_user_id}, Course: {course_code}, Extra attempts: {extra_attempts}, New total: {new_max}")
            
            logger.info(f"Admin {admin_id} granted {attempts_text} extra receipt attempts to user {target_user_id} for course {course_code}")
            
        except Exception as e:
            error_logger.error(f"Error in handle_grant_receipt_approval: {e}", exc_info=True)
            await admin_error_handler.handle_admin_error(
                update, context, e, "handle_grant_receipt_approval", admin_id
            )

    async def show_user_profile(self, query, target_user_id: int) -> None:
        """Show detailed user profile for admin review"""
        try:
            user_data = await self.data_manager.get_user_data(target_user_id)
            
            if not user_data:
                # Handle the case where we can't edit the message directly
                await self.safe_send_or_edit_profile(query, f"❌ کاربر با ID {target_user_id} یافت نشد.")
                return
            
            # Get user info from Telegram
            try:
                chat_member = await self.application.bot.get_chat(target_user_id)
                telegram_name = chat_member.first_name
                username = f"@{chat_member.username}" if chat_member.username else "ندارد"
            except:
                telegram_name = "نامشخص"
                username = "ندارد"
            
            # Build profile message
            profile_text = f"""👤 پروفایل کاربر
            
🆔 شناسه: {target_user_id}
📱 نام تلگرام: {telegram_name}
🔗 نام کاربری: {username}
📚 دوره انتخابی: {self.get_course_name_farsi(user_data.get('course_selected', 'انتخاب نشده'))}
💳 وضعیت پرداخت: {self.get_payment_status_text(user_data.get('payment_status'))}
🧾 وضعیت فیش: {'✅ ارسال شده' if user_data.get('receipt_submitted') else '❌ ارسال نشده'}
📋 وضعیت پرسشنامه: {self.get_questionnaire_status_text(user_data)}
📅 تاریخ ثبت نام: {user_data.get('registration_date', 'نامشخص')}

📊 آمار کاربر:
• تعداد پیام‌ها: {user_data.get('message_count', 0)}
• آخرین فعالیت: {user_data.get('last_activity', 'نامشخص')}
"""
            
            # Add questionnaire responses if available
            if user_data.get('questionnaire_responses'):
                responses = user_data['questionnaire_responses']
                profile_text += f"\n📝 پاسخ‌های پرسشنامه:\n"
                profile_text += f"• نام: {responses.get('full_name', 'ندارد')}\n"
                profile_text += f"• سن: {responses.get('age', 'ندارد')}\n"
                profile_text += f"• قد: {responses.get('height', 'ندارد')} سانتی‌متر\n"
                profile_text += f"• وزن: {responses.get('weight', 'ندارد')} کیلوگرم\n"
                if responses.get('phone'):
                    profile_text += f"• شماره تلفن: {responses['phone']}\n"
            
            # Create action buttons
            keyboard = [
                [
                    InlineKeyboardButton("✅ تایید پرداخت", callback_data=f'approve_payment_{target_user_id}'),
                    InlineKeyboardButton("❌ رد پرداخت", callback_data=f'reject_payment_{target_user_id}')
                ],
                [InlineKeyboardButton("📤 دانلود اسناد کاربر", callback_data=f'export_user_{target_user_id}')],
                [InlineKeyboardButton("🔙 بازگشت", callback_data='admin_pending_payments')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Use safe method to handle both text and media messages
            await self.safe_send_or_edit_profile(query, profile_text, reply_markup)
            
        except Exception as e:
            await self.safe_send_or_edit_profile(query, f"❌ خطا در بارگیری پروفایل: {str(e)}")

    async def safe_send_or_edit_profile(self, query, text, reply_markup=None):
        """Safely send or edit a message, handling both text and media messages"""
        try:
            # First, try to edit the message text if it exists
            if query.message.text:
                await query.edit_message_text(text, reply_markup=reply_markup)
            else:
                # If no text (probably a photo/media message), send a new message
                await query.message.reply_text(text, reply_markup=reply_markup)
                # Answer the callback query to remove the loading state
                await query.answer("پروفایل کاربر نمایش داده شد")
        except Exception as e:
            # If editing fails for any reason, send a new message
            try:
                await query.message.reply_text(text, reply_markup=reply_markup)
                await query.answer("پروفایل کاربر نمایش داده شد")
            except Exception as send_error:
                # Last resort: just answer the callback query with an error
                await query.answer(f"❌ خطا در نمایش پروفایل: {str(e)}", show_alert=True)
    
    def get_payment_status_text(self, status):
        """Convert payment status to readable text"""
        status_map = {
            'pending_approval': '⏳ در انتظار تایید',
            'approved': '✅ تایید شده',
            'rejected': '❌ رد شده',
            None: '❓ نامشخص'
        }
        return status_map.get(status, '❓ نامشخص')
    
    def get_questionnaire_status_text(self, user_data):
        """Get questionnaire completion status"""
        if user_data.get('questionnaire_completed'):
            return '✅ تکمیل شده'
        elif user_data.get('questionnaire_started'):
            return '🔄 در حال انجام'
        else:
            return '❌ شروع نشده'

    async def handle_quick_approve_all(self, query) -> None:
        """Handle quick approval of multiple payments with confirmation"""
        try:
            # Get pending payments
            with open('bot_data.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            payments = data.get('payments', {})
            pending = {k: v for k, v in payments.items() if v.get('status') == 'pending_approval'}
            
            if not pending:
                await query.edit_message_text("✅ هیچ پرداخت معلقی برای تایید وجود ندارد!")
                return
            
            # Show confirmation dialog
            total_amount = sum(p.get('price', 0) for p in pending.values())
            text = f"""⚠️ تایید دسته‌جمعی پرداخت‌ها
            
📊 تعداد پرداخت‌ها: {len(pending)} مورد
💰 مجموع مبلغ: {total_amount:,} تومان

آیا از تایید همه پرداخت‌های معلق اطمینان دارید؟

⚠️ این عمل قابل بازگشت نیست!"""
            
            keyboard = [
                [
                    InlineKeyboardButton("✅ تایید همه", callback_data='confirm_approve_all'),
                    InlineKeyboardButton("❌ انصراف", callback_data='admin_pending_payments')
                ],
                [InlineKeyboardButton("👁️ مشاهده جزئیات", callback_data='admin_payments_detailed')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(text, reply_markup=reply_markup)
            
        except Exception as e:
            await query.edit_message_text(f"❌ خطا: {str(e)}")

    async def handle_questionnaire_choice(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle choice answers from questionnaire"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        if await self.check_cooldown(user_id):
            return
        answer = query.data.replace('q_answer_', '')
        
        # Submit the answer
        result = await self.questionnaire_manager.process_answer(user_id, answer)
        
        if result["status"] == "error":
            # Send error message and return
            await query.answer(result["message"], show_alert=True)
            return
        elif result["status"] == "completed":
            # Questionnaire completed
            await self.complete_questionnaire(update, context)
            return
        
        # Continue with next question
        question = result["question"]
        if question:
            # Show next question
            message = f"""{result['progress_text']}

{question['text']}"""
            
            keyboard = []
            if question.get('type') == 'choice':
                choices = question.get('choices', [])
                for choice in choices:
                    keyboard.append([InlineKeyboardButton(choice, callback_data=f'q_answer_{choice}')])
                keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data='back_to_user_menu')])
            else:
                keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data='back_to_user_menu')]]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(message, reply_markup=reply_markup)
        else:
            # Something went wrong, proceed to completion
            await self.complete_questionnaire(update, context)

    async def handle_text_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        FIXED ARCHITECTURE: Smart text dispatcher that ONLY processes text in valid input states.
        Completely ignores random text from users not in text input workflows.
        """
        user_id = update.effective_user.id
        text_input = update.message.text
        
        # COMPREHENSIVE DEBUG LOGGING for text input issue
        logger.info(f"🔍 TEXT INPUT HANDLER - User {user_id}: '{text_input[:50]}...'")
        logger.debug(f"🔍 Context user_data keys for user: {list(context.user_data.get(user_id, {}).keys())}")
        
        # STEP 1: Check if user is EXPLICITLY waiting for text input
        explicitly_waiting_for_text = await self._is_user_waiting_for_text_input(user_id, context)
        
        logger.info(f"🎯 TEXT INPUT DECISION - User {user_id}: waiting_for_text = {explicitly_waiting_for_text}")
        
        if not explicitly_waiting_for_text:
            # CORE FIX: Completely ignore random text - no processing, no responses
            logger.info(f"🔇 IGNORING random text from user {user_id} - not in text input mode")
            
            # DEBUG: Log questionnaire flow decision for ignored text with enhanced context
            await admin_error_handler.log_questionnaire_flow_debug(
                user_id=user_id,
                context="text_input_ignored",
                questionnaire_data=context.user_data.get(user_id, {}),
                flow_decision="ignore_text_not_waiting",
                details={
                    'text_input_preview': text_input[:50],
                    'user_context_keys': list(context.user_data.get(user_id, {}).keys()),
                    'questionnaire_active_flag': context.user_data.get(user_id, {}).get('questionnaire_active', False),
                    'questionnaire_activated_at': context.user_data.get(user_id, {}).get('questionnaire_activated_at', 'never'),
                    'auto_fix_attempted': False,  # This will be true when we add auto-fix
                    'validation_reason': 'flag_missing_or_false'
                }
            )
            return
        
        # STEP 2: User IS in valid text input mode - route to appropriate handler
        logger.info(f"✅ PROCESSING TEXT INPUT - User {user_id} in valid text input mode")
        await self._route_text_to_handler(update, context, text_input)

    async def _is_user_waiting_for_text_input(self, user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Check if user is explicitly waiting for text input"""
        user_context = context.user_data.get(user_id, {})
        
        # COMPREHENSIVE DEBUG for questionnaire text input validation
        logger.debug(f"🔍 TEXT INPUT VALIDATION - User {user_id}")
        logger.debug(f"  User context keys: {list(user_context.keys())}")
        logger.debug(f"  questionnaire_active flag: {user_context.get('questionnaire_active', False)}")
        
        # ADMIN TEXT INPUT STATES
        if await self.admin_panel.admin_manager.is_admin(user_id):
            admin_waiting_states = [
                'uploading_plan',
                'uploading_user_plan',
            ]
            if any(user_context.get(state) for state in admin_waiting_states):
                return True
            if user_id in self.admin_panel.admin_creating_coupons:
                return True
        
        # USER TEXT INPUT STATES
        user_waiting_states = [
            'waiting_for_coupon',  # Explicitly waiting for coupon code
            'awaiting_payment_receipt',  # Waiting for payment receipt photo (not text)
        ]
        if any(user_context.get(state) for state in user_waiting_states):
            return True
        
        # QUESTIONNAIRE ACTIVE STATE - ENHANCED CHECK with fallback to questionnaire data
        # KEY FIX: Check for questionnaire_active flag, not just having unfinished questionnaire data
        questionnaire_active_flag = user_context.get('questionnaire_active', False)
        logger.debug(f"  questionnaire_active flag: {questionnaire_active_flag}")
        
        # FALLBACK CHECK: If flag is missing, check if user has active questionnaire progress
        if not questionnaire_active_flag:
            logger.debug(f"  Flag missing - checking questionnaire progress as fallback")
            fallback_progress = await self.questionnaire_manager.load_user_progress(user_id)
            if fallback_progress and not fallback_progress.get("completed", False) and fallback_progress.get("current_step", 0) > 0:
                # User has active questionnaire but flag is missing - auto-set flag
                logger.warning(f"  ⚠️ AUTO-FIXING: User {user_id} has active questionnaire but missing flag")
                user_context['questionnaire_active'] = True
                questionnaire_active_flag = True
                logger.info(f"  ✅ AUTO-SET questionnaire_active flag for user {user_id}")
        
        if questionnaire_active_flag:
            logger.debug(f"  ✅ questionnaire_active flag is TRUE - checking questionnaire progress")
            questionnaire_progress = await self.questionnaire_manager.load_user_progress(user_id)
            logger.debug(f"  Questionnaire progress loaded: {questionnaire_progress is not None}")
            if questionnaire_progress:
                logger.debug(f"  Progress details: completed={questionnaire_progress.get('completed', False)}, current_step={questionnaire_progress.get('current_step', 0)}")
            
            if questionnaire_progress is not None:
                # Regular questionnaire mode
                if (not questionnaire_progress.get("completed", False) and
                    questionnaire_progress.get("current_step", 0) > 0):
                    
                    # Double-check current question exists
                    current_question = await self.questionnaire_manager.get_current_question(user_id)
                    logger.debug(f"  Current question exists: {current_question is not None}")
                    if current_question:
                        logger.debug(f"  📝 ACCEPTING TEXT INPUT - User {user_id} in active questionnaire")
                        return True
                    else:
                        logger.debug(f"  ❌ REJECTING TEXT INPUT - No current question available")
                
                # Edit mode
                if questionnaire_progress.get("edit_mode", False):
                    logger.debug(f"  📝 ACCEPTING TEXT INPUT - User {user_id} in questionnaire edit mode")
                    return True
            else:
                logger.debug(f"  ❌ REJECTING TEXT INPUT - No questionnaire progress found despite active flag")
        else:
            logger.debug(f"  ❌ questionnaire_active flag is FALSE or missing")
        
        # Default: User is NOT waiting for text input
        logger.debug(f"  ❌ FINAL DECISION: NOT waiting for text input")
        return False

    async def _route_text_to_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text_input: str):
        """Route text to appropriate handler based on user state"""
        user_id = update.effective_user.id
        user_context = context.user_data.get(user_id, {})
        
        # ADMIN HANDLERS
        if await self.admin_panel.admin_manager.is_admin(user_id):
            # Admin coupon creation
            if user_id in self.admin_panel.admin_creating_coupons:
                await self.admin_panel.handle_admin_coupon_creation(update, text_input)
                return
            
            # Admin plan upload
            if user_context.get('uploading_plan') or user_context.get('uploading_user_plan'):
                await self.handle_plan_upload_text(update, context, text_input)
                return
        
        # USER HANDLERS
        # Payment receipt input - expecting photo, not text
        if user_context.get('awaiting_payment_receipt'):
            # UNIFIED INPUT TYPE VALIDATION for payment receipt
            from input_validator import input_validator
            
            await input_validator.validate_and_reject_wrong_input_type(
                update, 'photo', "ارسال رسید پرداخت", is_admin=False
            )
            return
        
        # Coupon input
        if user_context.get('waiting_for_coupon'):
            # UNIFIED INPUT TYPE VALIDATION for coupon input
            from input_validator import input_validator
            
            is_valid = await input_validator.validate_and_reject_wrong_input_type(
                update, 'coupon_code', "ورود کد تخفیف", is_admin=False
            )
            if not is_valid:
                return
            
            await self.handle_coupon_code(update, context, text_input)
            return
        
        # Questionnaire input - handle both normal and edit modes
        questionnaire_progress = await self.questionnaire_manager.load_user_progress(user_id)
        if questionnaire_progress is not None:
            # Edit mode
            if questionnaire_progress.get("edit_mode", False):
                await self._handle_edit_mode_text_input(update, context, text_input)
                return
            
            # Normal questionnaire mode
            if (not questionnaire_progress.get("completed", False) and
                questionnaire_progress.get("current_step", 0) > 0):
                await self._handle_questionnaire_text_input(update, context, text_input)
                return
        
        # Should never reach here due to _is_user_waiting_for_text_input check
        logger.warning(f"⚠️ Text routed to handler but no valid state found for user {user_id}")

    async def _handle_questionnaire_text_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text_input: str):
        """Handle questionnaire text input - extracted from original handle_questionnaire_response"""
        user_id = update.effective_user.id
        
        # Get current question to validate
        current_question = await self.questionnaire_manager.get_current_question(user_id)
        if not current_question:
            logger.warning(f"⚠️ User {user_id} sent questionnaire text but no current question")
            await update.message.reply_text(
                "❌ خطا در بارگذاری سوال فعلی.\n\n"
                "لطفاً از /start استفاده کنید."
            )
            return
        
        # UNIFIED INPUT TYPE VALIDATION - Check if text is appropriate for this question type
        from input_validator import input_validator
        question_type = current_question.get('type', 'text')
        
        # Pre-validate input type before content validation
        is_type_valid = await input_validator.validate_and_reject_wrong_input_type(
            update, question_type, f"پرسشنامه - سوال {current_question.get('step', '?')}", is_admin=False
        )
        
        if not is_type_valid:
            # Error message already sent by validator
            return
        
        # Process questionnaire answer - reuse existing logic
        current_step = current_question.get('step', 1)
        
        # SANITIZE and validate the answer
        sanitized_input = sanitize_text(text_input)

        is_valid, error_msg = self.questionnaire_manager.validate_answer(current_step, sanitized_input)
        if not is_valid:
            await update.message.reply_text(f"❌ {error_msg}")
            return
        
        # Submit the SANITIZED answer
        result = await self.questionnaire_manager.process_answer(user_id, sanitized_input)
        
        if result["status"] == "error":
            await update.message.reply_text(f"❌ {result['message']}")
            return
        elif result["status"] == "completed":
            await self.complete_questionnaire_from_text(update, context)
            return
        
        # Continue with next question
        question = result["question"]
        if question:
            message = f"""{result['progress_text']}

{question['text']}"""
            
            keyboard = []
            if question.get('type') == 'choice':
                choices = question.get('choices', [])
                for choice in choices:
                    keyboard.append([InlineKeyboardButton(choice, callback_data=f'q_answer_{choice}')])
                keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data='back_to_user_menu')])
            else:
                keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data='back_to_user_menu')]]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(message, reply_markup=reply_markup)
        else:
            await self.complete_questionnaire_from_text(update, context)

    async def _handle_edit_mode_text_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text_input: str) -> None:
        """Handle text input during questionnaire edit mode"""
        user_id = update.effective_user.id
        sanitized_input = sanitize_text(text_input)
        
        result = await self.questionnaire_manager.update_answer_in_edit_mode(user_id, sanitized_input)
        
        if result["status"] == "answer_updated":
            # Send confirmation message
            confirmation_msg = await update.message.reply_text(result["message"])
            
            # Get updated question with the new answer for immediate UI refresh
            questionnaire_progress = await self.questionnaire_manager.load_user_progress(user_id)
            if questionnaire_progress and questionnaire_progress.get("edit_mode", False):
                current_step = questionnaire_progress.get("edit_step", 1)
                question = self.questionnaire_manager.get_question(current_step, questionnaire_progress["answers"])
                current_answer = questionnaire_progress["answers"].get(str(current_step), "")
                
                # Display refreshed question with updated answer and navigation buttons
                answer_text = f"\n\n💡 پاسخ فعلی: {current_answer}" if current_answer else ""
                message = f"✏️ حالت ویرایش پرسشنامه\n\n{question['text']}{answer_text}\n\n📝 پاسخ جدید خود را وارد کنید یا از دکمه‌های ناوبری استفاده کنید:"
                
                keyboard = [
                    [InlineKeyboardButton("⬅️ سوال قبلی", callback_data='edit_prev'),
                     InlineKeyboardButton("➡️ سوال بعدی", callback_data='edit_next')],
                    [InlineKeyboardButton("✅ اتمام ویرایش", callback_data='finish_edit')],
                    [InlineKeyboardButton("🏠 منوی اصلی", callback_data='back_to_user_menu')]
                ]
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                # Send the refreshed edit interface
                await update.message.reply_text(message, reply_markup=reply_markup)
        else:
            await update.message.reply_text(f"❌ {result['message']}")

    async def handle_questionnaire_response(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        DEPRECATED: This method is no longer used.
        Text input is now handled by the new handle_text_input() architecture.
        Keeping this method for backwards compatibility but it should never be called.
        """
        logger.warning(f"⚠️ DEPRECATED handle_questionnaire_response called - this should not happen!")
        user_id = update.effective_user.id
        logger.warning(f"⚠️ User {user_id} triggered deprecated text handler - routing to new system")
        
        # Route to new system
        await self.handle_text_input(update, context)
    async def complete_questionnaire(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle questionnaire completion from callback"""
        query = update.callback_query
        user_id = update.effective_user.id
        
        # CRITICAL: Clear all questionnaire states after completion
        states_cleared = await admin_error_handler.clear_all_input_states(
            context, user_id, "questionnaire_completion_callback"
        )
        
        # CRITICAL FIX: Clear questionnaire_active flag on completion
        if user_id in context.user_data and 'questionnaire_active' in context.user_data[user_id]:
            context.user_data[user_id]['questionnaire_active'] = False
            logger.info(f"🧹 CLEARED QUESTIONNAIRE_ACTIVE FLAG - User {user_id} on completion")
        
        # Log questionnaire completion
        log_user_action(user_id, update.effective_user.first_name, "questionnaire completed")
        
        # Get course type from pending payment
        course_type = self.payment_pending.get(user_id)
        
        completion_message = """🎉 تبریک! پرسشنامه با موفقیت تکمیل شد

✅ اطلاعات شما ثبت شد و در حال آماده‌سازی برنامه تمرینی شخصی‌سازی شده شما هستیم.

🔄 لطفاً منتظر بمانید تا یکی از مربیان ما با شما تماس بگیرد.

⏰ معمولاً تا چند ساعت آینده برنامه کاملتان آماده خواهد شد.

📞 اگر سوالی دارید، از طریق پشتیبانی ربات با ما در ارتباط باشید."""
        
        # Edit the message to show completion
        await query.edit_message_text(completion_message)
        
        # Completion - no further action needed as user has already paid

    async def complete_questionnaire_from_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle questionnaire completion from text message"""
        user_id = update.effective_user.id
        
        # CRITICAL: Clear all questionnaire states after completion
        states_cleared = await admin_error_handler.clear_all_input_states(
            context, user_id, "questionnaire_completion_text"
        )
        
        # Log questionnaire completion
        log_user_action(user_id, update.effective_user.first_name, "questionnaire completed (from text)")
        
        # Get course type from pending payment
        course_type = self.payment_pending.get(user_id)
        
        completion_message = """🎉 تبریک! پرسشنامه با موفقیت تکمیل شد

✅ اطلاعات شما ثبت شد و در حال آماده‌سازی برنامه تمرینی شخصی‌سازی شده شما هستیم.

🔄 لطفاً منتظر بمانید تا یکی از مربیان ما با شما تماس بگیرد.

⏰ معمولاً تا چند ساعت آینده برنامه کاملتان آماده خواهد شد.

📞 اگر سوالی دارید، از طریق پشتیبانی ربات با ما در ارتباط باشید."""
        
        # Send completion message
        await update.message.reply_text(completion_message)
        
        # Completion - no further action needed as user has already paid

    async def handle_questionnaire_completion_from_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle questionnaire completion from callback query"""
        user_id = update.effective_user.id
        
        # CRITICAL: Clear all questionnaire states after completion
        states_cleared = await admin_error_handler.clear_all_input_states(
            context, user_id, "questionnaire_completion_query"
        )
        
        # CRITICAL FIX: Clear questionnaire_active flag on completion
        if user_id in context.user_data and 'questionnaire_active' in context.user_data[user_id]:
            del context.user_data[user_id]['questionnaire_active']
            logger.info(f"🧹 CLEARED QUESTIONNAIRE_ACTIVE FLAG - User {user_id} on completion (from query)")
        
        # Log questionnaire completion
        log_user_action(user_id, update.effective_user.first_name, "questionnaire completed (from query)")
        
        completion_message = """🎉 تبریک! پرسشنامه با موفقیت تکمیل شد

✅ اطلاعات شما ثبت شد و در حال آماده‌سازی برنامه تمرینی شخصی‌سازی شده شما هستیم.

🔄 لطفاً منتظر بمانید تا یکی از مربیان ما با شما تماس بگیرد.

⏰ معمولاً تا چند ساعت آینده برنامه کاملتان آماده خواهد شد.

📞 اگر سوالی دارید، از طریق پشتیبانی ربات با ما در ارتباط باشید."""
        
        # Edit the query message to show completion
        query = update.callback_query
        await query.edit_message_text(completion_message)
        
        # Show status-based menu after completion
        await self.show_status_based_menu(update, context, await self.data_manager.get_user_data(user_id), update.effective_user.first_name or "کاربر")

    async def start_questionnaire_from_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Start questionnaire directly from callback"""
        query = update.callback_query
        user_id = update.effective_user.id
        if await self.check_cooldown(user_id):
            await query.answer()
            return
        
        # CRITICAL: Use get_user_status to check payments table, not user data
        user_data = await self.data_manager.get_user_data(user_id)
        user_status = await self.get_user_status(user_data)
        
        # Check if user has approved payment for any course (including nutrition plan)
        purchased_courses = await self.get_user_purchased_courses(user_id)
        
        if user_status != 'payment_approved' or not purchased_courses:
            await query.edit_message_text(
                "❌ برای شروع پرسشنامه ابتدا باید پرداخت شما تایید شود.\n\n"
                "لطفا ابتدا یک دوره انتخاب کنید و پرداخت کنید."
            )
            return
        
        # Start the questionnaire
        result = await self.questionnaire_manager.start_questionnaire(user_id)
        
        # The questionnaire manager returns progress object, not status object
        if result and "current_step" in result:
            # CRITICAL FIX: Set questionnaire_active flag for text input routing
            if user_id not in context.user_data:
                context.user_data[user_id] = {}
            context.user_data[user_id]['questionnaire_active'] = True
            
            # Get the current question
            current_step = result.get("current_step", 1)
            question = self.questionnaire_manager.get_question(current_step, result.get("answers", {}))
            
            if question:
                message = f"""{question.get('progress_text', f'سوال {current_step} از 21')}

{question['text']}"""
                
                keyboard = []
                if question.get('type') == 'choice':
                    choices = question.get('choices', [])
                    for choice in choices:
                        keyboard.append([InlineKeyboardButton(choice, callback_data=f'q_answer_{choice}')])
                    keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data='back_to_user_menu')])
                else:
                    keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data='back_to_user_menu')]]
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(message, reply_markup=reply_markup)
            else:
                await query.edit_message_text("❌ خطا در بارگذاری سوال پرسشنامه")
        else:
            await query.edit_message_text("❌ خطا در شروع پرسشنامه، لطفا دوباره تلاش کنید")

    async def back_to_main(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Return to main menu using unified status-based menu"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        if await self.check_cooldown(user_id):
            return
        user_data = await self.data_manager.get_user_data(user_id)
        user_data['user_id'] = user_id  # Ensure user_id is set
        user_name = user_data.get('name', update.effective_user.first_name or 'کاربر')
        
        # Use the same unified menu system as /start command
        await self.show_status_based_menu(update, context, user_data, user_name)

    async def back_to_user_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Return to appropriate user menu - COMPREHENSIVE STATE CLEARING"""
        try:
            query = update.callback_query
            await query.answer()

            user_id = update.effective_user.id
            if await self.check_cooldown(user_id):
                return
            
            # COMPREHENSIVE STATE CLEARING - clear EVERYTHING except questionnaire
            states_cleared = await admin_error_handler.clear_all_input_states(
                context, user_id, "back_to_user_menu - FORCE CLEAN STATE"
            )
            
            # DON'T RESET QUESTIONNAIRE PROGRESS - preserve questionnaire state
            # This ensures users can go back without losing their questionnaire progress
            # questionnaire_reset = await admin_error_handler.reset_questionnaire_state(
            #     user_id, self.questionnaire_manager, "back_to_user_menu - FORCE RESET"
            # )
            
            # CRITICAL FIX: Clear questionnaire_active flag but preserve questionnaire data
            # User exits active questionnaire session but keeps progress for later
            if user_id in context.user_data and 'questionnaire_active' in context.user_data[user_id]:
                # Check if user is in edit mode and clear it from questionnaire data
                questionnaire_progress = await self.questionnaire_manager.load_user_progress(user_id)
                if questionnaire_progress and questionnaire_progress.get("edit_mode", False):
                    # User is exiting edit mode via back button - clear edit mode
                    questionnaire_progress["edit_mode"] = False
                    questionnaire_progress.pop("edit_step", None)
                    await self.questionnaire_manager.save_user_progress(user_id, questionnaire_progress)
                    logger.info(f"🧹 CLEARED EDIT MODE - User {user_id} via back button")
                
                context.user_data[user_id].pop('questionnaire_active', None)
                logger.info(f"🧹 CLEARED QUESTIONNAIRE_ACTIVE FLAG - User {user_id} via back button (progress preserved)")
            
            logger.info(f"👤 PRESERVING QUESTIONNAIRE STATE - User {user_id} | back_to_user_menu preserves progress")
            
            # Clear payment_pending if exists
            if user_id in self.payment_pending:
                del self.payment_pending[user_id]
                states_cleared.append("payment_pending")
            
            # Clear admin states if user is admin
            if await self.admin_panel.admin_manager.is_admin(user_id):
                admin_states_cleared = await admin_error_handler.clear_admin_input_states(
                    self.admin_panel, user_id, "back_to_user_menu - ADMIN CLEANUP"
                )
                states_cleared.extend(admin_states_cleared)
            
            # Log comprehensive cleanup (questionnaire preserved)
            log_user_action(user_id, update.effective_user.first_name, "back to user menu", f"Total states cleared: {len(states_cleared)} | Questionnaire preserved")
            
            user_data = await self.data_manager.get_user_data(user_id)
            user_data['user_id'] = user_id  # Ensure user_id is set
            user_name = user_data.get('name', update.effective_user.first_name or 'کاربر')
            
            # ALWAYS show simple unified menu - same as /start command
            # This ensures consistent behavior when using back button
            await self.show_simple_unified_menu(update, context, user_data, user_name)
            
        except Exception as e:
            user_id = update.effective_user.id if update.effective_user else "unknown"
            
            # Log the specific error for debugging
            logger.error(f"ERROR in back_to_user_menu for user {user_id}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Try to send a helpful error message with more context
            error_context = ""
            if "There is no text in the message to edit" in str(e):
                error_context = "\n\n(خطا: تصویر موجود قابل ویرایش نیست)"
            elif "Message is not modified" in str(e):
                error_context = "\n\n(خطا: پیام تغییری نکرده)"
            elif "BadRequest" in str(e):
                error_context = "\n\n(خطا: درخواست نامعتبر)"
            
            try:
                await update.callback_query.edit_message_text(
                    f"❌ خطایی در بازگشت به منو رخ داد.{error_context}\n\n"
                    "🔄 برای حل مشکل /start را تایپ کنید.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔄 شروع مجدد", callback_data='start_over')]
                    ])
                )
            except Exception:
                # If even that fails, try sending a new message
                try:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=f"❌ خطایی رخ داد.{error_context}\n\n🔄 لطفاً /start را تایپ کنید."
                    )
                except Exception:
                    pass

    async def back_to_course_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Return to course category selection - COMPREHENSIVE STATE CLEARING"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        if await self.check_cooldown(user_id):
            return
        
        # COMPREHENSIVE state clearing - clear ALL input states
        states_cleared = await admin_error_handler.clear_all_input_states(
            context, user_id, "back_to_course_selection - FORCE CLEAN"
        )
        
        # Clear payment_pending if exists
        if user_id in self.payment_pending:
            del self.payment_pending[user_id]
            states_cleared.append("payment_pending")
        
        # Log navigation
        log_user_action(user_id, update.effective_user.first_name, "back to course selection", f"States cleared: {len(states_cleared)}")
        
        # Show the course selection interface
        await self.start_new_course_selection(update, context)

    async def back_to_category(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle back navigation to course categories - COMPREHENSIVE STATE CLEARING"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        if await self.check_cooldown(user_id):
            return
        
        # COMPREHENSIVE state clearing - clear ALL input states
        states_cleared = await admin_error_handler.clear_all_input_states(
            context, user_id, "back_to_category - FORCE CLEAN"
        )
        
        # Clear payment_pending if exists
        if user_id in self.payment_pending:
            del self.payment_pending[user_id]
            states_cleared.append("payment_pending")
        
        # Log navigation
        log_user_action(user_id, update.effective_user.first_name, "back to category", f"States cleared: {len(states_cleared)}")
        
        # Extract category from callback data
        if query.data == 'back_to_online':
            # Show online courses directly
            purchased_courses = await self.get_user_purchased_courses(user_id)
            
            weights_text = "1️⃣ برنامه وزنه"
            cardio_text = "2️⃣ برنامه هوازی و کار با توپ"
            combo_text = "3️⃣ برنامه وزنه + برنامه هوازی (با تخفیف بیشتر)"
            
            if 'online_weights' in purchased_courses:
                weights_text += " ✅"
            if 'online_cardio' in purchased_courses:
                cardio_text += " ✅"
            if 'online_combo' in purchased_courses:
                combo_text += " ✅"
            
            keyboard = [
                [InlineKeyboardButton(weights_text, callback_data='online_weights')],
                [InlineKeyboardButton(cardio_text, callback_data='online_cardio')],
                [InlineKeyboardButton(combo_text, callback_data='online_combo')],
                [InlineKeyboardButton("🔙 بازگشت به انتخاب دوره", callback_data='back_to_course_selection')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("انتخاب کنید:", reply_markup=reply_markup)
            
        elif query.data == 'back_to_in_person':
            # Show in-person courses directly
            purchased_courses = await self.get_user_purchased_courses(user_id)
            
            cardio_text = "1️⃣ تمرین هوازی سرعتی چابکی کار با توپ"
            weights_text = "2️⃣ تمرین وزنه"
            
            if 'in_person_cardio' in purchased_courses:
                cardio_text += " ✅"
            if 'in_person_weights' in purchased_courses:
                weights_text += " ✅"
            
            keyboard = [
                [InlineKeyboardButton(cardio_text, callback_data='in_person_cardio')],
                [InlineKeyboardButton(weights_text, callback_data='in_person_weights')],
                [InlineKeyboardButton("🔙 بازگشت به انتخاب دوره", callback_data='back_to_course_selection')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("انتخاب کنید:", reply_markup=reply_markup)

    async def handle_status_callbacks(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle status-related callback queries"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        user_data = await self.data_manager.get_user_data(user_id)
        
        if query.data == 'my_status':
            await self.show_user_status(update, context, user_data)
        elif query.data == 'check_payment_status':
            await self.show_payment_status(update, context, user_data)
        elif query.data == 'continue_questionnaire':
            await self.continue_questionnaire_callback(update, context)
        elif query.data == 'purchase_additional_course':
            await self.purchase_additional_course(update, context)
        elif query.data == 'restart_questionnaire':
            await self.restart_questionnaire(update, context)
        elif query.data == 'edit_questionnaire':
            await self.edit_questionnaire(update, context)
        elif query.data == 'view_program':
            # Check if user has multiple courses, if so show course selection
            user_courses = await self.get_user_approved_courses(user_id)
            if len(user_courses) > 1:
                await self.show_course_selection_for_program(update, context, user_courses)
            else:
                await self.show_training_program(update, context, user_data)
        elif query.data == 'contact_support':
            await self.show_support_info(update, context)
        elif query.data.startswith('view_program_'):
            # Handle course-specific program viewing
            course_code = query.data.replace('view_program_', '')
            await self.show_training_program(update, context, course_code=course_code)
        elif query.data == 'new_course':
            # Start new course selection process
            await self.start_new_course_selection(update, context)
        elif query.data == 'start_over':
            # Restart the bot flow from the beginning
            await self.start(update, context)
        elif query.data == 'start_questionnaire':
            # Start the questionnaire directly
            await self.start_questionnaire_from_callback(update, context)
        elif query.data == 'continue_photo_question':
            # Continue to next question when minimum photo requirements are met
            await self.handle_continue_photo_question(update, context)
        elif query.data == 'add_more_photos':
            # User wants to add more photos - just show message
            await query.edit_message_text(
                "📷 عالی! حالا عکس‌های بیشتری ارسال کنید.\n\n"
                "💡 بعد از ارسال عکس، دوباره گزینه ادامه نمایش داده می‌شود."
            )

    async def handle_nutrition_form_callbacks(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle nutrition form related callback queries"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        
        if query.data == 'nutrition_form_understood':
            # User confirmed they understood - show completion message
            message = """✅ عالی! 

اکنون روی لینک کلیک کنید و فرم را پر کنید. پس از تکمیل فرم، برنامه غذایی شخصی‌سازی شده‌تان آماده خواهد شد.

📞 اگر سوالی داشتید، می‌توانید با @DrBohloul تماس بگیرید."""
            
            keyboard = [
                [InlineKeyboardButton("🔗 رفتن به فرم", url='https://fitava.ir/coach/drbohloul/question')],
                [InlineKeyboardButton("🏠 بازگشت به منوی اصلی", callback_data='back_to_user_menu')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(message, reply_markup=reply_markup)
            log_user_action(user_id, "nutrition_form", "User confirmed understanding")
            
        elif query.data == 'nutrition_form_question':
            # User has questions - show help message
            message = """❓ راهنمایی برای فرم برنامه غذایی:

🔗 **مرحله 1:** روی لینک کلیک کنید: https://fitava.ir/coach/drbohloul/question

📝 **مرحله 2:** همه فیلدهای فرم را پر کنید (هیچ فیلدی را خالی نگذارید)

🔢 **مرحله 3:** برای قسمت‌هایی که عدد می‌خواهند، حتماً از اعداد انگلیسی استفاده کنید (مثل: 25 به جای ۲۵)

✅ **مرحله 4:** فرم را ارسال کنید تا برنامه غذایی‌تان آماده شود

📞 برای سوالات بیشتر: @DrBohloul"""
            
            keyboard = [
                [InlineKeyboardButton("✅ متوجه شدم، برم فرم را پر کنم", callback_data='nutrition_form_understood')],
                [InlineKeyboardButton("🔗 رفتن به فرم", url='https://fitava.ir/coach/drbohloul/question')],
                [InlineKeyboardButton("🏠 منوی اصلی", callback_data='back_to_user_menu')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(message, reply_markup=reply_markup)
            log_user_action(user_id, "nutrition_form", "User requested help")

    async def handle_continue_photo_question(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle continuing to next question when minimum photo requirements are met"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        
        try:
            # Use questionnaire manager to continue to next question
            result = await self.questionnaire_manager.continue_to_next_question(user_id)
            
            if result["status"] == "error":
                await query.edit_message_text(result["message"])
                return
            elif result["status"] == "next_question":
                # Send next question
                progress_text = result.get("progress_text", "")
                message = f"✅ ادامه به سوال بعد\n\n{progress_text}\n\n{result['question']['text']}"
                
                keyboard = []
                if result['question'].get('type') == 'choice':
                    choices = result['question'].get('choices', [])
                    for choice in choices:
                        keyboard.append([InlineKeyboardButton(choice, callback_data=f'q_answer_{choice}')])
                keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data='back_to_user_menu')])
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(message, reply_markup=reply_markup)
                return
            elif result["status"] == "completed":
                # Questionnaire completed
                await query.edit_message_text(result["message"])
                await self.handle_questionnaire_completion_from_query(update, context)
                return
            else:
                await query.edit_message_text("❌ خطا در ادامه به سوال بعد!")
                
        except Exception as e:
            error_logger.error(f"Error continuing photo question for user {user_id}: {e}", exc_info=True)
            await query.edit_message_text(
                "❌ خطایی رخ داده است!\n\n"
                "لطفاً دوباره تلاش کنید یا با پشتیبانی تماس بگیرید."
            )

    async def start_new_course_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Start new course selection process"""
        try:
            user_id = update.effective_user.id
            purchased_courses = await self.get_user_purchased_courses(user_id)
            
            # Create course selection keyboard
            course_keyboard = await self.create_course_selection_keyboard(user_id)
            # Add back button and status button to the existing keyboard
            keyboard = list(course_keyboard.inline_keyboard) + [
                [InlineKeyboardButton("🔙 بازگشت به منو اصلی", callback_data='back_to_user_menu')],
                [InlineKeyboardButton("📊 وضعیت فعلی", callback_data='my_status')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            message = "انتخاب دوره جدید:\n\nکدام دوره را می‌خواهید انتخاب کنید?"
            await update.callback_query.edit_message_text(message, reply_markup=reply_markup)
            
        except Exception as e:
            logging.error(f"Error in start_new_course_selection: {e}")
            await update.callback_query.answer("متاسفانه خطایی رخ داد. لطفا دوباره تلاش کنید.")

    async def purchase_additional_course(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle additional course purchase"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        
        # Set flag that user is buying additional course
        if user_id not in context.user_data:
            context.user_data[user_id] = {}
        context.user_data[user_id]['buying_additional_course'] = True
        
        # Show course selection for additional purchase
        await self.start_new_course_selection(update, context)

    async def continue_questionnaire_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle continue questionnaire callback"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        
        try:
            # Get user data and purchased courses
            user_data = await self.data_manager.get_user_data(user_id)
            purchased_courses = await self.get_user_purchased_courses(user_id)
            
            # Check if user has any courses with approved payment (including nutrition plan)
            user_status = await self.get_user_status(user_data)
            
            if not purchased_courses or user_status != 'payment_approved':
                await query.edit_message_text(
                    "❌ برای دسترسی به پرسشنامه، باید:\n\n"
                    "✅ یک دوره خریداری کرده باشید\n"
                    "✅ پرداخت شما تایید شده باشد\n\n"
                    "لطفاً ابتدا یک دوره خرید کرده و پرداخت خود را تکمیل کنید.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🛒 خرید دوره", callback_data='new_course')],
                        [InlineKeyboardButton("📊 وضعیت من", callback_data='my_status')],
                        [InlineKeyboardButton("🔙 منوی اصلی", callback_data='back_to_user_menu')]
                    ])
                )
                return
            
            # Get current question and show it
            current_question = await self.questionnaire_manager.get_current_question(user_id)
            if current_question:
                # CRITICAL FIX: Set questionnaire_active flag when continuing questionnaire
                if user_id not in context.user_data:
                    context.user_data[user_id] = {}
                context.user_data[user_id]['questionnaire_active'] = True
                
                question_text = f"""{current_question['progress_text']}

{current_question['text']}"""
                
                # Add choices as buttons if it's a choice question
                keyboard = []
                if current_question.get('type') in ['choice', 'multichoice']:
                    choices = current_question.get('choices', [])
                    for choice in choices:
                        keyboard.append([InlineKeyboardButton(choice, callback_data=f'q_answer_{choice}')])
                
                # Add navigation buttons
                keyboard.append([InlineKeyboardButton("🔙 بازگشت به منو", callback_data='back_to_user_menu')])
                
                reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
                
                await query.edit_message_text(question_text, reply_markup=reply_markup)
            else:
                # User has valid access but no questionnaire data - start new questionnaire
                user_logger.info(f"Starting new questionnaire for user {user_id} - no existing progress found")
                
                # Start questionnaire
                progress = await self.questionnaire_manager.start_questionnaire(user_id)
                
                # CRITICAL FIX: Set questionnaire_active flag when starting new questionnaire from continue
                if user_id not in context.user_data:
                    context.user_data[user_id] = {}
                context.user_data[user_id]['questionnaire_active'] = True
                
                first_question = await self.questionnaire_manager.get_current_question(user_id)
                
                if first_question:
                    question_text = f"""🎉 شروع پرسشنامه!

{first_question['progress_text']}

{first_question['text']}"""
                    
                    # Add choices as buttons if it's a choice question
                    keyboard = []
                    if first_question.get('type') in ['choice', 'multichoice']:
                        choices = first_question.get('choices', [])
                        for choice in choices:
                            keyboard.append([InlineKeyboardButton(choice, callback_data=f'q_answer_{choice}')])
                    
                    # Add navigation buttons
                    keyboard.append([InlineKeyboardButton("🔙 بازگشت به منو", callback_data='back_to_user_menu')])
                    
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await query.edit_message_text(question_text, reply_markup=reply_markup)
                else:
                    # Fallback error if even starting questionnaire fails
                    await query.edit_message_text(
                        "❌ خطا در شروع پرسشنامه.\n\n"
                        "لطفاً از /start استفاده کرده و مجدداً تلاش کنید.",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("🔄 تلاش مجدد", callback_data='continue_questionnaire')],
                            [InlineKeyboardButton("🔙 منوی اصلی", callback_data='back_to_user_menu')]
                        ])
                    )
        except Exception as e:
            error_logger.error(f"Error in continue_questionnaire_callback for user {user_id}: {e}")
            error_logger.error(f"Traceback: {traceback.format_exc()}")
            await query.edit_message_text(
                "❌ خطایی در راه‌اندازی پرسشنامه رخ داد.\n\n"
                "لطفاً چند لحظه صبر کرده و مجدداً تلاش کنید.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 تلاش مجدد", callback_data='continue_questionnaire')],
                    [InlineKeyboardButton("📊 وضعیت من", callback_data='my_status')],
                    [InlineKeyboardButton("🔙 منوی اصلی", callback_data='back_to_user_menu')]
                ])
            )

    async def show_user_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_data: dict) -> None:
        """Show comprehensive user status - ALL information in one place"""
        query = update.callback_query
        user_id = update.effective_user.id
        user_name = user_data.get('name', 'کاربر')
        
        # Get current status
        status = await self.get_user_status(user_data)
        
        # Get payment information from database
        payments_data = await self.data_manager.load_data('payments')
        user_payments = []
        for payment_id, payment_data in payments_data.items():
            if payment_data.get('user_id') == user_id:
                user_payments.append(payment_data)
        
        # Sort payments by timestamp (newest first)
        user_payments.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        # Get purchased courses
        purchased_courses = await self.get_user_purchased_courses(user_id)
        
        # Build comprehensive status message
        status_text = f"""📊 *وضعیت کامل شما*

👤 *نام:* {user_name}

"""

        # Show purchased courses
        if purchased_courses:
            status_text += "🎓 *دوره‌های خریداری شده:*\n"
            for course_code in purchased_courses:
                course_name = self.get_course_name_farsi(course_code)
                status_text += f"  ✅ {course_name}\n"
            status_text += "\n"
        
        # Show pending/recent payments
        if user_payments:
            latest_payment = user_payments[0]
            payment_status = latest_payment.get('status')
            course_code = latest_payment.get('course_type', 'نامشخص')
            course_name = self.get_course_name_farsi(course_code)
            
            status_text += "💳 *آخرین پرداخت:*\n"
            status_text += f"  📚 دوره: {course_name}\n"
            
            if payment_status == 'pending_approval':
                status_text += "  ⏳ وضعیت: در انتظار تایید\n"
            elif payment_status == 'approved':
                status_text += "  ✅ وضعیت: تایید شده\n"
            elif payment_status == 'rejected':
                status_text += "  ❌ وضعیت: رد شده\n"
            
            status_text += "\n"
        
        # Show questionnaire status for approved payments
        questionnaire_info = ""
        if purchased_courses:
            q_status = await self.questionnaire_manager.get_user_questionnaire_status(user_id)
            if q_status.get('completed'):
                questionnaire_info = "✅ پرسشنامه: تکمیل شده"
            else:
                current_step = q_status.get('current_step', 1)
                total_steps = q_status.get('total_steps', 21)
                questionnaire_info = f"📝 پرسشنامه: مرحله {current_step} از {total_steps}"
            
            status_text += questionnaire_info + "\n\n"
        
        # Action buttons based on status
        keyboard = []
        
        if status == 'payment_pending':
            keyboard.append([InlineKeyboardButton("🔄 بررسی مجدد پرداخت", callback_data='check_payment_status')])
        elif status == 'payment_approved':
            # All courses (including nutrition plans) need questionnaire for personalization
            q_status = await self.questionnaire_manager.get_user_questionnaire_status(user_id)
            if not q_status.get('completed'):
                keyboard.append([InlineKeyboardButton("➡️ ادامه پرسشنامه", callback_data='continue_questionnaire')])
            else:
                # User has completed questionnaire - show program view and edit options
                keyboard.append([InlineKeyboardButton("✏️ ویرایش پرسشنامه", callback_data='edit_questionnaire')])
                
                # Show appropriate program view button based on what courses they have
                has_nutrition_plan = 'nutrition_plan' in purchased_courses
                if has_nutrition_plan and len(purchased_courses) == 1:
                    # Only nutrition plan
                    keyboard.append([InlineKeyboardButton("🍎 مشاهده برنامه غذایی", callback_data='view_program')])
                else:
                    # Training courses or mixed courses
                    keyboard.append([InlineKeyboardButton("📋 مشاهده برنامه تمرینی", callback_data='view_program')])
        elif status == 'payment_rejected':
            keyboard.append([InlineKeyboardButton("💳 پرداخت مجدد", callback_data=f'payment_{user_payments[0].get("course_type", "") if user_payments else ""}')])
        
        # Always show these options
        keyboard.extend([
            [InlineKeyboardButton("🛒 خرید دوره جدید", callback_data='new_course')],
            [InlineKeyboardButton("📞 تماس با پشتیبانی", callback_data='contact_support')],
            [InlineKeyboardButton("🔙 منوی اصلی", callback_data='back_to_user_menu')]
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await self.safe_edit_message(query, status_text, reply_markup=reply_markup, parse_mode='Markdown')

    async def show_payment_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_data: dict) -> None:
        """Show detailed payment status"""
        query = update.callback_query
        user_id = update.effective_user.id
        
        try:
            # Get payment data using the existing logic from get_user_status
            payments_data = await self.data_manager.load_data('payments')
            user_payment = None
            
            # Find the most recent payment for this user
            for payment_id, payment_data in payments_data.items():
                if payment_data.get('user_id') == user_id:
                    if user_payment is None or payment_data.get('timestamp', '') > user_payment.get('timestamp', ''):
                        user_payment = payment_data
            
            payment_status = None
            
            if user_payment:
                payment_status = user_payment.get('status')
                course_code = user_payment.get('course_type', 'نامشخص')
            else:
                # Fallback to user_data payment_status (for backward compatibility)
                payment_status = user_data.get('payment_status')
                course_code = user_data.get('course_selected', user_data.get('course', 'نامشخص'))
            
            course_name = self.get_course_name_farsi(course_code)
            
            if payment_status == 'pending' or payment_status == 'pending_approval':
                message = f"""⏳ *وضعیت پرداخت*

دوره: {course_name}
وضعیت: در انتظار تایید ادمین

فیش واریزی شما دریافت شده و در حال بررسی است.
معمولاً این فرآیند تا 24 ساعت طول می‌کشد.

در صورت تایید، بلافاصله اطلاع‌رسانی خواهید شد."""
            elif payment_status == 'approved':
                message = f"""✅ *وضعیت پرداخت*

دوره: {course_name}
وضعیت: تایید شده

پرداخت شما با موفقیت تایید شده است!
اکنون می‌توانید برنامه تمرینی خود را دریافت کنید."""
            elif payment_status == 'rejected':
                message = f"""❌ *وضعیت پرداخت*

دوره: {course_name}
وضعیت: رد شده

متاسفانه پرداخت شما تایید نشده است.
لطفاً با پشتیبانی تماس بگیرید یا مجدداً پرداخت کنید."""
            else:
                message = "شما هنوز پرداختی انجام نداده‌اید یا اطلاعات پرداخت شما یافت نشد."
            
            keyboard = [
                [InlineKeyboardButton("📞 تماس با پشتیبانی", callback_data='contact_support')],
                [InlineKeyboardButton("🔙 بازگشت", callback_data='my_status')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await self.safe_edit_message(query, message, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            # Fallback error message
            error_message = """❌ متاسفانه خطایی در دریافت وضعیت پرداخت رخ داد.

لطفاً دوباره تلاش کنید یا با پشتیبانی تماس بگیرید."""
            
            keyboard = [
                [InlineKeyboardButton("📞 تماس با پشتیبانی", callback_data='contact_support')],
                [InlineKeyboardButton("🔄 تلاش مجدد", callback_data='check_payment_status')],
                [InlineKeyboardButton("🔙 بازگشت", callback_data='my_status')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(error_message, reply_markup=reply_markup)

    async def continue_questionnaire(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Continue questionnaire from where user left off"""
        query = update.callback_query
        user_id = update.effective_user.id
        
        # Get current question
        question = await self.questionnaire_manager.get_current_question(user_id)
        if question:
            await self.questionnaire_manager.send_question(context.bot, user_id, question)
        else:
            # No current progress, start new questionnaire
            await self.questionnaire_manager.start_questionnaire(user_id)
            question = await self.questionnaire_manager.get_current_question(user_id)
            if question:
                await self.questionnaire_manager.send_question(context.bot, user_id, question)
            else:
                await query.edit_message_text("❌ خطا در بارگذاری پرسشنامه. لطفاً مجدداً تلاش کنید.")

    async def restart_questionnaire(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Restart questionnaire from beginning"""
        query = update.callback_query
        user_id = update.effective_user.id
        
        # Reset questionnaire progress
        await self.questionnaire_manager.reset_questionnaire(user_id)
        
        # Start from first question
        question = await self.questionnaire_manager.get_current_question(user_id)
        if question:
            await self.questionnaire_manager.send_question(context.bot, user_id, question)
        else:
            await query.edit_message_text("❌ خطا در شروع مجدد پرسشنامه.")

    async def edit_questionnaire(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Start questionnaire editing mode for completed questionnaires"""
        query = update.callback_query
        user_id = update.effective_user.id
        
        try:
            # Check if questionnaire is completed
            questionnaire_status = await self.questionnaire_manager.get_user_questionnaire_status(user_id)
            if not questionnaire_status.get('completed', False):
                await query.edit_message_text(
                    "❌ فقط پرسشنامه‌های تکمیل شده قابل ویرایش هستند.\n\n"
                    "لطفاً ابتدا پرسشنامه را تکمیل کنید."
                )
                return
            
            # Start edit mode
            result = await self.questionnaire_manager.start_edit_mode(user_id)
            if result["status"] == "edit_started":
                # Set questionnaire_active flag for text input detection
                user_context = context.user_data.get(user_id, {})
                user_context['questionnaire_active'] = True
                context.user_data[user_id] = user_context
                
                question = result["question"]
                current_answer = result["current_answer"]
                
                # Display current question with current answer and navigation buttons
                answer_text = f"\n\n💡 پاسخ فعلی: {current_answer}" if current_answer else ""
                message = f"✏️ حالت ویرایش پرسشنامه\n\n{question['text']}{answer_text}\n\n📝 پاسخ جدید خود را وارد کنید یا از دکمه‌های ناوبری استفاده کنید:"
                
                keyboard = [
                    [InlineKeyboardButton("⬅️ سوال قبلی", callback_data='edit_prev'),
                     InlineKeyboardButton("➡️ سوال بعدی", callback_data='edit_next')],
                    [InlineKeyboardButton("✅ اتمام ویرایش", callback_data='finish_edit')],
                    [InlineKeyboardButton("🏠 منوی اصلی", callback_data='back_to_user_menu')]
                ]
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(message, reply_markup=reply_markup)
            else:
                await query.edit_message_text(f"❌ خطا در شروع ویرایش: {result['message']}")
                
        except Exception as e:
            logger.error(f"Error in edit_questionnaire for user {user_id}: {e}")
            await query.edit_message_text("❌ خطا در شروع ویرایش پرسشنامه.")

    async def handle_edit_navigation(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle navigation in edit mode (prev/next buttons)"""
        query = update.callback_query
        await query.answer()
        user_id = update.effective_user.id
        if await self.check_cooldown(user_id):
            return
        action = query.data  # 'edit_prev' or 'edit_next'
        
        try:
            direction = 'backward' if action == 'edit_prev' else 'forward'
            result = await self.questionnaire_manager.navigate_edit_mode(user_id, direction)
            
            if result["status"] == "edit_navigation":
                question = result["question"]
                current_answer = result["current_answer"]
                
                # Display question with current answer and navigation buttons
                answer_text = f"\n\n💡 پاسخ فعلی: {current_answer}" if current_answer else ""
                message = f"✏️ حالت ویرایش پرسشنامه - سوال {result.get('current_step', '?')}\n\n{question['text']}{answer_text}\n\n📝 پاسخ جدید خود را وارد کنید یا از دکمه‌های ناوبری استفاده کنید:"
                
                keyboard = [
                    [InlineKeyboardButton("⬅️ سوال قبلی", callback_data='edit_prev'),
                     InlineKeyboardButton("➡️ سوال بعدی", callback_data='edit_next')],
                    [InlineKeyboardButton("✅ اتمام ویرایش", callback_data='finish_edit')],
                    [InlineKeyboardButton("🏠 منوی اصلی", callback_data='back_to_user_menu')]
                ]
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(message, reply_markup=reply_markup)
            else:
                await query.answer(result['message'], show_alert=True)
                
        except Exception as e:
            logger.error(f"Error in handle_edit_navigation for user {user_id}: {e}")
            await query.answer("❌ خطا در ناوبری", show_alert=True)

    async def finish_edit_mode(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Finish questionnaire editing and return to main menu"""
        query = update.callback_query
        user_id = update.effective_user.id
        if await self.check_cooldown(user_id):
            await query.answer()
            return
        
        try:
            # Finish edit mode
            result = await self.questionnaire_manager.finish_edit_mode(user_id)
            if result["status"] == "edit_finished":
                # Clear questionnaire_active flag
                user_context = context.user_data.get(user_id, {})
                user_context.pop('questionnaire_active', None)
                context.user_data[user_id] = user_context
                
                await query.answer("✅ ویرایش با موفقیت ذخیره شد!", show_alert=True)
                # Return to main menu
                await self.back_to_user_menu(update, context)
            else:
                await query.edit_message_text(f"❌ خطا در ذخیره تغییرات: {result['message']}")
                
        except Exception as e:
            logger.error(f"Error in finish_edit_mode for user {user_id}: {e}")
            await query.edit_message_text("❌ خطا در ذخیره تغییرات.")

    async def get_user_approved_courses(self, user_id: int) -> list:
        """Get all courses that a user has approved payments for"""
        try:
            bot_data = await self.data_manager.load_data('bot_data')
            payments = bot_data.get('payments', {})
            
            user_courses = []
            for payment_id, payment_data in payments.items():
                if (payment_data.get('user_id') == user_id and 
                    payment_data.get('status') == 'approved'):
                    course_type = payment_data.get('course_type')
                    if course_type and course_type not in user_courses:
                        user_courses.append(course_type)
            
            return user_courses
        except Exception as e:
            error_logger.error(f"Error getting user approved courses for user {user_id}: {e}", exc_info=True)
            return []

    async def show_course_selection_for_program(self, update: Update, context: ContextTypes.DEFAULT_TYPE, courses: list) -> None:
        """Show course selection for program viewing when user has multiple courses"""
        try:
            message = """📋 برنامه‌های تمرینی شما

شما برای چندین دوره ثبت‌نام کرده‌اید. لطفاً دوره‌ای را که می‌خواهید برنامه آن را مشاهده کنید انتخاب کنید:"""

            keyboard = []
            for course_code in courses:
                course_name = self.get_course_name_farsi(course_code)
                keyboard.append([InlineKeyboardButton(course_name, callback_data=f'view_program_{course_code}')])
            
            keyboard.extend([
                [InlineKeyboardButton("📊 وضعیت من", callback_data='my_status')],
                [InlineKeyboardButton("🔙 منوی اصلی", callback_data='back_to_user_menu')]
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.callback_query.edit_message_text(message, reply_markup=reply_markup)
            
        except Exception as e:
            error_logger.error(f"Error in show_course_selection_for_program for user {update.effective_user.id}: {e}", exc_info=True)

    async def show_training_program(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_data: dict = None, course_code: str = None) -> None:
        """Show user's training program - displays all purchased courses and their assigned main plans"""
        try:
            user_id = update.effective_user.id
            
            # If no user_data provided, load it
            if user_data is None:
                user_data = await self.data_manager.get_user_data(user_id)
            
            # Get all purchased courses
            purchased_courses = await self.get_user_purchased_courses(user_id)
            
            if not purchased_courses:
                message = """📋 برنامه‌های شما

❌ شما هنوز هیچ دوره‌ای خریداری نکرده‌اید.

برای خرید دوره جدید از دکمه زیر استفاده کنید:"""
                keyboard = [
                    [InlineKeyboardButton("🛒 خرید دوره جدید", callback_data='new_course')],
                    [InlineKeyboardButton("🔙 منوی اصلی", callback_data='back_to_user_menu')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.callback_query.edit_message_text(message, reply_markup=reply_markup)
                return
            
            # If specific course requested, show only that course
            if course_code and course_code in purchased_courses:
                await self.show_single_course_program(update, context, user_data, course_code)
                return
            
            # Show all purchased courses and their main plans
            message = f"""📋 برنامه‌های شما

شما مالک {len(purchased_courses)} دوره هستید:

"""
            
            keyboard = []
            has_any_plan = False
            
            for course in purchased_courses:
                course_name = self.get_course_name_farsi(course)
                main_plan = await self.get_main_plan_for_user(str(user_id), course)
                
                if main_plan:
                    has_any_plan = True
                    plan_title = main_plan.get('title', 'برنامه بدون عنوان')
                    plan_date = main_plan.get('created_at', '')[:10] if main_plan.get('created_at') else 'نامشخص'
                    
                    message += f"✅ **{course_name}**\n"
                    message += f"   📋 برنامه اختصاصی: {plan_title}\n"
                    message += f"   📅 تاریخ: {plan_date}\n\n"
                    
                    # Add button to view/download this course's plan
                    keyboard.append([InlineKeyboardButton(f"📋 دریافت برنامه {course_name}", callback_data=f'get_main_plan_{course}')])
                else:
                    message += f"⏳ **{course_name}**\n"
                    message += f"   📋 برنامه اختصاصی در حال آماده‌سازی...\n\n"
                    
                    # Add button to view course details
                    keyboard.append([InlineKeyboardButton(f"👁️ مشاهده {course_name}", callback_data=f'view_program_{course}')])
            
            if has_any_plan:
                message += "💡 برای دریافت برنامه‌های آماده، روی دکمه‌های بالا کلیک کنید.\n"
                message += "📞 برای سوالات بیشتر با @DrBohloul تماس بگیرید."
            else:
                message += "⏳ برنامه‌های اختصاصی شما در حال آماده‌سازی است.\n"
                message += "📞 برای پیگیری با @DrBohloul تماس بگیرید."
            
            # Add general buttons
            keyboard.extend([
                [InlineKeyboardButton("📊 وضعیت من", callback_data='my_status')],
                [InlineKeyboardButton("🔙 منوی اصلی", callback_data='back_to_user_menu')]
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            error_logger.error(f"Error in show_training_program for user {user_id}: {e}", exc_info=True)
            await admin_error_handler.handle_admin_error(
                update, context, e, "show_training_program", update.effective_user.id
            )
    
    async def show_single_course_program(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_data: dict, course_code: str) -> None:
        """Show training program for a specific course"""
        try:
            user_id = update.effective_user.id
            course_name = self.get_course_name_farsi(course_code)
            
            # Check if user has a main plan assigned for this course
            main_plan = await self.get_main_plan_for_user(str(user_id), course_code)
            
            # Handle nutrition plan differently
            if course_code == 'nutrition_plan':
                if main_plan:
                    message = f"""🥗 برنامه غذایی شما

دوره: {course_name}

⭐ برنامه اختصاصی شما آماده است!

📋 نام برنامه: {main_plan.get('title', 'برنامه غذایی')}
📅 تاریخ: {main_plan.get('created_at', '')[:10] if main_plan.get('created_at') else 'نامشخص'}

برای دریافت برنامه کامل لطفاً به پشتیبانی @DrBohloul پیام دهید یا از دکمه زیر استفاده کنید:"""
                else:
                    message = f"""🥗 برنامه غذایی شما

دوره: {course_name}

برنامه غذایی شخصی‌سازی شده شما آماده است!

این برنامه بر اساس نیازهای تغذیه‌ای بازیکنان فوتبال طراحی شده است.

برای دریافت برنامه کامل لطفاً به پشتیبانی @DrBohloul پیام دهید یا از دکمه زیر استفاده کنید:"""
            else:
                # Regular training courses
                if main_plan:
                    message = f"""📋 برنامه تمرینی شما

دوره: {course_name}

⭐ برنامه اختصاصی شما آماده است!

📋 نام برنامه: {main_plan.get('title', 'برنامه تمرینی')}
📅 تاریخ: {main_plan.get('created_at', '')[:10] if main_plan.get('created_at') else 'نامشخص'}

برای دریافت برنامه کامل لطفاً به پشتیبانی @DrBohloul پیام دهید یا از دکمه زیر استفاده کنید:"""
                else:
                    message = f"""📋 برنامه تمرینی شما

دوره: {course_name}

برنامه تمرینی شخصی‌سازی شده شما بر اساس پاسخ‌های پرسشنامه آماده شده است.

برای دریافت برنامه کامل لطفاً به پشتیبانی @DrBohloul پیام دهید یا از دکمه زیر استفاده کنید:"""
            
            # Add download button if main plan exists
            keyboard = []
            if main_plan:
                keyboard.append([InlineKeyboardButton("📋 دریافت برنامه", callback_data=f'get_main_plan_{course_code}')])
            
            keyboard.extend([
                [InlineKeyboardButton("🔙 همه برنامه‌ها", callback_data='view_program')],
                [InlineKeyboardButton("📊 وضعیت من", callback_data='my_status')],
                [InlineKeyboardButton("🏠 منوی اصلی", callback_data='back_to_user_menu')]
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.callback_query.edit_message_text(message, reply_markup=reply_markup)
            
        except Exception as e:
            error_logger.error(f"Error in show_single_course_program for user {user_id}: {e}", exc_info=True)
            await admin_error_handler.handle_admin_error(
                update, context, e, "show_single_course_program", update.effective_user.id
            )
            
    async def get_main_plan_for_user(self, user_id: str, course_code: str) -> dict:
        """Get the main plan assigned to a user for a specific course"""
        try:
            # Load main plan assignments
            main_plans_file = 'admin_data/main_plan_assignments.json'
            if not os.path.exists(main_plans_file):
                user_logger.debug(f"Main plans file not found: {main_plans_file}")
                return None
            
            with open(main_plans_file, 'r', encoding='utf-8') as f:
                main_plans = json.load(f)
            
            assignment_key = f"{user_id}_{course_code}"
            main_plan_id = main_plans.get(assignment_key)
            
            user_logger.debug(f"get_main_plan_for_user: user_id={user_id}, course_code={course_code}")
            user_logger.debug(f"Looking for assignment key: {assignment_key}")
            user_logger.debug(f"Available assignments: {list(main_plans.keys())}")
            user_logger.debug(f"Found plan ID: {main_plan_id}")
            
            if not main_plan_id:
                user_logger.debug(f"No main plan assigned for {assignment_key}")
                return None
            
            # Find the plan details
            plans_file = f'admin_data/course_plans/{course_code}.json'
            if not os.path.exists(plans_file):
                user_logger.debug(f"Course plans file not found: {plans_file}")
                return None
            
            with open(plans_file, 'r', encoding='utf-8') as f:
                all_plans = json.load(f)
            
            user_logger.debug(f"Searching for plan ID {main_plan_id} in {len(all_plans)} plans")
            
            # Find the specific plan
            for plan in all_plans:
                plan_id = plan.get('id')
                target_user = plan.get('target_user_id')
                user_logger.debug(f"Checking plan: id={plan_id}, target_user={target_user}")
                
                if plan.get('id') == main_plan_id:
                    # Check if this plan is for this user or general
                    if not target_user or str(target_user) == str(user_id):
                        user_logger.debug(f"Found matching main plan for user {user_id}: {plan.get('title')}")
                        return plan
                    else:
                        user_logger.debug(f"Plan found but target_user mismatch for user {user_id}: {target_user} != {user_id}")
            
            user_logger.debug(f"Plan ID {main_plan_id} not found in course plans for user {user_id}")
            return None
        except Exception as e:
            error_logger.error(f"Error getting main plan for user {user_id} course {course_code}: {e}", exc_info=True)
            return None
            
    async def handle_get_main_plan(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle user request to download their main plan"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        if await self.check_cooldown(user_id):
            return
        course_code = query.data.replace('get_main_plan_', '')
        
        main_plan = await self.get_main_plan_for_user(str(user_id), course_code)
        
        if not main_plan:
            await query.answer("❌ برنامه‌ای یافت نشد!", show_alert=True)
            return
        
        try:
            # Send the plan to user
            plan_content = main_plan.get('content')
            plan_content_type = main_plan.get('content_type', 'document')
            plan_title = main_plan.get('title', 'برنامه تمرینی')
            plan_filename = main_plan.get('filename', 'برنامه')
            
            if plan_content:
                caption = f"📋 {plan_title}\n\n💪 برنامه اختصاصی شما\n📄 فایل: {plan_filename}"
                
                if plan_content_type == 'photo':
                    await query.message.reply_photo(
                        photo=plan_content,
                        caption=caption
                    )
                else:  # document or any other type
                    await query.message.reply_document(
                        document=plan_content,
                        caption=caption
                    )
                
                await query.answer("✅ برنامه ارسال شد!", show_alert=True)
            else:
                await query.answer("❌ فایل برنامه یافت نشد!", show_alert=True)
        
        except Exception as e:
            error_logger.error(f"Error sending main plan to user {user_id}: {e}", exc_info=True)
            await query.answer("❌ خطا در ارسال برنامه!", show_alert=True)

    async def show_support_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show support contact information"""
        message = """📞 *اطلاعات تماس پشتیبانی*

برای دریافت پشتیبانی می‌توانید از روش‌های زیر استفاده کنید:

🔹 تلگرام: @DrBohloul
🔹 پشتیبانی فنی: از طریق همین ربات

ساعات پاسخگویی:
شنبه تا پنج‌شنبه: ۹ صبح تا ۶ عصر
جمعه: ۱۰ صبح تا ۲ ظهر"""
        
        keyboard = [
            [InlineKeyboardButton("🔙 بازگشت", callback_data='my_status')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.safe_edit_message(
            update.callback_query,
            message, 
            reply_markup=reply_markup, 
            parse_mode='Markdown'
        )

    def get_payment_status_text(self, status: str) -> str:
        """Convert payment status to Persian text"""
        status_map = {
            'pending_approval': '⏳ در انتظار تایید',
            'approved': '✅ تایید شده', 
            'rejected': '❌ رد شده',
            'none': '❌ پرداخت نشده'
        }
        return status_map.get(status, '❓ نامشخص')

    def get_course_name_farsi(self, course_code: str) -> str:
        """Convert course code to Persian course name"""
        course_map = {
            'in_person': 'دوره تمرین حضوری',
            'online': 'دوره تمرین آنلاین',
            'in_person_cardio': 'حضوری - تمرین هوازی سرعتی چابکی',
            'in_person_weights': 'حضوری - تمرین وزنه',
            'online_cardio': 'آنلاین - برنامه هوازی و کار با توپ',
            'online_weights': 'آنلاین - برنامه وزنه',
            'online_combo': 'آنلاین - برنامه ترکیبی (وزنه + هوازی)',
            'nutrition_plan': 'برنامه غذایی',
            'in_person_nutrition': 'حضوری - برنامه تغذیه',
            'online_nutrition': 'آنلاین - برنامه تغذیه'
        }
        return course_map.get(course_code, course_code if course_code else 'انتخاب نشده')

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle errors"""
        import traceback
        
        # Log the full traceback
        error_logger.error(f"Exception while handling an update: {context.error}", exc_info=True)
        
        # Print to console for debugging
        print(f"❌ ERROR: {context.error}")
        print(f"📋 TRACEBACK:\n{traceback.format_exc()}")
        
        if update and hasattr(update, 'effective_message'):
            try:
                await update.effective_message.reply_text(
                    "متاسفانه خطایی رخ داد. لطفا دوباره تلاش کنید یا با پشتیبانی تماس بگیرید."
                )
            except Exception:
                pass

def main():
    """Main function to run the bot"""
    if not Config.BOT_TOKEN:
        logging.error("BOT_TOKEN not found in environment variables!")
        print("Error: BOT_TOKEN not found!")
        print("Please create .env file with your bot token:")
        print("BOT_TOKEN=your_bot_token_here")
        return
    
    # Create bot instance
    bot = FootballCoachBot()
    
    # Create application
    application = Application.builder().token(Config.BOT_TOKEN).build()

    # Store bot instance in application context for access by admin_panel
    application.bot_data['bot_instance'] = bot

    # Add handlers
    application.add_handler(CommandHandler("start", bot.start))
    # Hidden admin command - works but not shown in menu
    application.add_handler(CommandHandler("admin", bot.admin_panel.admin_menu))
    application.add_handler(CommandHandler("add_admin", bot.admin_panel.add_admin_command))
    application.add_handler(CommandHandler("remove_admin", bot.admin_panel.remove_admin_command))
    
    application.add_handler(CallbackQueryHandler(bot.handle_main_menu, pattern='^(in_person|online|nutrition_plan)$'))
    application.add_handler(CallbackQueryHandler(bot.handle_course_details, pattern='^(in_person_cardio|in_person_weights|online_weights|online_cardio|online_combo)$'))
    application.add_handler(CallbackQueryHandler(bot.handle_payment, pattern='^payment_'))
    application.add_handler(CallbackQueryHandler(bot.handle_coupon_request, pattern='^coupon_'))
    application.add_handler(CallbackQueryHandler(bot.handle_questionnaire_choice, pattern='^q_answer_'))
    # Payment approval handlers - with more specific pattern to avoid conflicts with plan management
    application.add_handler(CallbackQueryHandler(bot.handle_payment_approval, pattern='^(approve_payment_|reject_payment_|view_user_\\d+$|allow_extra_receipt_)'))
    application.add_handler(CallbackQueryHandler(bot.handle_grant_receipt_approval, pattern='^grant_receipt_'))
    application.add_handler(CallbackQueryHandler(bot.handle_status_callbacks, pattern='^(my_status|check_payment_status|continue_questionnaire|restart_questionnaire|edit_questionnaire|view_program|contact_support||new_course|start_over|start_questionnaire|continue_photo_question|add_more_photos|view_program_.+)$'))
    # Nutrition form callback handlers
    application.add_handler(CallbackQueryHandler(bot.handle_nutrition_form_callbacks, pattern='^(nutrition_form_understood|nutrition_form_question)$'))
    # Edit mode navigation handlers
    application.add_handler(CallbackQueryHandler(bot.handle_edit_navigation, pattern='^(edit_prev|edit_next)$'))
    application.add_handler(CallbackQueryHandler(bot.finish_edit_mode, pattern='^finish_edit$'))
    application.add_handler(CallbackQueryHandler(bot.back_to_main, pattern='^back_to_main$'))
    application.add_handler(CallbackQueryHandler(bot.back_to_user_menu, pattern='^back_to_user_menu$'))
    application.add_handler(CallbackQueryHandler(bot.back_to_course_selection, pattern='^back_to_course_selection$'))
    application.add_handler(CallbackQueryHandler(bot.back_to_category, pattern='^back_to_(online|in_person)$'))
    # Admin coupon handlers (must come before generic admin_ handler)
    application.add_handler(CallbackQueryHandler(bot.admin_panel.handle_admin_callbacks, pattern='^(toggle_coupon_|delete_coupon_)'))
    
    # Main plan assignment handlers (must come before other patterns!)
    application.add_handler(CallbackQueryHandler(bot.admin_panel.handle_admin_callbacks, pattern='^(set_main_plan_|unset_main_plan_)'))
    
    # New person-centric plan management handlers (MUST come before legacy patterns!)
    application.add_handler(CallbackQueryHandler(bot.admin_panel.handle_admin_callbacks, pattern='^(user_plans_|manage_user_course_|upload_user_plan_|send_user_plan_|view_user_plan_|delete_user_plan_|send_latest_plan_|confirm_delete_|export_user_|users_page_)'))
    
    # Legacy plan management handlers 
    application.add_handler(CallbackQueryHandler(bot.admin_panel.handle_admin_callbacks, pattern='^(plan_course_|upload_plan_|send_plan_|view_plans_|send_to_user_|send_to_all_|view_plan_)'))
    
    # Generic admin handlers (catch remaining admin_ callbacks)
    application.add_handler(CallbackQueryHandler(bot.admin_panel.handle_admin_callbacks, pattern='^admin_'))
    
    # Skip plan description handler
    application.add_handler(CallbackQueryHandler(bot.admin_panel.handle_admin_callbacks, pattern='^skip_plan_description$'))
    
    # User plan management handlers
    application.add_handler(CallbackQueryHandler(bot.handle_get_main_plan, pattern='^get_main_plan_'))
    
    # Handle photo messages (payment receipts and questionnaire photos)
    application.add_handler(MessageHandler(filters.PHOTO, bot.handle_photo_input))
    
    # Handle document uploads (PDF for questionnaire, CSV for admin)
    application.add_handler(MessageHandler(filters.Document.ALL, bot.handle_document))
    
    # Handle other unsupported file types (individual handlers for better compatibility)
    application.add_handler(MessageHandler(filters.VIDEO, bot.handle_unsupported_file))
    application.add_handler(MessageHandler(filters.AUDIO, bot.handle_unsupported_file))
    application.add_handler(MessageHandler(filters.VOICE, bot.handle_unsupported_file))
    application.add_handler(MessageHandler(filters.ANIMATION, bot.handle_unsupported_file))
    application.add_handler(MessageHandler(filters.Sticker.ALL, bot.handle_unsupported_file))
    application.add_handler(MessageHandler(filters.VIDEO_NOTE, bot.handle_unsupported_file))
    application.add_handler(MessageHandler(filters.CONTACT, bot.handle_unsupported_file))
    application.add_handler(MessageHandler(filters.LOCATION, bot.handle_unsupported_file))
    
    # FIXED ARCHITECTURE: Smart text dispatcher - only process text in valid input states
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_text_input))
    
    # Add error handler
    application.add_error_handler(bot.error_handler)
    
    # Set up bot commands menu (only user-visible commands)
    async def setup_commands(app):
        from telegram import BotCommand
        commands = [
            BotCommand("start", "شروع ربات و نمایش منوی اصلی")
        ]
        await app.bot.set_my_commands(commands)
        
        # Initialize bot only (admin sync happens here)
        await bot.initialize()
    
    # Initialize commands on startup
    application.post_init = setup_commands
    
    # Start the bot
    logging.info("Starting Football Coach Bot...")
    logging.info("📱 Bot is ready to receive messages!")
    print("🤖 Football Coach Bot is starting...")
    print("📱 Bot is ready to receive messages!")

    try:
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        error_logger.error(f"Error running bot: {e}", exc_info=True)
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    main()
