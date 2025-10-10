from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from admin_manager import AdminManager
from data_manager import DataManager
from coupon_manager import CouponManager
from config import Config
from admin_error_handler import admin_error_handler
from admin_debugger import admin_debugger
import json
import csv
import io
import os
import zipfile
import tempfile
import shutil
import traceback
from datetime import datetime
import logging

# Setup logger for admin panel
logger = logging.getLogger(__name__)

class AdminPanel:
    def __init__(self):
        # Use bot_data.json for AdminManager to match main.py admin sync
        self.admin_manager = AdminManager(admins_file='bot_data.json')
        self.data_manager = DataManager()
        self.coupon_manager = CouponManager()
        self.admin_creating_coupons = set()  # Track which admins are creating coupons
    
    async def admin_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Redirect to unified admin hub - no separate menu"""
        user_id = update.effective_user.id
        
        if not await self.admin_manager.is_admin(user_id):
            await update.message.reply_text("❌ شما دسترسی ادمین ندارید.")
            return
        
        # Show the unified admin hub directly
        await self.show_admin_hub_for_command(update, context, user_id)
    
    async def handle_admin_callbacks(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle admin panel callbacks with comprehensive error handling"""
        query = update.callback_query
        user_id = update.effective_user.id
        
        try:
            await query.answer()
            
            # Log callback attempt for debugging
            await admin_debugger.log_callback_attempt(
                user_id, query.data, {"success": True, "update_id": update.update_id}
            )
            
            # Log admin action
            await admin_error_handler.log_admin_action(
                user_id, f"callback_query", {"callback_data": query.data}
            )
            
            if not await self.admin_manager.is_admin(user_id):
                await query.edit_message_text("❌ شما دسترسی ادمین ندارید.")
                return
            
            logger.info(f"Admin {user_id} triggered callback: {query.data}")
            
            # Main callback routing with comprehensive error handling
            await self._route_admin_callback(query, context, user_id)
            
        except Exception as e:
            # Log the error with full context
            await admin_debugger.log_callback_attempt(
                user_id, query.data, {"success": False, "error": str(e), "update_id": update.update_id}
            )
            
            # Handle the error gracefully
            error_handled = await admin_error_handler.handle_admin_error(
                update, context, e, f"callback_query:{query.data}", user_id
            )
            
            if not error_handled:
                # If error handler couldn't handle it, send a basic error message
                try:
                    await query.edit_message_text(
                        "❌ خطای غیرمنتظره رخ داد. لطفاً مجددا تلاش کنید.\n\n"
                        "اگر مشکل ادامه دارد، دستور /admin را مجددا اجرا کنید."
                    )
                except Exception:
                    pass  # Even error handling failed
                
                # Re-raise for logging at application level
                raise e

    async def _route_admin_callback(self, query, context: ContextTypes.DEFAULT_TYPE, user_id: int):
        """Route admin callbacks to appropriate handlers"""
        callback_data = query.data
        
        # Add debug logging for callback routing
        logger.debug(f"Routing callback: {callback_data}")
        
        # Main admin menu callbacks
        if callback_data == 'admin_menu':
            await self.show_admin_hub_for_command_query(query, user_id)
        elif callback_data == 'admin_stats':
            await self.show_statistics(query)
        elif callback_data == 'admin_users':
            await self.show_users_management(query)
        elif callback_data.startswith('users_page_'):
            page = int(callback_data.split('_')[2])
            await self.show_users_management(query, page)
        elif callback_data == 'admin_payments':
            await self.show_payments_management(query)
        elif callback_data == 'admin_export_menu':
            await self.show_export_menu(query)
        elif callback_data == 'admin_coupons':
            await self.show_coupon_management(query)
        elif callback_data == 'admin_plans':
            await self.show_plan_management(query)
        elif callback_data == 'admin_maintenance':
            await self.show_maintenance_menu(query)
        elif callback_data == 'validate_file_ids':
            await self.handle_validate_file_ids(query, context)
        elif callback_data == 'system_health_check':
            await self.handle_system_health_check(query)
        elif callback_data == 'cleanup_temp_files':
            await self.handle_cleanup_temp_files(query)
            
        # New plan management callbacks - Person-centric approach
        elif callback_data.startswith('user_plans_'):
            logger.info(f"🎯 ROUTING: user_plans_ -> {callback_data}")
            user_id = callback_data.split('_', 2)[2]
            await self.show_user_course_plans(query, user_id)
        elif callback_data.startswith('manage_user_course_'):
            logger.info(f"🎯 ROUTING: manage_user_course_ -> {callback_data}")
            parts = callback_data.split('_', 3)
            user_id, course_code = parts[3].split('_', 1)
            await self.show_user_course_plan_management_enhanced(query, user_id, course_code)
        elif callback_data.startswith('confirm_delete_'):
            logger.info(f"🎯 ROUTING: confirm_delete_ -> {callback_data}")
            # confirm_delete_USER_ID_COURSE_CODE_PLAN_ID
            parts = callback_data.replace('confirm_delete_', '').split('_')
            if len(parts) >= 4:
                user_id = parts[0]
                if len(parts) >= 5 and parts[1] == 'in' and parts[2] == 'person':
                    course_code = f"{parts[1]}_{parts[2]}_{parts[3]}"
                    plan_id = '_'.join(parts[4:])
                elif len(parts) >= 4 and parts[1] == 'online':
                    course_code = f"{parts[1]}_{parts[2]}"
                    plan_id = '_'.join(parts[3:])
                elif len(parts) >= 4 and parts[1] == 'nutrition' and parts[2] == 'plan':
                    course_code = f"{parts[1]}_{parts[2]}"  # nutrition_plan
                    plan_id = '_'.join(parts[3:])
                else:
                    course_code = parts[1]
                    plan_id = '_'.join(parts[2:])
                await self.handle_confirm_delete_user_plan(query, user_id, course_code, plan_id)
            else:
                await query.answer("❌ خطا در تجزیه دستور!")
        elif callback_data.startswith(('upload_user_plan_', 'send_user_plan_', 'view_user_plan_', 'delete_user_plan_', 'send_latest_plan_')):
            logger.info(f"🎯 ROUTING: new plan management callback -> {callback_data}")
            await self.handle_new_plan_callback_routing(query, context)
        
        # Main plan assignment callbacks
        elif callback_data.startswith('set_main_plan_'):
            parts = callback_data.replace('set_main_plan_', '').split('_')
            if len(parts) >= 3:
                user_id = parts[0]
                # Handle different course code formats
                if len(parts) >= 5 and parts[1] == 'in' and parts[2] == 'person':
                    course_code = f"{parts[1]}_{parts[2]}_{parts[3]}"
                    plan_id = '_'.join(parts[4:])
                elif len(parts) >= 4 and parts[1] == 'online':
                    course_code = f"{parts[1]}_{parts[2]}"
                    plan_id = '_'.join(parts[3:])
                elif len(parts) >= 4 and parts[1] == 'nutrition' and parts[2] == 'plan':
                    course_code = f"{parts[1]}_{parts[2]}"  # nutrition_plan
                    plan_id = '_'.join(parts[3:])
                else:
                    course_code = parts[1]
                    plan_id = '_'.join(parts[2:])
                await self.handle_set_main_plan(query, user_id, course_code, plan_id)
        elif callback_data.startswith('unset_main_plan_'):
            parts = callback_data.replace('unset_main_plan_', '').split('_')
            if len(parts) >= 3:
                user_id = parts[0]
                # Handle different course code formats
                if len(parts) >= 5 and parts[1] == 'in' and parts[2] == 'person':
                    course_code = f"{parts[1]}_{parts[2]}_{parts[3]}"
                    plan_id = '_'.join(parts[4:])
                elif len(parts) >= 4 and parts[1] == 'online':
                    course_code = f"{parts[1]}_{parts[2]}"
                    plan_id = '_'.join(parts[3:])
                elif len(parts) >= 4 and parts[1] == 'nutrition' and parts[2] == 'plan':
                    course_code = f"{parts[1]}_{parts[2]}"  # nutrition_plan
                    plan_id = '_'.join(parts[3:])
                else:
                    course_code = parts[1]
                    plan_id = '_'.join(parts[2:])
                await self.handle_unset_main_plan(query, user_id, course_code, plan_id)
            
        # Legacy plan management callbacks (keeping for backward compatibility)
        elif callback_data.startswith(('plan_course_', 'upload_plan_', 'send_plan_', 'view_plans_', 'send_to_user_', 'send_to_all_', 'view_plan_')):
            logger.info(f"Routing legacy plan management callback: {callback_data}")
            await self.handle_plan_callback_routing(query, context)
            
        # Export callbacks
        elif callback_data == 'admin_export_users':
            await self.export_users_csv(query)
        elif callback_data == 'admin_export_payments':
            await self.export_payments_csv(query)
        elif callback_data == 'admin_export_questionnaire':
            await self.export_questionnaire_csv(query)
        elif callback_data == 'admin_export_person':
            await self.show_completed_users_list(query)
        elif callback_data == 'admin_export_telegram':
            await self.export_telegram_csv(query)
        elif callback_data == 'admin_export_all':
            await self.export_all_data(query)
        elif callback_data == 'admin_template_users':
            await self.generate_users_template(query)
        elif callback_data == 'admin_template_payments':
            await self.generate_payments_template(query)
        elif callback_data.startswith('export_user_'):
            # Handle user-specific export
            export_user_id = callback_data.replace('export_user_', '')
            await self.export_user_personal_data(query, export_user_id, context)
        
        # Coupon management callbacks
        elif callback_data == 'admin_view_coupons':
            await self.show_coupons_list(query)
        elif callback_data == 'admin_create_coupon':
            await self.handle_create_coupon(query, user_id)
        elif callback_data == 'admin_toggle_coupon':
            await self.handle_toggle_coupon(query)
        elif callback_data == 'admin_delete_coupon':
            await self.handle_delete_coupon(query)
        elif callback_data.startswith('toggle_coupon_'):
            await self.process_toggle_coupon(query)
        elif callback_data.startswith('delete_coupon_'):
            await self.process_delete_coupon(query)
        
        # Admin management callbacks
        elif callback_data == 'admin_manage_admins':
            await self.show_admin_management(query, user_id)
        elif callback_data == 'admin_cleanup_non_env':
            await self.handle_cleanup_non_env_admins(query, user_id)
        elif callback_data.startswith('admin_add_admin_'):
            await self.handle_add_admin(query, user_id)
        elif callback_data.startswith('admin_remove_admin_'):
            await self.handle_remove_admin(query, user_id)
        
        # Plan upload management
        elif callback_data == 'skip_plan_description':
            await self.handle_skip_plan_description(query, context)
        
        # Navigation callbacks
        elif callback_data == 'admin_back_main':
            await self.back_to_admin_main(query, user_id)
        elif callback_data == 'admin_back_start':
            await self.back_to_admin_start(query, user_id)
        
        else:
            # Unknown callback - log for debugging
            logger.warning(f"Unknown admin callback: {callback_data}")
            await admin_error_handler.log_admin_action(
                user_id, "unknown_callback", {"callback_data": callback_data}
            )
            
            # Provide helpful feedback
            await query.edit_message_text(
                f"⚠️ دستور ناشناخته: {callback_data}\n\n"
                f"🔍 Debug Info:\n{admin_error_handler.get_callback_debug_info(callback_data)}\n\n"
                f"🔄 بازگشت به منوی اصلی...",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 منوی اصلی", callback_data='admin_back_main')
                ]])
            )

    async def show_debug_panel(self, query, admin_id: int):
        """Show admin debug panel"""
        try:
            # Generate debug report
            debug_report = await admin_debugger.create_debug_report(admin_id)
            error_summary = await admin_error_handler.get_error_summary(admin_id, limit=5)
            file_status = await admin_debugger.get_file_system_status()
            callback_test = await admin_debugger.test_callback_routing()
            
            keyboard = [
                [InlineKeyboardButton("🔍 تست کال‌بک", callback_data='admin_debug_test')],
                [InlineKeyboardButton("📊 گزارش کامل", callback_data='admin_debug_full')],
                [InlineKeyboardButton("🗑️ پاک کردن لاگ‌ها", callback_data='admin_debug_clear')],
                [InlineKeyboardButton("🔙 بازگشت", callback_data='admin_back_main')]
            ]
            
            text = f"""🔍 پنل دیباگ ادمین
            
{error_summary}

📁 وضعیت فایل‌ها:
{file_status}

🧪 تست کال‌بک:
{callback_test[:500]}..."""
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, reply_markup=reply_markup)
            
        except Exception as e:
            await admin_error_handler.handle_admin_error(
                query, None, e, "show_debug_panel", admin_id
            )
    
    async def handle_admin_user_mode(self, query, admin_id) -> None:
        """Allow admin to test user interface without losing admin privileges"""
        try:
            await query.edit_message_text(
                "🔄 تغییر به حالت کاربر...\n\n"
                "شما اکنون رابط کاربری عادی را مشاهده می‌کنید.\n"
                "برای بازگشت به پنل ادمین از /start استفاده کنید.",
                reply_markup=None
            )
            
            # Import here to avoid circular imports  
            from main import FootballCoachBot
            
            # Create realistic mock objects
            class MockUser:
                def __init__(self, admin_id):
                    self.id = admin_id
                    self.first_name = "Admin"
                    self.username = "admin_test_mode"
                    self.is_bot = False
            
            class MockChat:
                def __init__(self, admin_id):
                    self.id = admin_id
                    self.type = "private"
            
            class MockMessage:
                def __init__(self, admin_id):
                    self.message_id = 1
                    self.date = None
                    self.chat = MockChat(admin_id)
                    self.from_user = MockUser(admin_id)
                    self.text = "/start"
                    
                async def reply_text(self, text, reply_markup=None, parse_mode=None):
                    # Send user interface to admin
                    await query.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
            
            class MockUpdate:
                def __init__(self, admin_id):
                    self.message = MockMessage(admin_id)
                    self.effective_user = MockUser(admin_id)
                    self.effective_chat = MockChat(admin_id)
                    self.callback_query = None
                    
            class MockContext:
                def __init__(self):
                    self.user_data = {}
                    self.chat_data = {}
                    self.bot_data = {}
                    self.application = None
                    self.bot = None
            
            # Show actual user interface with admin_mode bypass
            mock_update = MockUpdate(admin_id)
            mock_context = MockContext()
            
            # Create mock user data for a new user (empty data will trigger new_user status)
            mock_user_data = {
                'user_id': admin_id,
                'name': 'Admin',
                'username': 'admin_test_mode',
                'started_bot': False  # This will make them appear as a new user
            }
            
            bot = FootballCoachBot()
            # Use show_status_based_menu directly with admin_mode=True to bypass admin check
            await bot.show_status_based_menu(mock_update, mock_context, mock_user_data, "Admin", admin_mode=True)
            
        except Exception as e:
            # Log the specific error
            import traceback
            error_msg = f"Error in admin user mode: {str(e)}"
            print(f"❌ {error_msg}")
            print(traceback.format_exc())
            
            await query.message.reply_text(
                f"❌ خطا در نمایش حالت کاربر:\n{str(e)}\n\n"
                f"برای بازگشت به پنل ادمین از /start استفاده کنید."
            )
    
    async def show_statistics(self, query) -> None:
        """Show bot statistics"""
        try:
            # Load data from data_manager
            with open('bot_data.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            users = data.get('users', {})
            payments = data.get('payments', {})
            stats = data.get('statistics', {})
            
            total_users = len(users)
            total_payments = len(payments)
            # Only count approved payments for revenue calculation
            total_revenue = sum(payment.get('price', 0) for payment in payments.values() if payment.get('status') == 'approved')
            approved_payments = len([p for p in payments.values() if p.get('status') == 'approved'])
            pending_payments = len([p for p in payments.values() if p.get('status') == 'pending_approval'])
            rejected_payments = len([p for p in payments.values() if p.get('status') == 'rejected'])
            
            # Course statistics - Count actual payments by course type (not user course field)
            course_stats = {}
            for payment_data in payments.values():
                if payment_data.get('status') == 'approved':  # Only count approved payments
                    course = payment_data.get('course_type')
                    if course:
                        course_stats[course] = course_stats.get(course, 0) + 1
            
            stats_text = "📊 آمار کلی ربات:\n\n"
            stats_text += f"👥 تعداد کل کاربران: {total_users}\n"
            stats_text += f"💳 تعداد کل پرداخت‌ها: {total_payments}\n"
            stats_text += f"  ✅ تایید شده: {approved_payments}\n"
            stats_text += f"  ⏳ در انتظار: {pending_payments}\n"
            stats_text += f"  ❌ رد شده: {rejected_payments}\n"
            stats_text += f"💰 درآمد کل (تایید شده): {total_revenue:,} تومان\n\n"
            stats_text += "📚 آمار دوره‌ها:"
            
            for course, count in course_stats.items():
                course_name = {
                    'online_weights': 'وزنه آنلاین',
                    'online_cardio': 'هوازی آنلاین',
                    'in_person_cardio': 'حضوری هوازی',
                    'in_person_weights': 'حضوری وزنه',
                    'online_combo': 'آنلاین ترکیبی',
                    'nutrition_plan': 'برنامه تغذیه'
                }.get(course, course)
                stats_text += f"\n  • {course_name}: {count} نفر"
            
            keyboard = [
                [InlineKeyboardButton("🔄 بروزرسانی", callback_data='admin_stats')],
                [InlineKeyboardButton("🔙 بازگشت", callback_data='admin_back_main')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(stats_text, reply_markup=reply_markup)
            
        except Exception as e:
            await query.edit_message_text(f"❌ خطا در نمایش آمار: {str(e)}", 
                                        reply_markup=InlineKeyboardMarkup([
                                            [InlineKeyboardButton("🔙 بازگشت", callback_data='admin_back_main')]
                                        ]))
            # Load data from data_manager
            with open('bot_data.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            users = data.get('users', {})
            payments = data.get('payments', {})
            stats = data.get('statistics', {})
            
            total_users = len(users)
            total_payments = len(payments)
            # Only count approved payments for revenue calculation
            total_revenue = sum(payment.get('price', 0) for payment in payments.values() if payment.get('status') == 'approved')
            approved_payments = len([p for p in payments.values() if p.get('status') == 'approved'])
            pending_payments = len([p for p in payments.values() if p.get('status') == 'pending_approval'])
            rejected_payments = len([p for p in payments.values() if p.get('status') == 'rejected'])
            
            # Course statistics - Count actual payments by course type (not user course field)  
            course_stats = {}
            for payment_data in payments.values():
                if payment_data.get('status') == 'approved':  # Only count approved payments
                    course = payment_data.get('course_type')
                    if course:
                        course_stats[course] = course_stats.get(course, 0) + 1
            
            stats_text = "📊 آمار کلی ربات:\n\n"
            stats_text += f"👥 تعداد کل کاربران: {total_users}\n"
            stats_text += f"💳 تعداد کل پرداخت‌ها: {total_payments}\n"
            stats_text += f"  ✅ تایید شده: {approved_payments}\n"
            stats_text += f"  ⏳ در انتظار: {pending_payments}\n"
            stats_text += f"  ❌ رد شده: {rejected_payments}\n"
            stats_text += f"💰 درآمد کل (تایید شده): {total_revenue:,} تومان\n\n"
            stats_text += "📚 آمار دوره‌ها:"
            
            for course, count in course_stats.items():
                course_name = {
                    'online_weights': 'وزنه آنلاین',
                    'online_cardio': 'هوازی آنلاین', 
                    'online_combo': 'ترکیبی آنلاین',
                    'in_person_cardio': 'هوازی حضوری',
                    'in_person_weights': 'وزنه حضوری',
                    'nutrition_plan': 'برنامه غذایی'
                }.get(course, course)
                
                stats_text += f"\n• {course_name}: {count} نفر"
            
            keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی اصلی ادمین", callback_data='admin_back_main')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(stats_text, reply_markup=reply_markup)
            
        except Exception as e:
            await query.edit_message_text(f"❌ خطا در نمایش آمار: {str(e)}")
    
    async def show_admin_management(self, query, user_id: int) -> None:
        """Show admin management panel"""
        if not await self.admin_manager.can_add_admins(user_id):
            await query.edit_message_text("❌ شما دسترسی مدیریت ادمین‌ها را ندارید.")
            return
        
        from config import Config
        is_super = await self.admin_manager.is_super_admin(user_id)
        env_admin_ids = Config.get_admin_ids() or []
        
        text = "🔐 مدیریت ادمین‌ها:\n\n"
        
        env_admins = []
        manual_admins = []
        
        # Detect actual mode by checking if database admin data is available
        try:
            db_admins = await self.admin_manager.get_all_admins()
            # If this succeeds and returns data, we're in database mode
            using_database = len(db_admins) > 0
        except:
            # If it fails, we're in JSON mode
            using_database = False
        
        if using_database:
            # Database mode - use AdminManager
            admins = db_admins
            
            for admin in admins:
                admin_type = "🔥 سوپر ادمین" if admin['is_super_admin'] else "👤 ادمین"
                admin_info = f"{admin_type}: {admin['id']}"
                
                # Check if this is an environment admin
                admin_perms = admin.get('permissions', {})
                if (admin_perms.get('added_by') == 'config_sync' or 
                    int(admin['id']) in env_admin_ids):
                    admin_info += " 🌍 (از فایل تنظیمات)"
                    env_admins.append(admin_info)
                else:
                    admin_info += " 🤝 (اضافه شده دستی)"
                    manual_admins.append(admin_info)
        else:
            # JSON mode - use DataManager
            admins_data = await self.data_manager.load_data('admins')
            
            if isinstance(admins_data, dict):
                # Convert dict format to list for processing
                for user_id_str, admin_data in admins_data.items():
                    admin_id = int(user_id_str)
                    admin_type = "🔥 سوپر ادمین" if admin_data.get('is_super_admin') else "👤 ادمین"
                    admin_info = f"{admin_type}: {admin_id}"
                    
                    # Check if this is an environment admin
                    is_env_admin = (
                        admin_data.get('added_by') == 'env_sync' or 
                        admin_data.get('env_admin') == True or
                        admin_data.get('synced_from_config') == True or
                        admin_data.get('force_synced') == True or
                        admin_id in env_admin_ids
                    )
                    
                    if is_env_admin:
                        admin_info += " 🌍 (از فایل تنظیمات)"
                        env_admins.append(admin_info)
                    else:
                        admin_info += " 🤝 (اضافه شده دستی)"
                        manual_admins.append(admin_info)
            else:
                # List format
                for admin in admins_data:
                    admin_id = admin.get('user_id')
                    admin_type = "🔥 سوپر ادمین" if admin.get('is_super_admin') else "👤 ادمین"
                    admin_info = f"{admin_type}: {admin_id}"
                    
                    # Check if this is an environment admin
                    is_env_admin = (
                        admin.get('added_by') == 'env_sync' or 
                        admin.get('env_admin') == True or
                        admin.get('synced_from_config') == True or
                        admin.get('force_synced') == True or
                        admin_id in env_admin_ids
                    )
                    
                    if is_env_admin:
                        admin_info += " 🌍 (از فایل تنظیمات)"
                        env_admins.append(admin_info)
                    else:
                        admin_info += " 🤝 (اضافه شده دستی)"
                        manual_admins.append(admin_info)
        
        for admin_info in env_admins:
            text += admin_info + "\n"
        for admin_info in manual_admins:
            text += admin_info + "\n"
        
        text += "\n💡 برای افزودن ادمین جدید، از دستور زیر استفاده کنید:\n"
        text += "/add_admin [USER_ID]\n\n"
        text += "💡 برای حذف ادمین:\n"
        text += "/remove_admin [USER_ID]"
        
        keyboard = []
        
        # Add cleanup button for super admins (always show for super admins for testing)
        if is_super:
            keyboard.append([InlineKeyboardButton("🧹 پاک کردن ادمین‌های غیر محیطی", callback_data='admin_cleanup_non_env')])
        
        keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی اصلی ادمین", callback_data='admin_back_main')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup)
    
    async def show_users_management(self, query, page: int = 0) -> None:
        """Show users management with pagination and safe formatting"""
        try:
            with open('bot_data.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            users = data.get('users', {})
            
            # Convert to list for pagination
            users_list = list(users.items())
            users_list.reverse()  # Show newest first
            
            # Pagination logic
            users_per_page = 10
            total_users = len(users_list)
            total_pages = max(1, (total_users + users_per_page - 1) // users_per_page)
            current_page = max(0, min(page, total_pages - 1))
            
            start_idx = current_page * users_per_page
            end_idx = start_idx + users_per_page
            page_users = users_list[start_idx:end_idx]
            
            text = "👥 مدیریت کاربران:\n\n"
            text += f"📊 تعداد کل: {total_users} کاربر\n"
            text += f"📄 صفحه {current_page + 1} از {total_pages}\n\n"
            
            if page_users:
                text += "📋 فهرست کاربران:\n"
                for user_id, user_data in page_users:
                    name = user_data.get('name', 'نامشخص')
                    username = user_data.get('username', '')
                    course = user_data.get('course', 'انتخاب نشده')
                    
                    # Safely escape name and username for Markdown
                    safe_name = self._escape_markdown_v2(name) if name else 'نامشخص'
                    
                    # Create clickable profile link with safe formatting
                    if username:
                        # Remove @ if present and create safe username
                        clean_username = username.replace('@', '').replace('_', '\\_')
                        profile_link = f"[{safe_name}](https://t.me/{clean_username})"
                    else:
                        profile_link = f"[{safe_name}](tg://user?id={user_id})"
                    
                    # Translate course name
                    course_name = self._get_course_name_farsi(course)
                    
                    text += f"• {profile_link}\n"
                    text += f"  🆔 ID: `{user_id}`\n"
                    text += f"  📚 دوره: {course_name}\n\n"
            else:
                text += "هیچ کاربری یافت نشد.\n"
            
            # Create pagination buttons
            keyboard = []
            
            # Navigation row
            nav_row = []
            if current_page > 0:
                nav_row.append(InlineKeyboardButton("⬅️ قبلی", callback_data=f'users_page_{current_page - 1}'))
            if current_page < total_pages - 1:
                nav_row.append(InlineKeyboardButton("بعدی ➡️", callback_data=f'users_page_{current_page + 1}'))
            
            if nav_row:
                keyboard.append(nav_row)
            
            # Back button
            keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی اصلی ادمین", callback_data='admin_back_main')])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='MarkdownV2', disable_web_page_preview=True)
            
        except Exception as e:
            logger.error(f"Error in show_users_management: {e}")
            await query.edit_message_text(
                f"❌ خطا در نمایش کاربران:\n\n"
                f"جزئیات: {str(e)}\n\n"
                f"🔄 لطفاً دوباره تلاش کنید یا با مدیر سیستم تماس بگیرید.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_back_main')]])
            )
    
    async def show_payments_management(self, query) -> None:
        """Show payments management"""
        try:
            with open('bot_data.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            payments = data.get('payments', {})
            
            text = "💳 مدیریت پرداخت‌ها:\n\n"
            text += f"📊 تعداد کل: {len(payments)} پرداخت\n"
            
            # Only count approved payments for revenue calculation
            approved_payments = [p for p in payments.values() if p.get('status') == 'approved']
            total_revenue = sum(payment.get('price', 0) for payment in approved_payments)
            text += f"💰 درآمد کل (تایید شده): {total_revenue:,} تومان\n\n"
            
            # Show recent 5 payments
            recent_payments = list(payments.items())[-5:]
            
            text += "🆕 آخرین پرداخت‌ها:\n"
            for payment_id, payment_data in recent_payments:
                user_id = payment_data.get('user_id', 'نامشخص')
                price = payment_data.get('price', 0)
                course_type = payment_data.get('course_type', 'نامشخص')
                # Translate course type to Persian name
                course_name = {
                    'online_weights': 'وزنه آنلاین',
                    'online_cardio': 'هوازی آنلاین', 
                    'online_combo': 'ترکیبی آنلاین',
                    'in_person_cardio': 'هوازی حضوری',
                    'in_person_weights': 'وزنه حضوری',
                    'nutrition_plan': 'برنامه غذایی'
                }.get(course_type, course_type)
                text += f"• {user_id} - {price:,} تومان ({course_name})\n"
            
            keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی اصلی ادمین", callback_data='admin_back_main')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(text, reply_markup=reply_markup)
            
        except Exception as e:
            await query.edit_message_text(f"❌ خطا: {str(e)}")
    
    async def back_to_admin_main(self, query, user_id: int) -> None:
        """Return to unified admin command hub"""
        # Clear admin-specific input states when navigating back to main admin
        from admin_error_handler import admin_error_handler
        await admin_error_handler.clear_admin_input_states(self, user_id, "back_to_admin_main")
        
        await self.show_unified_admin_panel(query, user_id)
    
    async def back_to_admin_start(self, query, user_id: int) -> None:
        """Return to main admin hub - the unified admin command center"""
        await self.show_unified_admin_panel(query, user_id)
    
    async def back_to_manage_admins(self, query, user_id: int) -> None:
        """Return to admin management menu"""
        await self.show_admin_management(query)
    
    async def back_to_stats_menu(self, query, user_id: int) -> None:
        """Return to statistics menu"""
        await self.show_statistics(query)
    
    async def back_to_users_menu(self, query, user_id: int) -> None:
        """Return to users management menu"""
        await self.show_user_management(query)
    
    async def back_to_payments_menu(self, query, user_id: int) -> None:
        """Return to payments management menu"""
        await self.show_payment_management(query)
    
    async def back_to_export_menu(self, query, user_id: int) -> None:
        """Return to export menu"""
        await self.show_export_menu(query)
    
    async def back_to_coupons_menu(self, query, user_id: int) -> None:
        """Return to coupons management menu"""
        await self.show_coupon_management(query)
    
    async def show_user_management(self, query) -> None:
        """Show user management menu"""
        await self.show_users_management(query)
    
    async def show_payment_management(self, query) -> None:
        """Show payment management menu - placeholder that redirects to payments"""
        await self.show_payments_management(query)
    
    async def show_unified_admin_panel(self, query, user_id: int) -> None:
        """Unified admin command hub - the ONLY admin panel"""
        is_super = await self.admin_manager.is_super_admin(user_id)
        can_manage_admins = await self.admin_manager.can_add_admins(user_id)
        user_name = query.from_user.first_name or "ادمین"
        
        keyboard = [
            [InlineKeyboardButton("📊 آمار و گزارشات", callback_data='admin_stats'),
             InlineKeyboardButton("👥 مدیریت کاربران", callback_data='admin_users')],
            [InlineKeyboardButton("💳 مدیریت پرداخت‌ها", callback_data='admin_payments'),
             InlineKeyboardButton(" اکسپورت داده‌ها", callback_data='admin_export_menu')],
            [InlineKeyboardButton("🎟️ مدیریت کوپن", callback_data='admin_coupons'),
             InlineKeyboardButton("📋 مدیریت برنامه‌ها", callback_data='admin_plans')],
            [InlineKeyboardButton("🔧 تعمیر و نگهداری", callback_data='admin_maintenance')]
        ]
        
        if can_manage_admins:
            keyboard.append([InlineKeyboardButton("🔐 مدیریت ادمین‌ها", callback_data='admin_manage_admins')])
        
        keyboard.append([InlineKeyboardButton("👤 حالت کاربر", callback_data='admin_user_mode')])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        admin_type = "🔥 سوپر ادمین" if is_super else "👤 ادمین"
        welcome_text = f"🎛️ پنل مدیریت\n\nسلام {user_name}! 👋\n{admin_type} - مرکز فرماندهی ربات:\n\n📋 همه ابزارهای مدیریت در یک مکان"
        
        await query.edit_message_text(welcome_text, reply_markup=reply_markup)

    async def show_admin_hub_for_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int) -> None:
        """Show the unified admin hub when called from command (/admin)"""
        is_super = await self.admin_manager.is_super_admin(user_id)
        can_manage_admins = await self.admin_manager.can_add_admins(user_id)
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

    async def show_admin_hub_for_command_query(self, query, user_id: int) -> None:
        """Show the unified admin hub when called from callback query (for back buttons)"""
        is_super = await self.admin_manager.is_super_admin(user_id)
        can_manage_admins = await self.admin_manager.can_add_admins(user_id)
        user_name = query.from_user.first_name or "ادمین"
        
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
        
        await query.edit_message_text(welcome_text, reply_markup=reply_markup)

    async def add_admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /add_admin command"""
        user_id = update.effective_user.id
        
        if not await self.admin_manager.can_add_admins(user_id):
            await update.message.reply_text("❌ شما دسترسی افزودن ادمین ندارید.")
            return
        
        if not context.args:
            await update.message.reply_text("❌ لطفا ID کاربر را وارد کنید:\n/add_admin 123456789")
            return
        
        try:
            new_admin_id = int(context.args[0])
            
            success = await self.admin_manager.add_admin(new_admin_id, user_id)
            
            if success:
                await update.message.reply_text(f"✅ کاربر {new_admin_id} به عنوان ادمین اضافه شد.")
            else:
                await update.message.reply_text("❌ خطا در افزودن ادمین.")
                
        except ValueError:
            await update.message.reply_text("❌ ID وارد شده معتبر نیست.")
    
    async def remove_admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /remove_admin command"""
        user_id = update.effective_user.id
        
        if not await self.admin_manager.can_remove_admins(user_id):
            await update.message.reply_text("❌ شما دسترسی حذف ادمین ندارید.")
            return
        
        if not context.args:
            await update.message.reply_text("❌ لطفا ID ادمین را وارد کنید:\n/remove_admin 123456789")
            return
        
        try:
            admin_id = int(context.args[0])
            
            if await self.admin_manager.is_super_admin(admin_id):
                await update.message.reply_text("❌ نمی‌توان سوپر ادمین را حذف کرد.")
                return
            
            success = await self.admin_manager.remove_admin(admin_id, user_id)
            
            if success:
                await update.message.reply_text(f"✅ ادمین {admin_id} حذف شد.")
            else:
                await update.message.reply_text("❌ خطا در حذف ادمین.")
                
        except ValueError:
            await update.message.reply_text("❌ ID وارد شده معتبر نیست.")
    
    async def handle_cleanup_non_env_admins(self, query, user_id: int) -> None:
        """Handle cleanup of non-environment admins (super admin only)"""
        if not await self.admin_manager.is_super_admin(user_id):
            await query.edit_message_text("❌ فقط سوپر ادمین‌ها می‌توانند این عملیات را انجام دهند.")
            return
        
        try:
            from config import Config
            
            if Config.USE_DATABASE:
                # Database mode cleanup
                result = await self.admin_manager.cleanup_non_env_admins(user_id)
                removed_count = result['removed']
                removal_details = result['details']
                total_checked = result['total_checked']
                
                if removed_count == 0:
                    await query.edit_message_text(
                        "✅ هیچ ادمین غیر محیطی برای حذف یافت نشد.\n\n"
                        "🔙 بازگشت به مدیریت ادمین‌ها",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به مدیریت ادمین‌ها", callback_data='admin_back_to_manage_admins')]])
                    )
                    return
                
                result_text = f"🧹 پاکسازی ادمین‌های غیر محیطی تکمیل شد!\n\n"
                result_text += f"📊 نتایج:\n"
                result_text += f"• حذف شده: {removed_count}\n"
                result_text += f"• کل ادمین‌های بررسی شده: {total_checked}\n\n"
                
                if removal_details:
                    result_text += "ادمین‌های حذف شده:\n"
                    for detail in removal_details[:10]:  # Show first 10
                        result_text += f"• {detail}\n"
                    
                    if len(removal_details) > 10:
                        result_text += f"• ... و {len(removal_details) - 10} مورد دیگر\n"
                
            else:
                # JSON mode cleanup
                admins_data = await self.data_manager.load_data('admins')
                
                # Identify non-environment admins
                non_env_admins = []
                env_admin_ids = Config.get_admin_ids() or []
                
                # Convert admins_data dict to list format for processing
                if isinstance(admins_data, dict):
                    # Convert from dict format {user_id: admin_data} to list format
                    admins_list = []
                    for user_id, admin_data in admins_data.items():
                        admin_info = admin_data.copy()
                        admin_info['user_id'] = int(user_id)
                        admins_list.append(admin_info)
                    admins_data = admins_list
                
                for admin in admins_data:
                    admin_id = admin.get('user_id')
                    
                    # Skip if this is an environment admin (check multiple possible flags)
                    is_env_admin = (
                        admin.get('added_by') == 'env_sync' or 
                        admin.get('env_admin') == True or
                        admin.get('synced_from_config') == True or
                        admin.get('force_synced') == True or
                        admin_id in env_admin_ids
                    )
                    
                    if is_env_admin:
                        continue
                    
                    # Skip super admins for safety
                    if admin.get('is_super_admin'):
                        continue
                        
                    non_env_admins.append(admin)
                
                if not non_env_admins:
                    await query.edit_message_text(
                        "✅ هیچ ادمین غیر محیطی برای حذف یافت نشد.\n\n"
                        "🔙 بازگشت به مدیریت ادمین‌ها",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به مدیریت ادمین‌ها", callback_data='admin_back_to_manage_admins')]])
                    )
                    return
                
                # Remove non-environment admins
                if isinstance(await self.data_manager.load_data('admins'), dict):
                    # Convert back to dict format for saving
                    remaining_admins_dict = {}
                    for admin in admins_data:
                        if admin not in non_env_admins:
                            remaining_admins_dict[str(admin['user_id'])] = admin
                    
                    await self.data_manager.save_data('admins', remaining_admins_dict)
                else:
                    # List format
                    remaining_admins = [
                        admin for admin in admins_data 
                        if admin not in non_env_admins
                    ]
                    await self.data_manager.save_data('admins', remaining_admins)
                
                removed_count = len(non_env_admins)
                
                result_text = f"🧹 پاکسازی ادمین‌های غیر محیطی تکمیل شد!\n\n"
                result_text += f"📊 نتایج:\n"
                result_text += f"• حذف شده: {removed_count}\n"
                result_text += f"• کل ادمین‌های بررسی شده: {len(non_env_admins)}\n\n"
                
                if non_env_admins:
                    result_text += "ادمین‌های حذف شده:\n"
                    for admin in non_env_admins[:10]:  # Show first 10
                        result_text += f"• {admin.get('user_id')}\n"
                    
                    if len(non_env_admins) > 10:
                        result_text += f"• ... و {len(non_env_admins) - 10} مورد دیگر\n"
            
            result_text += "\n🌍 ادمین‌های محیطی (از فایل .env) دست نخورده باقی ماندند."
            
            keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_manage_admins')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(result_text, reply_markup=reply_markup)
            
        except Exception as e:
            await query.edit_message_text(
                f"❌ خطا در پاکسازی ادمین‌ها: {str(e)}\n\n"
                "🔙 بازگشت به مدیریت ادمین‌ها",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به مدیریت ادمین‌ها", callback_data='admin_back_to_manage_admins')]])
            )
    
    async def get_id_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /id command to show user's ID"""
        user_id = update.effective_user.id
        username = update.effective_user.username
        first_name = update.effective_user.first_name
        
        is_admin = await self.admin_manager.is_admin(user_id)
        is_super = await self.admin_manager.is_super_admin(user_id)
        
        if is_super:
            role = "🔥 سوپر ادمین"
        elif is_admin:
            role = "👤 ادمین"
        else:
            role = "👤 کاربر عادی"
        
        text = f"""🆔 اطلاعات شما:

{role}
📱 Chat ID: `{user_id}`
👤 نام: {first_name or 'نامشخص'}
🔗 نام کاربری: @{username or 'ندارد'}"""
        
        await update.message.reply_text(text, parse_mode='Markdown')

    async def admin_menu_callback(self, query) -> None:
        """Redirect to unified admin panel - no separate menu"""
        user_id = query.from_user.id
        await self.show_unified_admin_panel(query, user_id)
    
    async def show_pending_payments(self, query) -> None:
        """Show pending payments for quick admin access"""
        try:
            with open('bot_data.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            payments = data.get('payments', {})
            pending = {k: v for k, v in payments.items() if v.get('status') == 'pending_approval'}
            
            if not pending:
                text = "✅ هیچ پرداخت معلقی وجود ندارد!"
            else:
                text = f"⏳ پرداخت‌های معلق ({len(pending)} مورد):\n\n"
                for payment_id, payment in list(pending.items())[:5]:  # Show max 5
                    user_name = payment.get('user_name', 'نامشخص')
                    amount = payment.get('price', 0)
                    course = payment.get('course', 'نامشخص')
                    text += f"👤 {user_name} - {course}\n💰 {amount:,} تومان\n\n"
                
                if len(pending) > 5:
                    text += f"... و {len(pending) - 5} مورد دیگر"
            
            keyboard = [
                [InlineKeyboardButton("💳 مدیریت کامل پرداخت‌ها", callback_data='admin_payments')],
                [InlineKeyboardButton("🔙 منوی اصلی ادمین", callback_data='admin_back_main')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(text, reply_markup=reply_markup)
            
        except Exception as e:
            await query.edit_message_text(f"❌ خطا در بارگیری پرداخت‌ها: {str(e)}")
    
    # 📥 EXPORT FUNCTIONALITY
    async def show_export_menu(self, query) -> None:
        """Show export options menu"""
        text = """📥 اکسپورت

انتخاب کنید:"""
        
        keyboard = [
            [InlineKeyboardButton("📤 صادرات کاربران (CSV)", callback_data='admin_export_users')],
            [InlineKeyboardButton("📤 صادرات پرداخت‌ها (CSV)", callback_data='admin_export_payments')],
            [InlineKeyboardButton("📤 صادرات پرسشنامه (CSV)", callback_data='admin_export_questionnaire')],
            [InlineKeyboardButton("📤 صادرات مدارک شخص خاص", callback_data='admin_export_person')],
            [InlineKeyboardButton("📤 صادرات تلگرام‌ها (CSV)", callback_data='admin_export_telegram')],
            [InlineKeyboardButton("📤 پشتیبان کامل (JSON)", callback_data='admin_export_all')],
            [InlineKeyboardButton("📋 دانلود نمونه کاربران", callback_data='admin_template_users')],
            [InlineKeyboardButton("📋 دانلود نمونه پرداخت‌ها", callback_data='admin_template_payments')],
            [InlineKeyboardButton("🔙 بازگشت", callback_data='admin_back_main')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup)

    async def export_users_csv(self, query) -> None:
        """Export users data to CSV format"""
        try:
            with open('bot_data.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            users = data.get('users', {})
            
            if not users:
                await query.edit_message_text(
                    "📭 هیچ کاربری برای صادرات وجود ندارد!",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 بازگشت", callback_data='admin_export_menu')]
                    ])
                )
                return
            
            # Create CSV content
            output = io.StringIO()
            writer = csv.writer(output)
            
            # CSV Headers
            headers = [
                'user_id', 'name', 'username', 'course_selected', 'payment_status',
                'questionnaire_completed', 'registration_date', 'last_interaction'
            ]
            writer.writerow(headers)
            
            # Write user data
            for user_id, user_data in users.items():
                row = [
                    user_id,
                    user_data.get('name', ''),
                    user_data.get('username', ''),
                    user_data.get('course_selected', ''),
                    user_data.get('payment_status', ''),
                    user_data.get('questionnaire_completed', False),
                    user_data.get('last_updated', ''),
                    user_data.get('last_interaction', '')
                ]
                writer.writerow(row)
            
            csv_content = output.getvalue()
            
            # Send CSV file
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"users_export_{timestamp}.csv"
            
            await query.message.reply_document(
                document=io.BytesIO(csv_content.encode('utf-8')),
                filename=filename,
                caption=f"📤 صادرات کاربران\n\n"
                       f"📊 تعداد: {len(users)} کاربر\n"
                       f"📅 تاریخ: {datetime.now().strftime('%Y/%m/%d %H:%M')}"
            )
            
            keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_export_menu')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("✅ فایل CSV کاربران ارسال شد!", reply_markup=reply_markup)
            
        except Exception as e:
            await query.edit_message_text(f"❌ خطا در صادرات کاربران: {str(e)}")

    async def export_payments_csv(self, query) -> None:
        """Export payments data to CSV format"""
        try:
            with open('bot_data.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            payments = data.get('payments', {})
            
            if not payments:
                await query.edit_message_text(
                    "📭 هیچ پرداختی برای صادرات وجود ندارد!",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 بازگشت", callback_data='admin_export_menu')]
                    ])
                )
                return
            
            # Create CSV content
            output = io.StringIO()
            writer = csv.writer(output)
            
            # CSV Headers
            headers = [
                'payment_id', 'user_id', 'course_type', 'price', 'status',
                'payment_date', 'approval_date', 'rejection_reason'
            ]
            writer.writerow(headers)
            
            # Write payment data
            for payment_id, payment_data in payments.items():
                row = [
                    payment_id,
                    payment_data.get('user_id', ''),
                    payment_data.get('course_type', ''),
                    payment_data.get('price', ''),
                    payment_data.get('status', ''),
                    payment_data.get('timestamp', ''),
                    payment_data.get('approval_date', ''),
                    payment_data.get('rejection_reason', '')
                ]
                writer.writerow(row)
            
            csv_content = output.getvalue()
            
            # Send CSV file
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"payments_export_{timestamp}.csv"
            
            await query.message.reply_document(
                document=io.BytesIO(csv_content.encode('utf-8')),
                filename=filename,
                caption=f"📤 صادرات پرداخت‌ها\n\n"
                       f"📊 تعداد: {len(payments)} پرداخت\n"
                       f"📅 تاریخ: {datetime.now().strftime('%Y/%m/%d %H:%M')}"
            )
            
            keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_export_menu')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("✅ فایل CSV پرداخت‌ها ارسال شد!", reply_markup=reply_markup)
            
        except Exception as e:
            await query.edit_message_text(f"❌ خطا در صادرات پرداخت‌ها: {str(e)}")

    async def export_questionnaire_csv(self, query) -> None:
        """Export questionnaire data including photos to CSV format"""
        try:
            # Load questionnaire data
            questionnaire_file = 'questionnaire_data.json'
            if not os.path.exists(questionnaire_file):
                await query.edit_message_text(
                    "📭 هیچ داده پرسشنامه‌ای برای صادرات وجود ندارد!",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 بازگشت", callback_data='admin_export_menu')]
                    ])
                )
                return
            
            with open(questionnaire_file, 'r', encoding='utf-8') as f:
                questionnaire_data = json.load(f)
            
            # Filter out non-user data (responses, photos, completed are not user IDs)
            # Only process entries that look like user IDs (numeric strings)
            user_questionnaires = {}
            for key, value in questionnaire_data.items():
                if key.isdigit() and isinstance(value, dict):
                    user_questionnaires[key] = value
            
            if not user_questionnaires:
                await query.edit_message_text(
                    "📭 هیچ پرسشنامه‌ای تکمیل نشده است!",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 بازگشت", callback_data='admin_export_menu')]
                    ])
                )
                return
            
            # Create CSV content
            output = io.StringIO()
            writer = csv.writer(output)
            
            # CSV Headers
            headers = [
                'user_id', 'نام_فامیل', 'سن', 'قد', 'وزن', 'تجربه_لیگ', 'وقت_تمرین',
                'هدف_مسابقات', 'وضعیت_تیم', 'تمرین_اخیر', 'جزئیات_هوازی', 'جزئیات_وزنه',
                'تجهیزات', 'اولویت_اصلی', 'مصدومیت', 'تغذیه_خواب', 'نوع_تمرین', 'چالش‌ها',
                'تعداد_عکس', 'شناسه‌های_عکس', 'بهبود_بدنی', 'شبکه‌های_اجتماعی', 'شماره_تماس',
                'تاریخ_شروع', 'تاریخ_تکمیل', 'وضعیت_تکمیل'
            ]
            writer.writerow(headers)
            
            # Write questionnaire data
            for user_id, user_progress in user_questionnaires.items():
                answers = user_progress.get('answers', {})
                photos = answers.get('photos', {})
                
                # Count photos and create file_id list
                photo_count = 0
                photo_file_ids = []
                for step_photos in photos.values():
                    if isinstance(step_photos, list):
                        photo_count += len(step_photos)
                        # Extract file_ids from the photo objects
                        for photo in step_photos:
                            if isinstance(photo, dict) and 'file_id' in photo:
                                photo_file_ids.append(photo['file_id'])
                            elif isinstance(photo, str):
                                photo_file_ids.append(photo)  # Legacy format
                
                row = [
                    user_id,
                    answers.get('1', ''),  # نام فامیل
                    answers.get('2', ''),  # سن
                    answers.get('3', ''),  # قد
                    answers.get('4', ''),  # وزن
                    answers.get('5', ''),  # تجربه لیگ
                    answers.get('6', ''),  # وقت تمرین
                    answers.get('7', ''),  # هدف مسابقات
                    answers.get('8', ''),  # وضعیت تیم
                    answers.get('9', ''),  # تمرین اخیر
                    answers.get('10', ''), # جزئیات هوازی
                    answers.get('11', ''), # جزئیات وزنه
                    answers.get('12', ''), # تجهیزات
                    answers.get('13', ''), # اولویت اصلی
                    answers.get('14', ''), # مصدومیت
                    answers.get('15', ''), # تغذیه خواب
                    answers.get('16', ''), # نوع تمرین
                    answers.get('17', ''), # چالش‌ها
                    photo_count,           # تعداد عکس
                    '|'.join(photo_file_ids), # شناسه‌های عکس (جدا شده با |)
                    answers.get('19', ''), # بهبود بدنی
                    answers.get('20', ''), # شبکه‌های اجتماعی
                    answers.get('21', ''), # شماره تماس
                    user_progress.get('started_at', ''),
                    user_progress.get('completed_at', ''),
                    'تکمیل شده' if user_progress.get('completed', False) else 'در حال انجام'
                ]
                writer.writerow(row)
            
            csv_content = output.getvalue()
            
            # Send CSV file with BOM for proper Persian text display in Excel
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"questionnaire_export_{timestamp}.csv"
            
            # Add BOM (Byte Order Mark) for UTF-8 to ensure proper display in Excel
            csv_bytes = '\ufeff'.encode('utf-8') + csv_content.encode('utf-8')
            
            await query.message.reply_document(
                document=io.BytesIO(csv_bytes),
                filename=filename,
                caption=f"📤 صادرات پرسشنامه‌ها\n\n"
                       f"📊 تعداد: {len(user_questionnaires)} پرسشنامه\n"
                       f"📷 شامل اطلاعات عکس‌ها\n"
                       f"📅 تاریخ: {datetime.now().strftime('%Y/%m/%d %H:%M')}\n"
                       f"💡 برای نمایش صحیح فارسی، با Excel باز کنید"
            )
            
            keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_export_menu')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("✅ فایل CSV پرسشنامه‌ها ارسال شد!", reply_markup=reply_markup)
            
        except Exception as e:
            await admin_error_handler.handle_admin_error(
                update=query,
                context=None,
                error=e,
                operation_context="export_questionnaire_csv",
                admin_id=query.from_user.id
            )
            await query.edit_message_text(f"❌ خطا در صادرات پرسشنامه‌ها: {str(e)}")

    async def show_completed_users_list(self, query) -> None:
        """Show list of users who completed questionnaire for personal export"""
        try:
            # Load questionnaire data
            questionnaire_file = 'questionnaire_data.json'
            if not os.path.exists(questionnaire_file):
                await query.edit_message_text(
                    "📭 هیچ کاربری پرسشنامه تکمیل نکرده است!",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 بازگشت", callback_data='admin_export_menu')]
                    ])
                )
                return
            
            with open(questionnaire_file, 'r', encoding='utf-8') as f:
                questionnaire_data = json.load(f)
            
            # Load user data to get names
            with open('bot_data.json', 'r', encoding='utf-8') as f:
                bot_data = json.load(f)
            
            users = bot_data.get('users', {})
            completed_users = []
            
            # Filter out system keys and only process user IDs (numeric strings)
            for user_id, q_data in questionnaire_data.items():
                # Skip system keys like 'responses', 'photos', 'completed'
                if not user_id.isdigit():
                    continue
                    
                # Check if user has completed questionnaire or has any answers
                if not isinstance(q_data, dict):
                    continue
                    
                # Include users who have completed OR have some answers
                has_answers = bool(q_data.get('answers', {}))
                is_completed = q_data.get('completed', False)
                
                if has_answers or is_completed:
                    user_info = users.get(user_id, {})
                    user_name = user_info.get('name', 'نامشخص')
                    user_phone = user_info.get('phone', 'نامشخص')
                    completion_date = q_data.get('completion_timestamp', q_data.get('completed_at', ''))
                    
                    # Count photos correctly from answers
                    answers = q_data.get('answers', {})
                    photos_count = 0
                    documents_count = 0
                    
                    # Count photos and documents from answers
                    for step_key, step_value in answers.items():
                        if step_key == 'photos' and isinstance(step_value, dict):
                            for step_photos in step_value.values():
                                if isinstance(step_photos, list):
                                    photos_count += len(step_photos)
                        elif step_key == 'documents' and isinstance(step_value, dict):
                            documents_count = len(step_value)
                    
                    completed_users.append({
                        'user_id': user_id,
                        'name': user_name,
                        'phone': user_phone,
                        'completion_date': completion_date,
                        'photos_count': photos_count,
                        'documents_count': documents_count,
                        'is_completed': is_completed
                    })
            
            if not completed_users:
                await query.edit_message_text(
                    "📭 هیچ کاربری پرسشنامه شروع نکرده است!",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 بازگشت", callback_data='admin_export_menu')]
                    ])
                )
                return
            
            # Sort by completion date (newest first)
            completed_users.sort(key=lambda x: x.get('completion_date', ''), reverse=True)
            
            # Create buttons for each user (max 20 users to avoid message length issues)
            keyboard = []
            text = "👥 کاربران با پرسشنامه:\n\n"
            
            for i, user in enumerate(completed_users[:20]):
                user_id = user['user_id']
                name = user['name']
                phone = user['phone']
                photos = user['photos_count']
                docs = user['documents_count']
                status = "✅" if user['is_completed'] else "🔄"
                
                text += f"{i+1}. {status} {name} ({phone})\n📷 {photos} عکس | 📎 {docs} سند\n\n"
                
                keyboard.append([InlineKeyboardButton(
                    f"{i+1}. {status} {name} ({phone}) - 📷{photos} 📎{docs}",
                    callback_data=f'export_user_{user_id}'
                )])
            
            keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data='admin_export_menu')])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(text, reply_markup=reply_markup)
            
        except Exception as e:
            logger.error(f"Error in show_completed_users_list: {e}")
            await query.edit_message_text(
                f"❌ خطا در بارگذاری لیست کاربران: {str(e)}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 بازگشت", callback_data='admin_export_menu')]
                ])
            )
            
            if len(completed_users) > 20:
                text += f"\n⚠️ فقط 20 کاربر اول نمایش داده شد. کل: {len(completed_users)} کاربر"
            
            await query.edit_message_text(text, reply_markup=reply_markup)
            
        except Exception as e:
            await admin_error_handler.handle_admin_error(
                update=query,
                context=None,
                error=e,
                operation_context="show_completed_users_list",
                admin_id=query.from_user.id
            )
            await query.edit_message_text(f"❌ خطا در بارگذاری لیست کاربران: {str(e)}")

    async def export_user_personal_data(self, query, user_id: str, context) -> None:
        """Export all data for a specific user including questionnaire photos and documents"""
        try:
            # Load all data
            with open('bot_data.json', 'r', encoding='utf-8') as f:
                bot_data = json.load(f)
            
            questionnaire_file = 'questionnaire_data.json'
            questionnaire_data = {}
            if os.path.exists(questionnaire_file):
                with open(questionnaire_file, 'r', encoding='utf-8') as f:
                    questionnaire_data = json.load(f)
            
            # Get user data
            user_data = bot_data.get('users', {}).get(user_id, {})
            user_questionnaire = questionnaire_data.get(user_id, {})
            
            # Log detailed questionnaire analysis for debugging
            await admin_error_handler.log_questionnaire_data_analysis(user_id, user_questionnaire)
            
            if not user_data:
                await query.edit_message_text(
                    "❌ کاربر یافت نشد!",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 بازگشت", callback_data='admin_export_person')]
                    ])
                )
                return
            
            user_name = user_data.get('name', 'نامشخص')
            
            # Translate course to Persian name
            course_type = user_data.get('course_selected', 'نامشخص')
            course_name = {
                'online_weights': 'وزنه آنلاین',
                'online_cardio': 'هوازی آنلاین', 
                'online_combo': 'ترکیبی آنلاین',
                'in_person_cardio': 'هوازی حضوری',
                'in_person_weights': 'وزنه حضوری',
                'nutrition_plan': 'برنامه غذایی'
            }.get(course_type, course_type)
            
            # Count photos and get their info
            photo_count = 0
            photo_files = []
            document_count = 0
            document_files = []
            
            if user_questionnaire.get('answers'):
                answers = user_questionnaire.get('answers', {})
                
                # Add comprehensive debugging for document export
                admin_id = query.from_user.id
                await admin_error_handler.log_admin_action(
                    admin_id, 
                    "export_user_start", 
                    {"export_user_id": user_id, "user_name": user_name}
                )
                
                print(f"🔍 DEBUG: Processing user {user_id} ({user_name})")
                print(f"📝 Answer keys: {list(answers.keys())}")
                
                admin_error_handler.admin_logger.info(f"EXPORT DEBUG - Processing user {user_id} | Answer keys: {list(answers.keys())}")
                self.admin_logger = admin_error_handler.admin_logger
                
                # Handle photos stored in the 'photos' key
                photos_data = answers.get('photos', {})
                print(f"📷 Photos data: {type(photos_data)} with keys: {list(photos_data.keys()) if isinstance(photos_data, dict) else 'Not a dict'}")
                
                if isinstance(photos_data, dict):
                    for step, step_photos in photos_data.items():
                        if isinstance(step_photos, list):
                            for photo in step_photos:
                                photo_count += 1
                                if isinstance(photo, dict):
                                    file_id = photo.get('file_id')
                                    local_path = photo.get('local_path')
                                    if local_path and os.path.exists(local_path):
                                        photo_files.append((step, local_path, file_id))
                                    elif file_id:
                                        photo_files.append((step, None, file_id))  # No local file, but has file_id
                                elif isinstance(photo, str):
                                    # Legacy format where photo is just a file_id
                                    photo_files.append((step, None, photo))
                
                # Handle other step-based photos (for backward compatibility)
                for step, answer in answers.items():
                    if step == 'photos' or step == 'documents':
                        continue  # Already processed above
                    if isinstance(answer, dict) and answer.get('type') == 'photo':
                        photo_count += 1
                        local_path = answer.get('local_path')
                        file_ids = answer.get('file_ids', [])
                        
                        if local_path and os.path.exists(local_path):
                            photo_files.append((step, local_path, file_ids[0] if file_ids else None))
                        elif file_ids:
                            for i, file_id in enumerate(file_ids):
                                photo_files.append((step, None, file_id))
                
                # Check for documents in questionnaire answers
                documents_data = answers.get('documents', {})
                print(f"📎 Documents data: {type(documents_data)} content: {documents_data}")
                
                await admin_error_handler.log_file_operation(
                    operation="check_documents",
                    file_type="document",
                    success=True,
                    admin_id=admin_id,
                    error_message=f"Documents data type: {type(documents_data)}, content: {documents_data}"
                )
                
                if isinstance(documents_data, dict):
                    for step, doc_info in documents_data.items():
                        if isinstance(doc_info, dict):
                            document_count += 1
                            document_files.append((step, doc_info))
                            print(f"📎 Found document in step {step}: {doc_info}")
                            
                            await admin_error_handler.log_file_operation(
                                operation="found_document",
                                file_type="document",
                                file_id=doc_info.get('file_id'),
                                success=True,
                                admin_id=admin_id,
                                error_message=f"Step {step}, doc_info: {doc_info}"
                            )
                        else:
                            print(f"⚠️ Document in step {step} is not a dict: {type(doc_info)} - {doc_info}")
                            
                            await admin_error_handler.log_file_operation(
                                operation="invalid_document_format",
                                file_type="document",
                                success=False,
                                admin_id=admin_id,
                                error_message=f"Step {step}, invalid format: {type(doc_info)} - {doc_info}"
                            )
                
                # Also check for any document-like fields in other answers
                for step, answer in answers.items():
                    if isinstance(answer, dict) and answer.get('type') == 'document':
                        print(f"📎 Found document-type answer in step {step}: {answer}")
                        document_count += 1
                        document_files.append((step, answer))
                
                print(f"📊 Final counts - Photos: {photo_count}, Documents: {document_count}")
                
                # Initialize counters for export process
                documents_added = 0
                documents_failed = 0
                photos_added = 0
                photos_downloaded = 0
                photos_noted = 0
                
                # Log final export summary
                await admin_error_handler.log_document_export_debug(
                    admin_id,
                    user_id,
                    user_questionnaire,
                    document_count,
                    {
                        "documents_added": documents_added,
                        "documents_failed": documents_failed,
                        "photos_added": photos_added,
                        "photos_downloaded": photos_downloaded
                    }
                )
            
            # Create comprehensive user report
            report = f"""📋 گزارش کامل کاربر: {user_name}

👤 اطلاعات شخصی:
• نام: {user_data.get('name', 'نامشخص')}
• تلفن: {user_data.get('phone', 'نامشخص')}
• شناسه: {user_id}
• دوره: {course_name}
• وضعیت پرداخت: {user_data.get('payment_status', 'نامشخص')}

📝 پرسشنامه:
• وضعیت: {'تکمیل شده' if user_questionnaire.get('completed') else 'تکمیل نشده'}
• تاریخ تکمیل: {user_questionnaire.get('completion_timestamp', user_questionnaire.get('completed_at', 'نامشخص'))}

📷 تصاویر پرسشنامه: {photo_count} عکس
📎 اسناد ارسالی: {document_count} سند

💡 نکته: {f'اسناد در قدم‌های 10 و 11 (تمرین هوازی/وزنه) قابل آپلود هستند' if document_count == 0 else 'اسناد آپلود شده موجود است'}

"""
            
            # Add questionnaire answers
            if user_questionnaire.get('answers'):
                report += "\n📋 پاسخ‌های پرسشنامه:\n"
                for step, answer in user_questionnaire.get('answers', {}).items():
                    if step in ['documents', 'photos']:
                        continue  # Skip these, we'll handle them separately
                    elif isinstance(answer, dict):
                        if answer.get('type') == 'photo':
                            local_path = answer.get('local_path', 'مسیر نامشخص')
                            report += f"سوال {step}: [تصویر] {os.path.basename(local_path) if local_path != 'مسیر نامشخص' else 'فایل موجود نیست'}\n"
                        else:
                            report += f"سوال {step}: {answer.get('text', 'پاسخ نامشخص')}\n"
                    else:
                        report += f"سوال {step}: {answer}\n"
            
            # Add documents info from questionnaire data
            if document_files:
                report += "\n📎 اسناد ارسالی در پرسشنامه:\n"
                for i, (step, doc_info) in enumerate(document_files, 1):
                    doc_name = doc_info.get('name', 'نامشخص')
                    doc_file_id = doc_info.get('file_id', 'نامشخص')
                    report += f"{i}. سوال {step}: {doc_name}\n"
                    report += f"   🆔 File ID: {doc_file_id}\n"
            
            # Create temporary directory for zip file
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Create zip file with report and photos
            zip_filename = f"user_export_{user_id}_{timestamp}.zip"
            temp_zip_path = os.path.join(tempfile.gettempdir(), zip_filename)
            
            with zipfile.ZipFile(temp_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Add text report
                report_filename = f"گزارش_{user_name}_{user_id}.txt"
                zipf.writestr(report_filename, report.encode('utf-8'))
                
                # Add photos if they exist
                for step, photo_path, file_id in photo_files:
                    try:
                        if photo_path and os.path.exists(photo_path):
                            # Local file exists
                            photo_extension = os.path.splitext(photo_path)[1]
                            photo_name = f"تصویر_قدم_{step}{photo_extension}"
                            zipf.write(photo_path, f"photos/{photo_name}")
                            photos_added += 1
                        elif file_id:
                            # Try to download from Telegram using file_id
                            try:
                                file = await context.bot.get_file(file_id)
                                
                                # Determine file extension from file path or default to .jpg
                                file_extension = '.jpg'
                                if hasattr(file, 'file_path') and file.file_path:
                                    file_extension = os.path.splitext(file.file_path)[1] or '.jpg'
                                
                                # Create temp file for photo
                                temp_photo_path = os.path.join(tempfile.gettempdir(), f"temp_photo_{step}_{file_id[:10]}{file_extension}")
                                
                                # Download the file
                                await file.download_to_drive(temp_photo_path)
                                
                                # Add to zip with meaningful name
                                photo_name = f"تصویر_قدم_{step}_{file_id[:10]}{file_extension}"
                                zipf.write(temp_photo_path, f"photos/{photo_name}")
                                photos_downloaded += 1
                                
                                # Clean up temp file
                                try:
                                    os.unlink(temp_photo_path)
                                except:
                                    pass
                                    
                            except Exception as download_error:
                                print(f"Error downloading photo for step {step}: {download_error}")
                                # Add a note about the failed download
                                note_content = f"Step {step}: Photo (File ID: {file_id})\nDownload failed: {str(download_error)}\n"
                                zipf.writestr(f"failed_photo_step_{step}_{file_id[:10]}.txt", note_content.encode('utf-8'))
                                photos_noted += 1
                        else:
                            # No file_id and no local path
                            note_content = f"Step {step}: Photo data incomplete (no file_id or local_path)\n"
                            zipf.writestr(f"missing_photo_step_{step}.txt", note_content.encode('utf-8'))
                            photos_noted += 1
                    except Exception as e:
                        print(f"Error processing photo for step {step}: {e}")
                        photos_noted += 1
                
                # Add documents by downloading them from Telegram
                await admin_error_handler.log_admin_action(
                    admin_id,
                    "start_document_download",
                    {"total_documents": len(document_files)}
                )
                
                for step, doc_info in document_files:
                    try:
                        doc_file_id = doc_info.get('file_id')
                        doc_name = doc_info.get('name', f'document_step_{step}')
                        
                        await admin_error_handler.log_file_operation(
                            operation="attempt_document_download",
                            file_type="document",
                            file_id=doc_file_id,
                            admin_id=admin_id,
                            error_message=f"Step {step}, name: {doc_name}"
                        )
                        
                        if doc_file_id:
                            # Try to download the document from Telegram
                            try:
                                # Get file from Telegram
                                file = await context.bot.get_file(doc_file_id)
                                
                                await admin_error_handler.log_file_operation(
                                    operation="telegram_get_file_success",
                                    file_type="document",
                                    file_id=doc_file_id,
                                    success=True,
                                    admin_id=admin_id
                                )
                                
                                # Create temp file for document
                                doc_extension = os.path.splitext(doc_name)[1] or '.pdf'
                                temp_doc_path = os.path.join(tempfile.gettempdir(), f"temp_doc_{step}_{doc_name}")
                                
                                # Download the file
                                await file.download_to_drive(temp_doc_path)
                                
                                await admin_error_handler.log_file_operation(
                                    operation="document_download_success",
                                    file_type="document",
                                    file_id=doc_file_id,
                                    local_path=temp_doc_path,
                                    success=True,
                                    admin_id=admin_id
                                )
                                
                                # Add to zip with meaningful name
                                zip_doc_name = f"سند_قدم_{step}_{doc_name}"
                                zipf.write(temp_doc_path, f"documents/{zip_doc_name}")
                                documents_added += 1
                                
                                await admin_error_handler.log_file_operation(
                                    operation="zip_add_document",
                                    file_type="document",
                                    local_path=temp_doc_path,
                                    success=True,
                                    admin_id=admin_id,
                                    error_message=f"Added as {zip_doc_name}"
                                )
                                
                                # Clean up temp file
                                try:
                                    os.unlink(temp_doc_path)
                                except:
                                    pass
                                    
                            except Exception as download_error:
                                print(f"Error downloading document for step {step}: {download_error}")
                                
                                await admin_error_handler.log_file_operation(
                                    operation="document_download_failed",
                                    file_type="document",
                                    file_id=doc_file_id,
                                    success=False,
                                    admin_id=admin_id,
                                    error_message=str(download_error)
                                )
                                
                                # Add a note about the failed download
                                note_content = f"Step {step}: Document '{doc_name}' (File ID: {doc_file_id})\nDownload failed: {str(download_error)}\n"
                                zipf.writestr(f"failed_document_step_{step}.txt", note_content.encode('utf-8'))
                                documents_failed += 1
                        else:
                            await admin_error_handler.log_file_operation(
                                operation="document_no_file_id",
                                file_type="document",
                                success=False,
                                admin_id=admin_id,
                                error_message=f"Step {step}: No file_id in doc_info: {doc_info}"
                            )
                            documents_failed += 1
                    except Exception as e:
                        print(f"Error processing document for step {step}: {e}")
                        
                        await admin_error_handler.log_file_operation(
                            operation="document_processing_error",
                            file_type="document",
                            success=False,
                            admin_id=admin_id,
                            error_message=f"Step {step}: {str(e)}"
                        )
                        documents_failed += 1
                
                # Add note about photos
                total_photos_processed = photos_added + photos_downloaded
                if total_photos_processed > 0 or photos_noted > 0:
                    photo_note = f"📷 تصاویر در این بسته:\n"
                    if photos_added > 0:
                        photo_note += f"• {photos_added} تصویر محلی در پوشه photos\n"
                    if photos_downloaded > 0:
                        photo_note += f"• {photos_downloaded} تصویر دانلود شده از تلگرام در پوشه photos\n"
                    if photos_noted > 0:
                        photo_note += f"• {photos_noted} تصویر قابل دسترسی نبود (یادداشت خطا موجود)\n"
                    if total_photos_processed < photo_count:
                        photo_note += f"⚠️ {photo_count - total_photos_processed - photos_noted} تصویر به دلیل عدم دسترسی، اضافه نشد.\n"
                    zipf.writestr("راهنمای_تصاویر.txt", photo_note.encode('utf-8'))
                
                # Add note about documents
                if documents_added > 0 or documents_failed > 0:
                    doc_note = f"📎 اسناد در این بسته:\n"
                    if documents_added > 0:
                        doc_note += f"• {documents_added} سند با موفقیت دانلود شده در پوشه documents\n"
                    if documents_failed > 0:
                        doc_note += f"• {documents_failed} سند دانلود نشد (یادداشت خطا موجود)\n"
                    zipf.writestr("راهنمای_اسناد.txt", doc_note.encode('utf-8'))
            
            # Send the zip file
            with open(temp_zip_path, 'rb') as zip_file:
                await query.message.reply_document(
                    document=zip_file,
                    filename=zip_filename,
                    caption=f"📤 گزارش کامل کاربر {user_name}\n\n"
                           f"📋 شامل: گزارش متنی + {total_photos_processed} تصویر + {documents_added} سند"
                           f"{f' + {photos_noted} تصویر ناموفق' if photos_noted > 0 else ''}"
                           f"{f' + {documents_failed} سند ناموفق' if documents_failed > 0 else ''}\n"
                           f"📅 تاریخ تولید: {datetime.now().strftime('%Y/%m/%d %H:%M')}"
                )
            
            # Clean up temporary file
            try:
                os.unlink(temp_zip_path)
            except:
                pass
            
            keyboard = [
                [InlineKeyboardButton("🔙 بازگشت به لیست", callback_data='admin_export_person')],
                [InlineKeyboardButton("📋 منوی اصلی", callback_data='admin_export_menu')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"✅ گزارش کامل {user_name} ارسال شد!\n\n"
                f"📋 شامل: اطلاعات شخصی، پاسخ‌های پرسشنامه\n"
                f"📷 تصاویر: {photos_added} فایل محلی + {photos_downloaded} دانلود شده"
                f"{f', {photos_noted} فایل ناموفق' if photos_noted > 0 else ''}\n"
                f"📎 اسناد: {documents_added} فایل دانلود شده"
                f"{f', {documents_failed} فایل ناموفق' if documents_failed > 0 else ''}",
                reply_markup=reply_markup
            )
            
        except Exception as e:
            await admin_error_handler.handle_admin_error(
                update=query,
                context=context,
                error=e,
                operation_context="export_user_personal_data",
                admin_id=query.from_user.id
            )
            await query.edit_message_text(f"❌ خطا در تولید گزارش: {str(e)}")
            print(f"Export error: {e}")  # For debugging

    async def export_all_data(self, query) -> None:
        """Export complete database as JSON with admin-friendly format"""
        try:
            with open('bot_data.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Load questionnaire data if exists
            questionnaire_data = {}
            try:
                with open('questionnaire_data.json', 'r', encoding='utf-8') as f:
                    questionnaire_data = json.load(f)
            except FileNotFoundError:
                pass
            
            # Create admin-friendly simplified data structure
            admin_data = {
                "export_info": {
                    "generated_date": datetime.now().strftime('%Y/%m/%d %H:%M:%S'),
                    "total_users": len(data.get('users', {})),
                    "total_payments": len(data.get('payments', {})),
                    "total_questionnaires": len(questionnaire_data),
                    "description": "پشتیبان کامل داده‌های ربات مربی فوتبال"
                },
                "users_summary": [],
                "payments_summary": [],
                "questionnaires_summary": [],
                "complete_data": data,  # Original data for technical recovery
                "questionnaire_data": questionnaire_data
            }
            
            # Create user summaries for easy reading
            users = data.get('users', {})
            for user_id, user_data in users.items():
                user_summary = {
                    "user_id": user_id,
                    "name": user_data.get('name', 'نامشخص'),
                    "username": user_data.get('username', ''),
                    "phone": user_data.get('phone', ''),
                    "course": user_data.get('course_selected', ''),
                    "payment_status": user_data.get('payment_status', ''),
                    "questionnaire_completed": user_data.get('questionnaire_completed', False),
                    "registration_date": user_data.get('last_updated', '')
                }
                admin_data["users_summary"].append(user_summary)
            
            # Create payment summaries for easy reading
            payments = data.get('payments', {})
            for payment_id, payment_data in payments.items():
                payment_summary = {
                    "payment_id": payment_id,
                    "user_id": payment_data.get('user_id', ''),
                    "course_type": payment_data.get('course_type', ''),
                    "price": payment_data.get('price', 0),
                    "status": payment_data.get('status', ''),
                    "payment_date": payment_data.get('timestamp', ''),
                    "approval_date": payment_data.get('approval_timestamp', '')
                }
                admin_data["payments_summary"].append(payment_summary)
            
            # Create questionnaire summaries for easy reading
            for user_id, user_questionnaire in questionnaire_data.items():
                questionnaire_summary = {
                    "user_id": user_id,
                    "completed": user_questionnaire.get('completed', False),
                    "completion_date": user_questionnaire.get('completion_timestamp', ''),
                    "total_answers": len(user_questionnaire.get('answers', {})),
                    "photos_uploaded": len([a for a in user_questionnaire.get('answers', {}).values() if isinstance(a, dict) and a.get('type') == 'photo'])
                }
                admin_data["questionnaires_summary"].append(questionnaire_summary)
            
            # Create formatted JSON with proper indentation
            json_content = json.dumps(admin_data, ensure_ascii=False, indent=2)
            
            # Send JSON file
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"admin_backup_{timestamp}.json"
            
            await query.message.reply_document(
                document=io.BytesIO(json_content.encode('utf-8')),
                filename=filename,
                caption=f"📤 پشتیبان کامل دیتابیس (فرمت ادمین)\n\n"
                       f"👥 کاربران: {len(data.get('users', {}))}\n"
                       f"💳 پرداخت‌ها: {len(data.get('payments', {}))}\n"
                       f"📋 پرسشنامه‌ها: {len(questionnaire_data)}\n"
                       f"📋 شامل: خلاصه آسان + داده‌های کامل\n"
                       f"📅 تاریخ: {datetime.now().strftime('%Y/%m/%d %H:%M')}"
            )
            
            keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_export_menu')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("✅ فایل پشتیبان کامل ارسال شد!", reply_markup=reply_markup)
            
        except Exception as e:
            await query.edit_message_text(f"❌ خطا در صادرات کامل: {str(e)}")

    async def export_telegram_csv(self, query) -> None:
        """Export Telegram contact information to CSV format"""
        try:
            with open('bot_data.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            users = data.get('users', {})
            
            if not users:
                await query.edit_message_text(
                    "📭 هیچ کاربری برای صادرات وجود ندارد!",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 بازگشت", callback_data='admin_export_menu')]
                    ])
                )
                return
            
            # Create CSV content
            output = io.StringIO()
            writer = csv.writer(output)
            
            # CSV Headers for telegram data
            headers = [
                'user_id', 'name', 'username', 'phone', 'telegram_link',
                'course_selected', 'payment_status', 'registration_date'
            ]
            writer.writerow(headers)
            
            # Write telegram contact data
            for user_id, user_data in users.items():
                username = user_data.get('username', '')
                telegram_link = f"https://t.me/{username}" if username else ''
                
                row = [
                    user_id,
                    user_data.get('name', ''),
                    f"@{username}" if username else '',
                    user_data.get('phone', ''),
                    telegram_link,
                    user_data.get('course_selected', ''),
                    user_data.get('payment_status', ''),
                    user_data.get('last_updated', '')
                ]
                writer.writerow(row)
            
            csv_content = output.getvalue()
            
            # Send CSV file
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"telegram_contacts_{timestamp}.csv"
            
            await query.message.reply_document(
                document=io.BytesIO(csv_content.encode('utf-8')),
                filename=filename,
                caption=f"📤 صادرات مخاطبین تلگرام\n\n"
                       f"👥 تعداد: {len(users)} مخاطب\n"
                       f"📅 تاریخ: {datetime.now().strftime('%Y/%m/%d %H:%M')}"
            )
            
            keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_export_menu')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("✅ فایل CSV مخاطبین تلگرام ارسال شد!", reply_markup=reply_markup)
            
        except Exception as e:
            await query.edit_message_text(f"❌ خطا در صادرات مخاطبین: {str(e)}")



    async def show_coupon_management(self, query) -> None:
        """Show coupon management menu"""
        keyboard = [
            [InlineKeyboardButton("📋 مشاهده کدهای تخفیف", callback_data='admin_view_coupons')],
            [InlineKeyboardButton("➕ ایجاد کد تخفیف جدید", callback_data='admin_create_coupon')],
            [InlineKeyboardButton("🔄 فعال/غیرفعال کردن کد", callback_data='admin_toggle_coupon')],
            [InlineKeyboardButton("🗑️ حذف کد تخفیف", callback_data='admin_delete_coupon')],
            [InlineKeyboardButton("🔙 بازگشت", callback_data='admin_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = """🏷️ مدیریت کدهای تخفیف
        
انتخاب کنید:"""
        
        await query.edit_message_text(text, reply_markup=reply_markup)

    async def show_coupons_list(self, query) -> None:
        """Show list of all coupons"""
        coupons = self.coupon_manager.get_all_coupons()
        
        if not coupons:
            text = "❌ هیچ کد تخفیفی تعریف نشده است!"
        else:
            text = "🏷️ لیست کدهای تخفیف:\n\n"
            
            for code, details in coupons.items():
                status = "✅ فعال" if details.get('active', False) else "❌ غیرفعال"
                usage = details.get('usage_count', 0)
                max_uses = details.get('max_uses', 'نامحدود')
                expires = details.get('expires_at', 'ندارد')
                
                if expires != 'ندارد':
                    try:
                        expires_date = datetime.fromisoformat(expires)
                        expires = expires_date.strftime('%Y/%m/%d')
                    except:
                        expires = 'نامعلوم'
                
                text += f"🏷️ **{code}**\n"
                text += f"📊 تخفیف: {details.get('discount_percent', 0)}%\n"
                text += f"📈 استفاده: {usage}/{max_uses}\n"
                text += f"📅 انقضا: {expires}\n"
                text += f"🔘 وضعیت: {status}\n"
                text += f"📝 توضیحات: {details.get('description', 'ندارد')}\n\n"
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_coupons')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

    async def handle_create_coupon(self, query, user_id: int) -> None:
        """Handle creating a new coupon code"""
        await query.answer()
        
        # Set flag that admin is creating a coupon
        self.admin_creating_coupons.add(user_id)
        
        text = (
            "➕ ایجاد کد تخفیف جدید\n\n"
            "برای ایجاد کد تخفیف جدید، لطفاً اطلاعات زیر را با فرمت مشخص شده ارسال کنید:\n\n"
            "📝 فرمت:\n"
            "کد_تخفیف درصد_تخفیف توضیحات\n\n"
            "🔤 مثال:\n"
            "WELCOME20 20 کد تخفیف خوش‌آمدگویی\n\n"
            "⚠️ نکات:\n"
            "• کد تخفیف باید انگلیسی باشد\n"
            "• درصد تخفیف عددی بین 1 تا 100\n"
            "• توضیحات اختیاری است"
        )
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_coupons')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup)

    async def handle_admin_coupon_creation(self, update, text_answer: str) -> None:
        # Handle admin coupon creation from text input
        user_id = update.effective_user.id
        
        # Remove admin from creating state
        self.admin_creating_coupons.discard(user_id)
        
        try:
            # Parse input: "CODE PERCENT description"
            parts = text_answer.strip().split()
            if len(parts) < 2:
                raise ValueError("Not enough parts")
            
            code = parts[0].upper()
            discount_percent = int(parts[1])
            description = " ".join(parts[2:]) if len(parts) > 2 else ""
            
            # Validate
            if not code.replace('_', '').isalnum():
                raise ValueError(f"Invalid code format: {code}")
            if not (1 <= discount_percent <= 100):
                raise ValueError(f"Invalid discount percent: {discount_percent}")
            
            # Create coupon
            success = self.coupon_manager.create_coupon(
                code=code,
                discount_percent=discount_percent,
                description=description,
                created_by=f"admin_{user_id}"
            )
            
            if success:
                text = f"✅ کد تخفیف {code} با موفقیت ایجاد شد!\n\n"
                text += f"💰 تخفیف: {discount_percent}%\n"
                text += f"📝 توضیحات: {description or 'ندارد'}"
            else:
                text = f"❌ خطا در ایجاد کد تخفیف!\nاحتمالا کد {code} قبلا وجود دارد."
                
        except ValueError as e:
            error_msg = str(e)
            text = f"❌ فرمت نادرست! خطا: {error_msg}\n\n"
            text += "لطفاً فرمت صحیح را رعایت کنید:\n"
            text += "کد_تخفیف درصد_تخفیف توضیحات\n\n"
            text += "مثال: WELCOME20 20 کد تخفیف خوش‌آمدگویی\n\n"
            text += "⚠️ نکات:\n"
            text += "• کد تخفیف باید انگلیسی باشد\n"
            text += "• درصد تخفیف عددی بین 1 تا 100"
        except Exception as e:
            text = f"❌ خطای غیرمنتظره: {str(e)}"
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_coupons')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup)

    async def handle_toggle_coupon(self, query) -> None:
        # Handle toggling coupon active status
        await query.answer()
        
        coupons = self.coupon_manager.get_all_coupons()
        
        if not coupons:
            text = "❌ هیچ کد تخفیفی برای تغییر وضعیت وجود ندارد!"
            keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_coupons')]]
        else:
            text = "🔄 انتخاب کد تخفیف برای تغییر وضعیت:\n\n"
            keyboard = []
            
            for code, details in coupons.items():
                status = "✅ فعال" if details.get('active', False) else "❌ غیرفعال"
                keyboard.append([InlineKeyboardButton(
                    f"{code} - {status}", 
                    callback_data=f'toggle_coupon_{code}'
                )])
            
            keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data='admin_coupons')])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup)

    async def handle_delete_coupon(self, query) -> None:
        # Handle deleting coupon codes
        await query.answer()
        
        coupons = self.coupon_manager.get_all_coupons()
        
        if not coupons:
            text = "❌ هیچ کد تخفیفی برای حذف وجود ندارد!"
            keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_coupons')]]
        else:
            text = "🗑️ انتخاب کد تخفیف برای حذف:\n\n⚠️ توجه: این عمل غیرقابل بازگشت است!"
            keyboard = []
            
            for code, details in coupons.items():
                usage = details.get('usage_count', 0)
                keyboard.append([InlineKeyboardButton(
                    f"❌ {code} (استفاده: {usage})", 
                    callback_data=f'delete_coupon_{code}'
                )])
            
            keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data='admin_coupons')])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup)

    async def process_toggle_coupon(self, query) -> None:
        # Process toggling a specific coupon
        coupon_code = query.data.replace('toggle_coupon_', '')
        new_status = self.coupon_manager.toggle_coupon(coupon_code)
        
        if new_status is not None:
            # Show brief confirmation in the callback answer (small popup)
            status_text = "فعال" if new_status else "غیرفعال"
            await query.answer(f"✅ {coupon_code} {status_text} شد", show_alert=False)
            
            # Immediately return to the toggle menu with updated buttons
            await self.handle_toggle_coupon(query)
        else:
            # Show error in callback answer
            await query.answer(f"❌ خطا در تغییر {coupon_code}", show_alert=True)

    async def process_delete_coupon(self, query) -> None:
        # Process deleting a specific coupon
        await query.answer()
        
        coupon_code = query.data.replace('delete_coupon_', '')
        success = self.coupon_manager.delete_coupon(coupon_code)
        
        if success:
            text = f"✅ کد تخفیف {coupon_code} با موفقیت حذف شد!"
        else:
            text = f"❌ خطا در حذف کد تخفیف {coupon_code}"
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_coupons')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup)

    # =====================================
    # PLAN MANAGEMENT SYSTEM - NEW PERSON-CENTRIC APPROACH
    # =====================================
    
    async def show_plan_management(self, query) -> None:
        """Show users who have bought courses for personalized plan management"""
        await query.answer()
        
        try:
            # Load both user and payment data
            with open('bot_data.json', 'r', encoding='utf-8') as f:
                bot_data = json.load(f)
            
            users = bot_data.get('users', {})
            payments = bot_data.get('payments', {})
            
            # Find users who have approved payments (actual purchases)
            paid_users = []
            user_course_map = {}  # user_id -> set of purchased courses
            
            # First, build map of users with approved payments
            for payment_id, payment_data in payments.items():
                if payment_data.get('status') == 'approved':
                    user_id = str(payment_data.get('user_id'))
                    course_type = payment_data.get('course_type')
                    
                    if user_id not in user_course_map:
                        user_course_map[user_id] = set()
                    user_course_map[user_id].add(course_type)
            
            # Create user list with their purchased courses
            for user_id, purchased_courses in user_course_map.items():
                user_data = users.get(user_id, {})
                if user_data:  # Only include users that exist in user data
                    # Get primary course (most recent or first one)
                    primary_course = list(purchased_courses)[0] if purchased_courses else 'نامشخص'
                    
                    paid_users.append({
                        'user_id': user_id,
                        'name': user_data.get('name', 'نامشخص'),
                        'phone': user_data.get('phone', 'نامشخص'),
                        'course': primary_course,
                        'purchased_courses': purchased_courses,
                        'course_count': len(purchased_courses)
                    })
            
            if not paid_users:
                keyboard = [[InlineKeyboardButton("🔙 بازگشت به پنل اصلی", callback_data='admin_back_main')]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                text = """📋 مدیریت برنامه‌های شخصی

❌ هنوز هیچ کاربری دوره‌ای خریداری نکرده است.

💡 برای استفاده از این بخش، ابتدا باید:
• کاربرانی ثبت‌نام کنند
• دوره‌ای را انتخاب کنند  
• پرداخت آن‌ها تأیید شود

🔍 Debug Info: Checked {len(payments)} payments, found {len([p for p in payments.values() if p.get('status') == 'approved'])} approved"""
                
                await query.edit_message_text(text, reply_markup=reply_markup)
                return
            
            # Sort users by name
            paid_users.sort(key=lambda x: x['name'])
            
            keyboard = []
            text = f"👥 کاربران خریدار دوره ({len(paid_users)} نفر)\n\n"
            text += "برای مدیریت برنامه شخصی هر کاربر، روی نام کلیک کنید:\n\n"
            
            course_names = {
                'online_weights': '🏋️ وزنه آنلاین',
                'online_cardio': '🏃 هوازی آنلاین',
                'online_combo': '💪 ترکیبی آنلاین',
                'in_person_cardio': '🏃‍♂️ هوازی حضوری',
                'in_person_weights': '🏋️‍♀️ وزنه حضوری',
                'nutrition_plan': '🍎 برنامه غذایی'
            }
            
            for i, user in enumerate(paid_users, 1):
                # Show primary course and course count if multiple
                course_display = course_names.get(user['course'], user['course'])
                if user['course_count'] > 1:
                    course_display += f" (+{user['course_count'] - 1} دیگر)"
                    
                user_display = f"{i}. {user['name']} ({user['phone']}) - {course_display}"
                text += f"{user_display}\n"
                
                keyboard.append([InlineKeyboardButton(
                    user_display[:60] + "..." if len(user_display) > 60 else user_display,
                    callback_data=f'user_plans_{user["user_id"]}'
                )])
            
            keyboard.append([InlineKeyboardButton("🔙 بازگشت به پنل اصلی", callback_data='admin_back_main')])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(text, reply_markup=reply_markup)
            
        except Exception as e:
            await admin_error_handler.handle_admin_error(
                query, None, e, "show_plan_management", query.from_user.id
            )

    async def show_user_course_plans(self, query, user_id: str) -> None:
        """Show courses purchased by a specific user for plan management"""
        try:
            await query.answer()
            
            # Load user and payment data
            with open('bot_data.json', 'r', encoding='utf-8') as f:
                bot_data = json.load(f)
            
            # Load existing plans
            user_plans = await self.load_user_plans(user_id)
            
            user_data = bot_data.get('users', {}).get(user_id, {})
            payments = bot_data.get('payments', {})
            
            if not user_data:
                await query.edit_message_text(
                    "❌ کاربر یافت نشد!",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 بازگشت", callback_data='admin_plans')]
                    ])
                )
                return
            
            user_name = user_data.get('name', 'نامشخص')
            user_phone = user_data.get('phone', 'نامشخص')
            
            # Get all purchased courses for this user from payments table
            purchased_courses = []
            for payment_id, payment_data in payments.items():
                if (payment_data.get('user_id') == int(user_id) and 
                    payment_data.get('status') == 'approved'):
                    course_type = payment_data.get('course_type')
                    if course_type and course_type not in purchased_courses:
                        purchased_courses.append(course_type)
            
            if not purchased_courses:
                await query.edit_message_text(
                    f"❌ کاربر {user_name} هنوز هیچ دوره‌ای خریداری نکرده است!\n\n"
                    f"🔍 Debug: Checked {len(payments)} payments for user_id {user_id}",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 بازگشت", callback_data='admin_plans')]
                    ])
                )
                return
            
            course_names = {
                'online_weights': '🏋️ وزنه آنلاین',
                'online_cardio': '🏃 هوازی آنلاین',
                'online_combo': '💪 ترکیبی آنلاین',
                'in_person_cardio': '🏃‍♂️ هوازی حضوری',
                'in_person_weights': '🏋️‍♀️ وزنه حضوری',
                'nutrition_plan': '🍎 برنامه غذایی'
            }
            
            keyboard = []
            text = f"📋 مدیریت برنامه‌های {user_name}\n"
            text += f"📱 تلفن: {user_phone}\n\n"
            text += "دوره‌های خریداری شده:\n\n"
            
            for course_code in purchased_courses:
                course_name = course_names.get(course_code, course_code)
                course_plans = user_plans.get(course_code, [])
                plan_count = len(course_plans)
                
                text += f"📚 {course_name}\n"
                text += f"   📋 {plan_count} برنامه موجود\n"
                if course_plans:
                    # Fix field reference: use 'created_at' instead of 'upload_date'
                    latest_plan = max(course_plans, key=lambda x: x.get('created_at', ''))
                    plan_date = latest_plan.get('created_at', '')
                    if plan_date:
                        formatted_date = plan_date[:10].replace('-', '/')  # Format: YYYY/MM/DD
                        text += f"   🕐 آخرین برنامه: {formatted_date}\n"
                    else:
                        text += f"   🕐 آخرین برنامه: نامشخص\n"
                else:
                    text += f"   🕐 آخرین برنامه: -\n"
                text += "\n"
                
                keyboard.append([InlineKeyboardButton(
                    f"📚 {course_name} ({plan_count} برنامه)",
                    callback_data=f'manage_user_course_{user_id}_{course_code}'
                )])
            
            keyboard.append([InlineKeyboardButton("🔙 بازگشت به لیست کاربران", callback_data='admin_plans')])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(text, reply_markup=reply_markup)
            
        except Exception as e:
            await admin_error_handler.handle_admin_error(
                query, None, e, f"show_user_course_plans:{user_id}", query.from_user.id
            )

    async def show_user_course_plan_management(self, query, user_id: str, course_code: str) -> None:
        """Show plan management for a specific user's specific course"""
        try:
            await query.answer()
            
            # Load user data and plans
            with open('bot_data.json', 'r', encoding='utf-8') as f:
                bot_data = json.load(f)
            
            user_data = bot_data.get('users', {}).get(user_id, {})
            user_name = user_data.get('name', 'نامشخص')
            
            print(f"🔍 PLAN MANAGEMENT DEBUG - User: {user_id} ({user_name}), Course: {course_code}")
            
            user_plans = await self.load_user_plans(user_id)
            course_plans = user_plans.get(course_code, [])
            
            print(f"📊 LOADED PLANS FOR DISPLAY - Course: {course_code}, Plans: {len(course_plans)}")
            if course_plans:
                for i, plan in enumerate(course_plans):
                    print(f"   Plan {i+1}: {plan.get('filename', 'no filename')} - ID: {plan.get('id', 'no id')}")
            else:
                print(f"   No plans found for course {course_code}")
            
            course_names = {
                'online_weights': '🏋️ وزنه آنلاین',
                'online_cardio': '🏃 هوازی آنلاین',
                'online_combo': '💪 ترکیبی آنلاین',
                'in_person_cardio': '🏃‍♂️ هوازی حضوری',
                'in_person_weights': '🏋️‍♀️ وزنه حضوری'
            }
            course_name = course_names.get(course_code, course_code)
            
            keyboard = [
                [InlineKeyboardButton("📤 آپلود برنامه جدید", callback_data=f'upload_user_plan_{user_id}_{course_code}')]
            ]
            
            text = f"📋 مدیریت برنامه {course_name}\n"
            text += f"👤 کاربر: {user_name}\n\n"
            
            if course_plans:
                text += f"📚 برنامه‌های موجود ({len(course_plans)} عدد):\n\n"
                
                # Check current main plan for this user+course
                current_main_plan = await self.get_main_plan_for_user_course(user_id, course_code)
                if current_main_plan:
                    text += f"⭐ برنامه اصلی فعلی: {current_main_plan}\n\n"
                
                # Sort plans by created date (newest first)
                sorted_plans = sorted(course_plans, key=lambda x: x.get('created_at', ''), reverse=True)
                
                for i, plan in enumerate(sorted_plans, 1):
                    created_at = plan.get('created_at', 'نامشخص')[:16].replace('T', ' ')
                    plan_type = plan.get('content_type', 'document')
                    file_name = plan.get('filename', 'نامشخص')
                    
                    plan_id = plan.get('id', f'plan_{i}')
                    
                    # Check if this plan is the current main plan
                    is_main_plan = (current_main_plan == plan_id)
                    main_indicator = " ⭐ (برنامه اصلی)" if is_main_plan else ""
                    
                    text += f"{i}. 📄 {file_name}{main_indicator}\n"
                    text += f"   📅 {created_at}\n"
                    text += f"   📋 نوع: {plan_type}\n"
                    
                    # Streamlined UI: only send and delete buttons (view is redundant)
                    plan_id = plan.get('id', f'plan_{i}')
                    keyboard.append([
                        InlineKeyboardButton(f" ارسال برنامه {i} به کاربر", callback_data=f'send_user_plan_{user_id}_{course_code}_{plan_id}'),
                        InlineKeyboardButton(f"🗑 حذف برنامه {i}", callback_data=f'delete_user_plan_{user_id}_{course_code}_{plan_id}')
                    ])
                    text += "\n"
                
                keyboard.append([InlineKeyboardButton("📤 ارسال آخرین برنامه", callback_data=f'send_latest_plan_{user_id}_{course_code}')])
            else:
                text += "📭 هنوز هیچ برنامه‌ای برای این کاربر و دوره آپلود نشده است.\n\n"
                text += "📤 برای شروع، روی 'آپلود برنامه جدید' کلیک کنید."
            
            keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data=f'user_plans_{user_id}')])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(text, reply_markup=reply_markup)
            
        except Exception as e:
            await admin_error_handler.handle_admin_error(
                query, None, e, f"show_user_course_plan_management:{user_id}:{course_code}", query.from_user.id
            )

    async def load_user_plans(self, user_id: str) -> dict:
        """Load all plans for a specific user organized by course - reads from course_plans files"""
        try:
            user_plans = {}
            
            # List of course types to check
            course_types = ['online_weights', 'online_cardio', 'online_combo', 
                           'in_person_cardio', 'in_person_weights', 'nutrition_plan']
            
            print(f"🔍 LOADING USER PLANS DEBUG - User: {user_id}")
            
            for course_type in course_types:
                plans_file = f'admin_data/course_plans/{course_type}.json'
                print(f"   Checking {plans_file}...")
                
                if os.path.exists(plans_file):
                    with open(plans_file, 'r', encoding='utf-8') as f:
                        all_plans = json.load(f)
                    
                    # Filter plans for this specific user
                    user_specific_plans = []
                    for plan in all_plans:
                        target_user = plan.get('target_user_id')
                        # Check both string and int versions
                        if str(target_user) == str(user_id) or target_user == int(user_id):
                            user_specific_plans.append(plan)
                    
                    if user_specific_plans:
                        user_plans[course_type] = user_specific_plans
                        print(f"   Found {len(user_specific_plans)} plans for {course_type}")
                    else:
                        print(f"   No plans found for user in {course_type}")
                else:
                    print(f"   File not found: {plans_file}")
            
            print(f"📊 TOTAL USER PLANS LOADED: {sum(len(plans) for plans in user_plans.values())} across {len(user_plans)} courses")
            return user_plans
            
        except Exception as e:
            print(f"❌ ERROR LOADING USER PLANS: {e}")
            logger.error(f"Error loading user plans for {user_id}: {e}")
            return {}

    async def save_user_plans(self, user_id: str, plans_data: dict) -> bool:
        """Save plans for a specific user"""
        try:
            # Create user_plans directory if it doesn't exist
            os.makedirs('user_plans', exist_ok=True)
            
            plans_file = f'user_plans/{user_id}_plans.json'
            with open(plans_file, 'w', encoding='utf-8') as f:
                json.dump(plans_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving user plans for {user_id}: {e}")
            return False

    async def add_user_plan(self, user_id: str, course_code: str, plan_data: dict) -> bool:
        """Add a new plan for a specific user and course"""
        try:
            user_plans = await self.load_user_plans(user_id)
            
            if course_code not in user_plans:
                user_plans[course_code] = []
            
            # Add timestamp and unique ID - use consistent field names
            plan_data['created_at'] = datetime.now().isoformat()
            plan_data['id'] = f"plan_{int(datetime.now().timestamp())}"
            
            user_plans[course_code].append(plan_data)
            
            return await self.save_user_plans(user_id, user_plans)
        except Exception as e:
            logger.error(f"Error adding user plan for {user_id}, course {course_code}: {e}")
            return False

    async def delete_user_plan(self, user_id: str, course_code: str, plan_id: str) -> bool:
        """Delete a specific plan for a user and course - works with course-centric storage"""
        try:
            # Load the course-specific plans file
            plans_file = f'admin_data/course_plans/{course_code}.json'
            
            if not os.path.exists(plans_file):
                logger.warning(f"Plans file not found: {plans_file}")
                return False
            
            # Load all plans for this course
            with open(plans_file, 'r', encoding='utf-8') as f:
                all_plans = json.load(f)
            
            # Find and remove the specific plan
            original_count = len(all_plans)
            all_plans = [
                plan for plan in all_plans 
                if not (plan.get('id') == plan_id and str(plan.get('target_user_id')) == str(user_id))
            ]
            
            if len(all_plans) < original_count:
                # Save the updated plans back to the course file
                with open(plans_file, 'w', encoding='utf-8') as f:
                    json.dump(all_plans, f, ensure_ascii=False, indent=2)
                
                # Check if this was the main plan and unset it if so
                current_main_plan = await self.get_main_plan_for_user_course(user_id, course_code)
                if current_main_plan == plan_id:
                    await self.unset_main_plan_for_user_course(user_id, course_code)
                
                logger.info(f"Successfully deleted plan {plan_id} for user {user_id} in course {course_code}")
                return True
            else:
                logger.warning(f"Plan {plan_id} not found for user {user_id} in course {course_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting user plan for {user_id}, course {course_code}, plan {plan_id}: {e}")
            return False

    async def get_user_plan(self, user_id: str, course_code: str, plan_id: str) -> dict:
        """Get a specific plan for a user and course"""
        try:
            user_plans = await self.load_user_plans(user_id)
            
            if course_code in user_plans:
                for plan in user_plans[course_code]:
                    if plan.get('id') == plan_id:
                        return plan
            return {}
        except Exception as e:
            logger.error(f"Error getting user plan for {user_id}, course {course_code}, plan {plan_id}: {e}")
            return {}

    async def load_course_plans(self, course_type: str) -> list:
        """Load plans for a specific course type"""
        try:
            # Create admin data directory structure if it doesn't exist
            os.makedirs('admin_data/course_plans', exist_ok=True)
            
            plans_file = f'admin_data/course_plans/{course_type}.json'
            
            # Special handling for nutrition_plan - check for both nutrition_plan.json and nutrition.json
            if course_type == 'nutrition_plan':
                primary_file = f'admin_data/course_plans/nutrition_plan.json'
                fallback_file = f'admin_data/course_plans/nutrition.json'
                
                if os.path.exists(primary_file):
                    plans_file = primary_file
                elif os.path.exists(fallback_file):
                    plans_file = fallback_file
                    # Optional: migrate data from nutrition.json to nutrition_plan.json
                    try:
                        import shutil
                        shutil.copy2(fallback_file, primary_file)
                        print(f"✅ Migrated nutrition plans from {fallback_file} to {primary_file}")
                        plans_file = primary_file
                    except Exception as e:
                        print(f"⚠️ Could not migrate nutrition plans: {e}, using fallback file")
                        plans_file = fallback_file
            
            # Check for old file in root directory and migrate if exists
            old_file = f'course_plans_{course_type}.json'
            if os.path.exists(old_file) and not os.path.exists(plans_file):
                import shutil
                shutil.move(old_file, plans_file)
                print(f"✅ Migrated {old_file} to {plans_file}")
            
            if os.path.exists(plans_file):
                with open(plans_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return []
        except Exception as e:
            print(f"Error loading plans for {course_type}: {e}")
            return []

    async def save_course_plans(self, course_type: str, plans: list) -> bool:
        """Save plans for a specific course type"""
        try:
            # Ensure admin data directory structure exists
            os.makedirs('admin_data/course_plans', exist_ok=True)
            
            # Special handling for nutrition_plan - always save to nutrition_plan.json
            if course_type == 'nutrition_plan':
                plans_file = 'admin_data/course_plans/nutrition_plan.json'
            elif course_type == 'nutrition':
                # If someone tries to save as 'nutrition', redirect to 'nutrition_plan.json'
                plans_file = 'admin_data/course_plans/nutrition_plan.json'
            else:
                plans_file = f'admin_data/course_plans/{course_type}.json'
            
            # Enhanced logging with more details
            print(f"🔧 PLAN SAVE DEBUG - Course: {course_type}, Plans count: {len(plans)}, File: {plans_file}")
            
            # Log save attempt with detailed info
            from admin_error_handler import admin_error_handler
            await admin_error_handler.log_plan_management_debug(
                admin_id=0,  # System operation
                operation='save_plans',
                course_type=course_type,
                plans_before=None,
                plans_after=len(plans),
                success=None,
                details={'plans_file': plans_file, 'total_plans': len(plans)}
            )
            
            # Check file permissions before attempting to write
            import stat
            if os.path.exists(plans_file):
                file_stat = os.stat(plans_file)
                file_perms = stat.filemode(file_stat.st_mode)
                print(f"📋 EXISTING FILE PERMISSIONS: {file_perms}")
            
            # Create backup of existing file first
            if os.path.exists(plans_file):
                backup_file = f'{plans_file}.backup'
                import shutil
                shutil.copy2(plans_file, backup_file)
                print(f"💾 BACKUP CREATED: {backup_file}")
            
            # Save new data with explicit encoding and error handling
            print(f"💾 ATTEMPTING TO WRITE {len(plans)} plans to {plans_file}")
            with open(plans_file, 'w', encoding='utf-8') as f:
                json.dump(plans, f, ensure_ascii=False, indent=2)
            
            print(f"✅ FILE WRITE COMPLETED")
            
            # Verify save by reading back
            print(f"🔍 VERIFYING SAVE BY READING BACK...")
            with open(plans_file, 'r', encoding='utf-8') as f:
                saved_plans = json.load(f)
                
            save_successful = len(saved_plans) == len(plans)
            print(f"📊 VERIFICATION RESULT - Expected: {len(plans)}, Found: {len(saved_plans)}, Success: {save_successful}")
            
            # Log save result
            await admin_error_handler.log_plan_management_debug(
                admin_id=0,
                operation='save_plans_verify',
                course_type=course_type,
                plans_before=len(plans),
                plans_after=len(saved_plans),
                success=save_successful,
                details={'verification': 'read_back_check'}
            )
            
            print(f"🎉 PLAN SAVE COMPLETED SUCCESSFULLY: {save_successful}")
            return save_successful
            
        except Exception as e:
            # Enhanced error logging
            print(f"❌ PLAN SAVE FAILED - Course: {course_type}, Error: {e}")
            print(f"❌ ERROR TYPE: {type(e).__name__}")
            print(f"❌ ERROR DETAILS: {str(e)}")
            
            # Log save failure
            from admin_error_handler import admin_error_handler
            await admin_error_handler.log_plan_management_debug(
                admin_id=0,
                operation='save_plans_failed',
                course_type=course_type,
                success=False,
                details={'error': str(e), 'error_type': type(e).__name__}
            )
            return False

    async def handle_plan_upload(self, query, course_type: str, context=None) -> None:
        """Handle plan upload request"""
        await query.answer()
        
        course_names = {
            'online_weights': '🏋️ وزنه آنلاین',
            'online_cardio': '🏃 هوازی آنلاین',
            'online_combo': '💪 ترکیبی آنلاین', 
            'in_person_cardio': '🏃‍♂️ هوازی حضوری',
            'in_person_weights': '🏋️‍♀️ وزنه حضوری'
        }
        
        course_name = course_names.get(course_type, course_type)
        user_id = query.from_user.id
        
        # Set upload state in context if available
        if context:
            if user_id not in context.user_data:
                context.user_data[user_id] = {}
            context.user_data[user_id]['uploading_plan'] = True
            context.user_data[user_id]['plan_course_type'] = course_type
            context.user_data[user_id]['plan_upload_step'] = 'title'
        
        text = f"""📤 آپلود برنامه جدید برای {course_name}

📋 فرمت‌های قابل قبول:
• فایل PDF
• تصاویر (JPG, PNG)
• متن (فایل متنی یا پیام)

💡 نحوه آپلود:
1️⃣ عنوان برنامه را بنویسید
2️⃣ فایل یا تصویر برنامه را ارسال کنید
3️⃣ توضیحات اضافی (اختیاری)

⏳ لطفاً ابتدا عنوان برنامه را بنویسید:"""
        
        keyboard = [[InlineKeyboardButton("🔙 انصراف", callback_data=f'plan_course_{course_type}')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup)

    async def handle_plan_callback_routing(self, query, context=None) -> None:
        """Route plan-related callbacks with error handling"""
        try:
            await admin_error_handler.log_admin_action(
                query.from_user.id, "plan_callback", {"callback_data": query.data}
            )
            
            logger.info(f"Handling plan callback: {query.data}")
            
            if query.data.startswith('plan_course_'):
                course_type = query.data.replace('plan_course_', '')
                await self.show_course_plan_management(query, course_type)
            elif query.data.startswith('upload_plan_'):
                course_type = query.data.replace('upload_plan_', '')
                await self.handle_plan_upload(query, course_type, context)
            elif query.data.startswith('send_plan_'):
                course_type = query.data.replace('send_plan_', '')
                await self.handle_send_plan_to_users(query, course_type)
            elif query.data.startswith('view_plans_'):
                course_type = query.data.replace('view_plans_', '')
                await self.show_existing_plans(query, course_type)
            else:
                logger.warning(f"Unhandled plan callback: {query.data}")
                await query.edit_message_text(
                    f"⚠️ دستور برنامه ناشناخته: {query.data}\n\n"
                    "🔄 بازگشت به مدیریت برنامه‌ها...",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 مدیریت برنامه‌ها", callback_data='admin_plans')
                    ]])
                )
                
        except Exception as e:
            await admin_error_handler.handle_admin_error(
                query, context, e, f"plan_callback_routing:{query.data}", query.from_user.id
            )

    async def handle_new_plan_callback_routing(self, query, context=None) -> None:
        """Route new person-centric plan management callbacks"""
        try:
            callback_data = query.data
            logger.info(f"🔄 NEW PLAN ROUTING: {callback_data}")
            
            await admin_error_handler.log_admin_action(
                query.from_user.id, "new_plan_callback", {"callback_data": callback_data}
            )
            
            if callback_data.startswith('upload_user_plan_'):
                # upload_user_plan_USER_ID_COURSE_CODE
                parts = callback_data.replace('upload_user_plan_', '').split('_')
                if len(parts) >= 3:
                    user_id = parts[0]
                    # Find course code - look for known patterns
                    if len(parts) >= 4 and parts[1] == 'in' and parts[2] == 'person':
                        course_code = f"{parts[1]}_{parts[2]}_{parts[3]}"  # in_person_cardio or in_person_weights
                    elif len(parts) >= 3 and parts[1] == 'online':
                        course_code = f"{parts[1]}_{parts[2]}"  # online_cardio, online_weights, online_combo
                    elif len(parts) >= 3 and parts[1] == 'nutrition' and parts[2] == 'plan':
                        course_code = f"{parts[1]}_{parts[2]}"  # nutrition_plan
                    else:
                        # Fallback - assume single word course code
                        course_code = parts[1]
                    await self.handle_user_plan_upload(query, user_id, course_code, context)
                else:
                    await query.answer("❌ خطا در تجزیه دستور!")
                
            elif callback_data.startswith('send_user_plan_'):
                # send_user_plan_USER_ID_COURSE_CODE_PLAN_ID
                # Parse more carefully: send_user_plan_293893885_in_person_cardio_plan_123
                parts = callback_data.replace('send_user_plan_', '').split('_')
                if len(parts) >= 4:  # Need at least user_id, course_part1, course_part2, plan_id
                    user_id = parts[0]
                    # Find course code - look for known patterns
                    if len(parts) >= 5 and parts[1] == 'in' and parts[2] == 'person':
                        course_code = f"{parts[1]}_{parts[2]}_{parts[3]}"  # in_person_cardio or in_person_weights
                        plan_id = '_'.join(parts[4:])
                    elif len(parts) >= 4 and parts[1] == 'online':
                        course_code = f"{parts[1]}_{parts[2]}"  # online_cardio, online_weights, online_combo
                        plan_id = '_'.join(parts[3:])
                    elif len(parts) >= 4 and parts[1] == 'nutrition' and parts[2] == 'plan':
                        course_code = f"{parts[1]}_{parts[2]}"  # nutrition_plan
                        plan_id = '_'.join(parts[3:])
                    else:
                        # Fallback - assume single word course code
                        course_code = parts[1]
                        plan_id = '_'.join(parts[2:])
                    await self.handle_send_user_plan(query, user_id, course_code, plan_id, context)
                else:
                    await query.answer("❌ خطا در تجزیه دستور!")
                    
            elif callback_data.startswith('view_user_plan_'):
                # view_user_plan_USER_ID_COURSE_CODE_PLAN_ID
                parts = callback_data.replace('view_user_plan_', '').split('_')
                if len(parts) >= 4:
                    user_id = parts[0]
                    # Find course code - look for known patterns
                    if len(parts) >= 5 and parts[1] == 'in' and parts[2] == 'person':
                        course_code = f"{parts[1]}_{parts[2]}_{parts[3]}"
                        plan_id = '_'.join(parts[4:])
                    elif len(parts) >= 4 and parts[1] == 'online':
                        course_code = f"{parts[1]}_{parts[2]}"
                        plan_id = '_'.join(parts[3:])
                    elif len(parts) >= 4 and parts[1] == 'nutrition' and parts[2] == 'plan':
                        course_code = f"{parts[1]}_{parts[2]}"  # nutrition_plan
                        plan_id = '_'.join(parts[3:])
                    else:
                        course_code = parts[1]
                        plan_id = '_'.join(parts[2:])
                    await self.handle_view_user_plan(query, user_id, course_code, plan_id)
                else:
                    await query.answer("❌ خطا در تجزیه دستور!")
                    
            elif callback_data.startswith('delete_user_plan_'):
                # delete_user_plan_USER_ID_COURSE_CODE_PLAN_ID
                parts = callback_data.replace('delete_user_plan_', '').split('_')
                if len(parts) >= 4:
                    user_id = parts[0]
                    if len(parts) >= 5 and parts[1] == 'in' and parts[2] == 'person':
                        course_code = f"{parts[1]}_{parts[2]}_{parts[3]}"
                        plan_id = '_'.join(parts[4:])
                    elif len(parts) >= 4 and parts[1] == 'online':
                        course_code = f"{parts[1]}_{parts[2]}"
                        plan_id = '_'.join(parts[3:])
                    elif len(parts) >= 4 and parts[1] == 'nutrition' and parts[2] == 'plan':
                        course_code = f"{parts[1]}_{parts[2]}"  # nutrition_plan
                        plan_id = '_'.join(parts[3:])
                    else:
                        course_code = parts[1]
                        plan_id = '_'.join(parts[2:])
                    await self.handle_delete_user_plan(query, user_id, course_code, plan_id)
                else:
                    await query.answer("❌ خطا در تجزیه دستور!")
                    
            elif callback_data.startswith('send_latest_plan_'):
                # send_latest_plan_USER_ID_COURSE_CODE
                parts = callback_data.replace('send_latest_plan_', '').split('_')
                if len(parts) >= 3:
                    user_id = parts[0]
                    if len(parts) >= 4 and parts[1] == 'in' and parts[2] == 'person':
                        course_code = f"{parts[1]}_{parts[2]}_{parts[3]}"
                    elif len(parts) >= 3 and parts[1] == 'online':
                        course_code = f"{parts[1]}_{parts[2]}"
                    elif len(parts) >= 3 and parts[1] == 'nutrition' and parts[2] == 'plan':
                        course_code = f"{parts[1]}_{parts[2]}"  # nutrition_plan
                    else:
                        course_code = parts[1]
                    await self.handle_send_latest_user_plan(query, user_id, course_code, context)
                else:
                    await query.answer("❌ خطا در تجزیه دستور!")
                
            else:
                await query.answer("❌ عملیات نامشخص!")
                
        except Exception as e:
            await admin_error_handler.handle_admin_error(
                query, context, e, f"new_plan_callback_routing:{query.data}", query.from_user.id
            )

    async def handle_user_plan_upload(self, query, user_id: str, course_code: str, context=None) -> None:
        """Handle plan upload for a specific user and course"""
        await query.answer()
        
        course_names = {
            'online_weights': '🏋️ وزنه آنلاین',
            'online_cardio': '🏃 هوازی آنلاین',
            'online_combo': '💪 ترکیبی آنلاین',
            'in_person_cardio': '🏃‍♂️ هوازی حضوری',
            'in_person_weights': '🏋️‍♀️ وزنه حضوری'
        }
        course_name = course_names.get(course_code, course_code)
        
        # Load user data to get name
        with open('bot_data.json', 'r', encoding='utf-8') as f:
            bot_data = json.load(f)
        user_data = bot_data.get('users', {}).get(user_id, {})
        user_name = user_data.get('name', 'نامشخص')
        
        # Set upload state in context if available
        if context:
            admin_id = query.from_user.id
            if admin_id not in context.user_data:
                context.user_data[admin_id] = {}
            context.user_data[admin_id]['uploading_user_plan'] = True
            context.user_data[admin_id]['plan_user_id'] = user_id
            context.user_data[admin_id]['plan_course_type'] = course_code  # Fixed: was plan_course_code
            context.user_data[admin_id]['plan_upload_step'] = 'title'
        
        text = f"""📤 آپلود برنامه شخصی

👤 کاربر: {user_name}
📚 دوره: {course_name}

📋 فرمت‌های قابل قبول:
• فایل PDF
• تصاویر (JPG, PNG)
• متن (فایل متنی یا پیام)

💡 نحوه آپلود:
1️⃣ عنوان برنامه را بنویسید
2️⃣ فایل یا تصویر برنامه را ارسال کنید
3️⃣ توضیحات اضافی (اختیاری)

⏳ لطفاً ابتدا عنوان برنامه را بنویسید:"""
        
        keyboard = [[InlineKeyboardButton("🔙 انصراف", callback_data=f'manage_user_course_{user_id}_{course_code}')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup)

    async def handle_send_user_plan(self, query, user_id: str, course_code: str, plan_id: str, context=None) -> None:
        """Send a specific plan to a specific user"""
        try:
            await query.answer("📤 در حال ارسال برنامه...")
            
            # Get plan data
            plan = await self.get_user_plan(user_id, course_code, plan_id)
            if not plan:
                await query.edit_message_text(
                    "❌ برنامه یافت نشد!",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 بازگشت", callback_data=f'manage_user_course_{user_id}_{course_code}')]
                    ])
                )
                return
            
            # Load user data
            with open('bot_data.json', 'r', encoding='utf-8') as f:
                bot_data = json.load(f)
            user_data = bot_data.get('users', {}).get(user_id, {})
            user_name = user_data.get('name', 'نامشخص')
            
            # Send plan to user - Updated for local file support with file_id fallback
            plan_content = plan.get('content')  # This is the Telegram file_id
            plan_local_path = plan.get('local_path')  # Local file path
            plan_content_type = plan.get('content_type', 'document')
            plan_title = plan.get('title', 'برنامه تمرینی')
            plan_filename = plan.get('filename', 'برنامه')
            
            if plan_local_path or plan_content:
                try:
                    caption = f"📋 {plan_title}\n\n💪 برنامه تمرینی شما آماده است!\n📄 فایل: {plan_filename}\n🕐 ارسال شده در: {datetime.now().strftime('%Y/%m/%d %H:%M')}"
                    
                    # Try to send from local file first
                    from plan_file_manager import plan_file_manager
                    sent_successfully = False
                    
                    if plan_local_path and plan_file_manager.file_exists(plan_local_path):
                        try:
                            # Send from local file
                            if plan_content_type == 'photo':
                                with open(plan_local_path, 'rb') as photo_file:
                                    await context.bot.send_photo(
                                        chat_id=int(user_id),
                                        photo=photo_file,
                                        caption=caption
                                    )
                            else:  # document
                                with open(plan_local_path, 'rb') as doc_file:
                                    await context.bot.send_document(
                                        chat_id=int(user_id),
                                        document=doc_file,
                                        caption=caption,
                                        filename=plan_filename
                                    )
                            sent_successfully = True
                            logger.info(f"Plan sent from local file: {plan_local_path}")
                        except Exception as local_error:
                            logger.warning(f"Failed to send from local file {plan_local_path}: {local_error}, trying file_id fallback")
                    
                    # Fallback to file_id if local file failed or doesn't exist
                    if not sent_successfully and plan_content:
                        # Validate file_id format first
                        if not isinstance(plan_content, str) or len(plan_content) < 10:
                            raise ValueError("Invalid file_id format")
                        
                        # Send using Telegram file_id directly
                        if plan_content_type == 'photo':
                            await context.bot.send_photo(
                                chat_id=int(user_id),
                                photo=plan_content,
                                caption=caption
                            )
                        else:  # document, or any other type - send as document
                            await context.bot.send_document(
                                chat_id=int(user_id),
                                document=plan_content,
                                caption=caption
                            )
                        logger.info(f"Plan sent using file_id: {plan_content[:20]}...")
                    
                    await query.edit_message_text(
                        f"✅ برنامه '{plan_title}' با موفقیت برای {user_name} ارسال شد!",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("🔙 بازگشت", callback_data=f'manage_user_course_{user_id}_{course_code}')]
                        ])
                    )
                    
                except Exception as send_error:
                    error_message = str(send_error)
                    
                    # Handle specific Telegram API errors
                    if "Wrong type of the web page content" in error_message:
                        error_details = "❌ فایل معتبر نیست یا منقضی شده است.\n\n🔧 راه حل:\n• از منوی تعمیر و نگهداری، گزینه 'بررسی فایل‌ها' را اجرا کنید\n• یا برنامه را مجدداً آپلود کنید"
                        
                        # Also mark this plan as needing reupload
                        plan['content_status'] = 'invalid_file_id'
                        plan['content_error'] = error_message
                        plan['needs_reupload'] = True
                        
                    elif "file_id" in error_message.lower():
                        error_details = "❌ شناسه فایل معتبر نیست.\n\n🔧 راه حل: لطفاً فایل را مجدداً آپلود کنید."
                    elif "Bad Request" in error_message:
                        error_details = "❌ خطا در درخواست ارسال.\n\n🔧 ممکن است فایل خراب یا نامعتبر باشد."
                    elif "Forbidden" in error_message:
                        error_details = "❌ کاربر ربات را مسدود کرده است یا دسترسی رد شده."
                    elif "network" in error_message.lower() or "timeout" in error_message.lower():
                        error_details = "❌ خطا در اتصال شبکه. لطفاً مجدداً تلاش کنید."
                    else:
                        error_details = f"❌ خطا در ارسال: {error_message}"
                    
                    # Log the detailed error for debugging
                    logging.error(f"Error sending plan to user {user_id}: {error_message}")
                    logging.error(f"Plan details - ID: {plan_id}, Content: {plan_content[:50]}..., Type: {plan_content_type}")
                    
                    await query.edit_message_text(
                        f"{error_details}\n\n💡 راه حل:\n• برنامه را دوباره آپلود کنید\n• از فرمت‌های معتبر استفاده کنید (PDF، JPG، PNG)\n• اندازه فایل کمتر از 50MB باشد",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("🔄 آپلود مجدد", callback_data=f'upload_user_plan_{user_id}_{course_code}')],
                            [InlineKeyboardButton("🔙 بازگشت", callback_data=f'manage_user_course_{user_id}_{course_code}')]
                        ])
                    )
            else:
                await query.edit_message_text(
                    "❌ فایل برنامه یافت نشد!",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 بازگشت", callback_data=f'manage_user_course_{user_id}_{course_code}')]
                    ])
                )
                
        except Exception as e:
            await admin_error_handler.handle_admin_error(
                query, None, e, f"handle_send_user_plan:{user_id}:{course_code}:{plan_id}", query.from_user.id
            )

    async def handle_view_user_plan(self, query, user_id: str, course_code: str, plan_id: str) -> None:
        """View details of a specific user plan"""
        try:
            await query.answer()
            
            plan = await self.get_user_plan(user_id, course_code, plan_id)
            if not plan:
                await query.edit_message_text(
                    "❌ برنامه یافت نشد!",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 بازگشت", callback_data=f'manage_user_course_{user_id}_{course_code}')]
                    ])
                )
                return
            
            # Load user data
            with open('bot_data.json', 'r', encoding='utf-8') as f:
                bot_data = json.load(f)
            user_data = bot_data.get('users', {}).get(user_id, {})
            user_name = user_data.get('name', 'نامشخص')
            
            plan_title = plan.get('title', 'برنامه ورزشی')
            plan_type = plan.get('content_type', 'document')
            created_at = plan.get('created_at', '')
            if created_at:
                formatted_date = created_at[:16].replace('T', ' ')
            else:
                formatted_date = 'نامشخص'
            file_name = plan.get('filename', 'نامشخص')
            description = plan.get('description', 'توضیحی ثبت نشده')
            
            text = f"""👁️ نمایش جزئیات برنامه

👤 کاربر: {user_name}
📋 عنوان: {plan_title}
📅 تاریخ آپلود: {formatted_date}
📄 نام فایل: {file_name}
📋 نوع: {plan_type}

📝 توضیحات:
{description}

💡 برای ارسال این برنامه به کاربر از دکمه 'ارسال' استفاده کنید."""
            
            keyboard = [
                [InlineKeyboardButton("📤 ارسال برنامه", callback_data=f'send_user_plan_{user_id}_{course_code}_{plan_id}')],
                [InlineKeyboardButton("🗑️ حذف برنامه", callback_data=f'delete_user_plan_{user_id}_{course_code}_{plan_id}')],
                [InlineKeyboardButton("🔙 بازگشت", callback_data=f'manage_user_course_{user_id}_{course_code}')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(text, reply_markup=reply_markup)
            
        except Exception as e:
            await admin_error_handler.handle_admin_error(
                query, None, e, f"handle_view_user_plan:{user_id}:{course_code}:{plan_id}", query.from_user.id
            )

    async def handle_delete_user_plan(self, query, user_id: str, course_code: str, plan_id: str) -> None:
        """Delete a specific user plan with confirmation"""
        try:
            await query.answer()
            
            plan = await self.get_user_plan(user_id, course_code, plan_id)
            if not plan:
                await query.edit_message_text(
                    "❌ برنامه یافت نشد!",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 بازگشت", callback_data=f'manage_user_course_{user_id}_{course_code}')]
                    ])
                )
                return
            
            # Load user data
            with open('bot_data.json', 'r', encoding='utf-8') as f:
                bot_data = json.load(f)
            user_data = bot_data.get('users', {}).get(user_id, {})
            user_name = user_data.get('name', 'نامشخص')
            
            plan_title = plan.get('title', 'نامشخص')
            
            text = f"""🗑️ حذف برنامه

👤 کاربر: {user_name}
📋 برنامه: {plan_title}

⚠️ آیا مطمئن هستید که می‌خواهید این برنامه را حذف کنید؟

❌ این عملیات قابل بازگشت نیست!"""
            
            keyboard = [
                [InlineKeyboardButton("✅ بله، حذف کن", callback_data=f'confirm_delete_{user_id}_{course_code}_{plan_id}')],
                [InlineKeyboardButton("❌ انصراف", callback_data=f'manage_user_course_{user_id}_{course_code}')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(text, reply_markup=reply_markup)
            
        except Exception as e:
            await admin_error_handler.handle_admin_error(
                query, None, e, f"handle_delete_user_plan:{user_id}:{course_code}:{plan_id}", query.from_user.id
            )

    async def handle_send_latest_user_plan(self, query, user_id: str, course_code: str, context=None) -> None:
        """Send the latest plan for a user and course"""
        try:
            await query.answer("📤 در حال ارسال آخرین برنامه...")
            
            user_plans = await self.load_user_plans(user_id)
            course_plans = user_plans.get(course_code, [])
            
            if not course_plans:
                await query.edit_message_text(
                    "❌ هیچ برنامه‌ای برای این کاربر و دوره یافت نشد!",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 بازگشت", callback_data=f'manage_user_course_{user_id}_{course_code}')]
                    ])
                )
                return
            
            # Get the latest plan (most recent upload) - use correct field name
            latest_plan = max(course_plans, key=lambda x: x.get('created_at', ''))
            plan_id = latest_plan.get('id')
            
            # Redirect to send_user_plan
            await self.handle_send_user_plan(query, user_id, course_code, plan_id, context)
            
        except Exception as e:
            await admin_error_handler.handle_admin_error(
                query, None, e, f"handle_send_latest_user_plan:{user_id}:{course_code}", query.from_user.id
            )

    async def handle_confirm_delete_user_plan(self, query, user_id: str, course_code: str, plan_id: str) -> None:
        """Confirm and delete a specific user plan"""
        try:
            await query.answer()
            
            plan = await self.get_user_plan(user_id, course_code, plan_id)
            if not plan:
                await query.edit_message_text(
                    "❌ برنامه یافت نشد!",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 بازگشت", callback_data=f'manage_user_course_{user_id}_{course_code}')]
                    ])
                )
                return
            
            # Delete the plan
            success = await self.delete_user_plan(user_id, course_code, plan_id)
            
            # Load user data for name
            with open('bot_data.json', 'r', encoding='utf-8') as f:
                bot_data = json.load(f)
            user_data = bot_data.get('users', {}).get(user_id, {})
            user_name = user_data.get('name', 'نامشخص')
            
            plan_title = plan.get('title', 'نامشخص')
            
            if success:
                # Try to delete the physical file as well
                file_path = plan.get('file_path')
                if file_path and os.path.exists(file_path):
                    try:
                        os.unlink(file_path)
                    except Exception as e:
                        logger.warning(f"Could not delete physical file {file_path}: {e}")
                
                await query.edit_message_text(
                    f"✅ برنامه '{plan_title}' برای کاربر {user_name} با موفقیت حذف شد!\n\n🔄 در حال بروزرسانی لیست برنامه‌ها...",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 بازگشت به لیست برنامه‌ها", callback_data=f'manage_user_course_{user_id}_{course_code}')]
                    ])
                )
            else:
                await query.edit_message_text(
                    f"❌ خطا در حذف برنامه '{plan_title}'!",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 بازگشت", callback_data=f'manage_user_course_{user_id}_{course_code}')]
                    ])
                )
            
        except Exception as e:
            await admin_error_handler.handle_admin_error(
                query, None, e, f"handle_confirm_delete_user_plan:{user_id}:{course_code}:{plan_id}", query.from_user.id
            )

    async def handle_send_plan_to_users(self, query, course_type: str) -> None:
        """Handle sending plans to specific users"""
        await query.answer()
        
        course_names = {
            'online_weights': '🏋️ وزنه آنلاین',
            'online_cardio': '🏃 هوازی آنلاین',
            'online_combo': '💪 ترکیبی آنلاین',
            'in_person_cardio': '🏃‍♂️ هوازی حضوری',
            'in_person_weights': '🏋️‍♀️ وزنه حضوری'
        }
        
        course_name = course_names.get(course_type, course_type)
        
        # Get users who have purchased this course
        users_with_course = await self.get_users_with_course(course_type)
        
        if not users_with_course:
            text = f"❌ هیچ کاربری برای دوره {course_name} یافت نشد!"
            keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data=f'plan_course_{course_type}')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, reply_markup=reply_markup)
            return
        
        keyboard = []
        for user_info in users_with_course[:10]:  # Show first 10 users
            user_id = user_info['user_id']
            user_name = user_info.get('name', 'بدون نام')
            keyboard.append([InlineKeyboardButton(f"👤 {user_name} ({user_id})", callback_data=f'send_to_user_{course_type}_{user_id}')])
        
        keyboard.append([InlineKeyboardButton("📤 ارسال به همه", callback_data=f'send_to_all_{course_type}')])
        keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data=f'plan_course_{course_type}')])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = f"""👥 ارسال برنامه به کاربران {course_name}

📊 تعداد کاربران: {len(users_with_course)} نفر

💡 انتخاب کنید:
• ارسال به کاربر خاص
• ارسال به همه کاربران این دوره

⚠️ نکته: ابتدا برنامه مورد نظر را آپلود کنید"""
        
        await query.edit_message_text(text, reply_markup=reply_markup)

    async def get_users_with_course(self, course_type: str) -> list:
        """Get list of users who have purchased a specific course"""
        try:
            with open('bot_data.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            users_with_course = []
            users = data.get('users', {})
            payments = data.get('payments', {})
            
            # Find users with approved payments for this course
            for payment_id, payment_data in payments.items():
                if (payment_data.get('course_type') == course_type and 
                    payment_data.get('status') == 'approved'):
                    user_id = payment_data.get('user_id')
                    if user_id and str(user_id) in users:
                        user_info = users[str(user_id)].copy()
                        user_info['user_id'] = user_id
                        users_with_course.append(user_info)
            
            return users_with_course
        except Exception as e:
            print(f"Error getting users with course {course_type}: {e}")
            return []

    async def show_course_plan_management(self, query, course_type: str) -> None:
        """Show plan management options for a specific course"""
        await query.answer()
        
        course_names = {
            'online_weights': '🏋️ وزنه آنلاین',
            'online_cardio': '🏃 هوازی آنلاین',
            'online_combo': '💪 ترکیبی آنلاین',
            'in_person_cardio': '🏃‍♂️ هوازی حضوری',
            'in_person_weights': '🏋️‍♀️ وزنه حضوری'
        }
        
        course_name = course_names.get(course_type, course_type)
        
        # Load plans to show counts
        all_plans = await self.load_course_plans(course_type)
        general_plans = [plan for plan in all_plans if not plan.get('is_user_specific', False)]
        user_specific_plans = [plan for plan in all_plans if plan.get('is_user_specific', False)]
        
        text = f"""📋 مدیریت برنامه‌های {course_name}

📊 آمار:
• برنامه‌های عمومی: {len(general_plans)} عدد
• برنامه‌های شخصی: {len(user_specific_plans)} عدد
• جمع کل: {len(all_plans)} عدد

🔧 عملیات موجود:"""
        
        keyboard = [
            [InlineKeyboardButton("📤 آپلود برنامه جدید", callback_data=f'upload_plan_{course_type}')],
            [InlineKeyboardButton("👁️ مشاهده برنامه‌های عمومی", callback_data=f'view_plans_{course_type}')],
            [InlineKeyboardButton("📤 ارسال برنامه به کاربران", callback_data=f'send_plan_{course_type}')],
            [InlineKeyboardButton("🔙 بازگشت به مدیریت برنامه‌ها", callback_data='admin_plans')]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup)

    async def show_existing_plans(self, query, course_type: str) -> None:
        """Show existing plans for a course (excluding user-specific plans)"""
        await query.answer()
        
        all_plans = await self.load_course_plans(course_type)
        
        # Filter out user-specific plans - only show general plans
        plans = [plan for plan in all_plans if not plan.get('is_user_specific', False)]
        
        if not plans:
            text = "❌ هیچ برنامه عمومی برای این دوره یافت نشد!\n\n💡 برنامه‌های شخصی کاربران در بخش مجزا نمایش داده می‌شوند."
            keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data=f'plan_course_{course_type}')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, reply_markup=reply_markup)
            return
        
        keyboard = []
        for i, plan in enumerate(plans[:10]):  # Show first 10 plans
            plan_title = plan.get('title', f'برنامه {i+1}')
            # Use the original index from all_plans to maintain correct references
            original_index = all_plans.index(plan)
            keyboard.append([InlineKeyboardButton(f"📋 {plan_title}", callback_data=f'view_plan_{course_type}_{original_index}')])
        
        keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data=f'plan_course_{course_type}')])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        course_names = {
            'online_weights': '🏋️ وزنه آنلاین',
            'online_cardio': '🏃 هوازی آنلاین',
            'online_combo': '💪 ترکیبی آنلاین',
            'in_person_cardio': '🏃‍♂️ هوازی حضوری', 
            'in_person_weights': '🏋️‍♀️ وزنه حضوری'
        }
        
        course_name = course_names.get(course_type, course_type)
        
        text = f"""📋 برنامه‌های موجود برای {course_name}

📊 تعداد: {len(plans)} برنامه

💡 روی هر برنامه کلیک کنید تا جزئیات آن را مشاهده کرده و بتوانید آن را ویرایش یا حذف کنید."""
        
        await query.edit_message_text(text, reply_markup=reply_markup)

    async def handle_skip_plan_description(self, query, context=None):
        """Handle skipping plan description step"""
        try:
            await query.answer()
            user_id = query.from_user.id
            
            logger.info(f"🔄 SKIP_DESCRIPTION - User {user_id} skipping description")
            logger.info(f"🔍 Context check: context={context is not None}, user_data={user_id in context.user_data if context else 'N/A'}")
            
            # Set empty description and complete upload
            if context and user_id in context.user_data:
                context.user_data[user_id]['plan_description'] = ''
                logger.info(f"✅ Set empty description for user {user_id}")
                logger.info(f"📦 User data keys: {list(context.user_data[user_id].keys())}")
            else:
                logger.error(f"❌ No context or user_data for user {user_id}")
                await query.message.reply_text("❌ خطای سیستم! لطفاً از ابتدا شروع کنید.")
                return
            
            # Get bot instance from context instead of importing main
            bot = context.bot_data.get('bot_instance') if context else None
            logger.info(f"🤖 Bot instance: {bot is not None}")
            if not bot:
                logger.error("❌ Bot instance not found in context.bot_data")
                await query.message.reply_text("❌ خطای سیستم! لطفاً مجددا تلاش کنید.")
                return
            
            # Create a dummy update object for complete_plan_upload
            # Need to create proper effective_user object
            class EffectiveUser:
                def __init__(self, user_id):
                    self.id = user_id
            
            class DummyUpdate:
                def __init__(self, user_id, message):
                    self.effective_user = EffectiveUser(user_id)
                    self.message = message
            
            logger.info(f"🚀 Calling complete_plan_upload for user {user_id}")
            dummy_update = DummyUpdate(user_id, query.message)
            await bot.complete_plan_upload(dummy_update, context)
            logger.info(f"✅ complete_plan_upload finished for user {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Exception in skip_plan_description: {type(e).__name__}: {str(e)}")
            await admin_error_handler.log_admin_error(
                user_id, e, "callback_query:skip_plan_description", update=None
            )
            await query.message.reply_text("❌ خطا در رد کردن توضیحات! لطفاً مجددا تلاش کنید.")

    # =====================================
    # MAIN PLAN ASSIGNMENT SYSTEM
    
    async def show_user_course_plan_management_enhanced(self, query, user_id: str, course_code: str) -> None:
        """Enhanced version of plan management with main plan assignment"""
        try:
            await query.answer()
            
            # Load user data and plans
            with open('bot_data.json', 'r', encoding='utf-8') as f:
                bot_data = json.load(f)
            
            user_data = bot_data.get('users', {}).get(user_id, {})
            user_name = user_data.get('name', 'نامشخص')
            
            user_plans = await self.load_user_plans(user_id)
            course_plans = user_plans.get(course_code, [])
            
            course_names = {
                'online_weights': '🏋️ وزنه آنلاین',
                'online_cardio': '🏃 هوازی آنلاین',
                'online_combo': '💪 ترکیبی آنلاین',
                'in_person_cardio': '🏃‍♂️ هوازی حضوری',
                'in_person_weights': '🏋️‍♀️ وزنه حضوری',
                'nutrition_plan': '🥗 برنامه غذایی'
            }
            course_name = course_names.get(course_code, course_code)
            
            keyboard = [
                [InlineKeyboardButton("📤 آپلود برنامه جدید", callback_data=f'upload_user_plan_{user_id}_{course_code}')]
            ]
            
            text = f"📋 مدیریت برنامه {course_name}\n"
            text += f"👤 کاربر: {user_name}\n\n"
            
            if course_plans:
                # Check current main plan
                current_main_plan = await self.get_main_plan_for_user_course(user_id, course_code)
                
                text += f"📚 برنامه‌های موجود ({len(course_plans)} عدد):\n"
                if current_main_plan:
                    text += f"⭐ برنامه اصلی فعلی: {current_main_plan}\n"
                text += "\n"
                
                # Sort plans by created date (newest first)
                sorted_plans = sorted(course_plans, key=lambda x: x.get('created_at', ''), reverse=True)
                
                for i, plan in enumerate(sorted_plans, 1):
                    created_at = plan.get('created_at', 'نامشخص')[:16].replace('T', ' ')
                    plan_type = plan.get('content_type', 'document')
                    file_name = plan.get('filename', 'نامشخص')
                    plan_id = plan.get('id', f'plan_{i}')
                    
                    # Check if this is the main plan
                    is_main_plan = (current_main_plan == plan_id)
                    main_indicator = " ⭐ (برنامه اصلی)" if is_main_plan else ""
                    
                    text += f"{i}. 📄 {file_name}{main_indicator}\n"
                    text += f"   📅 {created_at}\n"
                    text += f"   📋 نوع: {plan_type}\n"
                    
                    # Create buttons for each plan
                    plan_buttons = [
                        InlineKeyboardButton(f"📤 ارسال {i}", callback_data=f'send_user_plan_{user_id}_{course_code}_{plan_id}'),
                        InlineKeyboardButton(f"🗑 حذف {i}", callback_data=f'delete_user_plan_{user_id}_{course_code}_{plan_id}')
                    ]
                    
                    # Add main plan toggle button
                    if is_main_plan:
                        plan_buttons.append(InlineKeyboardButton("❌ حذف از اصلی", callback_data=f'unset_main_plan_{user_id}_{course_code}_{plan_id}'))
                    else:
                        plan_buttons.append(InlineKeyboardButton("⭐ انتخاب اصلی", callback_data=f'set_main_plan_{user_id}_{course_code}_{plan_id}'))
                    
                    keyboard.append(plan_buttons)
                    text += "\n"
                
                keyboard.append([InlineKeyboardButton("📤 ارسال آخرین برنامه", callback_data=f'send_latest_plan_{user_id}_{course_code}')])
            else:
                text += "📭 هنوز هیچ برنامه‌ای برای این کاربر و دوره آپلود نشده است.\n\n"
                text += "📤 برای شروع، روی 'آپلود برنامه جدید' کلیک کنید."
            
            keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data=f'user_plans_{user_id}')])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(text, reply_markup=reply_markup)
            
        except Exception as e:
            await admin_error_handler.handle_admin_error(
                query, None, e, f"show_user_course_plan_management:{user_id}:{course_code}", query.from_user.id
            )

    # MAIN PLAN ASSIGNMENT SYSTEM
    # =====================================
    
    async def get_main_plan_for_user_course(self, user_id: str, course_code: str) -> str:
        """Get the main plan ID assigned to a user for a specific course"""
        try:
            # Load main plan assignments
            main_plans_file = 'admin_data/main_plan_assignments.json'
            if os.path.exists(main_plans_file):
                with open(main_plans_file, 'r', encoding='utf-8') as f:
                    main_plans = json.load(f)
                
                return main_plans.get(f"{user_id}_{course_code}")
            
            return None
        except Exception as e:
            logger.error(f"Error getting main plan for user {user_id} course {course_code}: {e}")
            return None
    
    async def set_main_plan_for_user_course(self, user_id: str, course_code: str, plan_id: str) -> bool:
        """Set a plan as the main plan for a user's specific course"""
        try:
            # Load or create main plan assignments
            main_plans_file = 'admin_data/main_plan_assignments.json'
            main_plans = {}
            
            if os.path.exists(main_plans_file):
                with open(main_plans_file, 'r', encoding='utf-8') as f:
                    main_plans = json.load(f)
            
            # Set the main plan
            main_plans[f"{user_id}_{course_code}"] = plan_id
            
            # Create directory if it doesn't exist
            os.makedirs('admin_data', exist_ok=True)
            
            # Save updated assignments
            with open(main_plans_file, 'w', encoding='utf-8') as f:
                json.dump(main_plans, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            logger.error(f"Error setting main plan for user {user_id} course {course_code}: {e}")
            return False
    
    async def unset_main_plan_for_user_course(self, user_id: str, course_code: str) -> bool:
        """Remove main plan assignment for a user's specific course"""
        try:
            main_plans_file = 'admin_data/main_plan_assignments.json'
            if not os.path.exists(main_plans_file):
                return True  # Nothing to remove
            
            with open(main_plans_file, 'r', encoding='utf-8') as f:
                main_plans = json.load(f)
            
            # Remove the assignment if it exists
            key = f"{user_id}_{course_code}"
            if key in main_plans:
                del main_plans[key]
                
                # Save updated assignments
                with open(main_plans_file, 'w', encoding='utf-8') as f:
                    json.dump(main_plans, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            logger.error(f"Error unsetting main plan for user {user_id} course {course_code}: {e}")
            return False

    async def handle_set_main_plan(self, query, user_id: str, course_code: str, plan_id: str) -> None:
        """Handle setting a plan as main plan"""
        try:
            await query.answer("⭐ در حال تنظیم برنامه اصلی...")
            
            success = await self.set_main_plan_for_user_course(user_id, course_code, plan_id)
            
            if success:
                await query.answer("✅ برنامه اصلی تنظیم شد!", show_alert=True)
            else:
                await query.answer("❌ خطا در تنظیم برنامه اصلی!", show_alert=True)
            
            # Refresh the plan management interface
            await self.show_user_course_plan_management_enhanced(query, user_id, course_code)
            
        except Exception as e:
            await admin_error_handler.handle_admin_error(
                query, None, e, f"set_main_plan:{user_id}:{course_code}:{plan_id}", query.from_user.id
            )

    async def handle_unset_main_plan(self, query, user_id: str, course_code: str, plan_id: str) -> None:
        """Handle removing main plan designation"""
        try:
            await query.answer("🔸 در حال حذف برنامه اصلی...")
            
            success = await self.unset_main_plan_for_user_course(user_id, course_code)
            
            if success:
                await query.answer("✅ برنامه اصلی حذف شد!", show_alert=True)
            else:
                await query.answer("❌ خطا در حذف برنامه اصلی!", show_alert=True)
            
            # Refresh the plan management interface
            await self.show_user_course_plan_management_enhanced(query, user_id, course_code)
            
        except Exception as e:
            await admin_error_handler.handle_admin_error(
                query, None, e, f"unset_main_plan:{user_id}:{course_code}:{plan_id}", query.from_user.id
            )
    
    def _escape_markdown_v2(self, text: str) -> str:
        """Escape special characters for MarkdownV2"""
        if not text:
            return ""
        
        # List of characters that need to be escaped in MarkdownV2
        escape_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        
        escaped_text = text
        for char in escape_chars:
            escaped_text = escaped_text.replace(char, '\\' + char)
        
        return escaped_text
    
    async def validate_and_cleanup_file_ids(self, context) -> dict:
        """Validate all stored file_ids and clean up invalid ones"""
        results = {
            'total_plans': 0,
            'invalid_file_ids': 0,
            'cleaned_plans': [],
            'errors': [],
            'course_plans_checked': 0,
            'user_plans_checked': 0  
        }
        
        try:
            # Check course plans (global plan pool)
            course_plans_dir = 'admin_data/course_plans'
            if os.path.exists(course_plans_dir):
                course_types = ['online_weights', 'online_cardio', 'online_combo', 'in_person_cardio', 'in_person_weights', 'nutrition_plan']
                plans_updated = False
                
                for course_type in course_types:
                    plans_file = f'{course_plans_dir}/{course_type}.json'
                    if os.path.exists(plans_file):
                        try:
                            with open(plans_file, 'r', encoding='utf-8') as f:
                                course_plans = json.load(f)
                            
                            results['course_plans_checked'] += 1
                            
                            for plan in course_plans:
                                results['total_plans'] += 1
                                
                                plan_content = plan.get('content')
                                if plan_content and isinstance(plan_content, str):
                                    try:
                                        # Test if file_id is valid by attempting to get file info  
                                        await context.bot.get_file(plan_content)
                                        
                                    except Exception as e:
                                        # File_id is invalid
                                        results['invalid_file_ids'] += 1
                                        error_msg = str(e)
                                        
                                        if "Wrong type of the web page content" in error_msg or "file not found" in error_msg.lower():
                                            # Mark plan as having invalid file_id
                                            plan['content_status'] = 'invalid_file_id' 
                                            plan['content_error'] = error_msg
                                            plan['needs_reupload'] = True
                                            plans_updated = True
                                            
                                            results['cleaned_plans'].append({
                                                'location': 'course_plans',
                                                'course_type': course_type,
                                                'plan_id': plan.get('id', 'unknown'),
                                                'title': plan.get('title', 'بدون عنوان'),
                                                'error': error_msg[:100] + '...' if len(error_msg) > 100 else error_msg
                                            })
                            
                            # Save updated course plans if any invalid file_ids found
                            if plans_updated:
                                with open(plans_file, 'w', encoding='utf-8') as f:
                                    json.dump(course_plans, f, ensure_ascii=False, indent=2)
                        
                        except Exception as e:
                            results['errors'].append(f"Error checking {course_type}: {str(e)}")
            
            # Check user-specific plans
            if os.path.exists('user_plans.json'):
                try:
                    with open('user_plans.json', 'r', encoding='utf-8') as f:
                        plan_data = json.load(f)
                    
                    results['user_plans_checked'] = 1
                    user_plans_updated = False
                    
                    for user_id, user_plans in plan_data.items():
                        for course_code, course_plans in user_plans.items():
                            for plan_id, plan in course_plans.items():
                                results['total_plans'] += 1
                                
                                plan_content = plan.get('content')
                                if plan_content and isinstance(plan_content, str):
                                    try:
                                        # Test if file_id is valid by attempting to get file info
                                        await context.bot.get_file(plan_content)
                                        
                                    except Exception as e:
                                        # File_id is invalid
                                        results['invalid_file_ids'] += 1
                                        error_msg = str(e)
                                        
                                        if "Wrong type of the web page content" in error_msg or "file not found" in error_msg.lower():
                                            # Mark plan as having invalid file_id
                                            plan['content_status'] = 'invalid_file_id'
                                            plan['content_error'] = error_msg
                                            plan['needs_reupload'] = True
                                            user_plans_updated = True
                                            
                                            results['cleaned_plans'].append({
                                                'location': 'user_plans',
                                                'user_id': user_id,
                                                'course_code': course_code,
                                                'plan_id': plan_id,
                                                'title': plan.get('title', 'بدون عنوان'),
                                                'error': error_msg[:100] + '...' if len(error_msg) > 100 else error_msg
                                            })
                    
                    # Save updated user plans data
                    if user_plans_updated:
                        with open('user_plans.json', 'w', encoding='utf-8') as f:
                            json.dump(plan_data, f, ensure_ascii=False, indent=2)
                
                except Exception as e:
                    results['errors'].append(f"Error checking user_plans.json: {str(e)}")
            else:
                results['errors'].append("user_plans.json not found")
            
            if results['invalid_file_ids'] > 0:
                logger.info(f"Cleaned up {results['invalid_file_ids']} invalid file_ids from plans")
            
        except Exception as e:
            results['errors'].append(f"Error during validation: {str(e)}")
            logger.error(f"Error validating file_ids: {e}")
        
        return results
    
    async def show_file_validation_results(self, query, validation_results: dict):
        """Show results of file_id validation to admin"""
        total = validation_results['total_plans']
        invalid = validation_results['invalid_file_ids']
        course_plans_checked = validation_results.get('course_plans_checked', 0)
        user_plans_checked = validation_results.get('user_plans_checked', 0)
        
        if invalid == 0:
            text = f"✅ تمام فایل‌ها معتبر هستند!\n\n📊 آمار:\n• تعداد کل برنامه‌ها: {total}\n• فایل‌های معتبر: {total}\n• فایل‌های نامعتبر: 0\n\n🔍 منابع بررسی شده:\n• پول برنامه‌ها: {course_plans_checked} نوع دوره\n• برنامه‌های کاربران: {'✅' if user_plans_checked > 0 else '❌'}"
        else:
            text = f"⚠️ فایل‌های نامعتبر یافت شد!\n\n📊 آمار:\n• تعداد کل برنامه‌ها: {total}\n• فایل‌های معتبر: {total - invalid}\n• فایل‌های نامعتبر: {invalid}\n\n🔍 منابع بررسی شده:\n• پول برنامه‌ها: {course_plans_checked} نوع دوره\n• برنامه‌های کاربران: {'✅' if user_plans_checked > 0 else '❌'}\n\n"
            
            if validation_results['cleaned_plans']:
                text += "📋 برنامه‌های نیازمند آپلود مجدد:\n"
                for i, plan in enumerate(validation_results['cleaned_plans'][:5], 1):  # Show first 5
                    location_icon = "🏊‍♂️" if plan['location'] == 'course_plans' else "👤"
                    if plan['location'] == 'course_plans':
                        text += f"{i}. {location_icon} {plan['title']} (دوره: {plan.get('course_type', 'نامشخص')})\n"
                    else:
                        text += f"{i}. {location_icon} {plan['title']} (کاربر: {plan.get('user_id', 'نامشخص')})\n"
                
                if len(validation_results['cleaned_plans']) > 5:
                    text += f"... و {len(validation_results['cleaned_plans']) - 5} برنامه دیگر\n"
                
                text += "\n💡 برنامه‌های نامعتبر با علامت 'needs_reupload' مشخص شده‌اند"
        
        if validation_results['errors']:
            text += f"\n❌ خطاها:\n" + "\n".join(validation_results['errors'][:3])
        
        keyboard = [
            [InlineKeyboardButton("🔄 تست مجدد", callback_data='validate_file_ids')],
            [InlineKeyboardButton("🔙 بازگشت", callback_data='admin_maintenance')]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def show_maintenance_menu(self, query):
        """Show system maintenance menu"""
        text = """🔧 سیستم تعمیر و نگهداری
        
⚙️ ابزارهای تشخیص و رفع مشکل:

• 🔍 بررسی فایل‌ها - تشخیص فایل‌های نامعتبر
• 📊 بررسی سلامت سیستم  
• 🧹 پاکسازی فایل‌های موقت
• 📋 گزارش وضعیت کلی"""
        
        keyboard = [
            [InlineKeyboardButton("🔍 بررسی فایل‌ها", callback_data='validate_file_ids')],
            [InlineKeyboardButton("📊 بررسی سلامت", callback_data='system_health_check')],
            [InlineKeyboardButton("🧹 پاکسازی", callback_data='cleanup_temp_files')],
            [InlineKeyboardButton("🔙 بازگشت", callback_data='admin_panel')]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    def _get_course_name_farsi(self, course_code: str) -> str:
        """Convert course code to Persian name"""
        course_names = {
            'online_weights': 'وزنه آنلاین',
            'online_cardio': 'هوازی آنلاین', 
            'online_combo': 'ترکیبی آنلاین',
            'in_person_cardio': 'هوازی حضوری',
            'in_person_weights': 'وزنه حضوری',
            'nutrition_plan': 'برنامه غذایی',
            'انتخاب نشده': 'انتخاب نشده'
        }
        return course_names.get(course_code, course_code)
    
    async def handle_validate_file_ids(self, query, context):
        """Handle file_id validation request"""
        await query.answer("🔍 در حال بررسی فایل‌ها...")
        
        # Show progress message
        await query.edit_message_text(
            "🔍 در حال بررسی معتبر بودن فایل‌ها...\n\n⏳ لطفاً صبر کنید، این عملیات ممکن است چند دقیقه طول بکشد.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ لغو", callback_data='admin_maintenance')]
            ])
        )
        
        try:
            # Run validation
            validation_results = await self.validate_and_cleanup_file_ids(context)
            
            # Show results
            await self.show_file_validation_results(query, validation_results)
            
        except Exception as e:
            await query.edit_message_text(
                f"❌ خطا در بررسی فایل‌ها: {str(e)}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 بازگشت", callback_data='admin_maintenance')]
                ])
            )
    
    async def handle_system_health_check(self, query):
        """Handle system health check request"""
        await query.answer("📊 در حال بررسی سلامت سیستم...")
        
        try:
            import psutil
            import os
            
            # Get system info
            memory_info = psutil.virtual_memory()
            disk_info = psutil.disk_usage('.')
            
            # Check critical files
            critical_files = ['bot_data.json', 'user_plans.json', 'admins.json']
            file_status = []
            
            for file_path in critical_files:
                if os.path.exists(file_path):
                    size = os.path.getsize(file_path)
                    status = f"✅ {file_path} ({size:,} bytes)"
                else:
                    status = f"❌ {file_path} (غایب)"
                file_status.append(status)
            
            text = f"""📊 گزارش سلامت سیستم
            
🖥️ **حافظه:**
• کل: {memory_info.total // (1024**3):.1f} GB
• استفاده: {memory_info.percent:.1f}%
• در دسترس: {memory_info.available // (1024**3):.1f} GB

💾 **فضای ذخیره:**
• کل: {disk_info.total // (1024**3):.1f} GB  
• استفاده: {(disk_info.used / disk_info.total) * 100:.1f}%
• آزاد: {disk_info.free // (1024**3):.1f} GB

📁 **فایل‌های حیاتی:**
{chr(10).join(file_status)}

⏰ **زمان چک:** {datetime.now().strftime('%Y/%m/%d %H:%M:%S')}"""
            
            keyboard = [
                [InlineKeyboardButton("🔄 بروزرسانی", callback_data='system_health_check')],
                [InlineKeyboardButton("🔙 بازگشت", callback_data='admin_maintenance')]
            ]
            
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
            
        except Exception as e:
            await query.edit_message_text(
                f"❌ خطا در بررسی سلامت: {str(e)}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 بازگشت", callback_data='admin_maintenance')]
                ])
            )
    
    async def handle_cleanup_temp_files(self, query):
        """Handle temporary files cleanup"""
        await query.answer("🧹 در حال پاکسازی...")
        
        try:
            import os
            import tempfile
            import shutil
            
            cleaned_files = 0
            freed_space = 0
            
            # Clean temp directory
            temp_dir = tempfile.gettempdir()
            for filename in os.listdir(temp_dir):
                if filename.startswith('temp_doc_') or filename.startswith('temp_photo_'):
                    file_path = os.path.join(temp_dir, filename)
                    try:
                        file_size = os.path.getsize(file_path)
                        os.remove(file_path)
                        cleaned_files += 1
                        freed_space += file_size
                    except:
                        pass
            
            # Clean backup directory if it exists
            backup_dir = 'backups'
            if os.path.exists(backup_dir):
                for filename in os.listdir(backup_dir):
                    if filename.endswith('_CORRUPTED.json'):
                        file_path = os.path.join(backup_dir, filename)
                        try:
                            file_size = os.path.getsize(file_path)
                            os.remove(file_path)
                            cleaned_files += 1
                            freed_space += file_size
                        except:
                            pass
            
            text = f"""🧹 نتیجه پاکسازی
            
✅ **انجام شد:**
• {cleaned_files} فایل موقت حذف شد
• {freed_space // 1024:.1f} KB فضا آزاد شد

⏰ **زمان:** {datetime.now().strftime('%Y/%m/%d %H:%M:%S')}"""
            
            keyboard = [
                [InlineKeyboardButton("🔄 پاکسازی مجدد", callback_data='cleanup_temp_files')],
                [InlineKeyboardButton("🔙 بازگشت", callback_data='admin_maintenance')]
            ]
            
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
            
        except Exception as e:
            await query.edit_message_text(
                f"❌ خطا در پاکسازی: {str(e)}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 بازگشت", callback_data='admin_maintenance')]
                ])
            )
    
    async def show_file_validation_results(self, query, results):
        """Show file validation results"""
        if not results:
            text = "✅ همه فایل‌ها معتبر هستند!"
        else:
            invalid_count = len(results.get('invalid_file_ids', []))
            cleaned_count = len(results.get('cleaned_plans', []))
            
            text = f"""📊 نتایج بررسی فایل‌ها
            
❌ **فایل‌های نامعتبر:** {invalid_count}
🧹 **برنامه‌های پاکسازی شده:** {cleaned_count}

✅ **وضعیت:** {"همه فایل‌ها اکنون معتبر هستند" if cleaned_count > 0 else "نیازی به پاکسازی نبود"}

⏰ **زمان بررسی:** {datetime.now().strftime('%Y/%m/%d %H:%M:%S')}"""
        
        keyboard = [
            [InlineKeyboardButton("🔄 بررسی مجدد", callback_data='validate_file_ids')],
            [InlineKeyboardButton("🔙 بازگشت", callback_data='admin_maintenance')]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
