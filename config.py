import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    # Bot Configuration
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    ADMIN_ID = int(os.getenv('ADMIN_ID', '0')) if os.getenv('ADMIN_ID', '').isdigit() else None
    
    # Multiple Admin Support
    @classmethod
    def get_admin_ids(cls):
        """Get list of admin IDs from environment variables"""
        admin_ids = []
        
        # Add primary admin
        if cls.ADMIN_ID:
            admin_ids.append(cls.ADMIN_ID)
        
        # Add additional admins from ADMIN_IDS
        admin_ids_env = os.getenv('ADMIN_IDS', '')
        if admin_ids_env:
            for admin_id in admin_ids_env.split(','):
                admin_id = admin_id.strip()
                if admin_id.isdigit():
                    admin_id_int = int(admin_id)
                    if admin_id_int not in admin_ids:
                        admin_ids.append(admin_id_int)
        
        return admin_ids
    
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    
    # Database Configuration
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = int(os.getenv('DB_PORT', '5432'))
    DB_NAME = os.getenv('DB_NAME', 'football_coach_bot')
    DB_USER = os.getenv('DB_USER', 'postgres')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'password')
    
    # Use JSON files as fallback if DB is not configured
    USE_DATABASE = os.getenv('USE_DATABASE', 'False').lower() == 'true'
    
    # Payment Configuration
    PAYMENT_CARD_NUMBER = "1234-5678-9012-3456"
    PAYMENT_CARD_HOLDER = "محمد"
    
    @staticmethod
    def format_price(price: int) -> str:
        """Format price in a readable way"""
        if price >= 1000000:
            millions = price // 1000000
            if price % 1000000 == 0:
                return f"{millions}M تومان"
            else:
                remainder = (price % 1000000) // 1000
                if remainder == 0:
                    return f"{millions}M تومان"
                else:
                    return f"{millions}.{remainder}M تومان"
        elif price >= 1000:
            thousands = price // 1000
            if price % 1000 == 0:
                return f"{thousands}K تومان"
            else:
                return f"{thousands:,} تومان"
        else:
            return f"{price:,} تومان"
    
    # Course Prices (in Tomans)
    PRICES = {
        'in_person_cardio': 3000000,
        'in_person_weights': 3000000,
        'online_weights': 599000,
        'online_cardio': 599000,
        'online_combo': 999000
    }
    
    # Default coupon codes (can be overridden by admin-created ones)
    DEFAULT_COUPONS = {
        'WELCOME10': {'discount_percent': 10, 'active': True, 'description': 'خوش‌آمدگویی 10%'},
        'STUDENT20': {'discount_percent': 20, 'active': True, 'description': 'تخفیف دانشجویی 20%'},
        'VIP50': {'discount_percent': 50, 'active': False, 'description': 'تخفیف ویژه 50%'}
    }
    
    # Messages
    WELCOME_MESSAGE = """سلام رفیق خوبم💕

روی هر کدوم از دوره های مدنظرت که کلیک کنی اطلاعاتش برات ارسال میشه تا بتونی مناسب ترینشو متناسب با هدفت انتخاب کنی

و بدون که توی هرکدوم ازینا من کنارتم و بالاسرتم🩴🌝‌ تا بشی اون چیزی که میخوای…"""
    
    QUESTIONNAIRE = """اسم وفامیل خودت رو واسم بنویس.
سن
قد
وزن
چه لیگی بازی کردی ؟
چقدر تایم داری ؟
برای چه لیگ و مسابقاتی میخوای اماده شی؟
فصل بعد تیم داری با میخوای تست بری؟
یک ماه گذشته تمرین هوازی و وزنه داشتی؟
اگه تمرین داشتی با جزئیات برنامه تمرین هوازی و وزنه ات رو برام بفرست
برای تمرین هوازی توپ، کنز، زمین دم دستت هست؟(براساس اون تمرین هوازی بنویسم)
به عنوان یک بازیکن بزرگترین دغدغه ت چیه؟(قدرت ،سرعت ، حجم و….)
الان انفرادی تمرین میکنی یا با تیم؟
از نظر تو، سخت‌ترین مشکلات یا چالش‌هایی که تو تمرین کردن داری چیه؟
اگه قرار باشه یه قسمت از بدنتو تغییر بدی اون چیه؟
کدوم شبکه‌های اجتماعی را بیشتر استفاده می‌کنی؟
خب شماره‌تم بنویسسس  !"""
    
    # Course Details
    COURSE_DETAILS = {
        'in_person_cardio': {
            'title': 'دوره تمرین حضوری: هوازی سرعتی چابکی کاربا توپ',
            'description': """به خفن ترین دوره من خوش اومدی
اینجا قراره  روی تمام ضعف های بازیکن بطور حرفه ای وقت میذارم
هفته ای سه جلسه تمرینه
تمام نیازهای بازیکن کار میشه مثل
افزایش نفس
افزایش سرعت چابکی
افزایش تکنیک با توپ(شوت، دریبل و..)
افزایش پرش
و ....

در ماه ۱۲ جلسه
روزهای فرد
محدوده تمرین: پونک
شهریه ۳ تومن
ساعت تمرین و لوکیشن دقیق رو توی ما عضو میشی بهت میدم"""
        },
        'in_person_weights': {
            'title': 'دوره تمرین حضوری: وزنه اختصاصی',
            'description': """بهت تبریک میگن توی دوره ای رو انتخاب کردی که فقط بازیکنای حرفه ای و خاص میان سراغش😊🤝
 توی این دوره طوری باهات کار میشه که تا حالا تجربه اش نکردی
حرکات وزنه ای که تمرین میکنی هیچ جای دیگه ای کار نمیکنن چون ....😉
یه گرم کردن اختصاصی و متفاوت هر هر جای دیگه رو تجربه میکنی که موبیلیتی و دامنه حرکت مفاصل و کوتاهی عضلات رو برات حل میکنه
خود حرکات وزنه بهت کمک میکنه که
حجم خفنی بگیری
استایلت بهتر بشه
پرش و استارت هات سریع بشن
شوت قوی تر بزنی
تنه به تنه عالی بشی
عملکردت عجیب تغییر کنه

تمرینا روزای زوج هست
محدوده تمرین: خیابان کاشانی (کنار مترو کاشانی)
شهریه ۳ تومن
حق عضویت باشگاه جداست که حدود ۱ تومنه
ساعت تمرین و لوکیشن دقیق رو توی ما عضو میشی بهت میدم"""
        },
        'online_weights': {
            'title': 'دوره تمرین آنلاین: وزنه',
            'description': """این دوره پر فروش ترین دوره من بوده که بیش از هزار نفر تا الان ازش استفاده کردن
چرا اینقدر زیاد👇
چون جدیدترین حرکات وزنه ای که بازیکنای بزرگ دنیا کار میکنن رو اوردم 
بهت با فیلم یاد میدم هر حرکت چطوری درست بزنی
گرم کردن اختصاصی داره که بهت کمک میکنه موبیلیتی و دامنه حرکت مفاصلت زیاد بشه و کوتاهی عضلاتت از بین بره

داخل این دوره
بهت کمک میکنه حجم بهتر بگیری، استایلت بهتر بشه،  پرش و استارت هات سریع تر بشی، تنه به تنه قوی بشی، شوت قدرتی بزنی 
در کل عملکردت جوری تغییر کنه خودتم باورت نشه

برنامه های ۴ مرحله داره که براساس شرایط قبل اومدن پیش من و مدت زمانی که تو داری تا به اوج امادگی برسی بهت میگن چطوری کار کنی

قیمت هر برنامه ۵۹۹ تومنه
واریزی رو انجام دادی فیش رو همینجا ارسال میکنی و میریم توی کارش🤝💎😊"""
        },
        'online_cardio': {
            'title': 'دوره تمرین انلاین: هوازی و کاربا توپ',
            'description': """به دوره ای که باهات کاری میکنه دیگه توی زمین نفس کم نیاری خوش اومدی رفیق😊
اینجا بهت هر جلسه برنامه ای میدم که توش هم با توپ و هم بدون توپ تمرین میکنی
نفست زیاد میشه
تکنیک فوتبالیت افزایش پیدا میکنه
بازیکن بهتر و با کیفیت تری میشی
برنامه ها بصورت فیلم و عکس با جزئیات توضیح داده شده

از شروع تمرین یعنی گرم کردن بهت میگن طوری کار کنی تا آخرش که به سرد کردن میرسه
وسایل زیادی برای تمرین نیاز نداری
فقط یک توپ چندتا مانع و یک فضایی که بشه کار کرد و دوید 
همینا کاررو در میاره ✌️✌️✌️

برنامه ۱۲ جلسه ای (ماهانه) هست
قیمت هر برنامه  ۵۹۹ ت
واریزی رو انجام دادی فیش رو  همینجا ارسال میکنی میریم توی کارش🤝😊💎"""
        },
        'online_combo': {
            'title': 'دوره تمرین آنلاین: وزنه+ هوازی',
            'description': """توضیحات دوتا برنامه برای بازیکن بره و قیمت با تخفیف کلا بشه ۹۹۹ تومن

این پکیج شامل هر دو دوره آنلاین میشه:
✅ برنامه کامل وزنه با فیلم آموزشی
✅ برنامه کامل هوازی و کار با توپ
✅ گرم کردن اختصاصی
✅ پشتیبانی کامل من

قیمت با تخفیف ویژه: ۹۹۹ تومن (به جای ۱۱۹۸ تومن)
واریزی رو انجام دادی فیش رو همینجا ارسال میکنی و میریم توی کارش🤝💎😊"""
        }
    }
