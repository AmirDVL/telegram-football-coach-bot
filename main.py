import logging
import asyncio
import os
import json
import csv
import io
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

from config import Config
from data_manager import DataManager
from admin_panel import AdminPanel
from questionnaire_manager import QuestionnaireManager
from image_processor import ImageProcessor
from coupon_manager import CouponManager

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO if not Config.DEBUG else logging.DEBUG
)
logger = logging.getLogger(__name__)

class FootballCoachBot:
    def __init__(self):
        self.data_manager = DataManager()
        self.admin_panel = AdminPanel()
        self.questionnaire_manager = QuestionnaireManager()
        self.image_processor = ImageProcessor()
        self.coupon_manager = CouponManager()
        self.payment_pending = {}
        self.user_coupon_codes = {}  # Store coupon codes entered by users
    
    async def initialize(self):
        """Initialize bot on startup - comprehensive admin sync"""
        try:
            print("🔧 Initializing admin sync from environment variables...")
            
            # Check if using database mode
            if Config.USE_DATABASE:
                await self._sync_admins_database()
            else:
                await self._sync_admins_json()
        except Exception as e:
            print(f"⚠️  Warning: Failed to sync admins: {e}")
    
    async def notify_all_admins_payment_update(self, bot, payment_user_id: int, action: str, acting_admin_name: str, course_title: str = "", price: int = 0, user_name: str = ""):
        """Notify all admins when a payment status changes"""
        try:
            # Get all admin IDs
            admin_ids = []
            if Config.USE_DATABASE:
                admin_ids = await self.admin_panel.admin_manager.get_all_admin_ids()
            else:
                admins_data = await self.data_manager.load_data('admins')
                admin_ids = [int(admin_id) for admin_id in admins_data.keys()] if admins_data else []
            
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
        """Comprehensive admin sync for JSON mode - detects and applies all changes"""
        admin_ids = Config.get_admin_ids()
        if not admin_ids:
            return
        
        print(f"🔄 Syncing {len(admin_ids)} admin(s) to JSON mode...")
        
        # Get current super admin from config (ADMIN_ID)
        config_super_admin = Config.ADMIN_ID
        
        # Load existing admins
        admins_data = await self.data_manager.load_data('admins')
        
        # Track changes
        added_count = 0
        updated_count = 0
        
        # Handle both dict and list formats
        if isinstance(admins_data, dict):
            # Dict format: {user_id: admin_data}
            existing_admin_ids = [int(uid) for uid in admins_data.keys()]
            
            for admin_id in admin_ids:
                is_super = (admin_id == config_super_admin)
                
                if admin_id not in existing_admin_ids:
                    # Add new admin
                    admins_data[str(admin_id)] = {
                        'user_id': admin_id,
                        'is_super_admin': is_super,
                        'permissions': 'full',
                        'added_at': datetime.now().isoformat(),
                        'added_by': 'env_sync',
                        'env_admin': True,
                        'synced_from_config': True
                    }
                    print(f"  ✅ Added admin to JSON: {admin_id}")
                    added_count += 1
                else:
                    # Update existing admin's super admin status if changed
                    current_is_super = admins_data[str(admin_id)].get('is_super_admin', False)
                    if current_is_super != is_super:
                        admins_data[str(admin_id)]['is_super_admin'] = is_super
                        admins_data[str(admin_id)]['updated_at'] = datetime.now().isoformat()
                        role_change = "promoted to super admin" if is_super else "demoted from super admin"
                        print(f"  🎖️ Admin {admin_id} {role_change}")
                        updated_count += 1
        else:
            # List format: [{user_id: x, ...}, ...]
            existing_admin_ids = [admin.get('user_id') for admin in admins_data if admin.get('user_id')]
            
            for admin_id in admin_ids:
                is_super = (admin_id == config_super_admin)
                
                if admin_id not in existing_admin_ids:
                    # Add new admin
                    admins_data.append({
                        'user_id': admin_id,
                        'is_super_admin': is_super,
                        'is_active': True,
                        'permissions': {
                            "can_add_admins": is_super,
                            "can_remove_admins": is_super,
                            "can_approve_payments": True,
                            "can_view_users": True,
                            "can_manage_courses": True,
                            "can_export_data": True,
                            "can_import_data": True,
                            "can_view_analytics": True
                        },
                        'added_by': 'env_sync',
                        'env_admin': True
                    })
                    print(f"  ✅ Added admin to JSON: {admin_id}")
                    added_count += 1
                else:
                    # Update existing admin's super admin status if changed
                    for admin in admins_data:
                        if admin.get('user_id') == admin_id:
                            current_is_super = admin.get('is_super_admin', False)
                            if current_is_super != is_super:
                                admin['is_super_admin'] = is_super
                                admin['updated_at'] = datetime.now().isoformat()
                                # Update permissions based on super admin status
                                if 'permissions' in admin and isinstance(admin['permissions'], dict):
                                    admin['permissions']['can_add_admins'] = is_super
                                    admin['permissions']['can_remove_admins'] = is_super
                                role_change = "promoted to super admin" if is_super else "demoted from super admin"
                                print(f"  🎖️ Admin {admin_id} {role_change}")
                                updated_count += 1
                            break
        
        # Save updated admins
        await self.data_manager.save_data('admins', admins_data)
        total_changes = added_count + updated_count
        print(f"🎉 JSON admin sync completed! {len(admin_ids)} env admins active, {added_count} added, {updated_count} updated. Manual cleanup available via /admin_panel.")
    
    async def _sync_admins_database(self):
        """Comprehensive admin sync for database mode using admin_manager"""
        admin_ids = Config.get_admin_ids()
        if not admin_ids:
            return
        
        print(f"🔄 Syncing {len(admin_ids)} admin(s) to database mode...")
        
        # Use the comprehensive sync method from admin_manager
        success = await self.admin_panel.admin_manager.sync_admins_from_config()
        
        if success:
            print(f"🎉 Database admin sync completed! Manual cleanup available via /admin_panel.")
        else:
            print(f"⚠️ Database admin sync encountered issues.")
    
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
        """Start command handler with intelligent status checking"""
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name or "کاربر"
        
        # Get existing user data to check status
        user_data = await self.data_manager.get_user_data(user_id)
        
        # Update user interaction data
        await self.data_manager.save_user_data(user_id, {
            'name': user_name,
            'username': update.effective_user.username,
            'started_bot': True,
            'last_interaction': asyncio.get_event_loop().time()
        })
        
        # Check user status and show appropriate menu
        await self.show_status_based_menu(update, user_data, user_name)
    
    async def show_status_based_menu(self, update: Update, user_data: dict, user_name: str, admin_mode: bool = False) -> None:
        """Show menu based on user's current status"""
        user_id = update.effective_user.id
        
        # Check if user is admin first (but skip if in admin_mode)
        if not admin_mode:
            is_admin = await self.admin_panel.admin_manager.is_admin(user_id)
            if is_admin:
                await self.show_admin_start_menu(update, user_name, user_id)
                return
        
        # Determine user status
        status = await self.get_user_status(user_data)
        
        if status == 'new_user':
            # First-time user - show welcome and course selection
            reply_markup = await self.create_course_selection_keyboard(user_id)
            welcome_text = f"سلام {user_name}! 👋\n\n" + Config.WELCOME_MESSAGE
            
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
                keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی ادمین", callback_data='admin_back_start')])
            reply_markup = InlineKeyboardMarkup(keyboard)
            welcome_text = f"سلام {user_name}! 👋\n\n⏳ پرداخت شما برای دوره **{course_name}** در انتظار تایید است.\n\nمی‌توانید وضعیت پرداخت خود را بررسی کنید:"
            
        elif status == 'payment_approved':
            # User payment approved, questionnaire pending or in progress
            questionnaire_status = await self.questionnaire_manager.get_user_questionnaire_status(user_id)
            course_code = user_data.get('course', 'نامشخص')
            course_name = self.get_course_name_farsi(course_code)
            
            if questionnaire_status.get('completed', False):
                # Questionnaire completed, show comprehensive program access menu
                # Get purchased courses for better context
                purchased_courses = await self.get_user_purchased_courses(user_id)
                course_count = len(purchased_courses)
                
                keyboard = [
                    [InlineKeyboardButton("📋 مشاهده برنامه تمرینی", callback_data='view_program')],
                    [InlineKeyboardButton("📊 وضعیت من", callback_data='my_status')],
                    [InlineKeyboardButton("📞 تماس با مربی", callback_data='contact_coach')],
                    [InlineKeyboardButton("🔄 بروزرسانی پرسشنامه", callback_data='restart_questionnaire')],
                    [InlineKeyboardButton("🛒 دوره جدید", callback_data='new_course')]
                ]
                
                if admin_mode:
                    keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی ادمین", callback_data='admin_back_start')])
                
                # Enhanced welcome message showing completion status and purchased courses
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
                    welcome_text = f"سلام {user_name}! 👋\n\n✅ شما دارای {course_count} دوره فعال هستید!\n🎯 برنامه‌های تمرینی شخصی‌سازی شده شما آماده است!{nutrition_info}\n\n💪 برای دسترسی به برنامه تمرینی یا تماس با مربی، از منو استفاده کنید:"
                else:
                    welcome_text = f"سلام {user_name}! 👋\n\n✅ برنامه تمرینی شما برای دوره **{course_name}** آماده است!\n🎯 پرسشنامه شما تکمیل شده و برنامه شخصی‌سازی شده!{nutrition_info}\n\n💪 برای دسترسی به برنامه تمرینی یا تماس با مربی، از منو استفاده کنید:"
            else:
                # Questionnaire not completed
                current_step = questionnaire_status.get('current_step', 1)
                total_steps = questionnaire_status.get('total_steps', 17)
                keyboard = [
                    [InlineKeyboardButton("📝 ادامه پرسشنامه", callback_data='continue_questionnaire')],
                    [InlineKeyboardButton("🔄 شروع مجدد پرسشنامه", callback_data='restart_questionnaire')],
                    [InlineKeyboardButton("📊 وضعیت من", callback_data='my_status')]
                ]
                if admin_mode:
                    keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی ادمین", callback_data='admin_back_start')])
                welcome_text = f"سلام {user_name}! 👋\n\n✅ پرداخت شما تایید شده است.\n📝 پرسشنامه: مرحله {current_step} از {total_steps}\n\nلطفاً پرسشنامه را تکمیل کنید تا برنامه شخصی‌سازی شده شما آماده شود:"
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
        elif status == 'payment_rejected':
            # Payment was rejected
            course_code = user_data.get('course_selected', 'نامشخص')
            course_name = self.get_course_name_farsi(course_code)
            keyboard = [
                [InlineKeyboardButton("💳 پرداخت مجدد", callback_data=f'pay_{user_data.get("course_selected", "")}')],
                [InlineKeyboardButton("📞 تماس با پشتیبانی", callback_data='contact_support')],
                [InlineKeyboardButton("🔄 دوره جدید", callback_data='new_course')]
            ]
            if admin_mode:
                keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی ادمین", callback_data='admin_back_start')])
            reply_markup = InlineKeyboardMarkup(keyboard)
            welcome_text = f"سلام {user_name}! 👋\n\n❌ متاسفانه پرداخت شما برای دوره **{course_name}** تایید نشد.\n\nمی‌توانید مجدداً پرداخت کنید یا با پشتیبانی تماس بگیرید:"
            
        else:
            # Returning user without active course - show course selection
            course_keyboard = await self.create_course_selection_keyboard(user_id)
            # Add status button to the existing keyboard
            additional_buttons = [
                [InlineKeyboardButton("📊 وضعیت من", callback_data='my_status')]
            ]
            if admin_mode:
                additional_buttons.append([InlineKeyboardButton("� بازگشت به منوی ادمین", callback_data='admin_back_start')])
            
            keyboard = list(course_keyboard.inline_keyboard) + additional_buttons
            reply_markup = InlineKeyboardMarkup(keyboard)
            welcome_text = f"سلام {user_name}! 👋\n\nخوش برگشتی! چه کاری می‌تونم برات انجام بدم؟"
        
        if hasattr(update, 'message') and update.message:
            await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.callback_query.edit_message_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def get_user_status(self, user_data: dict) -> str:
        """Determine user's current status based on their data"""
        user_id = user_data.get('user_id')
        
        if not user_data or not user_data.get('started_bot'):
            return 'new_user'
        
        # Check payment status from the payments table
        payments_data = await self.data_manager.load_data('payments')
        user_payment = None
        
        # Find the most recent payment for this user
        for payment_id, payment_data in payments_data.items():
            if payment_data.get('user_id') == user_id:
                if user_payment is None or payment_data.get('timestamp', '') > user_payment.get('timestamp', ''):
                    user_payment = payment_data
        
        if user_payment:
            payment_status = user_payment.get('status')
            if payment_status == 'pending':
                return 'payment_pending'
            elif payment_status == 'approved':
                return 'payment_approved'
            elif payment_status == 'rejected':
                return 'payment_rejected'
        
        # Fallback to user_data payment_status (for backward compatibility)
        payment_status = user_data.get('payment_status')
        if payment_status == 'pending_approval':
            return 'payment_pending'
        elif payment_status == 'approved':
            return 'payment_approved'
        elif payment_status == 'rejected':
            return 'payment_rejected'
        elif user_data.get('course_selected') and not payment_status:
            return 'course_selected'
        else:
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
                [InlineKeyboardButton("2️⃣ دوره تمرین آنلاین", callback_data='online')]
            ]
        else:
            # Get purchased courses to add tick marks only for specific purchased courses
            purchased_courses = await self.get_user_purchased_courses(user_id)
            
            in_person_text = "1️⃣ دوره تمرین حضوری"
            online_text = "2️⃣ دوره تمرین آنلاین"
            
            # Only add checkmark if user has ANY purchased course
            # The specific course checkmark will be shown in subcategories
            # We don't add ✅ here anymore since it should only appear for specific purchased courses
            
            keyboard = [
                [InlineKeyboardButton(in_person_text, callback_data='in_person')],
                [InlineKeyboardButton(online_text, callback_data='online')]
            ]
        
        return InlineKeyboardMarkup(keyboard)

    async def show_admin_start_menu(self, update: Update, user_name: str, user_id: int) -> None:
        """Show streamlined start menu for admins"""
        is_super = await self.admin_panel.admin_manager.is_super_admin(user_id)
        can_manage_admins = await self.admin_panel.admin_manager.can_add_admins(user_id)
        
        keyboard = [
            [InlineKeyboardButton("🎛️ پنل مدیریت کامل", callback_data='admin_panel_main')],
            [InlineKeyboardButton("📊 آمار سریع", callback_data='admin_quick_stats'),
             InlineKeyboardButton("💳 پرداخت‌های معلق", callback_data='admin_pending_payments')],
            [InlineKeyboardButton("👥 کاربران جدید", callback_data='admin_new_users'),
             InlineKeyboardButton("👤 حالت کاربر", callback_data='admin_user_mode')]
        ]
        
        # Add admin management for those with permission
        if can_manage_admins:
            keyboard.append([InlineKeyboardButton("🔐 مدیریت ادمین‌ها", callback_data='admin_manage_admins')])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        admin_type = "🔥 سوپر ادمین" if is_super else "👤 ادمین"
        welcome_text = f"سلام {user_name}! 👋\n\n{admin_type} عزیز، به ربات مربی فوتبال خوش آمدید 🎛️\n\nانتخاب کنید:"
        
        if hasattr(update, 'message') and update.message:
            await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.callback_query.edit_message_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

    async def handle_admin_start_callbacks(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle admin start menu callbacks"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        
        if not await self.admin_panel.admin_manager.is_admin(user_id):
            await query.edit_message_text("❌ شما دسترسی ادمین ندارید.")
            return
        
        if query.data == 'admin_panel_main':
            # Redirect to full admin panel
            await self.admin_panel.admin_menu_callback(query)
        elif query.data == 'admin_quick_stats':
            await self.admin_panel.show_quick_statistics(query)
        elif query.data == 'admin_pending_payments':
            await self.admin_panel.show_pending_payments(query)
        elif query.data == 'admin_new_users':
            await self.admin_panel.show_new_users(query)
        elif query.data == 'admin_manage_admins':
            await self.admin_panel.show_admin_management(query, user_id)
        elif query.data == 'admin_payments_detailed':
            await self.admin_panel.show_payments_detailed_list(query)
        elif query.data == 'admin_quick_approve':
            await self.handle_quick_approve_all(query)
        elif query.data == 'admin_user_mode':
            # Show regular user interface
            user_data = await self.data_manager.get_user_data(user_id)
            user_name = update.effective_user.first_name or "ادمین"
            # Use the consolidated function with admin_mode=True
            await self.show_status_based_menu(update, user_data, user_name, admin_mode=True)
        elif query.data == 'admin_back_start':
            # Return to admin start menu
            await self.admin_panel.back_to_admin_start(query, user_id)



    async def handle_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle main menu selections"""
        query = update.callback_query
        await query.answer()
        user_id = update.effective_user.id
        
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
                [InlineKeyboardButton("🔙 بازگشت", callback_data='back_to_main')]
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
                [InlineKeyboardButton("🔙 بازگشت", callback_data='back_to_main')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("انتخاب کنید:", reply_markup=reply_markup)

    async def handle_course_details(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle detailed course information"""
        query = update.callback_query
        user_id = update.effective_user.id
        
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
                [InlineKeyboardButton("🏷️ کد تخفیف دارم", callback_data=f'coupon_{query.data}')],
                [InlineKeyboardButton("🔙 بازگشت", callback_data=f'back_to_{"online" if query.data.startswith("online") else "in_person"}')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(message_text, reply_markup=reply_markup)

    async def handle_coupon_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle coupon code request"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
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
        context.user_data['waiting_for_coupon'] = True
        context.user_data['coupon_course'] = course_type

    async def handle_coupon_code(self, update: Update, context: ContextTypes.DEFAULT_TYPE, coupon_code: str) -> None:
        """Handle coupon code validation and processing"""
        user_id = update.effective_user.id
        course_type = context.user_data.get('coupon_course')
        
        # Clear coupon waiting state
        context.user_data['waiting_for_coupon'] = False
        del context.user_data['coupon_course']
        
        if not course_type:
            await update.message.reply_text(
                "❌ خطایی رخ داده است. لطفاً مجدداً دوره را انتخاب کنید.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🏠 منوی اصلی", callback_data='back_to_user_menu')]
                ])
            )
            return
        
        # Validate coupon
        is_valid, message, discount_percent = self.coupon_manager.validate_coupon(coupon_code.strip().upper())
        
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
        final_price, discount_amount = self.coupon_manager.calculate_discounted_price(original_price, coupon_code.strip().upper())
        
        # Store coupon for this user
        self.user_coupon_codes[user_id] = {
            'code': coupon_code.strip().upper(),
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

    async def handle_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle payment process - go directly to payment"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        
        # Handle both regular payment and coupon payment
        if query.data.startswith('payment_coupon_'):
            course_type = query.data.replace('payment_coupon_', '')
        else:
            course_type = query.data.replace('payment_', '')
        
        # 🚫 DUPLICATE PURCHASE PREVENTION
        # Check if user already has an approved payment for this course
        if await self.check_duplicate_purchase(user_id, course_type):
            await query.edit_message_text(
                "⚠️ شما قبلاً این دوره را خریداری کرده‌اید!\n\n"
                "✅ پرداخت شما تایید شده و دسترسی فعال است.\n\n"
                "📋 اگر پرسشنامه را تکمیل نکرده‌اید، لطفاً تکمیل کنید.\n"
                "📞 برای سوالات بیشتر با پشتیبانی تماس بگیرید.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 بازگشت", callback_data='back_to_main')]
                ])
            )
            return
        
        # Check if user has a pending payment for this course
        if await self.check_pending_purchase(user_id, course_type):
            await query.edit_message_text(
                "⏳ شما قبلاً برای این دوره پرداخت کرده‌اید!\n\n"
                "🔍 پرداخت شما در حال بررسی توسط ادمین است.\n"
                "📱 از نتیجه بررسی مطلع خواهید شد.\n\n"
                "💡 اگر نیاز به پرداخت مجدد دارید، ابتدا با پشتیبانی تماس بگیرید.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 بازگشت", callback_data='back_to_main')]
                ])
            )
            return
        
        # Store the course type for this user
        self.payment_pending[user_id] = course_type
        
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
            logger.error(f"Error checking duplicate purchase: {e}")
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
            logger.error(f"Error checking pending purchase: {e}")
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
            logger.error(f"Error processing CSV import: {e}")
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
                    valid_courses = ['in_person_weights', 'in_person_cardio', 'online_weights', 'online_cardio', 'online_combo']
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
                    valid_courses = ['in_person_weights', 'in_person_cardio', 'online_weights', 'online_cardio', 'online_combo']
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

    async def start_questionnaire(self, update: Update, context: ContextTypes.DEFAULT_TYPE, course_type: str) -> None:
        """Start the questionnaire process"""
        query = update.callback_query
        user_id = update.effective_user.id
        
        # Start the questionnaire and get the first question
        await self.questionnaire_manager.start_questionnaire(user_id)
        question = await self.questionnaire_manager.get_current_question(user_id)
        
        if question:
            intro_message = f"""✨ عالی! قبل از پرداخت باید اطلاعاتت رو تکمیل کنیم

📋 این فرآیند فقط {17} سوال ساده داره تا بتونم بهترین برنامه تمرینی رو برات طراحی کنم

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
                keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data='back_to_main')])
            else:
                keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data='back_to_main')]]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(intro_message, reply_markup=reply_markup)
        else:
            # Something went wrong, proceed to payment
            await self.show_payment_details(update, context, course_type)

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
        
        # Save course selection in user data
        await self.data_manager.save_user_data(user_id, {
            'course_selected': course_type
        })
        
        # Save payment initiation with final price
        payment_data = {
            'course_type': course_type,
            'price': final_price,
            'original_price': original_price,
            'status': 'pending'
        }
        
        if coupon_info:
            payment_data.update({
                'coupon_code': coupon_info['code'],
                'discount_percent': coupon_info['discount_percent'],
                'discount_amount': coupon_info['discount_amount']
            })
        
        await self.data_manager.save_payment_data(user_id, payment_data)
        
        # Format prices properly
        final_price_text = Config.format_price(final_price)
        
        payment_message = f"""🥗 برنامه غذایی شخصی‌سازی شده

