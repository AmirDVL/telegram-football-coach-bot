# BotFather Setup Instructions

## Getting Your Bot Token

1. **Start BotFather**: Go to [@BotFather](https://t.me/botfather) on Telegram
2. **Create New Bot**: Send `/newbot`
3. **Set Bot Name**: Choose a display name (e.g., "Football Coach Bot")
4. **Set Username**: Choose a unique username ending in 'bot' (e.g., "football_coach_123_bot")
5. **Get Token**: Copy the token and add it to your `.env` file

## Optional BotFather Commands

### Set Bot Description
```
/setdescription
```
Then send:
```
ربات مربی فوتبال - دوره‌های تمرینی آنلاین و حضوری
🏃‍♂️ تمرینات هوازی و سرعتی
🏋️‍♂️ برنامه‌های وزنه تخصصی
⚽ تکنیک و کار با توپ
```

### Set Bot Commands (Menu)
```
/setcommands
```
Then send:
```
start - شروع و منوی اصلی
admin - پنل مدیریت (فقط ادمین)
id - نمایش Chat ID
```

### Set Bot About Text
```
/setabouttext
```
Then send:
```
مربی فوتبال حرفه‌ای با بیش از 10 سال تجربه
✅ دوره‌های تخصصی
✅ پشتیبانی کامل
✅ برنامه‌های شخصی‌سازی شده
```

### Set Bot Profile Photo
```
/setuserpic
```
Then upload your profile photo.

## Important Notes

❌ **Do NOT create inline keyboards in BotFather**
- Inline keyboards are created in the bot code automatically
- The buttons appear when users interact with the bot

✅ **What BotFather is for:**
- Getting bot token
- Setting bot info (description, commands, photo)
- Managing bot settings

✅ **What the code handles:**
- All inline keyboards and buttons
- User interactions and navigation
- Payment processing
- Admin panel

## Testing Your Bot

1. **Start your bot**: Run `python main.py`
2. **Test basic functionality**: Send `/start` to your bot
3. **Test admin features**: Send `/admin` (only works for admin IDs)
4. **Get your ID**: Send `/id` to see your chat ID

## Admin Commands Available

Once your bot is running:

- `/start` - Main menu for users
- `/admin` - Admin panel (admin only)
- `/id` - Show your chat ID
- `/add_admin [USER_ID]` - Add new admin (super admin only)
- `/remove_admin [USER_ID]` - Remove admin (super admin only)

## Troubleshooting

### If buttons don't appear:
- Make sure bot is running (`python main.py`)
- Check console for errors
- Verify bot token in `.env` file

### If admin panel doesn't work:
- Make sure your ID is in `.env` file as `ADMIN_ID`
- Use numeric ID (not username)
- Check `admins.json` file is created

### Getting your numeric Chat ID:
1. Send `/id` to your bot
2. Or message [@userinfobot](https://t.me/userinfobot)
3. Or check bot logs when you send `/start`
