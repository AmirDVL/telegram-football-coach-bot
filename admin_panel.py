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
        self.admin_manager = AdminManager()
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
                update, query.data, user_id, success=True
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
                update, query.data, user_id, success=False, error=str(e)
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
        if callback_data == 'admin_stats':
            await self.show_statistics(query)
        elif callback_data == 'admin_users':
            await self.show_users_management(query)
        elif callback_data == 'admin_payments':
            await self.show_payments_management(query)
        elif callback_data == 'admin_export_menu':
            await self.show_export_menu(query)
        elif callback_data == 'admin_coupons':
            await self.show_coupon_management(query)
        elif callback_data == 'admin_plans':
            await self.show_plan_management(query)
        elif callback_data == 'admin_debug':
            await self.show_debug_panel(query, user_id)
            
        # Plan management callbacks - THIS IS THE FIX!
        elif callback_data.startswith(('plan_course_', 'upload_plan_', 'send_plan_', 'view_plans_', 'send_to_user_', 'send_to_all_', 'view_plan_')):
            logger.info(f"Routing plan management callback: {callback_data}")
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
            await self.export_user_personal_data(query, export_user_id)
        
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
            
            # Course statistics
            course_stats = {}
            for user_data in users.values():
                course = user_data.get('course')
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
            
            # Course statistics
            course_stats = {}
            for user_data in users.values():
                course = user_data.get('course')
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
                    'in_person_weights': 'وزنه حضوری'
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
    
    async def show_users_management(self, query) -> None:
        """Show users management"""
        try:
            with open('bot_data.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            users = data.get('users', {})
            
            text = "👥 مدیریت کاربران:\n\n"
            text += f"📊 تعداد کل: {len(users)} کاربر\n\n"
            
            # Show recent 10 users
            recent_users = list(users.items())[-10:]
            
            text += "🆕 آخرین کاربران:\n"
            for user_id, user_data in recent_users:
                name = user_data.get('name', 'نامشخص')
                username = user_data.get('username', '')
                course = user_data.get('course', 'انتخاب نشده')
                
                # Create clickable profile link
                if username:
                    profile_link = f"[{name}](https://t.me/{username})"
                else:
                    profile_link = f"[{name}](tg://user?id={user_id})"
                
                text += f"• {profile_link} ({user_id}) - {course}\n"
            
            keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی اصلی ادمین", callback_data='admin_back_main')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            await query.edit_message_text(f"❌ خطا: {str(e)}")
    
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
             InlineKeyboardButton("📋 مدیریت برنامه‌ها", callback_data='admin_plans')]
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
             InlineKeyboardButton(" اکسپورت داده‌ها", callback_data='admin_export_menu')],
            [InlineKeyboardButton("🎟️ مدیریت کوپن", callback_data='admin_coupons'),
             InlineKeyboardButton("📋 مدیریت برنامه‌ها", callback_data='admin_plans')],
            [InlineKeyboardButton("🔍 پنل دیباگ", callback_data='admin_debug')]
        ]
        
        if can_manage_admins:
            keyboard.append([InlineKeyboardButton("🔐 مدیریت ادمین‌ها", callback_data='admin_manage_admins')])
        
        keyboard.append([InlineKeyboardButton("👤 حالت کاربر", callback_data='admin_user_mode')])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        admin_type = "🔥 سوپر ادمین" if is_super else "👤 ادمین"
        welcome_text = f"🎛️ پنل مدیریت\n\nسلام {user_name}! 👋\n{admin_type} - مرکز فرماندهی ربات:\n\n📋 همه ابزارهای مدیریت در یک مکان"
        
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)

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
            
            if not questionnaire_data:
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
            for user_id, user_progress in questionnaire_data.items():
                answers = user_progress.get('answers', {})
                photos = answers.get('photos', {})
                
                # Count photos and create file_id list
                photo_count = 0
                photo_file_ids = []
                for step_photos in photos.values():
                    if isinstance(step_photos, list):
                        photo_count += len(step_photos)
                        photo_file_ids.extend(step_photos)  # These are file_ids, not file_paths
                
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
            
            # Send CSV file
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"questionnaire_export_{timestamp}.csv"
            
            await query.message.reply_document(
                document=io.BytesIO(csv_content.encode('utf-8')),
                filename=filename,
                caption=f"📤 صادرات پرسشنامه‌ها\n\n"
                       f"📊 تعداد: {len(questionnaire_data)} پرسشنامه\n"
                       f"📷 شامل اطلاعات عکس‌ها\n"
                       f"📅 تاریخ: {datetime.now().strftime('%Y/%m/%d %H:%M')}"
            )
            
            keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_export_menu')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("✅ فایل CSV پرسشنامه‌ها ارسال شد!", reply_markup=reply_markup)
            
        except Exception as e:
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
            
            for user_id, q_data in questionnaire_data.items():
                if q_data.get('completed', False):
                    user_info = users.get(user_id, {})
                    user_name = user_info.get('name', 'نامشخص')
                    user_phone = user_info.get('phone', 'نامشخص')
                    completion_date = q_data.get('completion_timestamp', q_data.get('completed_at', ''))
                    
                    # Count photos correctly from photos object
                    photos = q_data.get('answers', {}).get('photos', {})
                    photos_count = 0
                    for step_photos in photos.values():
                        if isinstance(step_photos, list):
                            photos_count += len(step_photos)
                    
                    # Count documents
                    documents = q_data.get('answers', {}).get('documents', {})
                    documents_count = len(documents)
                    
                    completed_users.append({
                        'user_id': user_id,
                        'name': user_name,
                        'phone': user_phone,
                        'completion_date': completion_date,
                        'photos_count': photos_count,
                        'documents_count': documents_count
                    })
            
            if not completed_users:
                await query.edit_message_text(
                    "📭 هیچ کاربری پرسشنامه تکمیل نکرده است!",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 بازگشت", callback_data='admin_export_menu')]
                    ])
                )
                return
            
            # Sort by completion date (newest first)
            completed_users.sort(key=lambda x: x['completion_date'], reverse=True)
            
            # Create buttons for each user (max 20 users to avoid message length issues)
            keyboard = []
            text = "👥 کاربران تکمیل‌کننده پرسشنامه:\n\n"
            
            for i, user in enumerate(completed_users[:20]):
                user_id = user['user_id']
                name = user['name']
                phone = user['phone']
                photos = user['photos_count']
                docs = user['documents_count']
                
                text += f"{i+1}. {name} ({phone})\n📷 {photos} عکس | 📎 {docs} سند\n\n"
                
                keyboard.append([InlineKeyboardButton(
                    f"{i+1}. {name} ({phone}) - 📷{photos} 📎{docs}",
                    callback_data=f'export_user_{user_id}'
                )])
            
            keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data='admin_export_menu')])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            if len(completed_users) > 20:
                text += f"\n⚠️ فقط 20 کاربر اول نمایش داده شد. کل: {len(completed_users)} کاربر"
            
            await query.edit_message_text(text, reply_markup=reply_markup)
            
        except Exception as e:
            await query.edit_message_text(f"❌ خطا در بارگذاری لیست کاربران: {str(e)}")

    async def export_user_personal_data(self, query, user_id: str) -> None:
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
            if user_questionnaire.get('answers'):
                for step, answer in user_questionnaire.get('answers', {}).items():
                    if isinstance(answer, dict) and answer.get('type') == 'photo':
                        photo_count += 1
                        local_path = answer.get('local_path')
                        file_ids = answer.get('file_ids', [])
                        
                        if local_path and os.path.exists(local_path):
                            photo_files.append((step, local_path))
                        elif file_ids:
                            # For migrated photos without local storage, we'll note them
                            # In a real bot environment, these could be downloaded using the file_ids
                            photo_files.append((step, f"[File IDs: {len(file_ids)} photos - not locally stored]"))
            
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
📎 اسناد ارسالی: {len(user_data.get('documents', []))}