با توجه به اهداف و شرایط جسمانی شما، یک برنامه غذایی کاملاً شخصی‌سازی شده برای بازیکنان حرفه ای فوتبال تهیه می‌شود.

✨ این برنامه شامل:
• برنامه غذایی کامل بر اساس نیازهای شما
• راهنمایی تخصصی تغذیه ورزشی
• پیگیری و تنظیم برنامه

واریزی رو انجام دادی فیش رو  همینجا ارسال میکنی میریم توی کارش🤝😊💎

🔙 برای بازگشت به منوی اصلی، دکمه زیر را فشار دهید.

برای پرداخت به شماره کارت زیر واریز کنید:

💳 شماره کارت: {Config.PAYMENT_CARD_NUMBER}
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
        
        keyboard = [
            [InlineKeyboardButton("🔙 بازگشت", callback_data='back_to_user_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.edit_message_text(payment_message, reply_markup=reply_markup)
        else:
            await update.message.reply_text(payment_message, reply_markup=reply_markup)

    async def handle_payment_receipt(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle photo uploads - either payment receipts or questionnaire photos"""
        user_id = update.effective_user.id
        
        # First, validate that this is actually a photo message
        if not update.message or not update.message.photo:
            await update.message.reply_text(
                "❌ فقط تصاویر قابل پردازش هستند!\n\n"
                "لطفاً یک عکس ارسال کنید (نه فایل یا متن)."
            )
            return
        
        # Check if user is in questionnaire mode and current question expects a photo
        current_question = await self.questionnaire_manager.get_current_question(user_id)
        if current_question and current_question.get("type") == "photo":
            # Handle questionnaire photo
            await self.handle_questionnaire_photo(update, context)
            return
        
        # Check user's payment status from database
        user_data = await self.data_manager.get_user_data(user_id)
        payment_status = user_data.get('payment_status')
        course_selected = user_data.get('course_selected')
        
        # Only accept photos if user has selected a course but hasn't submitted receipt yet
        if not course_selected:
            await update.message.reply_text(
                "❌ ابتدا یک دوره انتخاب کنید!\n\n"
                "برای شروع /start را بزنید."
            )
            return
        
        # If payment is already submitted or approved/rejected, don't accept more photos
        if payment_status == 'pending_approval':
            await update.message.reply_text(
                "✅ فیش واریز شما قبلاً دریافت شده است!\n\n"
                "⏳ در حال بررسی توسط ادمین...\n"
                "📱 از وضعیت پرداخت مطلع خواهید شد."
            )
            return
        elif payment_status == 'approved':
            await update.message.reply_text(
                "✅ پرداخت شما قبلاً تایید شده است!\n\n"
                "📋 لطفا پرسشنامه را تکمیل کنید."
            )
            return
        elif payment_status == 'rejected':
            await update.message.reply_text(
                "❌ پرداخت قبلی شما رد شده است.\n\n"
                "📞 لطفا با پشتیبانی تماس بگیرید."
            )
            return
        
        # Validate photo size and format
        photo = update.message.photo[-1]  # Get highest resolution
        
        # Check file size (Telegram API limit)
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
        
        course_type = course_selected  # Get from user_data instead of payment_pending
        
        try:
            # Save receipt info with photo file_id
            await self.data_manager.save_user_data(user_id, {
                'receipt_submitted': True,
                'receipt_file_id': photo.file_id,
                'course_selected': course_type,
                'payment_status': 'pending_approval'
            })
            
            await update.message.reply_text(
                "✅ فیش واریز شما با موفقیت دریافت شد!\n\n"
                "⏳ در حال بررسی توسط ادمین...\n"
                "📱 از طریق همین بات از وضعیت پرداخت مطلع خواهید شد.\n\n"
                "⏱️ زمان تقریبی بررسی: تا ۲۴ ساعت"
            )
            
            # Get course details for admin notification
            course_title = Config.COURSE_DETAILS.get(course_type, {}).get('title', 'نامشخص')
            price = Config.PRICES.get(course_type, 0)
            
            # Notify ALL admins for approval
            admin_ids = Config.get_admin_ids()
            if admin_ids:
                admin_message = (f"🔔 درخواست تایید پرداخت جدید\n\n"
                               f"👤 کاربر: {update.effective_user.first_name}\n"
                               f"📱 نام کاربری: @{update.effective_user.username or 'ندارد'}\n"
                               f"🆔 User ID: {user_id}\n"
                               f"📚 دوره: {course_title}\n"
                               f"💰 مبلغ: {price:,} تومان\n\n"
                               f"⬇️ فیش واریز ارسالی:")
                
                # Create enhanced approval buttons
                keyboard = [
                    [
                        InlineKeyboardButton("✅ تایید", callback_data=f'approve_payment_{user_id}'),
                        InlineKeyboardButton("❌ رد", callback_data=f'reject_payment_{user_id}')
                    ],
                    [InlineKeyboardButton("🎛️ مدیریت پرداخت‌ها", callback_data='admin_pending_payments')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                # Send to ALL admins
                sent_count = 0
                for admin_id in admin_ids:
                    try:
                        await context.bot.send_photo(
                            chat_id=admin_id,
                            photo=photo.file_id,
                            caption=admin_message,
                            reply_markup=reply_markup
                        )
                        sent_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to send payment notification to admin {admin_id}: {e}")
                
                logger.info(f"Payment notification sent to {sent_count}/{len(admin_ids)} admins")
                
        except Exception as e:
            logger.error(f"Error processing payment receipt: {e}")
            await update.message.reply_text(
                "❌ خطا در پردازش فیش واریز!\n\n"
                "لطفاً دوباره تلاش کنید یا با پشتیبانی تماس بگیرید.\n"
                f"کد خطا: {str(e)[:50]}"
            )

    async def handle_questionnaire_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle photo submission for questionnaire question 18"""
        user_id = update.effective_user.id
        
        try:
            # Get the photo
            photo = update.message.photo[-1]  # Get highest resolution
            
            # Validate photo using ImageProcessor
            if not self.image_processor.validate_image(photo):
                await update.message.reply_text(
                    "❌ تصویر ارسالی معتبر نیست!\n\n"
                    "شرایط تصویر:\n"
                    "📏 حداقل ابعاد: ۲۰۰×۲۰۰ پیکسل\n"
                    "📦 حداکثر حجم: ۲۰ مگابایت\n"
                    "🖼️ فرمت: JPG, PNG, WebP\n\n"
                    "لطفاً تصویر مناسب‌تری ارسال کنید."
                )
                return
            
            # Process and compress the image
            file = await context.bot.get_file(photo.file_id)
            file_path = f"temp_{user_id}_{photo.file_id}.jpg"
            
            # Download the file
            await file.download_to_drive(file_path)
            
            try:
                # Compress the image
                compressed_path, compression_info = await self.image_processor.compress_image(file_path)
                
                # Save to database
                await self.database_manager.save_user_image(
                    user_id=user_id,
                    question_number=18,
                    file_id=photo.file_id,
                    original_size=compression_info['original_size'],
                    compressed_size=compression_info['compressed_size'],
                    compression_ratio=compression_info['compression_ratio']
                )
                
                # Clean up temp files
                os.remove(file_path)
                if os.path.exists(compressed_path):
                    os.remove(compressed_path)
                
                await update.message.reply_text(
                    "✅ تصویر شما با موفقیت دریافت و پردازش شد!\n\n"
                    f"📊 اطلاعات پردازش:\n"
                    f"📏 ابعاد: {photo.width}×{photo.height}\n"
                    f"📦 حجم اصلی: {compression_info['original_size'] // 1024} KB\n"
                    f"📦 حجم فشرده: {compression_info['compressed_size'] // 1024} KB\n"
                    f"🗜️ نرخ فشرده‌سازی: {compression_info['compression_ratio']:.1f}%\n\n"
                    "⏭️ بریم سوال بعدی..."
                )
                
                # Progress to next question
                await self.questionnaire_manager.save_answer(user_id, "photo_received")
                await self.questionnaire_manager.send_next_question(user_id, context)
                
            except Exception as process_error:
                # Clean up temp file
                if os.path.exists(file_path):
                    os.remove(file_path)
                raise process_error
                
        except Exception as e:
            logger.error(f"Error processing questionnaire photo: {e}")
            await update.message.reply_text(
                "❌ خطا در پردازش تصویر!\n\n"
                "لطفاً دوباره تلاش کنید.\n"
                "اگر مشکل ادامه داشت، با پشتیبانی تماس بگیرید.\n\n"
                f"کد خطا: {str(e)[:50]}"
            )

    async def handle_unsupported_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle non-photo file uploads with helpful error messages"""
        user_id = update.effective_user.id
        
        # Check if it's a CSV file and user is admin
        if update.message.document and update.message.document.file_name:
            filename = update.message.document.file_name.lower()
            if filename.endswith('.csv') and await self.admin_panel.admin_manager.is_admin(user_id):
                await self.handle_csv_import(update, context)
                return
        
        # Check if user is in questionnaire mode
        current_question = await self.questionnaire_manager.get_current_question(user_id)
        
        if current_question and current_question.get("type") == "photo":
            await update.message.reply_text(
                "❌ فقط عکس قابل ارسال است!\n\n"
                "💡 راهنمای ارسال عکس:\n"
                "1️⃣ در گالری گوشی عکس مورد نظر را انتخاب کنید\n"
                "2️⃣ روی گزینه 'ارسال به عنوان عکس' کلیک کنید\n"
                "3️⃣ از ارسال به عنوان 'فایل' خودداری کنید\n\n"
                "📸 فرمت‌های مجاز: JPG, PNG, WebP\n"
                "📏 حداقل اندازه: ۲۰۰×۲۰۰ پیکسل"
            )
        elif user_id in self.payment_pending:
            await update.message.reply_text(
                "❌ فقط عکس فیش واریز قابل ارسال است!\n\n"
                "💡 نحوه ارسال صحیح:\n"
                "1️⃣ عکس فیش واریز را از گالری انتخاب کنید\n"
                "2️⃣ حتماً به عنوان 'عکس' ارسال کنید (نه فایل)\n"
                "3️⃣ از وضوح و خوانایی فیش اطمینان حاصل کنید\n\n"
                "📋 اطلاعات مورد نیاز در فیش:\n"
                "• شماره کارت مقصد\n"
                "• مبلغ واریزی\n"
                "• تاریخ و ساعت تراکنش\n"
                "• شماره پیگیری"
            )
        else:
            await update.message.reply_text(
                "❌ نوع فایل ارسالی پشتیبانی نمی‌شود!\n\n"
                "✅ فایل‌های قابل قبول:\n"
                "📸 تصاویر: JPG, PNG, WebP\n\n"
                "💡 برای ارسال عکس:\n"
                "• از گالری گوشی عکس را انتخاب کنید\n"
                "• حتماً به عنوان 'عکس' ارسال کنید\n\n"
                "❓ اگر سوالی دارید /help را بزنید"
            )

    async def handle_payment_approval(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle admin payment approval/rejection and user profile viewing"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        logger.info(f"Payment approval attempt by user {user_id}")
        
        # Check if user is admin
        is_admin = await self.admin_panel.admin_manager.is_admin(user_id)
        logger.info(f"Admin check result for user {user_id}: {is_admin}")
        
        if not is_admin:
            await query.edit_message_text("❌ شما دسترسی ادمین ندارید.")
            return
        
        # Handle user profile viewing
        if query.data.startswith('view_user_'):
            target_user_id = int(query.data.replace('view_user_', ''))
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
            await query.edit_message_text("❌ داده نامعتبر.")
            return
        
        # Get user data
        user_data = await self.data_manager.get_user_data(target_user_id)
        
        if not user_data.get('receipt_submitted'):
            await query.edit_message_text("❌ هیچ فیش واریزی برای این کاربر یافت نشد.")
            return
        
        if action == 'approve':
            # Find and approve the most recent payment for this user
            payments_data = await self.data_manager.load_data('payments')
            user_payment = None
            payment_id = None
            
            # Find the most recent pending payment for this user
            for pid, payment_data in payments_data.items():
                if (payment_data.get('user_id') == target_user_id and 
                    payment_data.get('status') == 'pending'):
                    if user_payment is None or payment_data.get('timestamp', '') > user_payment.get('timestamp', ''):
                        user_payment = payment_data
                        payment_id = pid
            
            if not user_payment:
                await query.edit_message_text("❌ هیچ پرداخت معلقی برای این کاربر یافت نشد.")
                return
            
            course_type = user_payment.get('course_type')
            if not course_type:
                await query.edit_message_text("❌ نوع دوره برای این کاربر مشخص نیست.")
                return
            
            # Update payment status in payments table
            user_payment['status'] = 'approved'
            user_payment['approved_by'] = update.effective_user.id
            user_payment['approved_at'] = datetime.now().isoformat()
            payments_data[payment_id] = user_payment
            await self.data_manager.save_data('payments', payments_data)
            
            # Update user data
            await self.data_manager.save_user_data(target_user_id, {
                'payment_verified': True,
                'awaiting_form': True,
                'course': course_type,
                'payment_status': 'approved'
            })
            
            # Update statistics
            await self.data_manager.update_statistics('total_payments')
            if course_type:
                await self.data_manager.update_statistics(f'course_{course_type}')
            
            # Remove from pending payments
            if target_user_id in self.payment_pending:
                del self.payment_pending[target_user_id]
            
            # Notify user and start questionnaire
            try:
                # First, notify the user about approval
                await query.bot.send_message(
                    chat_id=target_user_id,
                    text="✅ پرداخت شما تایید شد! \n\nحالا برای شخصی‌سازی برنامه تمرینتان، چند سوال کوتاه از شما می‌پرسیم:"
                )
                
                # Then, start the questionnaire
                logger.info(f"Starting questionnaire for user {target_user_id}")
                await self.questionnaire_manager.start_questionnaire(target_user_id)
                
                # Get and send the first question
                question = await self.questionnaire_manager.get_current_question(target_user_id)
                if question:
                    await self.questionnaire_manager.send_question(query.bot, target_user_id, question)
                    logger.info(f"Successfully started questionnaire for user {target_user_id}")
                else:
                    logger.error(f"Failed to get first question for user {target_user_id}")
                    # Send fallback message
                    await query.bot.send_message(
                        chat_id=target_user_id,
                        text="✅ پرداخت تایید شد! برای ادامه از دستور /start استفاده کنید."
                    )
                
            except Exception as e:
                logger.error(f"Failed to notify/start questionnaire for user {target_user_id}: {e}")
                # Try to at least notify them of approval
                try:
                    await query.bot.send_message(
                        chat_id=target_user_id,
                        text="✅ پرداخت شما تایید شد! برای ادامه از دستور /start استفاده کنید."
                    )
                except Exception as e2:
                    logger.error(f"Failed to send even basic approval message to user {target_user_id}: {e2}")
            
            # Update admin message
            course_title = Config.COURSE_DETAILS.get(course_type, {}).get('title', 'نامشخص') if course_type else 'نامشخص'
            price = user_payment.get('price', 0)
            
            updated_message = f"""✅ پرداخت تایید شد:
👤 کاربر: {user_data.get('name', 'ناشناس')}
🆔 User ID: {target_user_id}
📚 دوره: {course_title}
💰 مبلغ: {Config.format_price(price)}
⏰ تایید شده توسط: {update.effective_user.first_name}"""
            
            # Edit caption for photo messages, text for text messages
            try:
                await query.edit_message_caption(caption=updated_message)
            except Exception:
                # Fallback to edit_message_text if it's not a photo message
                await query.edit_message_text(updated_message)
            
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
            
        elif action == 'reject':
            # Reject payment
            await self.data_manager.save_user_data(target_user_id, {
                'payment_status': 'rejected'
            })
            
            # Remove from pending payments
            if target_user_id in self.payment_pending:
                del self.payment_pending[target_user_id]
            
            # Notify user
            try:
                await query.bot.send_message(
                    chat_id=target_user_id,
                    text="❌ متاسفانه پرداخت شما تایید نشد. لطفا با پشتیبانی تماس بگیرید یا فیش صحیح را ارسال کنید."
                )
            except Exception as e:
                logger.error(f"Failed to notify user {target_user_id}: {e}")
            
            # Update admin message
            updated_message = f"""❌ پرداخت رد شد:
👤 کاربر: {user_data.get('name', 'ناشناس')}
🆔 User ID: {target_user_id}
⏰ رد شده توسط: {update.effective_user.first_name}"""
            
            # Edit caption for photo messages, text for text messages
            try:
                await query.edit_message_caption(caption=updated_message)
            except Exception:
                # Fallback to edit_message_text if it's not a photo message
                await query.edit_message_text(updated_message)
            
            # Notify all admins about the rejection
            await self.notify_all_admins_payment_update(
                bot=context.bot,
                payment_user_id=target_user_id,
                action='reject',
                acting_admin_name=update.effective_user.first_name or "ادمین",
                user_name=user_data.get('name', 'ناشناس')
            )

    async def show_user_profile(self, query, target_user_id: int) -> None:
        """Show detailed user profile for admin review"""
        try:
            user_data = await self.data_manager.get_user_data(target_user_id)
            
            if not user_data:
                await query.edit_message_text(f"❌ کاربر با ID {target_user_id} یافت نشد.")
                return
            
            # Get user info from Telegram
            try:
                chat_member = await query.bot.get_chat(target_user_id)
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
                [InlineKeyboardButton(" بازگشت", callback_data='admin_pending_payments')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(profile_text, reply_markup=reply_markup)
            
        except Exception as e:
            await query.edit_message_text(f"❌ خطا در بارگیری پروفایل: {str(e)}")
    
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
                keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data='back_to_main')])
            else:
                keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data='back_to_main')]]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(message, reply_markup=reply_markup)
        else:
            # Something went wrong, proceed to completion
            await self.complete_questionnaire(update, context)

    async def handle_questionnaire_response(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle text responses from questionnaire or coupon codes"""
        user_id = update.effective_user.id
        text_answer = update.message.text
        
        # Check if admin is creating a coupon
        if user_id in self.admin_panel.admin_creating_coupons:
            await self.admin_panel.handle_admin_coupon_creation(update, text_answer)
            return
        
        # Check if we're waiting for a coupon code
        if context.user_data.get('waiting_for_coupon'):
            await self.handle_coupon_code(update, context, text_answer)
            return
        
        # Check user's payment status first using the proper method
        user_data = await self.data_manager.get_user_data(user_id)
        user_status = await self.get_user_status(user_data)
        
        # If user is in payment process, ignore text inputs
        if user_status == 'payment_pending':
            await update.message.reply_text(
                "⏳ در حال بررسی پرداخت شما توسط ادمین هستیم.\n\n"
                "📸 لطفا فقط فیش واریز ارسال کنید و منتظر تایید بمانید.\n"
                "💬 پس از تایید، پرسشنامه برایتان ارسال خواهد شد."
            )
            return
        elif user_status == 'payment_rejected':
            await update.message.reply_text(
                "❌ پرداخت شما رد شده است.\n\n"
                "📞 لطفا با پشتیبانی تماس بگیرید یا مجددا اقدام به پرداخت کنید."
            )
            return
        elif user_status != 'payment_approved':
            # Check if user has selected a course but hasn't uploaded receipt
            course_selected = user_data.get('course_selected')
            
            if course_selected:
                # User selected course but hasn't uploaded payment receipt - ask for photo
                await update.message.reply_text(
                    "💳 شما دوره را انتخاب کرده‌اید اما هنوز فیش واریز ارسال نکرده‌اید.\n\n"
                    "📸 لطفاً فیش واریز یا اسکرین‌شات پرداخت خود را ارسال کنید.\n\n"
                    "⚠️ توجه: فقط عکس (تصویر) ارسال کنید، نه متن!"
                )
            else:
                # User hasn't selected course yet - show helpful message
                keyboard = [
                    [InlineKeyboardButton("🏁 شروع", callback_data='start_over')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(
                    "سلام! 👋\n\n"
                    "برای استفاده از ربات، ابتدا باید یک دوره انتخاب کنید.\n\n"
                    "👇 برای شروع دکمه زیر را بزنید:",
                    reply_markup=reply_markup
                )
            return
        
        # Check if user is in questionnaire mode
        current_question = await self.questionnaire_manager.get_current_question(user_id)
        
        if not current_question:
            # User is not in questionnaire mode - show helpful message
            keyboard = [
                [InlineKeyboardButton("📝 شروع پرسشنامه", callback_data='start_questionnaire')],
                [InlineKeyboardButton("🏠 منوی اصلی", callback_data='back_to_user_menu')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "شما در حال حاضر در مرحله پرسشنامه نیستید.\n\n"
                "👇 برای شروع پرسشنامه دکمه زیر را بزنید:",
                reply_markup=reply_markup
            )
            return
        
        # Get the current step from the question
        current_step = current_question.get("step")
        
        # Validate and submit the answer
        is_valid, error_msg = self.questionnaire_manager.validate_answer(current_step, text_answer)
        
        if not is_valid:
            # Send error message
            await update.message.reply_text(f"❌ {error_msg}")
            return
        
        # Submit the answer
        result = await self.questionnaire_manager.process_answer(user_id, text_answer)
        
        if result["status"] == "error":
            # Send error message
            await update.message.reply_text(f"❌ {result['message']}")
            return
        elif result["status"] == "completed":
            # Questionnaire completed
            await self.complete_questionnaire_from_text(update, context)
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
                keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data='back_to_main')])
            else:
                keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data='back_to_main')]]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(message, reply_markup=reply_markup)
        else:
            # Something went wrong, proceed to completion  
            await self.complete_questionnaire_from_text(update, context)

    async def complete_questionnaire(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle questionnaire completion from callback"""
        query = update.callback_query
        user_id = update.effective_user.id
        
        # Get course type from pending payment
        course_type = self.payment_pending.get(user_id)
        
        completion_message = """🎉 تبریک! پرسشنامه با موفقیت تکمیل شد

اطلاعات شما ذخیره شد و حالا می‌تونیم بهترین برنامه تمرینی رو برای شما طراحی کنیم!

حالا وقت پرداخته! 💳"""
        
        # Edit the message to show completion
        await query.edit_message_text(completion_message)
        
        # Wait a moment and then show payment details
        await asyncio.sleep(2)
        
        if course_type:
            await self.show_payment_details(update, context, course_type)

    async def complete_questionnaire_from_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle questionnaire completion from text message"""
        user_id = update.effective_user.id
        
        # Get course type from pending payment
        course_type = self.payment_pending.get(user_id)
        
        completion_message = """🎉 تبریک! پرسشنامه با موفقیت تکمیل شد

اطلاعات شما ذخیره شد و حالا می‌تونیم بهترین برنامه تمرینی رو برای شما طراحی کنیم!

حالا وقت پرداخته! 💳"""
        
        # Send completion message
        await update.message.reply_text(completion_message)
        
        # Wait a moment and then show payment details
        await asyncio.sleep(2)
        
        if course_type:
            # Create a mock update for payment details
            mock_update = update
            await self.show_payment_details(mock_update, context, course_type)

    async def start_questionnaire_from_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Start questionnaire directly from callback"""
        query = update.callback_query
        user_id = update.effective_user.id
        
        # Check if user's payment is approved
        user_data = await self.data_manager.get_user_data(user_id)
        payment_status = user_data.get('payment_status')
        
        if payment_status != 'approved':
            await query.edit_message_text(
                "❌ برای شروع پرسشنامه ابتدا باید پرداخت شما تایید شود.\n\n"
                "لطفا ابتدا یک دوره انتخاب کنید و پرداخت کنید."
            )
            return
        
        # Start the questionnaire
        result = await self.questionnaire_manager.start_questionnaire(user_id)
        
        if result["status"] == "success":
            question = result["question"]
            message = f"""{result['progress_text']}

{question['text']}"""
            
            keyboard = []
            if question.get('type') == 'choice':
                choices = question.get('choices', [])
                for choice in choices:
                    keyboard.append([InlineKeyboardButton(choice, callback_data=f'q_answer_{choice}')])
                keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data='back_to_main')])
            else:
                keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data='back_to_main')]]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(message, reply_markup=reply_markup)
        else:
            await query.edit_message_text(f"❌ خطا در شروع پرسشنامه: {result['message']}")

    async def back_to_main(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Return to main menu"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        reply_markup = await self.create_course_selection_keyboard(user_id)
        
        await query.edit_message_text(Config.WELCOME_MESSAGE, reply_markup=reply_markup)

    async def back_to_user_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Return to appropriate user menu based on their current status"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        user_data = await self.data_manager.get_user_data(user_id)
        user_name = user_data.get('name', update.effective_user.first_name or 'کاربر')
        
        # Show status-based menu (this handles editing automatically)
        await self.show_status_based_menu(update, user_data, user_name)

    async def back_to_course_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Return to course selection (online/offline)"""
        query = update.callback_query
        await query.answer()
        
        # Extract which section to go back to from callback data
        course_type = query.data.replace('back_to_', '')  # 'online' or 'in_person'
        
        # Simulate the original selection to show the course list
        # Create a mock update with the course type
        user_id = update.effective_user.id
        
        if course_type == 'online':
            # Show online courses
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
                [InlineKeyboardButton("🔙 بازگشت", callback_data='back_to_main')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("انتخاب کنید:", reply_markup=reply_markup)
            
        elif course_type == 'in_person':
            # Show in-person courses
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
                [InlineKeyboardButton("🔙 بازگشت", callback_data='back_to_main')]
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
            await self.continue_questionnaire(update, context)
        elif query.data == 'restart_questionnaire':
            await self.restart_questionnaire(update, context)
        elif query.data == 'view_program':
            await self.show_training_program(update, context, user_data)
        elif query.data == 'contact_support':
            await self.show_support_info(update, context)
        elif query.data == 'contact_coach':
            await self.show_coach_contact(update, context)
        elif query.data == 'new_course':
            await self.start_new_course_selection(update, context)
        elif query.data == 'start_over':
            # Restart the bot flow from the beginning
            await self.start(update, context)
        elif query.data == 'start_questionnaire':
            # Start the questionnaire directly
            await self.start_questionnaire_from_callback(update, context)

    async def show_user_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_data: dict) -> None:
        """Show comprehensive user status"""
        query = update.callback_query
        user_id = update.effective_user.id
        user_name = user_data.get('name', 'کاربر')
        
        # Get current status
        status = await self.get_user_status(user_data)
        payment_status = user_data.get('payment_status', 'none')
        course_code = user_data.get('course', user_data.get('course_selected', 'انتخاب نشده'))
        course_name = self.get_course_name_farsi(course_code)
        
        # Get questionnaire status if relevant
        questionnaire_status = ""
        if payment_status == 'approved':
            q_status = await self.questionnaire_manager.get_user_questionnaire_status(user_id)
            if q_status.get('completed'):
                questionnaire_status = "✅ تکمیل شده"
            else:
                current_step = q_status.get('current_step', 1)
                total_steps = q_status.get('total_steps', 21)
                questionnaire_status = f"📝 مرحله {current_step} از {total_steps}"
        
        # Format status message
        status_text = f"""📊 **وضعیت شما**

👤 **نام:** {user_name}
📚 **دوره:** {course_name}
💳 **وضعیت پرداخت:** {self.get_payment_status_text(payment_status)}"""
        
        if questionnaire_status:
            status_text += f"\n📝 **پرسشنامه:** {questionnaire_status}"
        
        # Add appropriate action buttons
        keyboard = []
        
        if status == 'payment_pending':
            keyboard.append([InlineKeyboardButton("🔄 بررسی مجدد", callback_data='check_payment_status')])
        elif status == 'payment_approved':
            q_status = await self.questionnaire_manager.get_user_questionnaire_status(user_id)
            if not q_status.get('completed'):
                keyboard.append([InlineKeyboardButton("📝 ادامه پرسشنامه", callback_data='continue_questionnaire')])
            else:
                keyboard.append([InlineKeyboardButton("📋 مشاهده برنامه", callback_data='view_program')])
        elif status == 'payment_rejected':
            keyboard.append([InlineKeyboardButton("💳 پرداخت مجدد", callback_data=f'pay_{user_data.get("course_selected", "")}')])
        
        keyboard.extend([
            [InlineKeyboardButton("📞 تماس با پشتیبانی", callback_data='contact_support')],
            [InlineKeyboardButton("🔙 منوی اصلی", callback_data='back_to_user_menu')]
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(status_text, reply_markup=reply_markup, parse_mode='Markdown')

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
                message = f"""⏳ **وضعیت پرداخت**

دوره: {course_name}
وضعیت: در انتظار تایید ادمین

فیش واریزی شما دریافت شده و در حال بررسی است.
معمولاً این فرآیند تا 24 ساعت طول می‌کشد.

در صورت تایید، بلافاصله اطلاع‌رسانی خواهید شد."""
            elif payment_status == 'approved':
                message = f"""✅ **وضعیت پرداخت**

دوره: {course_name}
وضعیت: تایید شده

پرداخت شما با موفقیت تایید شده است!
اکنون می‌توانید برنامه تمرینی خود را دریافت کنید."""
            elif payment_status == 'rejected':
                message = f"""❌ **وضعیت پرداخت**

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
            
            await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
            
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

    async def show_training_program(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_data: dict) -> None:
        """Show user's training program"""
        course_code = user_data.get('course', 'نامشخص')
        course_name = self.get_course_name_farsi(course_code)
        
        # This would typically fetch from a database or generate based on questionnaire answers
        message = f"""📋 **برنامه تمرینی شما**

دوره: {course_name}

برنامه تمرینی شخصی‌سازی شده شما بر اساس پاسخ‌های پرسشنامه آماده شده است.

برای دریافت برنامه کامل لطفاً با مربی تماس بگیرید:
@username_coach

یا از دکمه زیر استفاده کنید:"""
        
        keyboard = [
            [InlineKeyboardButton("📞 تماس با مربی", callback_data='contact_coach')],
            [InlineKeyboardButton("📊 وضعیت من", callback_data='my_status')],
            [InlineKeyboardButton("🔙 منوی اصلی", callback_data='back_to_main')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')

    async def show_support_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show support contact information"""
        message = """📞 **اطلاعات تماس پشتیبانی**

برای دریافت پشتیبانی می‌توانید از روش‌های زیر استفاده کنید:

🔹 تلگرام: @support_username
🔹 شماره تماس: ۰۹۱۲۳۴۵۶۷۸۹
🔹 ایمیل: support@example.com

ساعات پاسخگویی:
شنبه تا پنج‌شنبه: ۹ صبح تا ۶ عصر
جمعه: ۱۰ صبح تا ۲ ظهر"""
        
        keyboard = [
            [InlineKeyboardButton("🔙 بازگشت", callback_data='my_status')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')

    async def show_coach_contact(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show coach contact information"""
        message = """👨‍💼 **تماس با مربی**

برای دریافت برنامه تمرینی و مشاوره تخصصی:

🔹 تلگرام: @coach_username
🔹 شماره تماس: ۰۹۱۲۳۴۵۶۷۸۹

⏰ مربی معمولاً ظرف ۲۴ ساعت پاسخ می‌دهد.

نکته: لطفاً نام و نام خانوادگی خود را در پیام اول ذکر کنید."""
        
        keyboard = [
            [InlineKeyboardButton("🔙 بازگشت", callback_data='view_program')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')

    async def start_new_course_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Start new course selection process"""
        user_id = update.effective_user.id
        course_keyboard = await self.create_course_selection_keyboard(user_id)
        # Add status button to the existing keyboard
        keyboard = list(course_keyboard.inline_keyboard) + [
            [InlineKeyboardButton("📊 وضعیت فعلی", callback_data='my_status')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = "انتخاب دوره جدید:\n\nکدام دوره را می‌خواهید انتخاب کنید?"
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup)

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
            'in_person_nutrition': 'حضوری - برنامه تغذیه',
            'online_nutrition': 'آنلاین - برنامه تغذیه'
        }
        return course_map.get(course_code, course_code if course_code else 'انتخاب نشده')

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle errors"""
        import traceback
        
        # Log the full traceback
        logger.error(f"Exception while handling an update: {context.error}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        
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
        logger.error("BOT_TOKEN not found in environment variables!")
        print("Error: BOT_TOKEN not found!")
        print("Please create .env file with your bot token:")
        print("BOT_TOKEN=your_bot_token_here")
        return
    
    # Create bot instance
    bot = FootballCoachBot()
    
    # Create application
    application = Application.builder().token(Config.BOT_TOKEN).build()

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
    application.add_handler(CallbackQueryHandler(bot.handle_payment_approval, pattern='^(approve_payment_|reject_payment_|view_user_)'))
    application.add_handler(CallbackQueryHandler(bot.handle_status_callbacks, pattern='^(my_status|check_payment_status|continue_questionnaire|restart_questionnaire|view_program|contact_support|contact_coach|new_course|start_over|start_questionnaire)$'))
    application.add_handler(CallbackQueryHandler(bot.back_to_main, pattern='^back_to_main$'))
    application.add_handler(CallbackQueryHandler(bot.back_to_user_menu, pattern='^back_to_user_menu$'))
    application.add_handler(CallbackQueryHandler(bot.back_to_course_selection, pattern='^back_to_(online|in_person)$'))
    # Admin start menu handlers (must come before generic admin_ handler)
    application.add_handler(CallbackQueryHandler(bot.handle_admin_start_callbacks, pattern='^(admin_panel_main|admin_quick_stats|admin_pending_payments|admin_new_users|admin_manage_admins|admin_user_mode|admin_back_start|admin_payments_detailed|admin_quick_approve|confirm_approve_all)$'))
    # Admin coupon handlers (must come before generic admin_ handler)
    application.add_handler(CallbackQueryHandler(bot.admin_panel.handle_admin_callbacks, pattern='^(toggle_coupon_|delete_coupon_)'))
    # Generic admin handlers (catch remaining admin_ callbacks)
    application.add_handler(CallbackQueryHandler(bot.admin_panel.handle_admin_callbacks, pattern='^admin_'))
    
    # Handle photo messages (payment receipts and questionnaire photos)
    application.add_handler(MessageHandler(filters.PHOTO, bot.handle_payment_receipt))
    
    # Handle unsupported file types with helpful messages
    application.add_handler(MessageHandler(filters.Document.ALL | filters.VIDEO | filters.AUDIO | filters.VOICE | filters.ANIMATION, bot.handle_unsupported_file))
    
    # Handle text messages (questionnaire responses)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_questionnaire_response))
    
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
    logger.info("Starting Football Coach Bot...")
    print("🤖 Football Coach Bot is starting...")
    print("📱 Bot is ready to receive messages!")

    try:
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"Error running bot: {e}")
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    main()
