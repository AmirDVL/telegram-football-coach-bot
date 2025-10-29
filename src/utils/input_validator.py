"""
Unified Input Validation System
Provides consistent error messages for input type mismatches
"""

from typing import Dict, Tuple, Optional
from telegram import Update
from telegram.ext import ContextTypes

class InputValidator:
    """Centralized input validation with unified error messages"""
    
    # Unified error messages for different expected input types
    ERROR_MESSAGES = {
        'photo': "📷 این بخش نیاز به ارسال تصویر دارد.\n\n💡 لطفاً عکس ارسال کنید، نه متن.",
        'document': "📄 این بخش نیاز به ارسال فایل دارد.\n\n💡 لطفاً فایل (PDF، Word، Excel و غیره) ارسال کنید، نه متن.",
        'text': "📝 این بخش نیاز به ارسال متن دارد.\n\n💡 لطفاً متن وارد کنید، نه فایل یا عکس.",
        'text_or_document': "📝📄 این بخش نیاز به متن یا فایل PDF دارد.\n\n💡 می‌توانید:\n• متن پاسخ را بنویسید\n• یا فایل PDF ارسال کنید\n\n❌ استیکر، عکس و سایر فایل‌ها پذیرفته نمی‌شود.",
        'number': "🔢 این بخش نیاز به ارسال عدد دارد.\n\n💡 لطفاً یک عدد معتبر وارد کنید، نه متن عادی.",
        'phone': "📞 این بخش نیاز به شماره تلفن دارد.\n\n💡 لطفاً شماره تلفن را به فرمت 09123456789 وارد کنید.",
        'choice': "🔘 این بخش نیاز به انتخاب از گزینه‌های موجود دارد.\n\n💡 لطفاً از دکمه‌های زیر انتخاب کنید یا گزینه صحیح را تایپ کنید.",
        'coupon': "🎫 کد تخفیف نامعتبر است.\n\n💡 لطفاً کد تخفیف معتبر وارد کنید یا بدون کد ادامه دهید.",
        'admin_plan_description': "📋 توضیحات برنامه تمرینی نامعتبر.\n\n💡 لطفاً توضیحات مناسب برای برنامه تمرینی وارد کنید.",
        'admin_plan_file': "📁 این بخش نیاز به ارسال فایل برنامه تمرینی دارد.\n\n💡 لطفاً فایل برنامه (PDF، تصویر و غیره) ارسال کنید.",
        'invalid_context': "❓ ورودی نامشخص.\n\n💡 لطفاً از منوهای ربات استفاده کنید یا /start را فشار دهید."
    }
    
    @classmethod
    def get_input_type_error(cls, expected_type: str, context_info: str = "") -> str:
        """Get unified error message for wrong input type"""
        base_message = cls.ERROR_MESSAGES.get(expected_type, cls.ERROR_MESSAGES['invalid_context'])
        
        if context_info:
            return f"{base_message}\n\n📍 محل: {context_info}"
        return base_message
    
    @classmethod
    def validate_questionnaire_input_type(cls, question_type: str, input_type: str) -> Tuple[bool, Optional[str]]:
        """
        Validate if input type matches expected questionnaire question type
        
        Args:
            question_type: Expected type (photo, text, number, choice, etc.)
            input_type: Actual input type (text, photo, document)
            
        Returns:
            (is_valid, error_message)
        """
        # Define valid input types for each question type
        valid_inputs = {
            'text': ['text'],
            'number': ['text'],  # Numbers come as text and get validated
            'phone': ['text'],   # Phone numbers come as text
            'choice': ['text'],  # Choice answers come as text
            'multichoice': ['text'],  # Multiple choice answers come as text
            'photo': ['photo'],
            'document': ['document'],
            'text_or_document': ['text', 'document'],  # Accepts both
            'coupon_code': ['text']  # Coupon codes are text input from users
        }
        
        expected_inputs = valid_inputs.get(question_type, ['text'])
        
        if input_type in expected_inputs:
            return True, None
        
        # Generate appropriate error message
        if question_type == 'photo':
            return False, cls.get_input_type_error('photo')
        elif question_type == 'document':
            return False, cls.get_input_type_error('document')
        elif question_type == 'text_or_document':
            return False, cls.get_input_type_error('text_or_document')
        elif question_type in ['text', 'number', 'phone', 'choice', 'multichoice', 'coupon_code']:
            return False, cls.get_input_type_error('text')
        else:
            return False, cls.get_input_type_error('invalid_context')
    
    @classmethod
    def validate_admin_input_type(cls, expected_type: str, input_type: str, context: str = "") -> Tuple[bool, Optional[str]]:
        """
        Validate admin input types
        
        Args:
            expected_type: What admin input is expected (plan_description, plan_file, etc.)
            input_type: What was actually sent (text, photo, document)
            context: Additional context for error message
            
        Returns:
            (is_valid, error_message)
        """
        # Define valid input types for admin operations
        admin_valid_inputs = {
            'plan_description': ['text'],
            'plan_file': ['photo', 'document'],
            'coupon_code': ['text'],
            'user_search': ['text']
        }
        
        expected_inputs = admin_valid_inputs.get(expected_type, ['text'])
        
        if input_type in expected_inputs:
            return True, None
        
        # Generate appropriate error message based on expected type
        if expected_type == 'plan_description':
            return False, cls.get_input_type_error('admin_plan_description', context)
        elif expected_type == 'plan_file':
            return False, cls.get_input_type_error('admin_plan_file', context)
        elif expected_type in ['coupon_code', 'user_search']:
            return False, cls.get_input_type_error('text', context)
        else:
            return False, cls.get_input_type_error('invalid_context', context)
    
    @classmethod
    def get_input_type_from_update(cls, update: Update) -> str:
        """Determine the input type from telegram update"""
        if update.message.photo:
            return 'photo'
        elif update.message.document:
            return 'document'
        elif update.message.text:
            return 'text'
        elif update.message.sticker:
            return 'sticker'
        elif update.message.voice:
            return 'voice'
        elif update.message.video:
            return 'video'
        elif update.message.audio:
            return 'audio'
        elif update.message.animation:
            return 'animation'
        elif update.message.contact:
            return 'contact'
        elif update.message.location:
            return 'location'
        else:
            return 'unknown'
    
    @classmethod
    async def validate_and_reject_wrong_input_type(cls, update: Update, expected_type: str, 
                                                 context_info: str = "", is_admin: bool = False) -> bool:
        """
        Validate input type and send error message if wrong type
        
        Args:
            update: Telegram update
            expected_type: Expected input type
            context_info: Additional context for error message
            is_admin: Whether this is admin input
            
        Returns:
            True if input type is correct, False if wrong (error message sent)
        """
        actual_type = cls.get_input_type_from_update(update)
        
        if is_admin:
            is_valid, error_message = cls.validate_admin_input_type(expected_type, actual_type, context_info)
        else:
            is_valid, error_message = cls.validate_questionnaire_input_type(expected_type, actual_type)
        
        if not is_valid and error_message:
            await update.message.reply_text(error_message)
            return False
        
        return True

# Create global instance
input_validator = InputValidator()
