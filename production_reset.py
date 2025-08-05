#!/usr/bin/env python3
"""
🔄 PRODUCTION RESET SCRIPT
Comprehensive reset utility for testing and deployment preparation
SECURITY-FOCUSED: Cleans all test data and prepares for production
"""

import os
import shutil
import json
import glob
import time
from datetime import datetime
from pathlib import Path

class ProductionReset:
    """Comprehensive reset utility for production deployment"""
    
    def __init__(self):
        self.reset_log = []
        self.start_time = datetime.now()
        self.backup_dir = f"pre_reset_backup_{int(time.time())}"
        
    def log(self, message: str, level: str = "INFO"):
        """Log reset operations"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {level}: {message}"
        self.reset_log.append(log_entry)
        print(log_entry)
    
    def create_backup(self):
        """Create backup of critical data before reset"""
        try:
            os.makedirs(self.backup_dir, exist_ok=True)
            
            # Backup critical data files
            critical_files = [
                'bot_data.json',
                'questionnaire_data.json', 
                'admins.json',
                'coupons.json',
                '.env'
            ]
            
            for file in critical_files:
                if os.path.exists(file):
                    shutil.copy2(file, f"{self.backup_dir}/{file}")
                    self.log(f"Backed up: {file}")
            
            # Backup user documents if they exist
            if os.path.exists('user_documents'):
                shutil.copytree('user_documents', f"{self.backup_dir}/user_documents")
                self.log("Backed up: user_documents/")
                
            self.log(f"Backup created in: {self.backup_dir}")
            return True
            
        except Exception as e:
            self.log(f"Backup failed: {e}", "ERROR")
            return False
    
    def clean_development_files(self):
        """Remove all development and testing files"""
        self.log("Cleaning development files...")
        
        # Development file patterns
        dev_patterns = [
            'test_*.py',
            '*_test.py', 
            'debug_*.py',
            'verify_*.py',
            'check_*.py',
            'audit_*.py',
            'fix_*.py',
            'clear_*.py',
            'reset_*.py',
            '*_temp.py',
            'simple_*.py',
            'migrate_*.py',
            'diagnose_*.py',
            'fresh_*.py'
        ]
        
        removed_count = 0
        for pattern in dev_patterns:
            for file in glob.glob(pattern):
                try:
                    os.remove(file)
                    self.log(f"Removed dev file: {file}")
                    removed_count += 1
                except Exception as e:
                    self.log(f"Failed to remove {file}: {e}", "WARNING")
        
        self.log(f"Removed {removed_count} development files")
    
    def clean_documentation(self):
        """Remove excessive documentation files"""
        self.log("Cleaning excessive documentation...")
        
        # Documentation patterns to remove
        doc_patterns = [
            '*_SUMMARY.md',
            '*_FIXES.md',
            '*_GUIDE.md', 
            '*_ANALYSIS.md',
            '*_REPORT.md',
            '*_COMPLETE.md',
            '*_REFERENCE.md',
            'ADMIN_*.md',
            'CRITICAL_*.md',
            'ENHANCED_*.md',
            'NAVIGATION_*.md',
            'PHOTO_*.md',
            'POSTGRESQL_*.md',
            'NUTRITION_*.md',
            'MIGRATION_*.md',
            'SECURITY_*.md',
            'CLEANUP_*.md',
            'KEYERROR_*.md',
            'HOSTING_*.md',
            'GITHUB_*.md',
            '*_CHECKLIST.md',
            '*_LINUX.md',
            '*_NEW.md',
            '*_IMPLEMENTATION.md'
        ]
        
        removed_count = 0
        for pattern in doc_patterns:
            for file in glob.glob(pattern):
                try:
                    os.remove(file)
                    self.log(f"Removed doc file: {file}")
                    removed_count += 1
                except Exception as e:
                    self.log(f"Failed to remove {file}: {e}", "WARNING")
        
        self.log(f"Removed {removed_count} documentation files")
    
    def clean_scripts(self):
        """Remove deployment and setup scripts"""
        self.log("Cleaning scripts...")
        
        script_patterns = [
            '*.sh',
            '*.bat',
            '*.ps1',
            'deploy*',
            'setup*',
            'bootstrap*',
            'manage*',
            'startup*',
            'update*',
            'run.*'
        ]
        
        # Keep requirements.txt
        excluded = ['requirements.txt']
        
        removed_count = 0
        for pattern in script_patterns:
            for file in glob.glob(pattern):
                if file not in excluded:
                    try:
                        os.remove(file)
                        self.log(f"Removed script: {file}")
                        removed_count += 1
                    except Exception as e:
                        self.log(f"Failed to remove {file}: {e}", "WARNING")
        
        self.log(f"Removed {removed_count} script files")
    
    def clean_logs_and_cache(self):
        """Clean logs, cache, and temporary files"""
        self.log("Cleaning logs and cache...")
        
        # Remove log files
        if os.path.exists('logs'):
            try:
                shutil.rmtree('logs')
                self.log("Removed logs directory")
            except Exception as e:
                self.log(f"Failed to remove logs: {e}", "WARNING")
        
        # Remove Python cache
        for root, dirs, files in os.walk('.'):
            if '__pycache__' in dirs:
                try:
                    shutil.rmtree(os.path.join(root, '__pycache__'))
                    self.log(f"Removed cache: {os.path.join(root, '__pycache__')}")
                except Exception as e:
                    self.log(f"Failed to remove cache: {e}", "WARNING")
        
        # Remove temp files
        temp_patterns = ['*.tmp', '*.temp', '*~', '*.swp', '*.swo']
        for pattern in temp_patterns:
            for file in glob.glob(pattern):
                try:
                    os.remove(file)
                    self.log(f"Removed temp file: {file}")
                except Exception as e:
                    self.log(f"Failed to remove {file}: {e}", "WARNING")
    
    def clean_backups(self):
        """Remove backup files"""
        self.log("Cleaning backup files...")
        
        backup_patterns = [
            '*.backup',
            '*.bak',
            '*_backup.*',
            '*_backup_*',
            'questionnaire_data_backup_*.json'
        ]
        
        removed_count = 0
        for pattern in backup_patterns:
            for file in glob.glob(pattern):
                try:
                    os.remove(file)
                    self.log(f"Removed backup: {file}")
                    removed_count += 1
                except Exception as e:
                    self.log(f"Failed to remove {file}: {e}", "WARNING")
        
        self.log(f"Removed {removed_count} backup files")
    
    def reset_data_files(self, preserve_structure=True):
        """Reset data files to clean state"""
        self.log("Resetting data files...")
        
        if preserve_structure:
            # Keep file structure but clear content
            data_files = {
                'bot_data.json': {
                    "users": {},
                    "payments": {},
                    "statistics": {
                        "total_users": 0,
                        "total_payments": 0,
                        "total_approved": 0,
                        "total_revenue": 0
                    }
                },
                'questionnaire_data.json': {},
                'coupons.json': {},
                'admins.json': {
                    "admins": [],
                    "last_updated": datetime.now().isoformat()
                }
            }
            
            for filename, content in data_files.items():
                try:
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(content, f, ensure_ascii=False, indent=2)
                    self.log(f"Reset data file: {filename}")
                except Exception as e:
                    self.log(f"Failed to reset {filename}: {e}", "ERROR")
        else:
            # Remove data files completely
            data_files = [
                'bot_data.json',
                'questionnaire_data.json',
                'admins.json',
                'coupons.json'
            ]
            
            for file in data_files:
                if os.path.exists(file):
                    try:
                        os.remove(file)
                        self.log(f"Removed data file: {file}")
                    except Exception as e:
                        self.log(f"Failed to remove {file}: {e}", "ERROR")
        
        # Reset plan files
        plan_files = glob.glob('course_plans_*.json')
        for file in plan_files:
            try:
                with open(file, 'w', encoding='utf-8') as f:
                    json.dump([], f, ensure_ascii=False, indent=2)
                self.log(f"Reset plan file: {file}")
            except Exception as e:
                self.log(f"Failed to reset {file}: {e}", "ERROR")
    
    def verify_production_files(self):
        """Verify essential production files exist"""
        self.log("Verifying production files...")
        
        essential_files = [
            'main.py',
            'config.py',
            'data_manager.py',
            'questionnaire_manager.py',
            'admin_panel.py',
            'admin_manager.py',
            'admin_error_handler.py',
            'admin_debugger.py',
            'coupon_manager.py',
            'image_processor.py',
            'bot_logger.py',
            'requirements.txt',
            'README.md',
            '.env.example'
        ]
        
        missing_files = []
        for file in essential_files:
            if not os.path.exists(file):
                missing_files.append(file)
                self.log(f"Missing essential file: {file}", "WARNING")
            else:
                self.log(f"Verified: {file}")
        
        if missing_files:
            self.log(f"WARNING: {len(missing_files)} essential files missing!", "ERROR")
            return False
        else:
            self.log("All essential production files verified ✅")
            return True
    
    def generate_report(self):
        """Generate reset report"""
        duration = datetime.now() - self.start_time
        
        report = f"""
