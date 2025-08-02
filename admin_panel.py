from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from admin_manager import AdminManager
from data_manager import DataManager
from coupon_manager import CouponManager
from config import Config
import json
import csv
import io
from datetime import datetime

class AdminPanel:
    def __init__(self):
        self.admin_manager = AdminManager()
        self.data_manager = DataManager()
        self.coupon_manager = CouponManager()
        self.admin_creating_coupons = set()  # Track which admins are creating coupons
    
    async def admin_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Main admin menu"""
        user_id = update.effective_user.id
        
        if not await self.admin_manager.is_admin(user_id):
            await update.message.reply_text("❌ شما دسترسی ادمین ندارید.")
            return
        
        is_super = await self.admin_manager.is_super_admin(user_id)
        can_manage_admins = await self.admin_manager.can_add_admins(user_id)
        
        keyboard = [
            [InlineKeyboardButton("📊 آمار کلی", callback_data='admin_stats')],
            [InlineKeyboardButton("👥 مدیریت کاربران", callback_data='admin_users')],
            [InlineKeyboardButton("💳 مدیریت پرداخت‌ها", callback_data='admin_payments')],
            [InlineKeyboardButton("� اکسپورت", callback_data='admin_export_menu')]
        ]
        
        if can_manage_admins:
            keyboard.append([InlineKeyboardButton("🔐 مدیریت ادمین‌ها", callback_data='admin_manage_admins')])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        admin_type = "🔥 سوپر ادمین" if is_super else "👤 ادمین"
        welcome_text = f"سلام {admin_type}!\n\nبه پنل مدیریت خوش آمدید 🎛️"
        
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)
    
    async def handle_admin_callbacks(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle admin panel callbacks"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        
        if not await self.admin_manager.is_admin(user_id):
            await query.edit_message_text("❌ شما دسترسی ادمین ندارید.")
            return
        
        if query.data == 'admin_stats':
            await self.show_statistics(query)
        elif query.data == 'admin_users':
            await self.show_users_management(query)
        elif query.data == 'admin_payments':
            await self.show_payments_management(query)
        elif query.data == 'admin_export_menu':
            await self.show_export_menu(query)
        elif query.data == 'admin_coupons':
            await self.show_coupon_management(query)
        elif query.data == 'admin_export_users':
            await self.export_users_csv(query)
        elif query.data == 'admin_export_payments':
            await self.export_payments_csv(query)
        elif query.data == 'admin_export_questionnaire':
            await self.export_questionnaire_csv(query)
        elif query.data == 'admin_export_person':
            await self.show_completed_users_list(query)
        elif query.data == 'admin_export_telegram':
            await self.export_telegram_csv(query)
        elif query.data == 'admin_export_all':
            await self.export_all_data(query)
        elif query.data == 'admin_template_users':
            await self.generate_users_template(query)
        elif query.data == 'admin_template_payments':
            await self.generate_payments_template(query)
        elif query.data.startswith('export_user_'):
            # Handle user-specific export
            user_id = query.data.replace('export_user_', '')
            await self.export_user_personal_data(query, user_id)
        elif query.data == 'admin_view_coupons':
            await self.show_coupons_list(query)
        elif query.data == 'admin_create_coupon':
            await self.handle_create_coupon(query, user_id)
        elif query.data == 'admin_toggle_coupon':
            await self.handle_toggle_coupon(query)
        elif query.data == 'admin_delete_coupon':
            await self.handle_delete_coupon(query)
        elif query.data == 'admin_manage_admins':
            await self.show_admin_management(query, user_id)
        elif query.data == 'admin_cleanup_non_env':
            await self.handle_cleanup_non_env_admins(query, user_id)
        elif query.data.startswith('admin_add_admin_'):
            await self.handle_add_admin(query, user_id)
        elif query.data.startswith('admin_remove_admin_'):
            await self.handle_remove_admin(query, user_id)
        elif query.data.startswith('toggle_coupon_'):
            await self.process_toggle_coupon(query)
        elif query.data.startswith('delete_coupon_'):
            await self.process_delete_coupon(query)
        elif query.data == 'admin_back_main':
            await self.back_to_admin_main(query, user_id)
        elif query.data == 'admin_back_start':
            await self.back_to_admin_start(query, user_id)
        elif query.data == 'admin_menu':
            # Fix: handle coupon menu back button
            await self.admin_menu_callback(query)
    
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
                    'online_combo': 'ترکیبی آنلاین',
                    'in_person_cardio': 'هوازی حضوری',
                    'in_person_weights': 'وزنه حضوری'
                }.get(course, course)
                
                stats_text += f"\n• {course_name}: {count} نفر"
            
            keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_back_main')]]
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
        
        keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data='admin_back_main')])
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
            
            keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_back_main')]]
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
                course = payment_data.get('course_type', 'نامشخص')
                text += f"• {user_id} - {price:,} تومان ({course})\n"
            
            keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_back_main')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(text, reply_markup=reply_markup)
            
        except Exception as e:
            await query.edit_message_text(f"❌ خطا: {str(e)}")
    
    async def back_to_admin_main(self, query, user_id: int) -> None:
        """Return to unified admin command hub"""
        await self.show_unified_admin_panel(query, user_id)
    
    async def back_to_admin_start(self, query, user_id: int) -> None:
        """Return to unified admin command hub (legacy compatibility)"""
        await self.show_unified_admin_panel(query, user_id)
    
    async def show_unified_admin_panel(self, query, user_id: int) -> None:
        """Unified admin command hub - the ONLY admin panel"""
        is_super = await self.admin_manager.is_super_admin(user_id)
        can_manage_admins = await self.admin_manager.can_add_admins(user_id)
        user_name = query.from_user.first_name or "ادمین"
        
        keyboard = [
            [InlineKeyboardButton("📊 آمار کلی", callback_data='admin_stats'),
             InlineKeyboardButton("📈 آمار سریع", callback_data='admin_quick_stats')],
            [InlineKeyboardButton("� مدیریت کاربران", callback_data='admin_users'),
             InlineKeyboardButton("💳 مدیریت پرداخت‌ها", callback_data='admin_payments')],
            [InlineKeyboardButton("💳 پرداخت‌های معلق", callback_data='admin_pending_payments'),
             InlineKeyboardButton("👥 کاربران جدید", callback_data='admin_new_users')],
            [InlineKeyboardButton("� اکسپورت", callback_data='admin_export_menu'),
             InlineKeyboardButton("🎟️ مدیریت کوپن", callback_data='admin_coupons')]
        ]
        
        if can_manage_admins:
            keyboard.append([InlineKeyboardButton("🔐 مدیریت ادمین‌ها", callback_data='admin_manage_admins')])
        
        keyboard.append([InlineKeyboardButton("👤 حالت کاربر", callback_data='admin_user_mode')])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        admin_type = "🔥 سوپر ادمین" if is_super else "👤 ادمین"
        welcome_text = f"🎛️ Admin Command Hub\n\nسلام {user_name}! 👋\n{admin_type} - مرکز فرماندهی ربات:\n\n📋 همه ابزارهای مدیریت در یک مکان"
        
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
                        "🔙 بازگشت به منوی ادمین‌ها",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_manage_admins')]])
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
                        "🔙 بازگشت به منوی ادمین‌ها",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_manage_admins')]])
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
                "🔙 بازگشت به منوی ادمین‌ها",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_manage_admins')]])
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
        """Comprehensive admin panel accessible via callback"""
        user_id = query.from_user.id
        
        if not await self.admin_manager.is_admin(user_id):
            await query.edit_message_text("❌ شما دسترسی ادمین ندارید.")
            return
        
        is_super = await self.admin_manager.is_super_admin(user_id)
        can_manage_admins = await self.admin_manager.can_add_admins(user_id)
        
        keyboard = [
            [InlineKeyboardButton("📊 آمار کلی", callback_data='admin_stats'),
             InlineKeyboardButton("📈 آمار سریع", callback_data='admin_quick_stats')],
            [InlineKeyboardButton("👥 مدیریت کاربران", callback_data='admin_users'),
             InlineKeyboardButton("💳 مدیریت پرداخت‌ها", callback_data='admin_payments')],
            [InlineKeyboardButton("� اکسپورت", callback_data='admin_export_menu'),
             InlineKeyboardButton("🎟️ مدیریت کوپن", callback_data='admin_coupons')]
        ]
        
        if can_manage_admins:
            keyboard.append([InlineKeyboardButton("🔐 مدیریت ادمین‌ها", callback_data='admin_manage_admins')])
        
        keyboard.append([InlineKeyboardButton("🔙 بازگشت به منو", callback_data='admin_back_main')])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        admin_type = "🔥 سوپر ادمین" if is_super else "👤 ادمین"
        welcome_text = f"🎛️ پنل مدیریت کامل\n\n{admin_type} - همه‌ی ابزارهای مدیریت:"
        
        await query.edit_message_text(welcome_text, reply_markup=reply_markup)
    
    async def show_quick_statistics(self, query) -> None:
        """Show quick statistics for admin start menu"""
        try:
            with open('bot_data.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            users = data.get('users', {})
            payments = data.get('payments', {})
            
            total_users = len(users)
            pending_payments = len([p for p in payments.values() if p.get('status') == 'pending_approval'])
            approved_payments = len([p for p in payments.values() if p.get('status') == 'approved'])
            total_revenue = sum(payment.get('price', 0) for payment in payments.values() if payment.get('status') == 'approved')
            
            stats_text = f"""📊 آمار سریع:

