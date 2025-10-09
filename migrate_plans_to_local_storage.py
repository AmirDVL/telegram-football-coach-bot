"""
Migration Script: Download Existing Plans to Local Storage

This script migrates all existing plans that only have file_id references
to local storage, ensuring they are permanently stored on disk.

Usage:
    python migrate_plans_to_local_storage.py [--dry-run]
"""

import os
import sys
import json
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
from telegram import Bot
from telegram.error import TelegramError

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('plan_migration')

# Import config and managers
from config import Config
from plan_file_manager import plan_file_manager


class PlanMigrator:
    """Handles migration of plans from file_id-only to local storage"""
    
    def __init__(self, bot_token: str, dry_run: bool = False):
        """
        Initialize the migrator
        
        Args:
            bot_token: Telegram bot token
            dry_run: If True, only simulate the migration without making changes
        """
        self.bot = Bot(token=bot_token)
        self.dry_run = dry_run
        self.stats = {
            'total_plans': 0,
            'already_local': 0,
            'migrated': 0,
            'failed': 0,
            'skipped': 0
        }
        self.course_plans_dir = Path('admin_data/course_plans')
        
    async def get_all_plan_files(self) -> List[Path]:
        """Get all plan JSON files"""
        if not self.course_plans_dir.exists():
            logger.error(f"Course plans directory not found: {self.course_plans_dir}")
            return []
        
        plan_files = list(self.course_plans_dir.glob('*.json'))
        # Filter out backup files
        plan_files = [f for f in plan_files if not f.name.endswith('.backup')]
        
        logger.info(f"Found {len(plan_files)} plan files to process")
        return plan_files
    
    async def load_plans_from_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Load plans from a JSON file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                plans = json.load(f)
            return plans if isinstance(plans, list) else []
        except Exception as e:
            logger.error(f"Failed to load plans from {file_path}: {e}")
            return []
    
    async def save_plans_to_file(self, file_path: Path, plans: List[Dict[str, Any]]) -> bool:
        """Save plans back to JSON file"""
        try:
            # Create backup first
            backup_path = file_path.with_suffix(f'.json.migration_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
            with open(file_path, 'r', encoding='utf-8') as f:
                backup_content = f.read()
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(backup_content)
            
            # Save updated plans
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(plans, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Saved updated plans to {file_path} (backup: {backup_path})")
            return True
        except Exception as e:
            logger.error(f"Failed to save plans to {file_path}: {e}")
            return False
    
    async def migrate_plan(self, plan: Dict[str, Any], course_type: str) -> Dict[str, Any]:
        """
        Migrate a single plan to local storage
        
        Args:
            plan: Plan dictionary
            course_type: Course type for organization
            
        Returns:
            Updated plan dictionary with migration status
        """
        plan_id = plan.get('id', 'unknown')
        plan_title = plan.get('title', 'Untitled')
        file_id = plan.get('content')
        local_path = plan.get('local_path')
        
        # Skip if already has local_path and file exists
        if local_path and plan_file_manager.file_exists(local_path):
            logger.info(f"  ✓ Plan '{plan_title}' (ID: {plan_id}) already has local file: {local_path}")
            self.stats['already_local'] += 1
            plan['migration_status'] = 'already_local'
            return plan
        
        # Skip if no file_id
        if not file_id:
            logger.warning(f"  ⚠ Plan '{plan_title}' (ID: {plan_id}) has no file_id, skipping")
            self.stats['skipped'] += 1
            plan['migration_status'] = 'no_file_id'
            return plan
        
        # Try to download and save the file
        try:
            filename = plan.get('filename', f'plan_{plan_id}.pdf')
            content_type = plan.get('content_type', 'document')
            
            logger.info(f"  → Downloading plan '{plan_title}' (ID: {plan_id}, file_id: {file_id[:20]}...)")
            
            if self.dry_run:
                logger.info(f"  [DRY RUN] Would download file_id: {file_id[:30]}... to {course_type}/{filename}")
                self.stats['migrated'] += 1
                plan['migration_status'] = 'dry_run_success'
                return plan
            
            # Actually download the file
            file_info = await plan_file_manager.download_and_save_plan(
                bot=self.bot,
                file_id=file_id,
                filename=filename,
                course_type=course_type,
                metadata={
                    'migrated_at': datetime.now().isoformat(),
                    'migration_script': 'migrate_plans_to_local_storage.py',
                    'original_plan_id': plan_id
                }
            )
            
            if file_info:
                # Update plan with local path
                plan['local_path'] = file_info['local_path']
                plan['file_size'] = file_info['file_size']
                plan['migrated_at'] = file_info['downloaded_at']
                plan['migration_status'] = 'success'
                
                logger.info(f"  ✓ Successfully migrated '{plan_title}' to {file_info['local_path']} ({file_info['file_size']} bytes)")
                self.stats['migrated'] += 1
            else:
                raise Exception("Download returned None")
            
        except TelegramError as e:
            error_msg = str(e)
            logger.error(f"  ✗ Telegram error migrating '{plan_title}' (ID: {plan_id}): {error_msg}")
            
            # Mark plan with migration error
            plan['migration_status'] = 'failed'
            plan['migration_error'] = error_msg
            plan['migration_error_type'] = 'telegram_error'
            
            if "Wrong type" in error_msg or "file_id" in error_msg.lower():
                plan['content_status'] = 'invalid_file_id'
                logger.warning(f"    → File_id appears to be expired or invalid")
            
            self.stats['failed'] += 1
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"  ✗ Error migrating '{plan_title}' (ID: {plan_id}): {error_msg}")
            
            plan['migration_status'] = 'failed'
            plan['migration_error'] = error_msg
            plan['migration_error_type'] = 'general_error'
            
            self.stats['failed'] += 1
        
        return plan
    
    async def migrate_course_plans(self, file_path: Path) -> bool:
        """
        Migrate all plans in a course file
        
        Args:
            file_path: Path to the course plans JSON file
            
        Returns:
            True if successful
        """
        course_type = file_path.stem
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing course: {course_type}")
        logger.info(f"File: {file_path}")
        logger.info(f"{'='*60}")
        
        # Load plans
        plans = await self.load_plans_from_file(file_path)
        if not plans:
            logger.warning(f"No plans found in {file_path}")
            return True
        
        logger.info(f"Found {len(plans)} plans in {course_type}")
        
        # Process each plan
        updated_plans = []
        for i, plan in enumerate(plans, 1):
            logger.info(f"\nPlan {i}/{len(plans)}:")
            self.stats['total_plans'] += 1
            
            updated_plan = await self.migrate_plan(plan, course_type)
            updated_plans.append(updated_plan)
            
            # Small delay to avoid rate limiting
            await asyncio.sleep(0.5)
        
        # Save updated plans (unless dry run)
        if not self.dry_run:
            success = await self.save_plans_to_file(file_path, updated_plans)
            if not success:
                logger.error(f"Failed to save updated plans for {course_type}")
                return False
        else:
            logger.info(f"\n[DRY RUN] Would save updated plans to {file_path}")
        
        return True
    
    async def run_migration(self) -> Dict[str, Any]:
        """
        Run the complete migration process
        
        Returns:
            Migration statistics
        """
        logger.info("\n" + "="*80)
        logger.info("PLAN MIGRATION TO LOCAL STORAGE")
        logger.info("="*80)
        
        if self.dry_run:
            logger.info("\n⚠️  DRY RUN MODE - No changes will be made")
        
        logger.info(f"\nBot token: {self.bot.token[:20]}...")
        logger.info(f"Course plans directory: {self.course_plans_dir}")
        logger.info(f"Local storage directory: {plan_file_manager.base_path}")
        
        # Get all plan files
        plan_files = await self.get_all_plan_files()
        if not plan_files:
            logger.error("No plan files found to migrate")
            return self.stats
        
        # Process each file
        for plan_file in plan_files:
            try:
                await self.migrate_course_plans(plan_file)
            except Exception as e:
                logger.error(f"Error processing {plan_file}: {e}")
                continue
        
        # Print summary
        self.print_summary()
        
        return self.stats
    
    def print_summary(self):
        """Print migration summary"""
        logger.info("\n" + "="*80)
        logger.info("MIGRATION SUMMARY")
        logger.info("="*80)
        logger.info(f"Total plans processed:     {self.stats['total_plans']}")
        logger.info(f"Already had local storage: {self.stats['already_local']}")
        logger.info(f"Successfully migrated:     {self.stats['migrated']}")
        logger.info(f"Failed to migrate:         {self.stats['failed']}")
        logger.info(f"Skipped (no file_id):      {self.stats['skipped']}")
        logger.info("="*80)
        
        if self.stats['failed'] > 0:
            logger.warning(f"\n⚠️  {self.stats['failed']} plans failed to migrate")
            logger.warning("Check the logs above for details on failed migrations")
            logger.warning("Failed plans are marked with 'migration_status': 'failed' in the JSON files")
        
        if self.stats['migrated'] > 0:
            logger.info(f"\n✅ Successfully migrated {self.stats['migrated']} plans to local storage")
            logger.info(f"Files stored in: {plan_file_manager.base_path}")
        
        # Storage statistics
        storage_stats = plan_file_manager.get_storage_stats()
        logger.info(f"\n📊 Storage Statistics:")
        logger.info(f"Total files: {storage_stats.get('total_files', 0)}")
        logger.info(f"Total size: {storage_stats.get('total_size_mb', 0):.2f} MB")


async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Migrate existing plans to local storage',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simulate the migration without making changes'
    )
    
    args = parser.parse_args()
    
    # Get bot token from config
    bot_token = Config.BOT_TOKEN
    if not bot_token:
        logger.error("Bot token not found in config. Please set BOT_TOKEN environment variable.")
        sys.exit(1)
    
    # Create migrator and run
    migrator = PlanMigrator(bot_token=bot_token, dry_run=args.dry_run)
    
    try:
        stats = await migrator.run_migration()
        
        # Exit code based on results
        if stats['failed'] > 0:
            sys.exit(2)  # Some failures
        elif stats['migrated'] == 0 and stats['already_local'] == 0:
            sys.exit(3)  # Nothing to migrate
        else:
            sys.exit(0)  # Success
            
    except KeyboardInterrupt:
        logger.info("\n\nMigration interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"\n\nFatal error during migration: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