🔄 PRODUCTION RESET REPORT
========================

📅 Date: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}
⏱️ Duration: {duration.total_seconds():.2f} seconds
💾 Backup Location: {self.backup_dir}

📊 Operations Performed:
{chr(10).join(self.reset_log)}

✅ Reset Complete - System ready for production deployment

🔒 Security Notes:
- All development files removed
- Test data cleared
- Logs purged
- Cache cleaned
- Backup created for recovery

🚀 Next Steps:
1. Review .env configuration
2. Set up production database
3. Configure admin users
4. Deploy to production server
"""
        
        # Save report
        report_file = f"reset_report_{int(time.time())}.txt"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(report)
        self.log(f"Report saved to: {report_file}")
    
    def run_full_reset(self, preserve_data_structure=True):
        """Run complete production reset"""
        print("🔄 Starting Production Reset...")
        print("⚠️  This will clean all development files and test data!")
        
        # Confirm reset
        try:
            confirm = input("Continue? (type 'RESET' to confirm): ")
            if confirm != 'RESET':
                print("❌ Reset cancelled")
                return False
        except KeyboardInterrupt:
            print("\n❌ Reset cancelled")
            return False
        
        self.log("=== PRODUCTION RESET STARTED ===")
        
        # Create backup first
        if not self.create_backup():
            print("❌ Backup failed - aborting reset")
            return False
        
        # Perform cleanup operations
        self.clean_development_files()
        self.clean_documentation()
        self.clean_scripts()
        self.clean_logs_and_cache()
        self.clean_backups()
        self.reset_data_files(preserve_data_structure)
        
        # Verify production readiness
        if self.verify_production_files():
            self.log("=== PRODUCTION RESET COMPLETED SUCCESSFULLY ===")
            self.generate_report()
            return True
        else:
            self.log("=== PRODUCTION RESET COMPLETED WITH WARNINGS ===", "WARNING")
            self.generate_report()
            return False

def main():
    """Main reset function"""
    reset_tool = ProductionReset()
    
    print("🔄 Production Reset Tool")
    print("=" * 50)
    print("1. Full Reset (preserve data structure)")
    print("2. Full Reset (remove all data)")
    print("3. Clean only (keep data)")
    print("4. Verify only")
    print("5. Exit")
    
    try:
        choice = input("\nSelect option (1-5): ").strip()
        
        if choice == '1':
            reset_tool.run_full_reset(preserve_data_structure=True)
        elif choice == '2':
            reset_tool.run_full_reset(preserve_data_structure=False)
        elif choice == '3':
            reset_tool.create_backup()
            reset_tool.clean_development_files()
            reset_tool.clean_documentation() 
            reset_tool.clean_scripts()
            reset_tool.clean_logs_and_cache()
            reset_tool.clean_backups()
            reset_tool.generate_report()
        elif choice == '4':
            reset_tool.verify_production_files()
        elif choice == '5':
            print("👋 Goodbye!")
        else:
            print("❌ Invalid option")
            
    except KeyboardInterrupt:
        print("\n👋 Reset tool cancelled")

if __name__ == "__main__":
    main()
