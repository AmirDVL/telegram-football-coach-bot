# Football Coach Telegram Bot

A comprehensive Telegram bot for a football coach that offers training courses with payment processing and user registration. Built with the latest Python libraries and follows the exact sequence from bot.txt.

## Features

- **🎯 Course Selection**: In-person and online training courses
- **⌨️ Interactive Menus**: Inline keyboard navigation 
- **💳 Payment Processing**: Receipt verification system
- **📝 User Registration**: Detailed questionnaire system
- **👨‍💼 Admin Notifications**: Real-time alerts for new registrations
- **💾 Data Persistence**: JSON-based data storage
- **🔧 Environment Configuration**: Secure environment variables
- **📊 Statistics Tracking**: User and payment analytics

## Quick Start

### Windows
```bash
# 1. Run setup
setup.bat

# 2. Configure your bot token in .env file
# 3. Run the bot
run.bat
```

### Linux/Mac
```bash
# 1. Make scripts executable
chmod +x setup.sh run.sh

# 2. Run setup
./setup.sh

# 3. Configure your bot token in .env file
# 4. Run the bot
./run.sh
```

## Manual Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment Configuration**:
   - Create `.env` file in project root
   - Add your bot token from [@BotFather](https://t.me/botfather)
   ```env
   BOT_TOKEN=your_bot_token_here
   ADMIN_ID=your_admin_chat_id_here
   DEBUG=False
   ```

3. **Run the Bot**:
   ```bash
   python main.py
   ```

## Course Structure

### In-Person Courses (3,000,000 Tomans each)
1. **🏃‍♂️ Cardio Training**: Football-specific cardio, agility, and ball work
   - 3 sessions per week (odd days)
   - Location: Poonak area
   - Includes: Speed, agility, technique, jumping

2. **🏋️‍♂️ Weight Training**: Specialized weight training for football players
   - Sessions on even days
   - Location: Kashani Street (near Kashani Metro)
   - Gym membership: ~1,000,000 Tomans additional

### Online Courses
1. **💪 Weight Training Program**: 599,000 Tomans
   - Video tutorials for proper form
   - 4-phase program structure
   - Specialized warm-up routines

2. **⚽ Cardio & Ball Work Program**: 599,000 Tomans  
   - 12 monthly sessions
   - With and without ball exercises
   - Minimal equipment needed

3. **🎯 Combined Package**: 999,000 Tomans (discounted from 1,198,000)
   - Both weight and cardio programs
   - Complete support included

## Bot Flow Sequence

1. **👋 Welcome Message** → Course type selection
2. **📚 Course Categories** → Specific course selection  
3. **📖 Course Details** → Payment initiation
4. **💳 Payment Instructions** → Receipt submission
5. **✅ Payment Verification** → Questionnaire delivery
6. **📝 Registration Complete** → Program delivery (24h)

## Technical Architecture

### File Structure
```
telegram_bot/
├── main.py              # Main bot application
├── config.py            # Configuration and constants
├── data_manager.py      # Data persistence layer
├── requirements.txt     # Python dependencies
├── .env                # Environment variables (create this)
├── .gitignore          # Git ignore rules
├── README.md           # Documentation
├── setup.bat/.sh       # Setup scripts
├── run.bat/.sh         # Run scripts
└── bot_data.json       # User data storage (auto-created)
```

### Key Components

- **🔧 Config Class**: Centralized configuration management
- **💾 DataManager**: Async JSON-based data persistence  
- **🤖 FootballCoachBot**: Main bot logic with state management
- **📊 Statistics**: Automatic tracking of users and payments

## Configuration Options

### Environment Variables
```env
BOT_TOKEN=your_bot_token_here     # Required: From @BotFather
ADMIN_ID=your_admin_chat_id       # Optional: For notifications  
DEBUG=True                        # Optional: Enable debug logging
```

### Payment Configuration
Update in `config.py`:
```python
PAYMENT_CARD_NUMBER = "1234-5678-9012-3456"
PAYMENT_CARD_HOLDER = "محمد"
```

### Course Prices
Easily modify in `config.py`:
```python
PRICES = {
    'in_person_cardio': 3000000,
    'in_person_weights': 3000000,
    'online_weights': 599000,
    'online_cardio': 599000,
    'online_combo': 999000
}
```

## Advanced Features

### Admin Notifications
- Real-time payment confirmations
- User registration alerts  
- Questionnaire responses
- Statistical updates

### Data Persistence
- User profiles and preferences
- Payment history and status
- Course selections and progress
- System statistics

### Error Handling
- Graceful error recovery
- User-friendly error messages
- Detailed logging for debugging
- Admin notification on critical errors

## Security & Best Practices

- ✅ Environment variables for sensitive data
- ✅ Input validation and sanitization
- ✅ Secure payment receipt handling
- ✅ User data privacy protection
- ✅ Error logging without sensitive info

## Development

### Adding New Courses
1. Update `Config.COURSE_DETAILS` in `config.py`
2. Add pricing in `Config.PRICES`
3. Update keyboard handlers in `main.py`

### Custom Payment Integration
Replace the payment verification logic in `handle_payment_receipt()` with your preferred payment gateway.

### Database Integration
Replace `DataManager` with database connectivity (PostgreSQL, MongoDB, etc.)

## Troubleshooting

### Common Issues

1. **Bot Token Error**:
   - Verify token in `.env` file
   - Check token format from @BotFather

2. **Permission Errors**:
   - Ensure bot has proper permissions
   - Check admin ID configuration

3. **File Not Found**:
   - Run setup script first
   - Check file paths and permissions

### Logs
Check console output for detailed error messages and debugging information.

## Support & Updates

- **📚 Documentation**: [python-telegram-bot docs](https://python-telegram-bot.readthedocs.io/)
- **🔄 Updates**: Keep dependencies updated with `pip install -r requirements.txt --upgrade`
- **🐛 Issues**: Check logs and error messages for debugging

## License

This project is built for educational purposes. Ensure compliance with Telegram's Terms of Service and local regulations for payment processing.
