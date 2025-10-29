# Project Structure

```
telegram-football-coach-bot/
│
├── src/                          # Source code directory
│   ├── bot/                      # Core bot application
│   │   ├── main.py              # Main bot entry point
│   │   ├── config.py            # Configuration management
│   │   └── bot_logger.py        # Logging setup
│   │
│   ├── admin/                    # Admin panel and management
│   │   ├── admin_panel.py       # Admin UI and callbacks
│   │   ├── admin_manager.py     # Admin permissions and roles
│   │   └── admin_error_handler.py  # Admin error handling
│   │
│   ├── managers/                 # Business logic managers
│   │   ├── data_manager.py      # Data storage abstraction
│   │   ├── questionnaire_manager.py  # User questionnaire flow
│   │   ├── coupon_manager.py    # Discount code management
│   │   ├── plan_file_manager.py # Training plan file operations
│   │   └── enhanced_plan_management.py  # Advanced plan features
│   │
│   ├── database/                 # Database layer
│   │   ├── database_manager.py  # PostgreSQL operations
│   │   └── secure_database_manager.py  # Secure DB operations
│   │
│   ├── utils/                    # Utility functions
│   │   ├── image_processor.py   # Image compression/processing
│   │   ├── input_validator.py   # Input validation
│   │   └── csv_exporter.py      # CSV export functionality
│   │
│   └── security/                 # Security features
│       ├── security_config.py   # Security settings
│       ├── security_integration.py  # Security middleware
│       └── security_monitor.py  # Security monitoring
│
├── scripts/                      # Deployment and maintenance scripts
│   ├── startup.sh               # Bot startup script
│   ├── quick_setup.sh           # Quick installation
│   ├── server_deploy.sh         # Server deployment
│   ├── production_security.sh   # Security hardening
│   ├── security_setup.sh        # Security setup
│   ├── security_hardening.sh    # Advanced security
│   └── linux_production_reset.sh  # Production reset
│
├── docs/                         # Documentation
│   ├── BOTFATHER_SETUP.md       # Bot creation guide
│   ├── DEPLOYMENT_GUIDE.md      # Deployment instructions
│   ├── GITHUB_SETUP.md          # GitHub configuration
│   ├── HOSTING_OPTIONS.md       # Hosting recommendations
│   └── test_status_system.md    # Testing documentation
│
├── data/                         # Data storage
│   ├── templates/               # Template files
│   │   └── admin_data/         # Admin data templates
│   │       ├── README.md
│   │       └── course_plans/   # Course plan templates
│   ├── exports/                # Generated exports
│   └── backups/                # Data backups
│
├── tests/                        # Test suite (to be added)
│
├── .github/                      # GitHub configuration
│   └── copilot-instructions.md  # AI coding instructions
│
├── run.py                        # Main entry point
├── requirements.txt              # Python dependencies
├── .env.example                  # Environment variables template
├── .gitignore                    # Git ignore rules
└── README.md                     # Project documentation
```

## Directory Descriptions

### `src/` - Source Code
All production code organized by function:
- **bot/**: Core Telegram bot application and configuration
- **admin/**: Administrative interface and user management
- **managers/**: Business logic for various bot features
- **database/**: Database abstraction and operations
- **utils/**: Reusable utility functions
- **security/**: Security features and monitoring

### `scripts/` - Automation Scripts
Shell scripts for deployment, setup, and maintenance

### `docs/` - Documentation
Comprehensive guides for setup, deployment, and usage

### `data/` - Data Storage
- **templates/**: Template files for courses and plans
- **exports/**: Generated CSV exports (gitignored)
- **backups/**: Database and file backups (gitignored)

### `tests/` - Testing
Unit and integration tests (to be implemented)

## Running the Bot

### Development
```bash
python run.py
```

### Production
```bash
./scripts/startup.sh
```

## Import Convention

All imports use the new package structure:
```python
from bot.config import Config
from managers.data_manager import DataManager
from admin.admin_panel import AdminPanel
from utils.image_processor import ImageProcessor
```
