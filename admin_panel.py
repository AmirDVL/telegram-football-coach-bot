from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from admin_manager import AdminManager
from data_manager import DataManager
import json

class AdminPanel:
    def __init__(self):
        self.admin_manager = AdminManager()
        self.data_manager = DataManager()
    
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
            [InlineKeyboardButton("💳 مدیریت پرداخت‌ها", callback_data='admin_payments')]
        ]
        
        if can_manage_admins:
            keyboard.append([InlineKeyboardButton("🔐 مدیریت ادمین‌ها", callback_data='admin_manage_admins')])
        
        keyboard.append([InlineKeyboardButton("🆔 نمایش ID من", callback_data='admin_my_id')])
        
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
        elif query.data == 'admin_manage_admins':
            await self.show_admin_management(query, user_id)
        elif query.data == 'admin_my_id':
            await self.show_my_id(query, user_id)
        elif query.data.startswith('admin_add_admin_'):
            await self.handle_add_admin(query, user_id)
        elif query.data.startswith('admin_remove_admin_'):
            await self.handle_remove_admin(query, user_id)
        elif query.data == 'admin_back_main':
            await self.back_to_admin_main(query, user_id)
    
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
            total_revenue = sum(payment.get('price', 0) for payment in payments.values())
            
            # Course statistics
            course_stats = {}
            for user_data in users.values():
                course = user_data.get('course')
                if course:
                    course_stats[course] = course_stats.get(course, 0) + 1
            
            stats_text = f"""📊 آمار کلی ربات:

👥 تعداد کل کاربران: {total_users}
💳 تعداد کل پرداخت‌ها: {total_payments}
💰 درآمد کل: {total_revenue:,} تومان

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
        
        admins = await self.admin_manager.get_all_admins()
        
        text = "🔐 مدیریت ادمین‌ها:\n\n"
        
        for admin in admins:
            admin_type = "🔥 سوپر ادمین" if admin['is_super_admin'] else "👤 ادمین"
            text += f"{admin_type}: {admin['id']}\n"
        
        text += "\n💡 برای افزودن ادمین جدید، از دستور زیر استفاده کنید:\n"
        text += "/add_admin [USER_ID]\n\n"
        text += "💡 برای حذف ادمین:\n"
        text += "/remove_admin [USER_ID]"
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_back_main')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup)
    
    async def show_my_id(self, query, user_id: int) -> None:
        """Show user's ID"""
        is_super = await self.admin_manager.is_super_admin(user_id)
        admin_type = "🔥 سوپر ادمین" if is_super else "👤 ادمین"
        
        text = f"""🆔 اطلاعات شما:

{admin_type}
📱 Chat ID: `{user_id}`
👤 نام: {query.from_user.first_name or 'نامشخص'}
🔗 نام کاربری: @{query.from_user.username or 'ندارد'}

💡 از این ID برای افزودن به .env استفاده کنید"""
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_back_main')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
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
            
            total_revenue = sum(payment.get('price', 0) for payment in payments.values())
            text += f"💰 درآمد کل: {total_revenue:,} تومان\n\n"
            
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
            [InlineKeyboardButton("💳 مدیریت پرداخت‌ها", callback_data='admin_payments')]
        ]
        
        if can_manage_admins:
            keyboard.append([InlineKeyboardButton("🔐 مدیریت ادمین‌ها", callback_data='admin_manage_admins')])
        
        keyboard.append([InlineKeyboardButton("🆔 نمایش ID من", callback_data='admin_my_id')])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        admin_type = "🔥 سوپر ادمین" if is_super else "👤 ادمین"
        welcome_text = f"سلام {admin_type}!\n\nبه پنل مدیریت خوش آمدید 🎛️"
        
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
