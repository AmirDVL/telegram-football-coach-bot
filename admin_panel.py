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
            [InlineKeyboardButton("📥 واردات/صادرات داده", callback_data='admin_import_export')]
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
        elif query.data == 'admin_import_export':
            await self.show_import_export_menu(query)
        elif query.data == 'admin_coupons':
            await self.show_coupon_management(query)
        elif query.data == 'admin_export_users':
            await self.export_users_csv(query)
        elif query.data == 'admin_export_payments':
            await self.export_payments_csv(query)
        elif query.data == 'admin_export_telegram':
            await self.export_telegram_csv(query)
        elif query.data == 'admin_export_all':
            await self.export_all_data(query)
        elif query.data == 'admin_template_users':
            await self.generate_users_template(query)
        elif query.data == 'admin_template_payments':
            await self.generate_payments_template(query)
        elif query.data == 'admin_import_users':
            await self.show_import_instructions(query, 'users')
        elif query.data == 'admin_import_payments':
            await self.show_import_instructions(query, 'payments')
        elif query.data == 'admin_view_coupons':
            await self.show_coupons_list(query)
        elif query.data == 'admin_manage_admins':
            await self.show_admin_management(query, user_id)
        elif query.data == 'admin_cleanup_non_env':
            await self.handle_cleanup_non_env_admins(query, user_id)
        elif query.data.startswith('admin_add_admin_'):
            await self.handle_add_admin(query, user_id)
        elif query.data.startswith('admin_remove_admin_'):
            await self.handle_remove_admin(query, user_id)
        elif query.data == 'admin_back_main':
            await self.back_to_admin_main(query, user_id)
        elif query.data == 'admin_back_start':
            await self.back_to_admin_start(query, user_id)
    
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
            
            stats_text = f"""📊 آمار کلی ربات:

👥 تعداد کل کاربران: {total_users}
💳 تعداد کل پرداخت‌ها: {total_payments}
  ✅ تایید شده: {approved_payments}
  ⏳ در انتظار: {pending_payments}
  ❌ رد شده: {rejected_payments}
💰 درآمد کل (تایید شده): {total_revenue:,} تومان

📚 آمار دوره‌ها:"""
            
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
        
        if Config.USE_DATABASE:
            # Database mode - use AdminManager
            admins = await self.admin_manager.get_all_admins()
            
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
        
        # Add cleanup button for super admins if there are manual admins
        if is_super and manual_admins:
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
                course = user_data.get('course', 'انتخاب نشده')
                text += f"• {name} ({user_id}) - {course}\n"
            
            keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_back_main')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(text, reply_markup=reply_markup)
            
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
        """Return to admin main menu"""
        is_super = await self.admin_manager.is_super_admin(user_id)
        can_manage_admins = await self.admin_manager.can_add_admins(user_id)
        
        keyboard = [
            [InlineKeyboardButton("📊 آمار کلی", callback_data='admin_stats')],
            [InlineKeyboardButton("👥 مدیریت کاربران", callback_data='admin_users')],
            [InlineKeyboardButton("💳 مدیریت پرداخت‌ها", callback_data='admin_payments')],
            [InlineKeyboardButton("📥 واردات/صادرات داده", callback_data='admin_import_export')]
        ]
        
        if can_manage_admins:
            keyboard.append([InlineKeyboardButton("🔐 مدیریت ادمین‌ها", callback_data='admin_manage_admins')])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        admin_type = "🔥 سوپر ادمین" if is_super else "👤 ادمین"
        welcome_text = f"سلام {admin_type}!\n\nبه پنل مدیریت خوش آمدید 🎛️"
        
        await query.edit_message_text(welcome_text, reply_markup=reply_markup)
    
    async def back_to_admin_start(self, query, user_id: int) -> None:
        """Return to admin start menu"""
        is_super = await self.admin_manager.is_super_admin(user_id)
        can_manage_admins = await self.admin_manager.can_add_admins(user_id)
        user_name = query.from_user.first_name or "ادمین"
        
        keyboard = [
            [InlineKeyboardButton("🎛️ پنل مدیریت", callback_data='admin_panel_main')],
            [InlineKeyboardButton("📊 آمار سریع", callback_data='admin_quick_stats')],
            [InlineKeyboardButton("💳 پرداخت‌های معلق", callback_data='admin_pending_payments')],
            [InlineKeyboardButton("👥 کاربران جدید", callback_data='admin_new_users')]
        ]
        
        if can_manage_admins:
            keyboard.append([InlineKeyboardButton("🔐 مدیریت ادمین‌ها", callback_data='admin_manage_admins')])
        
        keyboard.append([InlineKeyboardButton("👤 حالت کاربر عادی", callback_data='admin_user_mode')])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        admin_type = "🔥 سوپر ادمین" if is_super else "👤 ادمین"
        welcome_text = f"سلام {user_name}! 👋\n\n{admin_type} عزیز، به ربات مربی فوتبال خوش آمدید 🎛️\n\nانتخاب کنید:"
        
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
                        admin.get('synced_from_config') == True or  # Current JSON format
                        admin.get('force_synced') == True or       # Current JSON format
                        admin_id in env_admin_ids                  # Always preserve env IDs
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
                            user_id = str(admin.get('user_id'))
                            admin_copy = admin.copy()
                            admin_copy.pop('user_id', None)  # Remove user_id from the data since it's the key
                            remaining_admins_dict[user_id] = admin_copy
                    
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
        """Admin menu accessible via callback (from admin start menu)"""
        user_id = query.from_user.id
        
        if not await self.admin_manager.is_admin(user_id):
            await query.edit_message_text("❌ شما دسترسی ادمین ندارید.")
            return
        
        is_super = await self.admin_manager.is_super_admin(user_id)
        can_manage_admins = await self.admin_manager.can_add_admins(user_id)
        
        keyboard = [
            [InlineKeyboardButton("📊 آمار کلی", callback_data='admin_stats')],
            [InlineKeyboardButton("👥 مدیریت کاربران", callback_data='admin_users')],
            [InlineKeyboardButton("💳 مدیریت پرداخت‌ها", callback_data='admin_payments')]
        ]
        
        if can_manage_admins:
            keyboard.append([InlineKeyboardButton("🔐 مدیریت ادمین‌ها", callback_data='admin_manage_admins')])
        
        keyboard.append([InlineKeyboardButton("🔙 منوی ادمین", callback_data='admin_back_start')])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        admin_type = "🔥 سوپر ادمین" if is_super else "👤 ادمین"
        welcome_text = f"🎛️ پنل مدیریت کامل\n\n{admin_type} - انتخاب کنید:"
        
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
                [InlineKeyboardButton("🔙 منوی ادمین", callback_data='admin_back_start')]
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
                [InlineKeyboardButton("🔙 منوی ادمین", callback_data='admin_back_start')]
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
                [InlineKeyboardButton("🔙 منوی ادمین", callback_data='admin_back_start')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(text, reply_markup=reply_markup)
            
        except Exception as e:
            await query.edit_message_text(f"❌ خطا در بارگیری کاربران: {str(e)}")

    # 📥 IMPORT/EXPORT FUNCTIONALITY
    async def show_import_export_menu(self, query) -> None:
        """Show import/export options menu"""
        text = """📥 مدیریت واردات/صادرات داده

انتخاب کنید:"""
        
        keyboard = [
            [InlineKeyboardButton("📤 صادرات کاربران (CSV)", callback_data='admin_export_users')],
            [InlineKeyboardButton("📤 صادرات پرداخت‌ها (CSV)", callback_data='admin_export_payments')],
            [InlineKeyboardButton("📤 صادرات تلگرام‌ها (CSV)", callback_data='admin_export_telegram')],
            [InlineKeyboardButton("📤 پشتیبان کامل (JSON)", callback_data='admin_export_all')],
            [InlineKeyboardButton("📋 دانلود نمونه کاربران", callback_data='admin_template_users')],
            [InlineKeyboardButton("📋 دانلود نمونه پرداخت‌ها", callback_data='admin_template_payments')],
            [InlineKeyboardButton("📥 واردات کاربران", callback_data='admin_import_users')],
            [InlineKeyboardButton("📥 واردات پرداخت‌ها", callback_data='admin_import_payments')],
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
                        [InlineKeyboardButton("🔙 بازگشت", callback_data='admin_import_export')]
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
            
            keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_import_export')]]
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
                        [InlineKeyboardButton("🔙 بازگشت", callback_data='admin_import_export')]
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
            
            keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_import_export')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("✅ فایل CSV پرداخت‌ها ارسال شد!", reply_markup=reply_markup)
            
        except Exception as e:
            await query.edit_message_text(f"❌ خطا در صادرات پرداخت‌ها: {str(e)}")

    async def export_all_data(self, query) -> None:
        """Export complete database as JSON with admin-friendly format"""
        try:
            with open('bot_data.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Create admin-friendly simplified data structure
            admin_data = {
                "export_info": {
                    "generated_date": datetime.now().strftime('%Y/%m/%d %H:%M:%S'),
                    "total_users": len(data.get('users', {})),
                    "total_payments": len(data.get('payments', {})),
                    "description": "پشتیبان کامل داده‌های ربات مربی فوتبال"
                },
                "users_summary": [],
                "payments_summary": [],
                "complete_data": data  # Original data for technical recovery
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
                       f"📋 شامل: خلاصه آسان + داده‌های کامل\n"
                       f"📅 تاریخ: {datetime.now().strftime('%Y/%m/%d %H:%M')}"
            )
            
            keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_import_export')]]
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
                        [InlineKeyboardButton("🔙 بازگشت", callback_data='admin_import_export')]
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
            
            keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_import_export')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("✅ فایل CSV مخاطبین تلگرام ارسال شد!", reply_markup=reply_markup)
            
        except Exception as e:
            await query.edit_message_text(f"❌ خطا در صادرات مخاطبین: {str(e)}")

    async def generate_users_template(self, query) -> None:
        """Generate template CSV file for users import"""
        try:
            # Create CSV template with sample data
            output = io.StringIO()
            writer = csv.writer(output)
            
            # CSV Headers
            headers = [
                'user_id', 'name', 'username', 'course_selected', 'payment_status',
                'questionnaire_completed', 'registration_date', 'last_interaction'
            ]
            writer.writerow(headers)
            
            # Add sample rows with Persian examples
            sample_rows = [
                ['123456789', 'احمد محمدی', 'ahmad_user', 'in_person_weights', 'approved', 'true', '2024-01-15', '2024-01-20'],
                ['987654321', 'فاطمه احمدی', 'fateme_user', 'online_cardio', 'pending_approval', 'false', '2024-01-16', '2024-01-18'],
                ['555666777', 'علی رضایی', 'ali_sports', 'online_combo', 'approved', 'true', '2024-01-17', '2024-01-19']
            ]
            
            for row in sample_rows:
                writer.writerow(row)
            
            csv_content = output.getvalue()
            
            # Send template file
            filename = "template_users_import.csv"
            
            await query.message.reply_document(
                document=io.BytesIO(csv_content.encode('utf-8')),
                filename=filename,
                caption="""📋 نمونه فایل واردات کاربران

این فایل شامل:
✅ ستون‌های ضروری
✅ نمونه داده‌های صحیح
✅ فرمت مناسب

نحوه استفاده:
1️⃣ این فایل را دانلود کنید
2️⃣ نمونه‌ها را پاک کنید
3️⃣ اطلاعات واقعی را وارد کنید
4️⃣ فایل را ذخیره و ارسال کنید"""
            )
            
            keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_import_export')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("✅ فایل نمونه کاربران ارسال شد!", reply_markup=reply_markup)
            
        except Exception as e:
            await query.edit_message_text(f"❌ خطا در ایجاد نمونه: {str(e)}")

    async def generate_payments_template(self, query) -> None:
        """Generate template CSV file for payments import"""
        try:
            # Create CSV template with sample data
            output = io.StringIO()
            writer = csv.writer(output)
            
            # CSV Headers
            headers = [
                'payment_id', 'user_id', 'course_type', 'price', 'status',
                'payment_date', 'approval_date', 'rejection_reason'
            ]
            writer.writerow(headers)
            
            # Add sample rows with Persian examples
            sample_rows = [
                ['PAY001', '123456789', 'in_person_weights', '3000000', 'approved', '2024-01-15 10:30:00', '2024-01-15 14:20:00', ''],
                ['PAY002', '987654321', 'online_cardio', '2000000', 'pending_approval', '2024-01-16 09:15:00', '', ''],
                ['PAY003', '555666777', 'online_combo', '2500000', 'rejected', '2024-01-17 16:45:00', '2024-01-17 18:30:00', 'مدارک ناکافی']
            ]
            
            for row in sample_rows:
                writer.writerow(row)
            
            csv_content = output.getvalue()
            
            # Send template file
            filename = "template_payments_import.csv"
            
            await query.message.reply_document(
                document=io.BytesIO(csv_content.encode('utf-8')),
                filename=filename,
                caption="""📋 نمونه فایل واردات پرداخت‌ها

این فایل شامل:
✅ ستون‌های ضروری
✅ نمونه داده‌های صحیح
✅ فرمت تاریخ مناسب

نحوه استفاده:
1️⃣ این فایل را دانلود کنید
2️⃣ نمونه‌ها را پاک کنید
3️⃣ اطلاعات واقعی را وارد کنید
4️⃣ فایل را ذخیره و ارسال کنید

💡 توجه: قیمت‌ها به ریال وارد شوند"""
            )
            
            keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_import_export')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("✅ فایل نمونه پرداخت‌ها ارسال شد!", reply_markup=reply_markup)
            
        except Exception as e:
            await query.edit_message_text(f"❌ خطا در ایجاد نمونه: {str(e)}")

    async def show_import_instructions(self, query, data_type: str) -> None:
        """Show import instructions for different data types"""
        if data_type == 'users':
            instructions = """📥 واردات کاربران

📋 فرمت CSV مورد نیاز:
user_id,name,username,course_selected,payment_status
123456789,احمد محمدی,ahmad_user,in_person_weights,approved
987654321,فاطمه احمدی,fateme_user,online_cardio,pending_approval

📌 ستون‌های ضروری:
• user_id: شناسه عددی کاربر
• name: نام و نام خانوادگی
• username: نام کاربری تلگرام (اختیاری)
• course_selected: نوع دوره انتخابی
• payment_status: وضعیت پرداخت

🔸 انواع دوره‌ها:
• in_person_weights
• in_person_cardio  
• online_weights
• online_cardio
• online_combo

🔸 وضعیت‌های پرداخت:
• pending_approval
• approved
• rejected

📤 برای واردات، فایل CSV را ارسال کنید."""
            
        elif data_type == 'payments':
            instructions = """📥 واردات پرداخت‌ها

📋 فرمت CSV مورد نیاز:
user_id,course_type,price,status
123456789,in_person_weights,3000000,approved
987654321,online_cardio,2000000,pending_approval

📌 ستون‌های ضروری:
• user_id: شناسه عددی کاربر
• course_type: نوع دوره
• price: مبلغ پرداختی (به ریال)
• status: وضعیت پرداخت

📤 برای واردات، فایل CSV را ارسال کنید."""
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_import_export')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(instructions, reply_markup=reply_markup)

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
