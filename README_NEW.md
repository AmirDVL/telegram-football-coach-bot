# ⚽ Telegram Football Coach Bot

A sophisticated Persian Telegram bot for football training course management with comprehensive admin panel, payment processing, and interactive questionnaire system.

## 🌟 Features

### 🎓 Course Management
- **Training Courses**: In-person and online football training programs
- **Pricing System**: Flexible pricing with Persian number formatting
- **Smart User Flow**: Course selection → Payment → Admin approval → Questionnaire → Training program

### 📝 Interactive Questionnaire
- **17-Step System**: Comprehensive data collection for personalized training
- **Real-time Validation**: Input validation and progress tracking
- **Media Support**: Photo uploads, document handling, text responses

### 💳 Payment Processing
- **Admin Approval Workflow**: Manual payment verification system
- **Receipt Management**: Image upload and processing
- **Status Tracking**: Real-time payment status updates

### 👨‍💼 Admin Panel
- **User Management**: Comprehensive user analytics and management
- **Payment Administration**: Approve/reject payments with detailed tracking
- **Data Export**: CSV/JSON export functionality for users and questionnaires
- **Admin Roles**: Super admin and regular admin permissions

### 🖼️ File Processing
- **Image Compression**: Automatic optimization (max 1MB, 85% quality)
- **File Validation**: Security checks and format validation
- **Document Support**: PDF handling for training materials

## 🏗️ Architecture

### Core Files
```
main.py                    # Main bot application
├── config.py             # Configuration management
├── data_manager.py       # Data persistence layer
├── questionnaire_manager.py # Questionnaire system
├── admin_panel.py        # Admin interface
├── admin_manager.py      # Admin user management
├── coupon_manager.py     # Discount system
├── image_processor.py    # Image handling
├── database_manager.py   # Database operations
└── bot_logger.py         # Logging system
```

### Data Storage
- **JSON Mode** (Default): File-based storage for development
- **PostgreSQL Mode**: Production database with full ACID compliance
- **Dual Support**: Seamlessly switch between storage modes

## 🚀 Quick Start

### 1. Setup Environment

```bash
# Clone the repository
git clone https://github.com/AmirDVL/telegram-football-coach-bot.git
cd telegram-football-coach-bot

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your bot token and settings
```

### 2. Bot Configuration

```bash
# Set up your Telegram bot with BotFather
# Follow BOTFATHER_SETUP.md for detailed instructions

# Configure admin users in .env
ADMIN_ID=your_telegram_user_id
```

### 3. Run the Bot

```bash
# Development mode (JSON storage)
python main.py

# Production mode (PostgreSQL)
export USE_DATABASE=true
python main.py
```

## 📊 User Flow

```
/start → Course Selection → Payment → Admin Approval → Questionnaire → Training Program
```

1. **New User**: Course selection with pricing information
2. **Payment**: Secure payment information collection
3. **Admin Review**: Manual payment approval workflow
4. **Questionnaire**: 17-step interactive data collection
5. **Training**: Personalized program delivery

## 🛡️ Security Features

- **Input Validation**: SQL injection and XSS prevention
- **File Security**: Malicious content detection
- **Admin Controls**: Multi-level permission system
- **Audit Logging**: Comprehensive action tracking
- **Data Protection**: Secure storage and transmission

## 🌐 Localization

- **Full Persian Support**: RTL text handling and Persian numerals
- **Course Translation**: Automatic conversion from English codes to Persian names
- **Cultural Adaptation**: Persian pricing format and communication style

## 📁 Documentation

- **[Deployment Guide](DEPLOYMENT_GUIDE.md)**: Production setup instructions
- **[BotFather Setup](BOTFATHER_SETUP.md)**: Telegram bot configuration
- **[File Storage](FILE_STORAGE_DOCUMENTATION.md)**: Data management details

## 🔧 Configuration Options

### Environment Variables

```bash
# Required
BOT_TOKEN=your_bot_token_here
ADMIN_ID=your_telegram_user_id

# Optional
USE_DATABASE=false              # true for PostgreSQL, false for JSON
DEBUG=false                     # Enable debug logging
DATABASE_URL=postgresql://...   # PostgreSQL connection string
```

### Storage Modes

#### JSON Mode (Development)
- File-based storage
- Easy setup and debugging
- Perfect for development and testing

#### PostgreSQL Mode (Production)
- Full database features
- Better performance and reliability
- Recommended for production use

## 📈 Statistics & Analytics

The bot automatically tracks:
- User registrations and course selections
- Payment completion rates
- Questionnaire completion statistics
- Admin activity logs
- System performance metrics

## 🛠️ Admin Commands

- `/start` - Access admin panel (for admin users)
- `/admin` - Alternative admin access
- Admin panel provides web-like interface for all management tasks

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📝 License

This project is private and proprietary. All rights reserved.

## 🆘 Support

For support and questions:
1. Check the documentation files
2. Review the deployment guide
3. Contact the development team

---

**Built with ❤️ for the Persian football community**
