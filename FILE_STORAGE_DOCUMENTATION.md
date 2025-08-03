# 📁 File Storage and Management System

## 📊 Data Storage Architecture

The bot supports dual storage modes with seamless switching between development and production environments.

### Storage Modes

#### JSON Mode (Default - Development)
- **bot_data.json**: User data, payments, admin info, statistics
- **questionnaire_data.json**: Questionnaire responses and progress
- **admins.json**: Admin user permissions and roles
- **coupons.json**: Discount codes and usage tracking

#### PostgreSQL Mode (Production)
- **Full relational database** with ACID compliance
- **Connection pooling** for performance optimization
- **UTF-8 encoding** with Persian/RTL text support
- **Indexed queries** for fast data retrieval

## 📂 File Processing System

### Photo Storage (Questionnaire Step 18)

**Storage Location**: `questionnaire_data.json` → answers → photos
**Structure**:
```json
{
  "user_id": {
    "current_step": 18,
    "answers": {
      "photos": {
        "18": ["file_id_1", "file_id_2", "file_id_3"]
      }
    }
  }
}
```

**Process**:
1. User sends photo via Telegram
2. Bot validates file size and dimensions
3. Stores Telegram `file_id` for future access
4. Supports multiple photos per step (step 18 requires 3 photos)

### Document Storage (PDF Files - Steps 10 & 11)

**Storage Location**: `questionnaire_data.json` → answers → documents
**Structure**:
```json
{
  "user_id": {
    "answers": {
      "10": "📎 فایل ارسال شده: training_program.pdf",
      "documents": {
        "10": {
          "file_id": "document_file_id",
          "name": "training_program.pdf"
        }
      }
    }
  }
}
```

**Process**:
1. User sends PDF document
2. Bot validates file type (.pdf only)
3. Stores both text answer and document metadata
4. Document accessible via Telegram file_id

### Payment Receipt Storage

**Storage Location**: `bot_data.json` → payments
**Process**:
1. User uploads photo as payment receipt
2. Photo `file_id` stored in payment record
3. Admins receive photo with approval/rejection buttons
4. All actions logged with photo context

## 🔧 File Validation System

### Photo Validation
```python
# Size validation: 20MB maximum
# Dimension validation: 200x200 minimum
# Format: Automatic via Telegram filters.PHOTO
```

### Document Validation
```python
# PDF files only for questionnaire documents
# CSV files for admin imports only
# File extension and content validation
```

### Security Features
- **Malicious content detection**
- **File size and dimension limits**
- **Type validation beyond extensions**
- **Admin-only access for sensitive files**

## 📤 Export System

### User Data Export
- **Personal Information**: Complete user profile
- **Questionnaire Responses**: All 17 steps with validation
- **Payment History**: Transaction records and status
- **File References**: Photo and document metadata

### Admin Export Options
- **CSV Format**: Questionnaire data with Persian headers
- **JSON Format**: Complete database dump
- **Individual User**: Personal data export for specific users

### Export Features
- **Persian Headers**: Localized column names
- **Photo Count**: Automatic calculation per user
- **Document Info**: File names and references
- **Completion Status**: Progress tracking

## 🔄 File Flow Architecture

```
USER UPLOADS FILE
       ↓
TELEGRAM FILE FILTERS
       ↓
VALIDATION (size, type, security)
       ↓
ROUTE BY CONTEXT
       ↓
┌─────────────┬─────────────┬─────────────┐
│   PHOTO     │  DOCUMENT   │    OTHER    │
│             │             │             │
│ Payment     │ PDF Files   │ Security    │
│ Receipt     │ (Steps      │ Rejection   │
│ or          │ 10 & 11)    │ with        │
│ Question    │ or Admin    │ Helpful     │
│ Step 18     │ CSV Import  │ Message     │
└─────────────┴─────────────┴─────────────┘
       ↓
STORE IN APPROPRIATE LOCATION
       ↓
CONTINUE WORKFLOW (questionnaire/payment)
       ↓
AVAILABLE FOR ADMIN EXPORT
```

## 📈 Performance Considerations

### File Access Optimization
- **Telegram file_id caching**: Avoids redundant API calls
- **Lazy loading**: Files loaded only when needed
- **Batch processing**: Multiple file operations grouped

### Storage Efficiency
- **Reference-based storage**: Store file_id instead of binary data
- **Compression**: Automatic image optimization
- **Cleanup routines**: Remove unused file references

## 🛠️ Maintenance Tasks

### Regular Maintenance
- **Monitor file storage usage**
- **Clean up orphaned file references**
- **Validate file accessibility**
- **Update file validation rules as needed**

### Backup Strategy
- **Database backups** include file references
- **File migration** between storage modes
- **Export verification** for data integrity

## 🔐 Security Best Practices

### File Security
- **Content validation** beyond file extensions
- **Size and dimension limits** prevent abuse
- **Admin-only access** for sensitive operations
- **Audit logging** for all file operations

### Data Protection
- **No sensitive data in filenames**
- **Secure file_id storage**
- **Regular security audits**
- **Encrypted database connections** (PostgreSQL mode)