"""
            
            # Add questionnaire answers
            if user_questionnaire.get('answers'):
                report += "\n📋 پاسخ‌های پرسشنامه:\n"
                for step, answer in user_questionnaire.get('answers', {}).items():
                    if isinstance(answer, dict):
                        if answer.get('type') == 'photo':
                            local_path = answer.get('local_path', 'مسیر نامشخص')
                            report += f"سوال {step}: [تصویر] {os.path.basename(local_path) if local_path != 'مسیر نامشخص' else 'فایل موجود نیست'}\n"
                        else:
                            report += f"سوال {step}: {answer.get('text', 'پاسخ نامشخص')}\n"
                    else:
                        report += f"سوال {step}: {answer}\n"
            
            # Add documents info
            documents = user_data.get('documents', [])
            if documents:
                report += "\n📎 اسناد ارسالی:\n"
                for i, doc in enumerate(documents, 1):
                    report += f"{i}. {doc.get('file_name', 'نامشخص')} ({doc.get('file_type', 'نامشخص')})\n"
                    report += f"   📅 {doc.get('upload_date', 'نامشخص')}\n"
                    report += f"   📁 {doc.get('file_path', 'مسیر نامشخص')}\n\n"
            
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
                photos_added = 0
                photos_noted = 0
                for step, photo_path in photo_files:
                    try:
                        if os.path.exists(photo_path):
                            # Create a meaningful filename
                            photo_extension = os.path.splitext(photo_path)[1]
                            photo_name = f"تصویر_قدم_{step}{photo_extension}"
                            zipf.write(photo_path, f"photos/{photo_name}")
                            photos_added += 1
                        elif "[File IDs:" in photo_path:
                            # Note migrated photos that aren't locally stored
                            note_content = f"Step {step}: {photo_path}\n"
                            zipf.writestr(f"migrated_photos_step_{step}.txt", note_content.encode('utf-8'))
                            photos_noted += 1
                    except Exception as e:
                        print(f"Error adding photo {photo_path}: {e}")
                
                # Add note about photos
                if photos_added > 0 or photos_noted > 0:
                    photo_note = f"📷 تصاویر در این بسته:\n"
                    if photos_added > 0:
                        photo_note += f"• {photos_added} تصویر محلی در پوشه photos\n"
                    if photos_noted > 0:
                        photo_note += f"• {photos_noted} تصویر قدیمی (فقط شناسه فایل - نیاز به دانلود مجدد)\n"
                    if photos_added < photo_count:
                        photo_note += f"⚠️ {photo_count - photos_added - photos_noted} تصویر به دلیل عدم دسترسی، اضافه نشد.\n"
                    zipf.writestr("راهنمای_تصاویر.txt", photo_note.encode('utf-8'))
            
            # Send the zip file
            with open(temp_zip_path, 'rb') as zip_file:
                await query.message.reply_document(
                    document=zip_file,
                    filename=zip_filename,
                    caption=f"📤 گزارش کامل کاربر {user_name}\n\n"
                           f"📋 شامل: گزارش متنی + {photos_added} تصویر محلی"
                           f"{f' + {photos_noted} تصویر قدیمی' if photos_noted > 0 else ''}\n"
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
                f"📷 تصاویر: {photos_added} فایل محلی"
                f"{f', {photos_noted} فایل قدیمی' if photos_noted > 0 else ''}",
                reply_markup=reply_markup
            )
            
        except Exception as e:
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
    # PLAN MANAGEMENT SYSTEM
    # =====================================
    
    async def show_plan_management(self, query) -> None:
        """Show the plan management main menu"""
        await query.answer()
        
        course_types = {
            'online_weights': '🏋️ وزنه آنلاین',
            'online_cardio': '🏃 هوازی آنلاین',
            'online_combo': '💪 ترکیبی آنلاین',
            'in_person_cardio': '🏃‍♂️ هوازی حضوری',
            'in_person_weights': '🏋️‍♀️ وزنه حضوری'
        }
        
        keyboard = []
        for course_code, course_name in course_types.items():
            keyboard.append([InlineKeyboardButton(f"📋 {course_name}", callback_data=f'plan_course_{course_code}')])
        
        keyboard.append([InlineKeyboardButton("🔙 بازگشت به پنل اصلی", callback_data='admin_back_main')])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = """📋 مدیریت برنامه‌های تمرینی

