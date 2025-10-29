import json
import os
import logging
from typing import Dict, Any, Optional
import aiofiles
from datetime import datetime

logger = logging.getLogger(__name__)

class QuestionnaireManager:
    def __init__(self, data_file='questionnaire_data.json'):
        # Ensure we use absolute path to avoid any directory issues
        if not os.path.isabs(data_file):
            data_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), data_file)
        self.data_file = data_file
        self.questions = {
            1: {
                "text": "🏃‍♂️ سلام! بیا با هم شروع کنیم.\n\nاسم و فامیل خودت رو بگو:",
                "type": "text",
                "emoji": "👤",
                "validation": {"min_length": 2, "max_length": 50}
            },
            2: {
                "text": "🎂 سن؟",
                "type": "number",
                "emoji": "🎂",
                "validation": {"min": 1, "max": 100}
            },
            3: {
                "text": "📏 قد؟ (برحسب سانتی‌متر)",
                "type": "number",
                "emoji": "📐",
                "validation": {"min": 150, "max": 210}
            },
            4: {
                "text": "⚖️ وزن؟ (برحسب کیلوگرم)",
                "type": "number",
                "emoji": "💪",
                "validation": {"min": 40, "max": 120}
            },
            5: {
                "text": "⚽ چه لیگی بازی کردی؟",
                "type": "text",
                "emoji": "🏆",
                "validation": {"min_length": 3, "max_length": 100}
            },
            6: {
                "text": "⏰ چقدر وقت داری؟",
                "type": "text",
                "emoji": "🕐",
                "validation": {"min_length": 3, "max_length": 50}
            },
            7: {
                "text": "🎯 برای چه لیگ و مسابقاتی می‌خواهی آماده بشی؟",
                "type": "text",
                "emoji": "🏁",
                "validation": {"min_length": 5, "max_length": 100}
            },
            8: {
                "text": "👥 فصل بعد تیم داری یا می‌خواهی تست بدی؟",
                "type": "text",
                "emoji": "⚽",
                "validation": {"min_length": 3, "max_length": 100}
            },
            9: {
                "text": "💪 یک ماه گذشته تمرین هوازی و وزنه داشتی؟",
                "type": "choice",
                "emoji": "🏋️‍♂️",
                "choices": ["بله", "خیر"]
            },
            10: {
                "text": "📋 اگر تمرین هوازی داشتی، جزئیات برنامه تمرین هوازی رو برام بفرست (متن یا فایل PDF):",
                "type": "text_or_document",
                "emoji": "🏃",
                "validation": {"min_length": 5, "max_length": 200},
                "condition": {"step": 9, "answer": "بله"}
            },
            11: {
                "text": "🏋️ اگر تمرین وزنه داشتی، جزئیات برنامه وزنه‌ات رو برام بفرست (متن یا فایل PDF):",
                "type": "text_or_document",
                "emoji": "🏋️‍♂️",
                "validation": {"min_length": 5, "max_length": 200},
                "condition": {"step": 9, "answer": "بله"}
            },
            12: {
                "text": "⚽ برای تمرین هوازی توپ، کنز، زمین دم دستت هست؟",
                "type": "text",
                "emoji": "⚽",
                "validation": {"min_length": 5, "max_length": 100}
            },
            13: {
                "text": "🎯 به عنوان یک بازیکن، بزرگترین دغدغه‌ات چیه؟ (قدرت، سرعت، حجم و …)",
                "type": "text",
                "emoji": "🎖️",
                "validation": {"min_length": 3, "max_length": 100}
            },
            14: {
                "text": "🏥 آیا مصدومیت‌های خاصی در گذشته داشتی؟",
                "type": "text",
                "emoji": "⚠️",
                "validation": {"min_length": 2, "max_length": 150}
            },
            15: {
                "text": "🍎 وضعیت تغذیه و خواب چطور است؟",
                "type": "text",
                "emoji": "😴",
                "validation": {"min_length": 5, "max_length": 150}
            },
            16: {
                "text": "🏃‍♂️ الان انفرادی تمرین می‌کنی یا با تیم؟",
                "type": "choice",
                "emoji": "👥",
                "choices": ["انفرادی", "با تیم", "ترکیبی از هر دو"]
            },
            17: {
                "text": "🤔 از نظر تو، سخت‌ترین مشکلات یا چالش‌هایی که تو تمرین داری چیه؟",
                "type": "text",
                "emoji": "⚠️",
                "validation": {"min_length": 5, "max_length": 150}
            },
            18: {
                "text": "📷 عکس از جلو، بغل و پشت برام بفرست برای آنالیز.\n\n⚠️ لطفاً حداقل یک عکس ارسال کنید (بهتره سه عکس جداگانه: جلو، پهلو، پشت).",
                "type": "photo",
                "emoji": "📷",
                "photo_count": 3,  # Maximum photos
                "min_photo_count": 1,  # Minimum photos required
                "validation": {"required": True}
            },
            19: {
                "text": "💪 اگر قرار باشه یک قسمت از بدنتو تغییر بدی، اون چیه؟",
                "type": "text",
                "emoji": "🎯",
                "validation": {"min_length": 3, "max_length": 100}
            },
            20: {
                "text": "📱 کدوم شبکه‌های اجتماعی رو بیشتر استفاده می‌کنی؟",
                "type": "text",
                "emoji": "📲",
                "validation": {"min_length": 2, "max_length": 100}
            },
            21: {
                "text": "📞 خب، شماره‌ات رو هم بنویس!\n(برای هماهنگی‌های ضروری نیاز داریم)\n\n(مثال: 09123456789)",
                "type": "phone",
                "emoji": "📱",
                "validation": {"pattern": r"^09[0-9]{9}$"}
            }
        }
        self.ensure_data_file()

    def ensure_data_file(self):
        """Ensure questionnaire data file exists"""
        if not os.path.exists(self.data_file):
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=2)

    async def load_user_progress(self, user_id: int) -> Dict[str, Any]:
        """Load user's questionnaire progress"""
        try:
            async with aiofiles.open(self.data_file, 'r', encoding='utf-8') as f:
                content = await f.read()
                data = json.loads(content)
                progress = data.get(str(user_id), None)
                
                # MIGRATION: Ensure photos dictionary exists for backward compatibility
                if progress and "answers" in progress:
                    if "photos" not in progress["answers"]:
                        progress["answers"]["photos"] = {}
                        # Save the migrated data back
                        await self.save_user_progress(user_id, progress)
                        print(f"INFO: Migrated user {user_id} questionnaire data to include photos dictionary")
                
                return progress
        except Exception as e:
            print(f"Error loading user progress for {user_id}: {e}")
            return None

    async def save_user_progress(self, user_id: int, progress: Dict[str, Any]):
        """Save user's questionnaire progress"""
        try:
            async with aiofiles.open(self.data_file, 'r', encoding='utf-8') as f:
                content = await f.read()
                data = json.loads(content) if content.strip() else {}
        except Exception:
            data = {}

        data[str(user_id)] = progress

        async with aiofiles.open(self.data_file, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(data, ensure_ascii=False, indent=2))

    async def start_questionnaire(self, user_id: int) -> Dict[str, Any]:
        """
        Start questionnaire for a user - only if no existing progress exists
        This method preserves existing questionnaire progress to prevent accidental resets
        """
        # Check if user already has questionnaire progress
        existing_progress = await self.load_user_progress(user_id)
        
        if existing_progress:
            # User already has questionnaire progress - return existing instead of overwriting
            print(f"INFO: User {user_id} already has questionnaire progress at step {existing_progress.get('current_step', 'unknown')} - preserving existing progress")
            return existing_progress
        
        # Only create new progress if none exists
        progress = {
            "current_step": 1,
            "answers": {"photos": {}},  # Initialize photos dictionary for backward compatibility
            "started_at": datetime.now().isoformat(),
            "completed": False
        }
        await self.save_user_progress(user_id, progress)
        print(f"INFO: Started fresh questionnaire for user {user_id}")
        return progress

    def get_question(self, step: int, user_answers: Dict = None) -> Optional[Dict]:
        """Get question for specific step"""
        if step not in self.questions:
            return None
        
        question = self.questions[step].copy()
        
        # Add progress text
        question["progress_text"] = f"سوال {step} از 21"
        
        # Replace placeholders in question text
        if user_answers and "name" in user_answers:
            question["text"] = question["text"].format(name=user_answers["name"])
        
        # Check if question has conditions
        if "condition" in question:
            condition = question["condition"]
            required_step = condition["step"]
            required_answer = condition["answer"]
            
            if not user_answers or str(required_step) not in user_answers:
                return None
            
            if user_answers[str(required_step)] != required_answer:
                return None
        
        return question

    def validate_answer(self, step: int, answer: str) -> tuple[bool, str]:
        """Validate user's answer for specific step"""
        question = self.questions.get(step)
        if not question:
            return False, "سوال نامعتبر"

        # Basic validation based on question type
        if question["type"] == "number":
            try:
                num = int(answer)
                validation = question.get("validation", {})
                if "min" in validation and num < validation["min"]:
                    return False, f"حداقل مقدار {validation['min']} است"
                if "max" in validation and num > validation["max"]:
                    return False, f"حداکثر مقدار {validation['max']} است"
                return True, ""
            except ValueError:
                return False, "لطفا یک عدد معتبر وارد کنید"

        elif question["type"] == "text":
            validation = question.get("validation", {})
            if "min_length" in validation and len(answer) < validation["min_length"]:
                return False, f"حداقل {validation['min_length']} کاراکتر وارد کنید"
            if "max_length" in validation and len(answer) > validation["max_length"]:
                return False, f"حداکثر {validation['max_length']} کاراکتر مجاز است"
            
            # Special validation for name field (step 1)
            if step == 1:
                # Check if name contains at least one letter
                import re
                if not re.search(r'[a-zA-Zآ-ی]', answer):
                    return False, "نام باید حداقل شامل یک حرف باشد. لطفاً نام و نام خانوادگی خود را به صورت کامل وارد کنید."
                # Check if it's not just numbers
                if answer.isdigit():
                    return False, "نام نمی‌تواند فقط شامل عدد باشد. لطفاً نام و نام خانوادگی خود را وارد کنید."
            
            return True, ""

        elif question["type"] == "phone":
            import re
            validation = question.get("validation", {})
            pattern = validation.get("pattern", r"^09[0-9]{9}$")
            if not re.match(pattern, answer):
                return False, "شماره تلفن نامعتبر است (مثال: 09123456789)"
            return True, ""

        elif question["type"] == "choice":
            choices = question.get("choices", [])
            if answer not in choices:
                return False, f"لطفا یکی از گزینه‌های موجود را انتخاب کنید: {', '.join(choices)}"
            return True, ""

        elif question["type"] == "multichoice":
            choices = question.get("choices", [])
            selected = [choice.strip() for choice in answer.split(",")]
            for choice in selected:
                if choice not in choices:
                    return False, f"گزینه '{choice}' نامعتبر است"
            return True, ""

        elif question["type"] == "text_or_document":
            # For text_or_document type, text validation applies
            validation = question.get("validation", {})
            if "min_length" in validation and len(answer) < validation["min_length"]:
                return False, f"حداقل {validation['min_length']} کاراکتر وارد کنید"
            if "max_length" in validation and len(answer) > validation["max_length"]:
                return False, f"حداکثر {validation['max_length']} کاراکتر مجاز است"
            return True, ""

        elif question["type"] == "photo":
            # Photo questions should only accept photos, not text
            # Use unified input validator for consistent error messages
            from utils.input_validator import input_validator
            return False, input_validator.get_input_type_error('photo')

        elif question["type"] == "document":
            # Document questions should only accept documents, not text
            from utils.input_validator import input_validator
            return False, input_validator.get_input_type_error('document')

        return True, ""

    async def process_answer(self, user_id: int, answer: str) -> Dict[str, Any]:
        """Process user's answer and return next step info"""
        progress = await self.load_user_progress(user_id)
        if not progress:
            return {
                "status": "error",
                "message": "شما در حال پاسخ دادن به پرسشنامه نیستید.",
                "current_step": 0
            }
            
        current_step = progress["current_step"]
        
        # Validate answer
        is_valid, error_message = self.validate_answer(current_step, answer)
        if not is_valid:
            return {
                "status": "error",
                "message": error_message,
                "current_step": current_step
            }
        
        # Save answer
        progress["answers"][str(current_step)] = answer
        progress["last_updated"] = datetime.now().isoformat()
        
        # Determine next step
        next_step = current_step + 1
        
        # Skip conditional questions if needed
        while next_step <= 21:
            next_question = self.get_question(next_step, progress["answers"])
            if next_question is not None:
                break
            next_step += 1
        
        if next_step > 21:
            # Questionnaire completed
            progress["completed"] = True
            progress["completed_at"] = datetime.now().isoformat()
            await self.save_user_progress(user_id, progress)
            
            return {
                "status": "completed",
                "message": self.get_completion_message(),
                "progress": progress
            }
        else:
            # Move to next step
            progress["current_step"] = next_step
            await self.save_user_progress(user_id, progress)
            
            next_question = self.get_question(next_step, progress["answers"])
            return {
                "status": "continue",
                "question": next_question,
                "step": next_step,
                "progress_text": f"سوال {next_step} از 21"
            }

    def get_completion_message(self) -> str:
        """Get completion message when questionnaire is finished"""
        return """🎉 عالی! پرسشنامه تکمیل شد!

✅ اطلاعات شما با موفقیت ثبت شد و در حال آماده‌سازی برنامه تمرینی شخصی‌سازی شده شما هستیم.

🔄 برنامه تمرینی شخصی‌سازی شده شما آماده سازی می‌شود.

⏰ معمولاً تا چند ساعت آینده برنامه کاملتان آماده خواهد شد.

📞 اگر سوالی دارید، از طریق @DrBohloul یا پشتیبانی ربات با ما در ارتباط باشید."""

    async def get_user_summary(self, user_id: int) -> Optional[str]:
        """Get formatted summary of user's answers"""
        progress = await self.load_user_progress(user_id)
        if not progress.get("completed"):
            return None
        
        answers = progress["answers"]
        summary = "📋 خلاصه اطلاعات کاربر:\n\n"
        
        for step, answer in answers.items():
            question = self.questions.get(int(step))
            if question:
                emoji = question.get("emoji", "•")
                summary += f"{emoji} {self.get_question_title(int(step))}: {answer}\n"
        
        return summary

    async def save_photo_answer(self, user_id: int, file_id: str, file_path: str) -> Dict[str, Any]:
        """Save photo answer for user"""
        progress = await self.load_user_progress(user_id)
        if not progress:
            return {"status": "error", "message": "User not in questionnaire"}
        
        current_step = progress["current_step"]
        current_question = self.get_question(current_step, progress["answers"])
        
        if not current_question or current_question.get("type") != "photo":
            return {"status": "error", "message": "Current question is not a photo question"}
        
        # Initialize photos storage
        if "photos" not in progress["answers"]:
            progress["answers"]["photos"] = {}
        
        if str(current_step) not in progress["answers"]["photos"]:
            progress["answers"]["photos"][str(current_step)] = []
        
        # Add photo info
        photo_info = {
            "file_id": file_id,
            "file_path": file_path,
            "uploaded_at": datetime.now().isoformat()
        }
        progress["answers"]["photos"][str(current_step)].append(photo_info)
        
        # Check if we have enough photos
        required_count = current_question.get("photo_count", 1)
        current_count = len(progress["answers"]["photos"][str(current_step)])
        
        if current_count >= required_count:
            # Mark step as completed and move to next
            progress["answers"][str(current_step)] = f"تصاویر ارسال شد ({current_count} عکس)"
            progress["last_updated"] = datetime.now().isoformat()
            
            # Move to next step
            next_step = current_step + 1
            while next_step <= 21:
                next_question = self.get_question(next_step, progress["answers"])
                if next_question is not None:
                    break
                next_step += 1
            
            if next_step > 21:
                # Questionnaire completed
                progress["completed"] = True
                progress["completed_at"] = datetime.now().isoformat()
                await self.save_user_progress(user_id, progress)
                return {
                    "status": "completed",
                    "message": self.get_completion_message()
                }
            else:
                progress["current_step"] = next_step
                await self.save_user_progress(user_id, progress)
                next_question = self.get_question(next_step, progress["answers"])
                return {
                    "status": "continue",
                    "question": next_question,
                    "step": next_step,
                    "progress_text": f"سوال {next_step} از 21"
                }
        else:
            # Need more photos
            await self.save_user_progress(user_id, progress)
            remaining = required_count - current_count
            return {
                "status": "need_more_photos",
                "message": f"✅ عکس دریافت شد! لطفاً {remaining} عکس دیگر ارسال کنید.",
                "remaining_photos": remaining
            }

    def get_question_title(self, step: int) -> str:
        """Get short title for each question"""
        titles = {
            1: "نام و فامیل",
            2: "سن", 
            3: "قد",
            4: "وزن",
            5: "تجربه لیگ",
            6: "وقت تمرین",
            7: "هدف مسابقات",
            8: "وضعیت تیم",
            9: "تمرین اخیر",
            10: "جزئیات تمرین هوازی",
            11: "جزئیات تمرین وزنه",
            12: "تجهیزات",
            13: "اولویت اصلی",
            14: "مصدومیت‌ها",
            15: "تغذیه و خواب",
            16: "نوع تمرین",
            17: "چالش‌ها",
            18: "عکس‌های بدن",
            19: "بهبود بدنی",
            20: "شبکه‌های اجتماعی",
            21: "شماره تماس"
        }
        return titles.get(step, f"سوال {step}")

    async def reset_user_progress(self, user_id: int):
        """Reset user's questionnaire progress"""
        try:
            async with aiofiles.open(self.data_file, 'r', encoding='utf-8') as f:
                content = await f.read()
                data = json.loads(content) if content.strip() else {}
        except Exception:
            data = {}

        if str(user_id) in data:
            del data[str(user_id)]

        async with aiofiles.open(self.data_file, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(data, ensure_ascii=False, indent=2))

    async def get_current_question(self, user_id: int) -> Optional[Dict]:
        """Get current question for user - only if questionnaire is explicitly active"""
        progress = await self.load_user_progress(user_id)
        
        # If user has no progress data or questionnaire is completed, return None
        # DON'T auto-start questionnaire - require explicit start
        if not progress or progress.get("completed"):
            return None
        
        current_step = progress["current_step"]
        question = self.get_question(current_step, progress["answers"])
        
        if question:
            question["step"] = current_step
            question["progress_text"] = f"سوال {current_step} از 21"
            
            # EDGE CASE HANDLING: If this is a photo question with partial photos uploaded
            if question.get("type") == "photo":
                # Ensure photos dictionary exists (backward compatibility)
                if "photos" not in progress["answers"]:
                    progress["answers"]["photos"] = {}
                
                photos_key = str(current_step)
                current_photos = len(progress["answers"]["photos"].get(photos_key, []))
                min_photo_count = question.get("min_photo_count", question.get("photo_count", 1))
                max_photo_count = question.get("photo_count", 1)
                
                if current_photos > 0:
                    # User has some photos uploaded - provide context
                    if current_photos >= min_photo_count:
                        question["partial_upload_message"] = f"شما قبلاً {current_photos} عکس ارسال کرده‌اید. می‌توانید ادامه دهید یا عکس‌های بیشتری اضافه کنید."
                        question["can_continue"] = True
                    else:
                        needed = min_photo_count - current_photos
                        question["partial_upload_message"] = f"شما {current_photos} عکس ارسال کرده‌اید. لطفاً {needed} عکس دیگر ارسال کنید."
                        question["can_continue"] = False
                    
                    question["photos_uploaded"] = current_photos
                    question["max_photos"] = max_photo_count
                    question["min_photos"] = min_photo_count
        
        return question

    async def send_question(self, bot, user_id: int, question: Dict):
        """Send a question to the user"""
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        base_message = f"""{question['progress_text']}

{question['text']}"""
        
        # Handle partial photo uploads
        if question.get("partial_upload_message"):
            base_message += f"\n\n💡 {question['partial_upload_message']}"
        
        message = base_message
        
        # Add choices as buttons if it's a choice question
        keyboard = []
        if question.get('type') in ['choice', 'multichoice']:
            choices = question.get('choices', [])
            for choice in choices:
                keyboard.append([InlineKeyboardButton(choice, callback_data=f'q_answer_{choice}')])
        elif question.get('type') == 'photo' and question.get('can_continue'):
            # Add continue button for photo questions where minimum is met
            keyboard = [
                [InlineKeyboardButton("➡️ ادامه به سوال بعد", callback_data='continue_photo_question')],
                [InlineKeyboardButton("📷 ارسال عکس بیشتر", callback_data='add_more_photos')]
            ]
        
        if keyboard:
            reply_markup = InlineKeyboardMarkup(keyboard)
        else:
            reply_markup = None
            
        await bot.send_message(
            chat_id=user_id,
            text=message,
            reply_markup=reply_markup
        )

    async def get_user_questionnaire_status(self, user_id: int) -> Dict[str, Any]:
        """Get user's questionnaire progress status"""
        try:
            async with aiofiles.open(self.data_file, 'r', encoding='utf-8') as f:
                content = await f.read()
                data = json.loads(content) if content else {}
            
            user_data = data.get(str(user_id), {})
            current_step = user_data.get('current_step', 1)
            total_steps = len(self.questions)
            completed = user_data.get('completed', False)
            
            return {
                'current_step': current_step,
                'total_steps': total_steps,
                'completed': completed,
                'progress_percentage': (current_step / total_steps) * 100 if not completed else 100,
                'answers_count': len(user_data.get('answers', {}))
            }
            
        except Exception as e:
            print(f"Error getting questionnaire status: {e}")
            return {
                'current_step': 1,
                'total_steps': len(self.questions),
                'completed': False,
                'progress_percentage': 0,
                'answers_count': 0
            }

    async def reset_questionnaire(self, user_id: int) -> bool:
        """Reset user's questionnaire progress"""
        try:
            async with aiofiles.open(self.data_file, 'r', encoding='utf-8') as f:
                content = await f.read()
                data = json.loads(content) if content else {}
            
            # Reset user's questionnaire data
            data[str(user_id)] = {
                'current_step': 1,
                'answers': {},
                'completed': False,
                'started_at': datetime.now().isoformat()
            }
            
            async with aiofiles.open(self.data_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(data, ensure_ascii=False, indent=2))
            
            return True
            
        except Exception as e:
            print(f"Error resetting questionnaire: {e}")
            return False

    async def process_photo_answer(self, user_id: int, photo_file_id: str, bot=None) -> Dict[str, Any]:
        """Process photo answer for questionnaire and download it locally"""
        progress = await self.load_user_progress(user_id)
        if not progress:
            return {
                "status": "error", 
                "message": "شما در حال پاسخ دادن به پرسشنامه نیستید.",
                "current_step": 0
            }
            
        current_step = progress["current_step"]
        
        # Check if current question is a photo question
        question = self.questions.get(current_step)
        if not question or question.get("type") != "photo":
            return {
                "status": "error",
                "message": "در حال حاضر عکس مورد نیاز نیست.",
                "current_step": current_step
            }
        
        # Download and save photo locally if bot is provided
        local_photo_path = None
        if bot:
            try:
                # Create user photo directory
                user_photo_dir = f"questionnaire_photos/user_{user_id}/step_{current_step}"
                os.makedirs(user_photo_dir, exist_ok=True)
                
                # Download photo from Telegram
                file = await bot.get_file(photo_file_id)
                photo_bytes = await file.download_as_bytearray()
                
                # Generate unique filename
                import time
                timestamp = int(time.time())
                filename = f"photo_{timestamp}_{len(progress['answers'].get('photos', {}).get(str(current_step), []))}.jpg"
                
                # Use image processor to compress and save
                from utils.image_processor import ImageProcessor
                image_processor = ImageProcessor()
                local_photo_path = await image_processor.save_compressed_image(
                    bytes(photo_bytes), 
                    filename, 
                    user_photo_dir
                )
                
                logger.info(f"Photo saved locally: {local_photo_path} for user {user_id}, step {current_step}")
                
            except Exception as e:
                logger.error(f"Error downloading/saving photo: {e}")
                # Continue without local save - still store file_id
        
        # Initialize photos array if it doesn't exist
        if "photos" not in progress["answers"]:
            progress["answers"]["photos"] = {}
        if str(current_step) not in progress["answers"]["photos"]:
            progress["answers"]["photos"][str(current_step)] = []
        
        # Store photo info (both file_id and local path)
        photo_info = {
            "file_id": photo_file_id,
            "local_path": local_photo_path,
            "timestamp": datetime.now().isoformat()
        }
        progress["answers"]["photos"][str(current_step)].append(photo_info)
        
        # Check photo requirements for this question
        photo_count = question.get("photo_count", 1)  # Maximum photos
        min_photo_count = question.get("min_photo_count", photo_count)  # Minimum photos (defaults to max for backwards compatibility)
        current_photos = len(progress["answers"]["photos"][str(current_step)])
        
        # Save progress after adding photo
        await self.save_user_progress(user_id, progress)
        
        # Check if we have minimum photos required
        if current_photos < min_photo_count:
            # Still need more photos to meet minimum
            remaining = min_photo_count - current_photos
            return {
                "status": "need_more_photos",
                "message": f"✅ عکس دریافت شد! ({current_photos}/{photo_count})\n\n📸 لطفاً حداقل {remaining} عکس دیگر ارسال کنید.",
                "current_step": current_step,
                "photos_received": current_photos,
                "photos_needed": photo_count,
                "min_photos_needed": min_photo_count
            }
        elif current_photos < photo_count:
            # Met minimum, but can add more photos
            remaining = photo_count - current_photos
            return {
                "status": "can_continue_or_add_more",
                "message": f"✅ عکس دریافت شد! ({current_photos}/{photo_count})\n\n📸 می‌تونید {remaining} عکس دیگر اضافه کنید یا به سوال بعد بروید.",
                "current_step": current_step,
                "photos_received": current_photos,
                "photos_needed": photo_count,
                "min_photos_met": True
            }
        
        # We have maximum photos, move to next step automatically
        progress["answers"][str(current_step)] = f"تصاویر ارسال شد ({current_photos} عکس)"
        progress["last_updated"] = datetime.now().isoformat()
        
        # Determine next step
        next_step = current_step + 1
        
        # Skip conditional questions if needed
        while next_step <= 21:
            next_question = self.get_question(next_step, progress["answers"])
            if next_question is not None:
                break
            next_step += 1
        
        if next_step > 21:
            # Questionnaire completed
            progress["completed"] = True
            progress["completed_at"] = datetime.now().isoformat()
            await self.save_user_progress(user_id, progress)
            
            return {
                "status": "completed",
                "message": self.get_completion_message(),
                "current_step": 21,
                "total_steps": 21,
                "completed": True
            }
        else:
            # Move to next step
            progress["current_step"] = next_step
            await self.save_user_progress(user_id, progress)
            
            next_question = self.get_question(next_step, progress["answers"])
            return {
                "status": "next_question",
                "question": next_question,
                "current_step": next_step,
                "total_steps": 21,
                "completed": False
            }
    async def process_document_answer(self, user_id: int, document_file_id: str, document_name: str = "") -> Dict[str, Any]:
        """Process document answer for questionnaire"""
        progress = await self.load_user_progress(user_id)
        if not progress:
            return {
                "status": "error", 
                "message": "شما در حال پاسخ دادن به پرسشنامه نیستید.",
                "current_step": 0
            }
            
        current_step = progress["current_step"]
        
        # Check if current question accepts documents
        question = self.questions.get(current_step)
        if not question or question.get("type") not in ["text_or_document"]:
            return {
                "status": "error",
                "message": "در حال حاضر فایل مورد نیاز نیست.",
                "current_step": current_step
            }
        
        # Save document information as the answer
        document_answer = f"📎 فایل ارسال شده: {document_name or 'document'}"
        
        # Store both text answer and document file_id
        progress["answers"][str(current_step)] = document_answer
        
        # Initialize documents array if it doesn't exist
        if "documents" not in progress["answers"]:
            progress["answers"]["documents"] = {}
        progress["answers"]["documents"][str(current_step)] = {
            "file_id": document_file_id,
            "name": document_name or "document"
        }
        
        # Move to next step
        progress["current_step"] += 1
        
        # Save progress
        await self.save_user_progress(user_id, progress)
        
        # Return next question or completion info
        if progress["current_step"] <= 18:
            next_question = await self.get_current_question(user_id)
            return {
                "status": "next_question",
                "question": next_question,
                "current_step": progress["current_step"],
                "total_steps": 18,
                "completed": False
            }
        else:
            # Questionnaire completed
            return {
                "status": "completed",
                "message": "پرسشنامه شما با موفقیت تکمیل شد!",
                "current_step": 18,
                "total_steps": 18,
                "completed": True
            }
        
        if current_photos < photo_count:
            # Need more photos
            remaining = photo_count - current_photos
            return {
                "status": "need_more_photos",
                "message": f"✅ عکس دریافت شد! ({current_photos}/{photo_count})\n\n📸 لطفاً {remaining} عکس دیگر ارسال کنید.",
                "current_step": current_step,
                "photos_received": current_photos,
                "photos_needed": photo_count
            }
        
        # We have enough photos, move to next step
        progress["answers"][str(current_step)] = f"تصاویر ارسال شد ({photo_count} عکس)"
        progress["last_updated"] = datetime.now().isoformat()
        
        # Determine next step
        next_step = current_step + 1
        
        # Skip conditional questions if needed
        while next_step <= 21:
            next_question = self.get_question(next_step, progress["answers"])
            if next_question is not None:
                break
            next_step += 1
        
        if next_step > 21:
            # Questionnaire completed
            progress["completed"] = True
            progress["completed_at"] = datetime.now().isoformat()
            await self.save_user_progress(user_id, progress)
            
            return {
                "status": "completed",
                "message": self.get_completion_message(),
                "progress": progress
            }
        else:
            # Move to next step
            progress["current_step"] = next_step
            await self.save_user_progress(user_id, progress)
            
            next_question = self.get_question(next_step, progress["answers"])
            return {
                "status": "continue",
                "question": next_question,
                "step": next_step,
                "progress_text": f"سوال {next_step} از 21"
            }

    def is_current_question_photo(self, user_id: int) -> bool:
        """Check if current question expects a photo"""
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            progress = loop.run_until_complete(self.load_user_progress(user_id))
            if not progress:
                return False
            current_step = progress["current_step"]
            question = self.questions.get(current_step)
            return question and question.get("type") == "photo"
        except Exception:
            return False

    async def get_user_photos(self, user_id: int) -> Dict[str, list]:
        """Get all user photos from questionnaire"""
        progress = await self.load_user_progress(user_id)
        if not progress:
            return {}
        return progress["answers"].get("photos", {})

    # ==================== EDIT MODE FUNCTIONALITY ====================

    async def start_edit_mode(self, user_id: int) -> Dict[str, Any]:
        """Start editing completed questionnaire from the beginning"""
        progress = await self.load_user_progress(user_id)
        if not progress or not progress.get("completed"):
            return {
                "status": "error",
                "message": "شما هنوز پرسشنامه را تکمیل نکرده‌اید یا پرسشنامه‌ای وجود ندارد."
            }
        
        # Set edit mode and start from first question
        progress["edit_mode"] = True
        progress["edit_step"] = 1
        progress["last_edit_updated"] = datetime.now().isoformat()
        await self.save_user_progress(user_id, progress)
        
        first_question = self.get_question(1, progress["answers"])
        current_answer = progress["answers"].get("1", "")
        
        return {
            "status": "edit_started",
            "question": first_question,
            "step": 1,
            "current_answer": current_answer,
            "progress_text": f"ویرایش سوال 1 از 21",
            "total_questions": 21
        }

    async def navigate_edit_mode(self, user_id: int, direction: str) -> Dict[str, Any]:
        """Navigate forward/backward in edit mode"""
        progress = await self.load_user_progress(user_id)
        if not progress or not progress.get("edit_mode"):
            return {
                "status": "error", 
                "message": "شما در حالت ویرایش نیستید."
            }
        
        current_edit_step = progress.get("edit_step", 1)
        
        if direction == "forward":
            new_step = current_edit_step + 1
        elif direction == "backward":
            new_step = current_edit_step - 1
        else:
            return {"status": "error", "message": "جهت نامعتبر"}
        
        # Validate step bounds
        if new_step < 1:
            return {
                "status": "error",
                "message": "شما در اولین سوال هستید."
            }
        elif new_step > 21:
            return {
                "status": "error", 
                "message": "شما در آخرین سوال هستید."
            }
        
        # Update edit step
        progress["edit_step"] = new_step
        await self.save_user_progress(user_id, progress)
        
        # Get question and current answer
        question = self.get_question(new_step, progress["answers"])
        current_answer = progress["answers"].get(str(new_step), "")
        
        return {
            "status": "edit_navigation",
            "question": question,
            "step": new_step,
            "current_answer": current_answer,
            "progress_text": f"ویرایش سوال {new_step} از 21",
            "total_questions": 21
        }

    async def update_answer_in_edit_mode(self, user_id: int, new_answer: str) -> Dict[str, Any]:
        """Update answer for current question in edit mode"""
        progress = await self.load_user_progress(user_id)
        if not progress or not progress.get("edit_mode"):
            return {
                "status": "error",
                "message": "شما در حالت ویرایش نیستید."
            }
        
        current_edit_step = progress.get("edit_step", 1)
        
        # Validate answer
        is_valid, error_message = self.validate_answer(current_edit_step, new_answer)
        if not is_valid:
            return {
                "status": "error",
                "message": error_message
            }
        
        # Update answer
        progress["answers"][str(current_edit_step)] = new_answer
        progress["last_edit_updated"] = datetime.now().isoformat()
        await self.save_user_progress(user_id, progress)
        
        return {
            "status": "answer_updated",
            "message": f"✅ پاسخ سوال {current_edit_step} به‌روزرسانی شد.",
            "step": current_edit_step
        }

    async def finish_edit_mode(self, user_id: int) -> Dict[str, Any]:
        """Exit edit mode and return to normal state"""
        progress = await self.load_user_progress(user_id)
        if not progress or not progress.get("edit_mode"):
            return {
                "status": "error",
                "message": "شما در حالت ویرایش نیستید."
            }
        
        # Remove edit mode flags
        progress.pop("edit_mode", None)
        progress.pop("edit_step", None)
        progress["last_updated"] = datetime.now().isoformat()
        await self.save_user_progress(user_id, progress)
        
        return {
            "status": "edit_finished",
            "message": "✅ ویرایش پرسشنامه تکمیل شد.\n\nتغییرات شما ذخیره شده است."
        }

    async def continue_to_next_question(self, user_id: int) -> Dict[str, Any]:
        """Continue to next question when minimum photo requirements are met"""
        progress = await self.load_user_progress(user_id)
        if not progress:
            return {
                "status": "error",
                "message": "پرسشنامه یافت نشد."
            }
        
        current_step = progress.get("current_step", 1)
        current_question = self.get_question(current_step, progress["answers"])
        
        if not current_question or current_question.get("type") != "photo":
            return {
                "status": "error",
                "message": "این گزینه فقط برای سوالات عکس قابل استفاده است."
            }
        
        # Check if minimum photo requirements are met
        min_photo_count = current_question.get("min_photo_count", current_question.get("photo_count", 1))
        photos_key = str(current_step)
        
        # Ensure photos dictionary exists (backward compatibility)
        if "photos" not in progress["answers"]:
            progress["answers"]["photos"] = {}
            
        current_photos = len(progress["answers"]["photos"].get(photos_key, []))
        
        if current_photos < min_photo_count:
            return {
                "status": "error",
                "message": f"❌ شما باید حداقل {min_photo_count} عکس ارسال کنید.\n\nتعداد عکس‌های ارسالی: {current_photos}"
            }
        
        # Mark current step as completed
        progress["answers"][str(current_step)] = f"تصاویر ارسال شد ({current_photos} عکس)"
        progress["last_updated"] = datetime.now().isoformat()
        
        # Move to next step
        next_step = current_step + 1
        
        # Skip conditional questions if needed
        while next_step <= 21:
            next_question = self.get_question(next_step, progress["answers"])
            if next_question is not None:
                break
            next_step += 1
        
        if next_step > 21:
            # Questionnaire completed
            progress["completed"] = True
            progress["completed_at"] = datetime.now().isoformat()
            await self.save_user_progress(user_id, progress)
            
            return {
                "status": "completed",
                "message": "🎉 پرسشنامه تکمیل شد!\n\nبرنامه تمرینی شما آماده خواهد شد."
            }
        else:
            # Update progress to next step
            progress["current_step"] = next_step
            await self.save_user_progress(user_id, progress)
            
            return {
                "status": "next_question",
                "question": next_question,
                "step": next_step,
                "progress_text": f"سوال {next_step} از 21"
            }
