# Local File Storage Implementation for Training Plans

## Overview

Implemented a comprehensive local file storage system for training plan PDFs and images to eliminate dependency on Telegram's file_id system, which can expire over time.

## Problem Solved

**Before:** Plans were stored only as Telegram `file_id` references, which:
- ❌ Can expire after some time
- ❌ Become invalid if deleted from Telegram servers
- ❌ Cause "Wrong type of web page content" errors
- ❌ Result in inability to send plans to users

**After:** Plans are now stored locally on disk with file_id as backup:
- ✅ Permanent local storage
- ✅ Independent of Telegram's file retention
- ✅ File_id used as fallback for compatibility
- ✅ Organized by course type

## Architecture

### New Component: `plan_file_manager.py`

**Features:**
- Downloads files from Telegram to local storage
- Organizes files by course type in subdirectories
- Generates unique filenames using MD5 hash + timestamp
- Tracks file metadata (size, upload time, uploader)
- Provides storage statistics
- Cleanup utilities for orphaned files

**Storage Structure:**
```
plan_files/
├── online_weights/
│   ├── abc123def456_20251009_220853.pdf
│   └── def789ghi012_20251009_221045.jpg
├── in_person_cardio/
│   └── ghi345jkl678_20251009_221230.pdf
└── nutrition_plan/
    └── jkl901mno234_20251009_221415.pdf
```

### Modified Components

#### 1. `main.py` - Plan Upload Handling

**Document Upload (Line ~1500):**
```python
# Now downloads and saves file locally
file_info = await plan_file_manager.download_and_save_plan(
    bot=context.bot,
    file_id=document.file_id,
    filename=filename,
    course_type=course_type,
    metadata={'uploaded_by': user_id, 'file_size': document.file_size}
)

# Stores both file_id and local_path
context.user_data[user_id]['plan_content'] = document.file_id
context.user_data[user_id]['plan_local_path'] = file_info['local_path']
```

**Photo Upload (Line ~1600):**
```python
# Same approach for photos
file_info = await plan_file_manager.download_and_save_plan(
    bot=context.bot,
    file_id=photo.file_id,
    filename=f"plan_photo_{timestamp}.jpg",
    course_type=course_type
)
```

**Plan Data Structure (Line ~1660):**
```python
plan_data = {
    'id': plan_id,
    'title': title,
    'content': content,              # Telegram file_id (backup)
    'local_path': local_path,        # Local file path (primary)
    'file_size': file_size,          # File size in bytes
    'content_type': content_type,
    'filename': filename,
    # ... other fields
}
```

#### 2. `admin_panel.py` - Plan Delivery

**Sending Plans to Users (Line ~3160):**
```python
# Try local file first
if plan_local_path and plan_file_manager.file_exists(plan_local_path):
    with open(plan_local_path, 'rb') as file:
        await context.bot.send_document(
            chat_id=int(user_id),
            document=file,
            caption=caption,
            filename=plan_filename
        )
    logger.info(f"Plan sent from local file: {plan_local_path}")

# Fallback to file_id if local file unavailable
elif plan_content:
    await context.bot.send_document(
        chat_id=int(user_id),
        document=plan_content,  # Telegram file_id
        caption=caption
    )
    logger.info(f"Plan sent using file_id fallback")
```

## Usage

### For Admins

**Uploading Plans:**
1. Upload PDF/image as before
2. File is automatically downloaded and saved locally
3. Both file_id and local path are stored
4. No change to user experience

**Sending Plans:**
1. System tries local file first
2. Falls back to file_id if local file missing
3. Handles both scenarios seamlessly

### Storage Management

**Check Storage Statistics:**
```python
from plan_file_manager import plan_file_manager

stats = plan_file_manager.get_storage_stats()
# Returns: total_files, total_size_mb, per-course breakdown
```

**File Information:**
```python
file_info = plan_file_manager.get_file_info(local_path)
# Returns: size, modified_at, exists status
```