یکی از دوره‌ها را انتخاب کنید تا برنامه‌های آن را مدیریت کنید:

💡 برای هر دوره می‌توانید:
• برنامه‌های موجود را مشاهده کنید
• برنامه جدید آپلود کنید
• برنامه‌های قدیمی را ویرایش کنید
• برنامه‌ها را برای کاربران ارسال کنید"""
        
        await query.edit_message_text(text, reply_markup=reply_markup)

    async def show_course_plan_management(self, query, course_type: str) -> None:
        """Show plan management for a specific course with error handling"""
        try:
            await query.answer()
            
            await admin_error_handler.log_admin_action(
                query.from_user.id, "view_course_plans", {"course_type": course_type}
            )
            
            course_names = {
                'online_weights': '🏋️ وزنه آنلاین',
                'online_cardio': '🏃 هوازی آنلاین', 
                'online_combo': '💪 ترکیبی آنلاین',
                'in_person_cardio': '🏃‍♂️ هوازی حضوری',
                'in_person_weights': '🏋️‍♀️ وزنه حضوری'
            }
            
            course_name = course_names.get(course_type, course_type)
            
            # Load existing plans for this course
            plans = await self.load_course_plans(course_type)
            
            keyboard = [
                [InlineKeyboardButton("📤 آپلود برنامه جدید", callback_data=f'upload_plan_{course_type}')],
                [InlineKeyboardButton("👥 ارسال برنامه به کاربران", callback_data=f'send_plan_{course_type}')]
            ]
            
            if plans:
                keyboard.append([InlineKeyboardButton("📋 مشاهده برنامه‌های موجود", callback_data=f'view_plans_{course_type}')])
            
            keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data='admin_plans')])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            plan_count = len(plans)
            text = f"""📋 مدیریت برنامه‌های {course_name}

