import json
import os
from typing import Dict, Any, Optional
import aiofiles
from datetime import datetime

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
                "validation": {"min": 16, "max": 40}
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
                "text": "📋 اگر تمرین هوازی داشتی، جزئیات برنامه تمرین هوازی رو برام بفرست:",
                "type": "text",
                "emoji": "🏃",
                "validation": {"min_length": 5, "max_length": 200},
                "condition": {"step": 9, "answer": "بله"}
            },
            11: {
                "text": "🏋️ اگر تمرین وزنه داشتی، جزئیات برنامه وزنه‌ات رو برام بفرست:",
                "type": "text",
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
                "text": "� عکس از جلو، بغل و پشت برام بفرست برای آنالیز.\n\n⚠️ لطفاً سه عکس جداگانه ارسال کنید: یکی از جلو، یکی از پهلو و یکی از پشت.",
                "type": "photo",
                "emoji": "📷",
                "photo_count": 3,
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
                "type": "multichoice",
                "emoji": "📲",
                "choices": ["اینستاگرام", "تلگرام", "یوتیوب", "فیسبوک", "توییتر", "هیچ‌کدام"]
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
        """Start questionnaire for a user"""
        progress = {
            "current_step": 1,
            "answers": {},
            "started_at": datetime.now().isoformat(),
            "completed": False
        }
        await self.save_user_progress(user_id, progress)
        return progress

    def get_question(self, step: int, user_answers: Dict = None) -> Optional[Dict]:
        """Get question for specific step"""
        if step not in self.questions:
            return None
        
        question = self.questions[step].copy()
        
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

        elif question["type"] == "photo":
            # Photo validation is handled separately in photo handler
            return True, ""

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

✅ اطلاعات شما با موفقیت ثبت شد
📊 بر اساس پاسخ‌هایت، برنامه تمرینی شخصی‌سازی شده‌ای آماده می‌کنم
⏰ تا چند ساعت آینده برنامه کاملت رو دریافت خواهی کرد

🔥 آماده‌ای تا بهترین ورژن خودت بشی؟

📞 اگر سوالی داری، با پشتیبانی در ارتباط باش."""

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
        """Get current question for user"""
        progress = await self.load_user_progress(user_id)
        if not progress or progress.get("completed"):
            return None
        
        current_step = progress["current_step"]
        question = self.get_question(current_step, progress["answers"])
        
        if question:
            question["step"] = current_step
            question["progress_text"] = f"سوال {current_step} از 21"
        
        return question

    async def send_question(self, bot, user_id: int, question: Dict):
        """Send a question to the user"""
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        message = f"""{question['progress_text']}

{question['text']}"""
        
        # Add choices as buttons if it's a choice question
        keyboard = []
        if question.get('type') in ['choice', 'multichoice']:
            choices = question.get('choices', [])
            for choice in choices:
                keyboard.append([InlineKeyboardButton(choice, callback_data=f'q_answer_{choice}')])
        
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

    async def process_photo_answer(self, user_id: int, photo_file_id: str) -> Dict[str, Any]:
        """Process photo answer for questionnaire"""
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
        
        # Initialize photos array if it doesn't exist
        if "photos" not in progress["answers"]:
            progress["answers"]["photos"] = {}
        if str(current_step) not in progress["answers"]["photos"]:
            progress["answers"]["photos"][str(current_step)] = []
        
        # Add photo to current step
        progress["answers"]["photos"][str(current_step)].append(photo_file_id)
        
        # Check if we have enough photos for this question
        photo_count = question.get("photo_count", 1)
        current_photos = len(progress["answers"]["photos"][str(current_step)])
        
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