**Cleanup Orphaned Files:**
```python
# Get all valid paths from database
valid_paths = [plan['local_path'] for plan in all_plans if plan.get('local_path')]

# Clean up files not in database
deleted_count = plan_file_manager.cleanup_orphaned_files(valid_paths)
```

## Benefits

### Reliability
- ✅ Plans always available, even if file_id expires
- ✅ No "Wrong type of web page content" errors
- ✅ Independent of Telegram's file retention policies

### Performance
- ✅ Faster delivery from local files
- ✅ No dependency on Telegram API for file retrieval
- ✅ Reduces API calls

### Management
- ✅ Easy backup - just backup `plan_files/` directory
- ✅ Organized by course type
- ✅ File metadata tracking
- ✅ Storage statistics

### Compatibility
- ✅ Backward compatible with existing file_id system
- ✅ Automatic fallback mechanism
- ✅ Works with existing plans (gradual migration)

## Migration Strategy

### Existing Plans
- Old plans still have file_id references
- System will use file_id for old plans
- New uploads automatically get local storage
- Can run migration script to download old plans (future feature)

### Gradual Transition
1. **Phase 1** (Current): New uploads stored locally + file_id
2. **Phase 2** (Future): Migrate existing plans to local storage
3. **Phase 3** (Future): Remove file_id dependency completely

## Disk Usage

### Current Storage (Before Implementation)
- JSON metadata only: **72KB**
- No actual files stored

### Expected Storage (After Implementation)
- Average PDF size: **1-5 MB**
- Average photo size: **500 KB - 2 MB**
- Estimated for 100 plans: **100-500 MB**
- Server has sufficient storage capacity

### Monitoring
```python
stats = plan_file_manager.get_storage_stats()
print(f"Total storage: {stats['total_size_mb']} MB")
print(f"Total files: {stats['total_files']}")
```

## Error Handling

### File Download Failure
- User receives error message
- Upload can be retried
- Logs error for debugging

### Local File Missing
- Automatically falls back to file_id
- Logs warning for investigation
- User experience unaffected

### File_id Expiration
- Local file used if available
- No impact on functionality
- System resilient to Telegram API changes

## Maintenance Tasks

### Regular Cleanup (Recommended: Monthly)
```python
# 1. Get all valid paths from all plan JSON files
# 2. Run cleanup to remove orphaned files
# 3. Review storage statistics
```

### Backup Strategy
```bash
# Backup plan files
rsync -av /opt/football-bot/plan_files/ /backup/plan_files/

# Backup plan metadata
cp admin_data/course_plans/*.json /backup/course_plans/
```

## Future Enhancements

### Planned Features
1. **Migration Tool**: Script to download all existing file_id-only plans
2. **Compression**: Automatic PDF compression to save space
3. **Cloud Backup**: Optional sync to cloud storage (S3, etc.)
4. **Admin Dashboard**: View storage statistics in admin panel
5. **File Validation**: Check PDF integrity before storing

### API Endpoints (Future)
```python
# Storage statistics endpoint
GET /admin/storage/stats

# Cleanup endpoint
POST /admin/storage/cleanup

# Migration endpoint
POST /admin/storage/migrate
```

## Deployment Notes

### Server Setup
1. Directory `plan_files/` created automatically on first upload
2. Permissions set to `footballbot:footballbot`
3. No manual configuration required

### Testing
1. Upload a new plan as admin
2. Check `/opt/football-bot/plan_files/{course_type}/` for file
3. Send plan to user - verify delivery
4. Delete local file manually - verify file_id fallback works

### Monitoring
```bash
# Check plan files directory
ls -lh /opt/football-bot/plan_files/

# Check disk usage
du -sh /opt/football-bot/plan_files/

# Check recent uploads
ls -lt /opt/football-bot/plan_files/*/ | head -10
```

## Conclusion

This implementation provides a robust, reliable solution for training plan storage that eliminates dependency on Telegram's file_id system while maintaining backward compatibility and providing a smooth migration path.

**Key Achievement**: Plans are now permanently stored and always accessible, regardless of Telegram API changes or file_id expiration.
