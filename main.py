import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

from config import Config
from data_manager import DataManager
from admin_panel import AdminPanel
from questionnaire_manager import QuestionnaireManager

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
                total_steps = questionnaire_status.get('total_steps', 17)
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
        """Show payment details"""
        user_id = update.effective_user.id
        
        # Save payment initiation
        await self.data_manager.save_payment_data(user_id, {
            'course_type': course_type,
            'price': Config.PRICES[course_type],
            'status': 'pending'
        })
        
        payment_message = f"""برای پرداخت به شماره کارت زیر واریز کنید:

💳 شماره کارت: {Config.PAYMENT_CARD_NUMBER}
👤 نام صاحب حساب: {Config.PAYMENT_CARD_HOLDER}
💰 مبلغ: {Config.PRICES[course_type]:,} تومان

بعد از واریز، فیش یا اسکرین شات رو همینجا ارسال کنید تا بررسی شه ✅

⚠️ توجه: فقط فیش واریز رو ارسال کنید"""
        
        keyboard = [
            [InlineKeyboardButton("🔙 بازگشت", callback_data='back_to_main')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.edit_message_text(payment_message, reply_markup=reply_markup)
        else:
            await update.message.reply_text(payment_message, reply_markup=reply_markup)

    async def handle_payment_receipt(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle payment receipt submission"""
        user_id = update.effective_user.id
        
        if user_id not in self.payment_pending:
            await update.message.reply_text("لطفا ابتدا یک دوره انتخاب کنید و سپس فیش واریز را ارسال نمایید.")
            return
        
        course_type = self.payment_pending[user_id]
        
        # Save receipt info
        await self.data_manager.save_user_data(user_id, {
            'receipt_submitted': True,
            'course_selected': course_type,
            'payment_status': 'pending_approval'
        })
        
        await update.message.reply_text("فیش واریز شما دریافت شد و در حال بررسی است... ⏳\n\nلطفا منتظر تایید ادمین بمانید.")
        
        # Get course details for admin notification
        course_title = Config.COURSE_DETAILS.get(course_type, {}).get('title', 'نامشخص')
        price = Config.PRICES.get(course_type, 0)
        
        # Notify admin for approval
        if Config.ADMIN_ID:
            try:
                admin_message = f"""🔔 درخواست تایید پرداخت جدید:
                
👤 کاربر: {update.effective_user.first_name} (@{update.effective_user.username or 'بدون نام کاربری'})
🆔 User ID: {user_id}
📚 دوره: {course_title}
💰 مبلغ: {price:,} تومان

⚠️ فیش واریز ارسال شده - لطفا بررسی کنید"""
                
                # Create approval buttons for admin
                keyboard = [
                    [InlineKeyboardButton("✅ تایید پرداخت", callback_data=f'approve_payment_{user_id}')],
                    [InlineKeyboardButton("❌ رد پرداخت", callback_data=f'reject_payment_{user_id}')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await context.bot.send_message(
                    chat_id=Config.ADMIN_ID, 
                    text=admin_message,
                    reply_markup=reply_markup
                )
            except Exception as e:
                logger.error(f"Failed to send admin notification: {e}")

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
            
            await update.message.reply_text("""🎉 عالی! اطلاعات شما دریافت شد.

برنامه تمرینی شما بر اساس اطلاعات ارائه شده طراحی میشه و ظرف ۲۴ ساعت براتون ارسال میشه.

از اینکه به خانواده ما پیوستید خوشحالیم! 💪⚽️

برای هر سوال یا مشکل، همیشه در دسترس هستم 🤝""")
            
            # Update statistics
            await self.data_manager.update_statistics('total_users')
            
            # Notify admin with full details
            if Config.ADMIN_ID:
                try:
                    admin_message = f"""📝 فرم جدید دریافت شد:
👤 کاربر: {update.effective_user.first_name} (@{update.effective_user.username or 'بدون نام کاربری'})
🆔 User ID: {user_id}
📚 دوره: {user_data.get('course', 'نامشخص')}
📄 پاسخ‌ها:
{update.message.text[:1000]}{'...' if len(update.message.text) > 1000 else ''}"""
                    
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
            
            updated_message = f"""✅ پرداخت تایید شد:
👤 کاربر: {user_data.get('name', 'ناشناس')}
🆔 User ID: {user_id}
📚 دوره: {course_title}
💰 مبلغ: {price:,} تومان
⏰ تایید شده توسط: {update.effective_user.first_name}"""
            
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
            updated_message = f"""❌ پرداخت رد شد:
👤 کاربر: {user_data.get('name', 'ناشناس')}
🆔 User ID: {user_id}
⏰ رد شده توسط: {update.effective_user.first_name}"""
            
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
        """Handle text responses from questionnaire"""
        user_id = update.effective_user.id
        text_answer = update.message.text
        
        # Check if user is in questionnaire mode
        current_question = await self.questionnaire_manager.get_current_question(user_id)
        
        if not current_question:
            # User is not in questionnaire mode, ignore
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
                total_steps = q_status.get('total_steps', 17)
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
            [InlineKeyboardButton("🔙 منوی اصلی", callback_data='back_to_main')]
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(status_text, reply_markup=reply_markup, parse_mode='Markdown')

    async def show_payment_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_data: dict) -> None:
        """Show detailed payment status"""
        payment_status = user_data.get('payment_status', 'none')
        course_name = user_data.get('course_selected', 'نامشخص')
        
        if payment_status == 'pending_approval':
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
        keyboard = [
            [InlineKeyboardButton("1️⃣ دوره تمرین حضوری", callback_data='in_person')],
            [InlineKeyboardButton("2️⃣ دوره تمرین آنلاین", callback_data='online')],
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

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle errors"""
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
    
    # Handle photo messages (payment receipts)
    application.add_handler(MessageHandler(filters.PHOTO, bot.handle_payment_receipt))
    
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
