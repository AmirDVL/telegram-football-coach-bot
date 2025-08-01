# Football Coach Bot - AI Coding Instructions

## Architecture Overview

This is a **Persian/Farsi Telegram bot** for football training course management with a sophisticated multi-stage user flow. The system uses a **component-based architecture** with dual storage modes (JSON/PostgreSQL).

### Core Components

- `main.py` - Central bot orchestrator with ~2400 lines handling all user interactions
- `data_manager.py` - Abstract storage layer supporting JSON files and PostgreSQL
- `questionnaire_manager.py` - 17-step interactive questionnaire system
- `admin_panel.py` - Multi-level admin interface with payment approval workflow
- `config.py` - Environment-driven configuration with admin ID management
- `coupon_manager.py` - Discount code system with usage tracking

## Critical User Flow (Status-Based Navigation)

The bot uses **status-based menu rendering** - users see different interfaces based on their current state:

```python
# Key status progression in main.py:
'new_user' → 'payment_pending' → 'payment_approved' → questionnaire completion
```

**Essential Pattern**: Always check user status via `get_user_status()` before rendering menus. This method determines the entire UI flow.

## Persian/Farsi Considerations

- All user-facing text is in **Persian/Farsi** with RTL support
- Use `get_course_name_farsi()` to convert English course codes to Persian display names
- Database/JSON stores English course codes (`in_person_cardio`, `online_weights`, etc.) but shows Persian names to users
- Payment amounts use Persian number formatting via `Config.format_price()`

## Data Management Patterns

### Dual Storage Architecture

```python
# Check storage mode in config.py:
USE_DATABASE = os.getenv('USE_DATABASE', 'false').lower() == 'true'
```

**JSON Mode** (default): Uses `bot_data.json`, `questionnaire_data.json`, `admins.json`
**PostgreSQL Mode**: Full relational database with connection pooling

### Critical Save Pattern

```python
# Always use merge pattern for user data:
existing_data = await self.data_manager.get_user_data(user_id)
updated_data = {**existing_data, **new_data}
await self.data_manager.save_user_data(user_id, updated_data)
```

## Admin System Architecture

**Two-tier admin system**:

- Super Admin (from ADMIN_ID env var) - can manage other admins
- Regular Admins (added by super admin) - payment approval only

Admin IDs sync from environment variables on bot startup. See `initialize()` method for admin sync logic.

## Payment Workflow

**Critical 4-stage process**:

1. Course selection → stores `course_selected`
2. Payment details display → user uploads receipt image
3. Admin approval → changes status to `payment_approved`
4. Questionnaire → 17 interactive steps → training program access

**Key files**: `handle_payment_receipt()` for image processing, admin panel payment approval methods.

## Development Commands

### Local Development

```bash
python main.py  # Starts bot in JSON mode
```

### Database Mode

```bash
# Set USE_DATABASE=true in .env
python test_postgresql_compatibility.py  # Test DB connectivity
python clear_database.py  # Reset database
```

### Admin Management

```bash
python debug_admin.py  # Check admin sync status
python force_admin_sync.py  # Force admin resync from env vars
```

## Key Integration Points

### Message Handler Priority

```python
# Handler order in main.py is critical:
1. Photos → payment receipts or questionnaire images
2. Text → questionnaire responses or coupon codes
3. Callbacks → all button interactions
```

### Questionnaire State Management

The bot tracks questionnaire progress per user. Check `questionnaire_manager.py` for step validation and photo handling patterns.

### Image Processing

All uploaded images go through `image_processor.py` for compression and validation before storage.

## Testing & Debugging

- Use `test_questionnaire.py` for questionnaire flow testing
- Check `DEPLOYMENT_GUIDE.md` for production setup
- Admin debug tools in `debug_*.py` files
- Security testing via `security_*.py` modules

## Common Pitfalls

1. **Never bypass status checks** - user flow depends on correct status-based rendering
2. **Persian text handling** - always use proper encoding and the translation functions
3. **Payment state management** - ensure proper status transitions in payment workflow
4. **Admin permissions** - verify admin level before sensitive operations
5. **Async patterns** - all data operations are async, don't mix sync/async calls
6. **Terminal commands** - ensure every command is compatible with powershell in development, but deploy with bash scripts for production

## Configuration Management

Environment variables are critical - see `.env.example` for required setup. Bot supports both development (JSON) and production (PostgreSQL) modes through config switching.
