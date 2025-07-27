import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

from config import Config
from data_manager import DataManager
from admin_panel import AdminPanel
from questionnaire_manager import QuestionnaireManager
from image_processor import ImageProcessor

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
        self.payment_pending = {}
        
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
    
    async def show_status_based_menu(self, update: Update, user_data: dict, user_name: str) -> None:
        """Show menu based on user's current status"""
        user_id = update.effective_user.id
        
        # Determine user status
        status = await self.get_user_status(user_data)
        
        if status == 'new_user':
            # First-time user - show welcome and course selection
            keyboard = [
                [InlineKeyboardButton("1️⃣ دوره تمرین حضوری", callback_data='in_person')],
                [InlineKeyboardButton("2️⃣ دوره تمرین آنلاین", callback_data='online')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            welcome_text = f"سلام {user_name}! 👋\n\n" + Config.WELCOME_MESSAGE
            
        elif status == 'payment_pending':
            # User has submitted payment, waiting for approval
            course_name = user_data.get('course_selected', 'نامشخص')
            keyboard = [
                [InlineKeyboardButton("📊 وضعیت پرداخت", callback_data='check_payment_status')],
                [InlineKeyboardButton("📞 تماس با پشتیبانی", callback_data='contact_support')],
                [InlineKeyboardButton("🔄 دوره جدید", callback_data='new_course')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            welcome_text = f"سلام {user_name}! 👋\n\n⏳ پرداخت شما برای دوره **{course_name}** در انتظار تایید است.\n\nمی‌توانید وضعیت پرداخت خود را بررسی کنید:"
            
        elif status == 'payment_approved':
            # User payment approved, questionnaire pending or in progress
            questionnaire_status = await self.questionnaire_manager.get_user_questionnaire_status(user_id)
            course_name = user_data.get('course', 'نامشخص')
            
            if questionnaire_status.get('completed', False):
                # Questionnaire completed, show program access
                keyboard = [
                    [InlineKeyboardButton("📋 مشاهده برنامه تمرینی", callback_data='view_program')],
                    [InlineKeyboardButton("📊 وضعیت من", callback_data='my_status')],
                    [InlineKeyboardButton("📞 تماس با مربی", callback_data='contact_coach')],
                    [InlineKeyboardButton("🔄 دوره جدید", callback_data='new_course')]
                ]
                welcome_text = f"سلام {user_name}! 👋\n\n✅ برنامه تمرینی شما برای دوره **{course_name}** آماده است!"
            else:
                # Questionnaire not completed
                current_step = questionnaire_status.get('current_step', 1)
                total_steps = questionnaire_status.get('total_steps', 21)
                keyboard = [
                    [InlineKeyboardButton("📝 ادامه پرسشنامه", callback_data='continue_questionnaire')],
                    [InlineKeyboardButton("🔄 شروع مجدد پرسشنامه", callback_data='restart_questionnaire')],
                    [InlineKeyboardButton("📊 وضعیت من", callback_data='my_status')]
                ]
                welcome_text = f"سلام {user_name}! 👋\n\n✅ پرداخت شما تایید شده است.\n📝 پرسشنامه: مرحله {current_step} از {total_steps}\n\nلطفاً پرسشنامه را تکمیل کنید تا برنامه شخصی‌سازی شده شما آماده شود:"
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
        elif status == 'payment_rejected':
            # Payment was rejected
            course_name = user_data.get('course_selected', 'نامشخص')
            keyboard = [
                [InlineKeyboardButton("💳 پرداخت مجدد", callback_data=f'pay_{user_data.get("course_selected", "")}')],
                [InlineKeyboardButton("📞 تماس با پشتیبانی", callback_data='contact_support')],
                [InlineKeyboardButton("🔄 دوره جدید", callback_data='new_course')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            welcome_text = f"سلام {user_name}! 👋\n\n❌ متاسفانه پرداخت شما برای دوره **{course_name}** تایید نشد.\n\nمی‌توانید مجدداً پرداخت کنید یا با پشتیبانی تماس بگیرید:"
            
        else:
            # Returning user without active course - show course selection
            keyboard = [
                [InlineKeyboardButton("1️⃣ دوره تمرین حضوری", callback_data='in_person')],
                [InlineKeyboardButton("2️⃣ دوره تمرین آنلاین", callback_data='online')],
                [InlineKeyboardButton("📊 وضعیت من", callback_data='my_status')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            welcome_text = f"سلام {user_name}! 👋\n\nخوش برگشتی! چه کاری می‌تونم برات انجام بدم؟"
        
        if hasattr(update, 'message') and update.message:
            await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.callback_query.edit_message_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def get_user_status(self, user_data: dict) -> str:
        """Determine user's current status based on their data"""
        if not user_data or not user_data.get('started_bot'):
            return 'new_user'
        
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

    async def handle_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle main menu selections"""
        query = update.callback_query
        await query.answer()
        
        if query.data == 'in_person':
            keyboard = [
                [InlineKeyboardButton("1️⃣ تمرین هوازی سرعتی چابکی کار با توپ", callback_data='in_person_cardio')],
                [InlineKeyboardButton("2️⃣ تمرین وزنه", callback_data='in_person_weights')],
                [InlineKeyboardButton("🔙 بازگشت", callback_data='back_to_main')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("انتخاب کنید:", reply_markup=reply_markup)
            
        elif query.data == 'online':
            keyboard = [
                [InlineKeyboardButton("1️⃣ برنامه وزنه", callback_data='online_weights')],
                [InlineKeyboardButton("2️⃣ برنامه هوازی و کار با توپ", callback_data='online_cardio')],
                [InlineKeyboardButton("3️⃣ برنامه وزنه + برنامه هوازی (با تخفیف بیشتر)", callback_data='online_combo')],
                [InlineKeyboardButton("🔙 بازگشت", callback_data='back_to_main')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("انتخاب کنید:", reply_markup=reply_markup)

    async def handle_course_details(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle detailed course information"""
        query = update.callback_query
        await query.answer()
        
        if query.data in Config.COURSE_DETAILS:
            course = Config.COURSE_DETAILS[query.data]
            price = Config.PRICES[query.data]
            
            # Format price properly
            if price >= 1000000:
                price_text = f"{price//1000:,} تومن"  # Convert to thousands
            else:
                price_text = f"{price:,} تومان"
            
            message_text = f"{course['title']}👇👇👇👇👇\n\n{course['description']}"
            
            keyboard = [
                [InlineKeyboardButton(f"💳 پرداخت و ثبت نام ({price_text})", callback_data=f'payment_{query.data}')],
                [InlineKeyboardButton("🔙 بازگشت", callback_data='back_to_main')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(message_text, reply_markup=reply_markup)

    async def handle_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle payment process - go directly to payment"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        course_type = query.data.replace('payment_', '')
        
        # Store the course type for this user
        self.payment_pending[user_id] = course_type
        
        # Go directly to payment details (questionnaire comes after approval)
        await self.show_payment_details(update, context, course_type)

    async def start_questionnaire(self, update: Update, context: ContextTypes.DEFAULT_TYPE, course_type: str) -> None:
        """Start the questionnaire process"""
        query = update.callback_query
        user_id = update.effective_user.id
        
        # Get the first question
        question = await self.questionnaire_manager.get_current_question(user_id)
        
        if question:
            intro_message = ("✨ عالی! قبل از پرداخت باید اطلاعاتت رو تکمیل کنیم\n"
                             "\n"
                             "📋 این فرآیند فقط {21} سوال ساده داره تا بتونم بهترین برنامه تمرینی رو برات طراحی کنم\n"
                             "\n"
                             "⏱️ زمان تقریبی: 3-5 دقیقه\n"
                             "\n"
                             "آماده‌ای؟ بیا شروع کنیم! 🚀\n"
                             "\n"
                             "───────────────────\n"
                             "{question['progress_text']}\n"
                             "\n"
                             "{question['text']}")
            
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
        """Show payment details"""
        user_id = update.effective_user.id
        
        # Save payment initiation
        await self.data_manager.save_payment_data(user_id, {
            'course_type': course_type,
            'price': Config.PRICES[course_type],
            'status': 'pending'
        })
        
        payment_message = ("برای پرداخت به شماره کارت زیر واریز کنید:\n"
                             "\n"
                             "💳 شماره کارت: {Config.PAYMENT_CARD_NUMBER}\n"
                             "👤 نام صاحب حساب: {Config.PAYMENT_CARD_HOLDER}\n"
                             "💰 مبلغ: {Config.PRICES[course_type]:,} تومان\n"
                             "\n"
                             "بعد از واریز، فیش یا اسکرین شات رو همینجا ارسال کنید تا بررسی شه ✅\n"
                             "\n"
                             "⚠️ توجه: فقط فیش واریز رو ارسال کنید")
        
        keyboard = [
            [InlineKeyboardButton("🔙 بازگشت", callback_data='back_to_main')]
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
        
        # Handle payment receipt validation
        if user_id not in self.payment_pending:
            await update.message.reply_text(
                "❌ هیچ درخواست پرداختی برای شما ثبت نشده است!\n\n"
                "مراحل صحیح:\n"
                "1️⃣ ابتدا یک دوره انتخاب کنید\n"
                "2️⃣ پرسشنامه را تکمیل کنید\n"
                "3️⃣ سپس فیش واریز را ارسال کنید\n\n"
                "برای شروع دوباره /start را بزنید."
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
        
        course_type = self.payment_pending[user_id]
        
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
            
            # Notify admin for approval
            if Config.ADMIN_ID:
                admin_message = ("🔔 درخواست تایید پرداخت جدید:\n"
                             "                \n"
                             "👤 کاربر: {update.effective_user.first_name} (@{update.effective_user.username or 'بدون نام کاربری'})\n"
                             "🆔 User ID: {user_id}\n"
                             "📚 دوره: {course_title}\n"
                             "💰 مبلغ: {price:,} تومان\n"
                             "📸 ابعاد تصویر: {photo.width}×{photo.height}\n"
                             "📦 حجم فایل: {photo.file_size // 1024 if photo.file_size else 'نامشخص'} KB\n"
                             "\n"
                             "⚠️ فیش واریز ارسال شده - لطفا بررسی کنید")
                
                # Create approval buttons for admin
                keyboard = [
                    [InlineKeyboardButton("✅ تایید پرداخت", callback_data=f'approve_payment_{user_id}')],
                    [InlineKeyboardButton("❌ رد پرداخت", callback_data=f'reject_payment_{user_id}')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                # Forward the photo to admin
                await context.bot.forward_message(
                    chat_id=Config.ADMIN_ID,
                    from_chat_id=update.effective_chat.id,
                    message_id=update.message.message_id
                )
                
                await context.bot.send_message(
                    chat_id=Config.ADMIN_ID, 
                    text=admin_message,
                    reply_markup=reply_markup
                )
                
        except Exception as e:
            logger.error(f"Error processing payment receipt: {e}")
            await update.message.reply_text(
                "❌ خطا در پردازش فیش واریز!\n\n"
                "لطفاً دوباره تلاش کنید یا با پشتیبانی تماس بگیرید.\n"
                f"کد خطا: {str(e)[:50]}"
            )

    async def handle_questionnaire_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle photo upload for questionnaire with comprehensive validation"""
        user_id = update.effective_user.id
        
        # Validate that this is actually a photo message
        if not update.message or not update.message.photo:
            await update.message.reply_text(
                "❌ لطفاً یک تصویر ارسال کنید!\n\n"
                "در این مرحله از پرسشنامه، باید عکس ارسال کنید."
            )
            return
        
        try:
            # Get the largest photo size
            photo = update.message.photo[-1]
            
            # Validate photo specifications
            if photo.file_size and photo.file_size > 20 * 1024 * 1024:  # 20MB
                await update.message.reply_text(
                    "❌ تصویر خیلی بزرگ است!\n\n"
                    "حداکثر سایز مجاز: ۲۰ مگابایت\n"
                    "لطفاً تصویر کوچک‌تری ارسال کنید."
                )
                return
            
            if photo.width < 300 or photo.height < 300:
                await update.message.reply_text(
                    "❌ تصویر خیلی کوچک است!\n\n"
                    "برای آنالیز بدن، حداقل ابعاد ۳۰۰×۳۰۰ پیکسل لازم است.\n"
                    "لطفاً تصویر با کیفیت بهتر ارسال کنید."
                )
                return
            
            # Download and validate image content
            photo_file = await context.bot.get_file(photo.file_id)
            photo_bytes = await photo_file.download_as_bytearray()
            
            # Validate image with our processor
            is_valid, error_msg = self.image_processor.validate_image(photo_bytes)
            if not is_valid:
                await update.message.reply_text(
                    f"❌ مشکل در تصویر ارسالی:\n\n{error_msg}\n\n"
                    "لطفاً تصویر صحیحی ارسال کنید."
                )
                return
            
            # Compress image
            compressed_bytes, compression_info = self.image_processor.compress_image(photo_bytes)
            
            # Process the photo answer in questionnaire
            result = await self.questionnaire_manager.process_photo_answer(user_id, photo.file_id)
            
            if result["status"] == "error":
                await update.message.reply_text(
                    f"❌ {result['message']}\n\n"
                    "اگر مشکل ادامه دارد، با پشتیبانی تماس بگیرید."
                )
                return
            elif result["status"] == "need_more_photos":
                photos_received = result.get("photos_received", 0)
                photos_needed = result.get("photos_needed", 3)
                
                await update.message.reply_text(
                    f"✅ تصویر {photos_received} از {photos_needed} دریافت شد!\n\n"
                    f"📸 لطفاً {photos_needed - photos_received} تصویر دیگر ارسال کنید:\n"
                    f"• تصویر از جلو (ایستاده، رو به دوربین)\n"
                    f"• تصویر از پهلو (ایستاده، نیمرخ)\n"
                    f"• تصویر از پشت (ایستاده، پشت به دوربین)\n\n"
                    f"💡 برای آنالیز بهتر، در محیط با نور کافی عکس بگیرید."
                )
                return
            elif result["status"] == "continue":
                # Show next question
                question = result["question"]
                if question:
                    message = ("✅ تصاویر شما دریافت شد و ذخیره شد!\n"
                             "                    \n"
                             "{result['progress_text']}\n"
                             "\n"
                             "{question['text']}")
                    
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
                    await update.message.reply_text(
                        "❌ خطا در بارگذاری سوال بعدی.\n"
                        "لطفاً دوباره تلاش کنید."
                    )
            elif result["status"] == "completed":
                await update.message.reply_text(
                    "🎉 عالی! تصاویر شما دریافت شد!\n\n"
                    "پرسشنامه تکمیل شد. حالا وقت پرداخت است! 💳"
                )
                await self.complete_questionnaire_from_text(update, context)
                
        except Exception as e:
            logger.error(f"Error processing questionnaire photo: {e}")
            await update.message.reply_text(
                "❌ خطا در پردازش تصویر!\n\n"
                "ممکن است مشکل موقتی باشد. لطفاً:\n"
                "1️⃣ چند لحظه صبر کنید\n"
                "2️⃣ دوباره تصویر را ارسال کنید\n"
                "3️⃣ اگر مشکل ادامه دارد، با پشتیبانی تماس بگیرید\n\n"
                f"کد خطا: {str(e)[:50]}"
            )

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
                
            # Save compressed image to database if using database mode
            if Config.USE_DATABASE:
                try:
                    # Get user's payment info to associate with images
                    user_data = await self.data_manager.get_user_data(user_id)
                    payment_id = user_data.get('current_payment_id', 1)  # Default to 1 if not found
                    
                    # Get current question step
                    current_question = await self.questionnaire_manager.get_current_question(user_id)
                    question_step = current_question.get("step", 18) if current_question else 18
                    
                    # Calculate image order based on existing photos
                    existing_photos = await self.data_manager.get_user_images_by_step(user_id, question_step, payment_id)
                    image_order = len(existing_photos) + 1
                    
                    # Save to database
                    await self.data_manager.save_user_image(
                        user_id=user_id,
                        payment_id=payment_id,
                        question_step=question_step,
                        file_id=photo.file_id,
                        image_order=image_order,
                        file_size=compression_info.get('original_size'),
                        compressed_size=compression_info.get('compressed_size')
                    )
                    
                    logger.info(f"Saved questionnaire photo for user {user_id}, step {question_step}, order {image_order}")
                except Exception as e:
                    logger.error(f"Error saving photo to database: {e}")
                    
        except Exception as e:
            logger.error(f"Error handling questionnaire photo: {e}")
            await update.message.reply_text("❌ خطا در پردازش تصویر. لطفاً دوباره تلاش کنید.")

    async def handle_unsupported_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle unsupported file types with helpful error messages"""
        user_id = update.effective_user.id
        
        # Check if user is in questionnaire mode and current question expects a photo
        current_question = await self.questionnaire_manager.get_current_question(user_id)
        if current_question and current_question.get("type") == "photo":
            # User is in photo questionnaire step but sent wrong file type
            await update.message.reply_text(
                "❌ در این مرحله فقط تصویر (عکس) قابل قبول است!\n\n"
                "📸 لطفاً به جای فایل، از دوربین گوشی عکس بگیرید و ارسال کنید.\n\n"
                "🚫 فایل‌های قابل قبول نیستند:\n"
                "• فایل PDF\n"
                "• فایل Word\n"
                "• ویدیو\n"
                "• فایل صوتی\n\n"
                "✅ فقط عکس (Photo) ارسال کنید."
            )
            return
        
        # Check if user is trying to send payment receipt
        if user_id in self.payment_pending:
            await update.message.reply_text(
                "❌ برای فیش واریز، فقط تصویر (عکس) قابل قبول است!\n\n"
                "📸 لطفاً عکس فیش واریز را ارسال کنید.\n"
                "🚫 فایل ارسال نکنید.\n\n"
                "💡 راهنمایی:\n"
                "1️⃣ از دوربین گوشی عکس بگیرید\n"
                "2️⃣ یا از گالری عکس انتخاب کنید\n"
                "3️⃣ روی دکمه 📎 کنار متن بزنید و Photo را انتخاب کنید"
            )
            return
        
        # General error for unsupported files
        file_type = "نامشخص"
        if update.message.document:
            file_type = "فایل"
        elif update.message.video:
            file_type = "ویدیو"
        elif update.message.audio or update.message.voice:
            file_type = "فایل صوتی"
        elif update.message.sticker:
            file_type = "استیکر"
        
        await update.message.reply_text(
            f"❌ {file_type} قابل پردازش نیست!\n\n"
            "🤖 این ربات فقط موارد زیر را پردازش می‌کند:\n"
            "• 💬 متن (برای پاسخ به سوالات)\n"
            "• 📸 تصویر (برای فیش واریز و عکس‌های پرسشنامه)\n\n"
            "💡 اگر نیاز به ارسال فایل دارید، با پشتیبانی تماس بگیرید."
        )

    async def handle_questionnaire_response(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle questionnaire responses"""
        user_id = update.effective_user.id
        
        # Get user data
        user_data = await self.data_manager.get_user_data(user_id)
        
        if user_data.get('awaiting_form'):
            # Save questionnaire responses
            await self.data_manager.save_user_data(user_id, {
                'questionnaire': update.message.text,
                'awaiting_form': False,
                'registration_complete': True
            })
            
            await update.message.reply_text("✅ عالی! اطلاعات شما دریافت شد.\n\n"
                                           "برنامه تمرینی شما بر اساس اطلاعات ارائه شده طراحی میشه و ظرف ۲۴ ساعت براتون ارسال میشه.\n\n"
                                           "از اینکه به خانواده ما پیوستید خوشحالیم! 💪⚽️\n\n"
                                           "برای هر سوال یا مشکل، همیشه در دسترس هستم 🤝")
            
            # Update statistics
            await self.data_manager.update_statistics('total_users')
            
            # Notify admin with full details
            if Config.ADMIN_ID:
                try:
                    admin_message = (f"📝 فرم جدید دریافت شد:\n"
                                   f"👤 کاربر: {update.effective_user.first_name} (@{update.effective_user.username or 'بدون نام کاربری'})\n"
                                   f"🆔 User ID: {user_id}\n"
                                   f"📚 دوره: {user_data.get('course', 'نامشخص')}\n"
                                   f"📄 پاسخ‌ها:\n"
                                   f"{update.message.text[:1000]}{'...' if len(update.message.text) > 1000 else ''}")
                    
                    await context.bot.send_message(chat_id=Config.ADMIN_ID, text=admin_message)
                except Exception as e:
                    logger.error(f"Failed to send admin notification: {e}")
        else:
            # Handle regular messages
            await update.message.reply_text("سلام! برای شروع دوباره /start را بزنید.")

    async def handle_payment_approval(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle admin payment approval/rejection"""
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
        
        # Extract user_id and action from callback data
        if query.data.startswith('approve_payment_'):
            user_id = int(query.data.replace('approve_payment_', ''))
            action = 'approve'
        elif query.data.startswith('reject_payment_'):
            user_id = int(query.data.replace('reject_payment_', ''))
            action = 'reject'
        else:
            await query.edit_message_text("❌ داده نامعتبر.")
            return
        
        # Get user data
        user_data = await self.data_manager.get_user_data(user_id)
        
        if not user_data.get('receipt_submitted'):
            await query.edit_message_text("❌ هیچ فیش واریزی برای این کاربر یافت نشد.")
            return
        
        if action == 'approve':
            # Approve payment
            course_type = self.payment_pending.get(user_id)
            if not course_type:
                course_type = user_data.get('course_selected')
            
            await self.data_manager.save_user_data(user_id, {
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
            if user_id in self.payment_pending:
                del self.payment_pending[user_id]
            
            # Notify user and start questionnaire
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="✅ پرداخت شما تایید شد! \n\nحالا برای شخصی‌سازی برنامه تمرینتان، چند سوال کوتاه از شما می‌پرسیم:"
                )
                
                # Start the questionnaire
                question = await self.questionnaire_manager.get_current_question(user_id)
                if question:
                    await self.questionnaire_manager.send_question(context.bot, user_id, question)
                
            except Exception as e:
                logger.error(f"Failed to notify user {user_id}: {e}")
            
            # Update admin message
            course_title = Config.COURSE_DETAILS.get(course_type, {}).get('title', 'نامشخص') if course_type else 'نامشخص'
            price = Config.PRICES.get(course_type, 0) if course_type else 0
            
            updated_message = (f"✅ پرداخت تایید شد:\n"
                              f"👤 کاربر: {user_data.get('name', 'ناشناس')}\n"
                              f"🆔 User ID: {user_id}\n"
                              f"📚 دوره: {course_title}\n"
                              f"💰 مبلغ: {price:,} تومان\n"
                              f"⏰ تایید شده توسط: {update.effective_user.first_name}")
            
            await query.edit_message_text(updated_message)
            
        elif action == 'reject':
            # Reject payment
            await self.data_manager.save_user_data(user_id, {
                'payment_status': 'rejected'
            })
            
            # Remove from pending payments
            if user_id in self.payment_pending:
                del self.payment_pending[user_id]
            
            # Notify user
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="❌ متاسفانه پرداخت شما تایید نشد. لطفا با پشتیبانی تماس بگیرید یا فیش صحیح را ارسال کنید."
                )
            except Exception as e:
                logger.error(f"Failed to notify user {user_id}: {e}")
            
            # Update admin message
            updated_message = (f"❌ پرداخت رد شد:\n"
                              f"👤 کاربر: {user_data.get('name', 'ناشناس')}\n"
                              f"🆔 User ID: {user_id}\n"
                              f"⏰ رد شده توسط: {update.effective_user.first_name}")
            
            await query.edit_message_text(updated_message)

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
            message = ("{result['progress_text']}\n"
                             "\n"
                             "{question['text']}")
            
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
        """Handle text responses from questionnaire"""
        user_id = update.effective_user.id
        
        # Validate that this is a text message
        if not update.message or not update.message.text:
            await update.message.reply_text(
                "❌ لطفاً متن ارسال کنید!\n\n"
                "در این مرحله از پرسشنامه، باید پاسخ متنی ارسال کنید."
            )
            return
        
        text_answer = update.message.text.strip()
        
        # Check if message is too long (prevent spam)
        if len(text_answer) > 2000:
            await update.message.reply_text(
                "❌ پاسخ خیلی طولانی است!\n\n"
                "حداکثر ۲۰۰۰ کاراکتر مجاز است.\n"
                "لطفاً پاسخ مختصرتری ارسال کنید."
            )
            return
        
        # Check if message is empty
        if not text_answer:
            await update.message.reply_text(
                "❌ پاسخ خالی ارسال کرده‌اید!\n\n"
                "لطفاً یک پاسخ معتبر ارسال کنید."
            )
            return
        
        # Check if user is in questionnaire mode
        current_question = await self.questionnaire_manager.get_current_question(user_id)
        
        if not current_question:
            # User is not in questionnaire mode, give helpful message
            await update.message.reply_text(
                "🤔 در حال حاضر هیچ پرسشنامه‌ای در جریان نیست.\n\n"
                "برای شروع دوباره /start را بزنید."
            )
            return
        
        # Get the current step from the question
        current_step = current_question.get("step")
        question_type = current_question.get("type")
        
        # Check if current question expects a photo but user sent text
        if question_type == "photo":
            await update.message.reply_text(
                "❌ در این مرحله باید عکس ارسال کنید!\n\n"
                "📸 لطفاً از دوربین گوشی عکس بگیرید و ارسال کنید.\n"
                "🚫 متن قابل قبول نیست."
            )
            return
        
        # Validate and submit the answer
        is_valid, error_msg = self.questionnaire_manager.validate_answer(current_step, text_answer)
        
        if not is_valid:
            # Send improved error message with context
            question_title = self.questionnaire_manager.get_question_title(current_step)
            await update.message.reply_text(
                f"❌ پاسخ نامعتبر برای \"{question_title}\":\n\n"
                f"🔍 مشکل: {error_msg}\n\n"
                "💡 لطفاً پاسخ صحیحی ارسال کنید."
            )
            return
        
        # Submit the answer
        result = await self.questionnaire_manager.process_answer(user_id, text_answer)
        
        if result["status"] == "error":
            # Send improved error message
            await update.message.reply_text(
                f"❌ خطا در ثبت پاسخ:\n\n"
                f"{result['message']}\n\n"
                "🔄 لطفاً دوباره تلاش کنید."
            )
            return
        elif result["status"] == "completed":
            # Questionnaire completed
            await self.complete_questionnaire_from_text(update, context)
            return
        
        # Continue with next question
        question = result["question"]
        if question:
            # Show next question
            message = ("{result['progress_text']}\n"
                             "\n"
                             "{question['text']}")
            
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
        
        completion_message = ("🎉 تبریک! پرسشنامه با موفقیت تکمیل شد\n\n"
                             "اطلاعات شما ذخیره شد و حالا می‌تونیم بهترین برنامه تمرینی رو برای شما طراحی کنیم!\n\n"
                             "حالا وقت پرداخته! 💳")
        
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
        
        completion_message = ("🎉 تبریک! پرسشنامه با موفقیت تکمیل شد\n\n"
                             "اطلاعات شما ذخیره شد و حالا می‌تونیم بهترین برنامه تمرینی رو برای شما طراحی کنیم!\n\n"
                             "حالا وقت پرداخته! 💳")
        
        # Send completion message
        await update.message.reply_text(completion_message)
        
        # Wait a moment and then show payment details
        await asyncio.sleep(2)
        
        if course_type:
            # Create a mock update for payment details
            mock_update = update
            await self.show_payment_details(mock_update, context, course_type)

    async def back_to_main(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Return to main menu"""
        query = update.callback_query
        await query.answer()
        
        keyboard = [
            [InlineKeyboardButton("1️⃣ دوره تمرین حضوری", callback_data='in_person')],
            [InlineKeyboardButton("2️⃣ دوره تمرین آنلاین", callback_data='online')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(Config.WELCOME_MESSAGE, reply_markup=reply_markup)

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

    async def show_user_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_data: dict) -> None:
        """Show comprehensive user status"""
        user_id = update.effective_user.id
        user_name = user_data.get('name', 'کاربر')
        
        # Get current status
        status = await self.get_user_status(user_data)
        payment_status = user_data.get('payment_status', 'none')
        course_name = user_data.get('course', user_data.get('course_selected', 'انتخاب نشده'))
        
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
        status_text = (f"📊 **وضعیت شما**\n\n"
                       f"👤 **نام:** {user_name}\n"
                       f"📚 **دوره:** {course_name}\n"
                       f"💳 **وضعیت پرداخت:** {self.get_payment_status_text(payment_status)}")
        
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
            [InlineKeyboardButton("🔙 منوی اصلی", callback_data='back_to_main')]
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(status_text, reply_markup=reply_markup, parse_mode='Markdown')

    async def show_payment_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_data: dict) -> None:
        """Show detailed payment status"""
        payment_status = user_data.get('payment_status', 'none')
        course_name = user_data.get('course_selected', 'نامشخص')
        
        if payment_status == 'pending_approval':
            message = (f"⏳ **وضعیت پرداخت**\n\n"
                       f"دوره: {course_name}\n"
                       f"وضعیت: در انتظار تایید ادمین\n\n"
                       f"فیش واریزی شما دریافت شده و در حال بررسی است.\n"
                       f"معمولاً این فرآیند تا 24 ساعت طول می‌کشد.\n\n"
                       f"در صورت تایید، بلافاصله اطلاع‌رسانی خواهید شد.")
        elif payment_status == 'approved':
            message = (f"✅ **وضعیت پرداخت**\n\n"
                       f"دوره: {course_name}\n"
                       f"وضعیت: تایید شده\n\n"
                       f"پرداخت شما با موفقیت تایید شده است!\n"
                       f"اکنون می‌توانید برنامه تمرینی خود را دریافت کنید.")
        elif payment_status == 'rejected':
            message = (f"❌ **وضعیت پرداخت**\n\n"
                       f"دوره: {course_name}\n"
                       f"وضعیت: رد شده\n\n"
                       f"متاسفانه پرداخت شما تایید نشده است.\n"
                       f"لطفاً با پشتیبانی تماس بگیرید یا مجدداً پرداخت کنید.")
        else:
            message = "شما هنوز پرداختی انجام نداده‌اید."
        
        keyboard = [
            [InlineKeyboardButton("📞 تماس با پشتیبانی", callback_data='contact_support')],
            [InlineKeyboardButton("🔙 بازگشت", callback_data='my_status')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')

    async def continue_questionnaire(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Continue questionnaire from where user left off"""
        query = update.callback_query
        user_id = update.effective_user.id
        
        # Get current question
        question = await self.questionnaire_manager.get_current_question(user_id)
        if question:
            await self.questionnaire_manager.send_question(query.message.bot, user_id, question)
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
            await self.questionnaire_manager.send_question(query.message.bot, user_id, question)
        else:
            await query.edit_message_text("❌ خطا در شروع مجدد پرسشنامه.")

    async def show_training_program(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_data: dict) -> None:
        """Show user's training program"""
        course_name = user_data.get('course', 'نامشخص')
        
        # This would typically fetch from a database or generate based on questionnaire answers
        message = (f"📋 **برنامه تمرینی شما**\n\n"
                   f"دوره: {course_name}\n\n"
                   f"برنامه تمرینی شخصی‌سازی شده شما بر اساس پاسخ‌های پرسشنامه آماده شده است.\n\n"
                   f"برای دریافت برنامه کامل لطفاً با مربی تماس بگیرید:\n"
                   f"@username_coach\n\n"
                   f"یا از دکمه زیر استفاده کنید:")
        
        keyboard = [
            [InlineKeyboardButton("📞 تماس با مربی", callback_data='contact_coach')],
            [InlineKeyboardButton("📊 وضعیت من", callback_data='my_status')],
            [InlineKeyboardButton("🔙 منوی اصلی", callback_data='back_to_main')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')

    async def show_support_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show support contact information"""
        message = ("📞 **اطلاعات تماس پشتیبانی**\n"
                             "\n"
                             "برای دریافت پشتیبانی می‌توانید از روش‌های زیر استفاده کنید:\n"
                             "\n"
                             "🔹 تلگرام: @support_username\n"
                             "🔹 شماره تماس: ۰۹۱۲۳۴۵۶۷۸۹\n"
                             "🔹 ایمیل: support@example.com\n"
                             "\n"
                             "ساعات پاسخگویی:\n"
                             "شنبه تا پنج‌شنبه: ۹ صبح تا ۶ عصر\n"
                             "جمعه: ۱۰ صبح تا ۲ ظهر")
        
        keyboard = [
            [InlineKeyboardButton("🔙 بازگشت", callback_data='my_status')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')

    async def show_coach_contact(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show coach contact information"""
        message = ("👨‍💼 **تماس با مربی**\n"
                             "\n"
                             "برای دریافت برنامه تمرینی و مشاوره تخصصی:\n"
                             "\n"
                             "🔹 تلگرام: @coach_username\n"
                             "🔹 شماره تماس: ۰۹۱۲۳۴۵۶۷۸۹\n"
                             "\n"
                             "⏰ مربی معمولاً ظرف ۲۴ ساعت پاسخ می‌دهد.\n"
                             "\n"
                             "نکته: لطفاً نام و نام خانوادگی خود را در پیام اول ذکر کنید.")
        
        keyboard = [
            [InlineKeyboardButton("🔙 بازگشت", callback_data='view_program')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')

    async def start_new_course_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Start new course selection process"""
        keyboard = [
            [InlineKeyboardButton("1️⃣ دوره تمرین حضوری", callback_data='in_person')],
            [InlineKeyboardButton("2️⃣ دوره تمرین آنلاین", callback_data='online')],
            [InlineKeyboardButton("📊 وضعیت فعلی", callback_data='my_status')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = "انتخاب دوره جدید:\n\nکدام دوره را می‌خواهید انتخاب کنید?"
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup)

    def get_payment_status_text(self, status: str) -> str:
        """Convert payment status to Persian text("        status_map = {\n"
                             "            'pending_approval': '⏳ در انتظار تایید',\n"
                             "            'approved': '✅ تایید شده', \n"
                             "            'rejected': '❌ رد شده',\n"
                             "            'none': '❌ پرداخت نشده'\n"
                             "        }\n"
                             "        return status_map.get(status, '❓ نامشخص')\n"
                             "\n"
                             "    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:")Handle errors"""
        logger.error(f"Exception while handling an update: {context.error}")
        
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
    application.add_handler(CommandHandler("admin", bot.admin_panel.admin_menu))
    application.add_handler(CommandHandler("id", bot.admin_panel.get_id_command))
    application.add_handler(CommandHandler("add_admin", bot.admin_panel.add_admin_command))
    application.add_handler(CommandHandler("remove_admin", bot.admin_panel.remove_admin_command))
    
    application.add_handler(CallbackQueryHandler(bot.handle_main_menu, pattern='^(in_person|online)$'))
    application.add_handler(CallbackQueryHandler(bot.handle_course_details, pattern='^(in_person_cardio|in_person_weights|online_weights|online_cardio|online_combo)$'))
    application.add_handler(CallbackQueryHandler(bot.handle_payment, pattern='^payment_'))
    application.add_handler(CallbackQueryHandler(bot.handle_questionnaire_choice, pattern='^q_answer_'))
    application.add_handler(CallbackQueryHandler(bot.handle_payment_approval, pattern='^(approve_payment_|reject_payment_)'))
    application.add_handler(CallbackQueryHandler(bot.handle_status_callbacks, pattern='^(my_status|check_payment_status|continue_questionnaire|restart_questionnaire|view_program|contact_support|contact_coach|new_course)$'))
    application.add_handler(CallbackQueryHandler(bot.back_to_main, pattern='^back_to_main$'))
    application.add_handler(CallbackQueryHandler(bot.admin_panel.handle_admin_callbacks, pattern='^admin_'))
    
    # Handle photo messages (payment receipts and questionnaire photos)
    application.add_handler(MessageHandler(filters.PHOTO, bot.handle_payment_receipt))
    
    # Handle document/file uploads with helpful error messages
    application.add_handler(MessageHandler(filters.Document.ALL, bot.handle_unsupported_file))
    
    # Handle video uploads with helpful error messages
    application.add_handler(MessageHandler(filters.VIDEO, bot.handle_unsupported_file))
    
    # Handle audio uploads with helpful error messages
    application.add_handler(MessageHandler(filters.AUDIO | filters.VOICE, bot.handle_unsupported_file))
    
    # Handle sticker uploads with helpful error messages
    application.add_handler(MessageHandler(filters.Sticker.ALL, bot.handle_unsupported_file))
    
    # Handle text messages (questionnaire responses)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_questionnaire_response))
    
    # Add error handler
    application.add_error_handler(bot.error_handler)
    
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