👥 کل کاربران: {total_users}
⏳ پرداخت‌های معلق: {pending_payments}
✅ پرداخت‌های تایید شده: {approved_payments}
💰 درآمد کل: {total_revenue:,} تومان"""
            
            keyboard = [
                [InlineKeyboardButton("📊 آمار کامل", callback_data='admin_stats')],
                [InlineKeyboardButton("🔙 منوی ادمین", callback_data='admin_back_main')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(stats_text, reply_markup=reply_markup)
            
        except Exception as e:
            await query.edit_message_text(f"❌ خطا در بارگیری آمار: {str(e)}")
    
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
                [InlineKeyboardButton("🔙 منوی ادمین", callback_data='admin_back_main')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(text, reply_markup=reply_markup)
            
        except Exception as e:
            await query.edit_message_text(f"❌ خطا در بارگیری پرداخت‌ها: {str(e)}")
    
    async def show_new_users(self, query) -> None:
        """Show new users for quick admin access"""
        try:
            with open('bot_data.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            users = data.get('users', {})
            
            # Sort by registration (users with payments are considered "new" if recent)
            new_users = []
            for user_id, user_data in users.items():
                if user_data.get('started_bot', False):
                    new_users.append((user_id, user_data))
            
            # Get the 10 most recent users
            recent_users = new_users[-10:] if len(new_users) > 10 else new_users
            
            if not recent_users:
                text = "🤷‍♂️ هیچ کاربر جدیدی یافت نشد."
            else:
                text = f"👥 کاربران اخیر ({len(recent_users)} نفر):\n\n"
                for user_id, user_data in recent_users:
                    name = user_data.get('name', 'نامشخص')
                    course = user_data.get('course', 'بدون دوره')
                    status = user_data.get('payment_status', 'نامشخص')
                    text += f"👤 {name} ({user_id})\n📚 {course} - {status}\n\n"
            
            keyboard = [
                [InlineKeyboardButton("👥 مدیریت کامل کاربران", callback_data='admin_users')],
                [InlineKeyboardButton("🔙 منوی ادمین", callback_data='admin_back_main')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(text, reply_markup=reply_markup)
            
        except Exception as e:
            await query.edit_message_text(f"❌ خطا در بارگیری کاربران: {str(e)}")

    # � EXPORT FUNCTIONALITY
    async def show_export_menu(self, query) -> None:
        """Show export options menu"""
        text = """� اکسپورت

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
                'تعداد_عکس', 'مسیرهای_عکس', 'بهبود_بدنی', 'شبکه‌های_اجتماعی', 'شماره_تماس',
                'تاریخ_شروع', 'تاریخ_تکمیل', 'وضعیت_تکمیل'
            ]
            writer.writerow(headers)
            
            # Write questionnaire data
            for user_id, user_progress in questionnaire_data.items():
                answers = user_progress.get('answers', {})
                photos = answers.get('photos', {})
                
                # Count photos and create paths list
                photo_count = 0
                photo_paths = []
                for step_photos in photos.values():
                    if isinstance(step_photos, list):
                        photo_count += len(step_photos)
                        photo_paths.extend([photo.get('file_path', '') for photo in step_photos])
                
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
                    '|'.join(photo_paths), # مسیرهای عکس (جدا شده با |)
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
                    
                    # Count photos and documents
                    photos_count = len([a for a in q_data.get('answers', {}).values() if isinstance(a, dict) and a.get('type') == 'photo'])
                    documents_count = len(user_info.get('documents', []))
                    
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
            
            # Create comprehensive user report
            report = f"""📋 گزارش کامل کاربر: {user_name}

👤 اطلاعات شخصی:
• نام: {user_data.get('name', 'نامشخص')}
• تلفن: {user_data.get('phone', 'نامشخص')}
• شناسه: {user_id}
• دوره: {user_data.get('course_selected', 'نامشخص')}
• وضعیت پرداخت: {user_data.get('payment_status', 'نامشخص')}

📝 پرسشنامه:
• وضعیت: {'تکمیل شده' if user_questionnaire.get('completed') else 'تکمیل نشده'}
• تاریخ تکمیل: {user_questionnaire.get('completion_timestamp', user_questionnaire.get('completed_at', 'نامشخص'))}

📷 تصاویر پرسشنامه: {len([a for a in user_questionnaire.get('answers', {}).values() if isinstance(a, dict) and a.get('type') == 'photo'])}
📎 اسناد ارسالی: {len(user_data.get('documents', []))}

"""
            
            # Add questionnaire answers
            if user_questionnaire.get('answers'):
                report += "\n📋 پاسخ‌های پرسشنامه:\n"
                for step, answer in user_questionnaire.get('answers', {}).items():
                    if isinstance(answer, dict):
                        if answer.get('type') == 'photo':
                            report += f"سوال {step}: [تصویر] {answer.get('file_path', 'مسیر نامشخص')}\n"
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
            
            # Send as text file
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"user_report_{user_id}_{timestamp}.txt"
            
            await query.message.reply_document(
                document=io.BytesIO(report.encode('utf-8')),
                filename=filename,
                caption=f"📤 گزارش کامل کاربر {user_name}\n\n"
                       f"📅 تاریخ تولید: {datetime.now().strftime('%Y/%m/%d %H:%M')}"
            )
            
            keyboard = [
                [InlineKeyboardButton("🔙 بازگشت به لیست", callback_data='admin_export_person')],
                [InlineKeyboardButton("📋 منوی اصلی", callback_data='admin_export_menu')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"✅ گزارش کامل {user_name} ارسال شد!\n\n"
                f"📋 شامل: اطلاعات شخصی، پاسخ‌های پرسشنامه، مسیر تصاویر و اسناد",
                reply_markup=reply_markup
            )
            
        except Exception as e:
            await query.edit_message_text(f"❌ خطا در تولید گزارش: {str(e)}")

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