📊 تعداد برنامه‌های موجود: {plan_count}

💡 امکانات:
• آپلود برنامه جدید (PDF, تصویر، متن)
• ارسال برنامه‌ها به کاربران خاص
• مشاهده و ویرایش برنامه‌های موجود
• حذف برنامه‌های قدیمی"""
            
            await query.edit_message_text(text, reply_markup=reply_markup)
            
        except Exception as e:
            await admin_error_handler.handle_admin_error(
                query, None, e, f"show_course_plan_management:{course_type}", query.from_user.id
            )

    async def load_course_plans(self, course_type: str) -> list:
        """Load plans for a specific course type"""
        try:
            plans_file = f'course_plans_{course_type}.json'
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
            plans_file = f'course_plans_{course_type}.json'
            with open(plans_file, 'w', encoding='utf-8') as f:
                json.dump(plans, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Error saving plans for {course_type}: {e}")
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

    async def show_existing_plans(self, query, course_type: str) -> None:
        """Show existing plans for a course"""
        await query.answer()
        
        plans = await self.load_course_plans(course_type)
        
        if not plans:
            text = "❌ هیچ برنامه‌ای برای این دوره یافت نشد!"
            keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data=f'plan_course_{course_type}')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, reply_markup=reply_markup)
            return
        
        keyboard = []
        for i, plan in enumerate(plans[:10]):  # Show first 10 plans
            plan_title = plan.get('title', f'برنامه {i+1}')
            keyboard.append([InlineKeyboardButton(f"📋 {plan_title}", callback_data=f'view_plan_{course_type}_{i}')])
        
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
