"""
Plan File Manager - Handles downloading and storing training plan files locally
"""
import os
import logging
import hashlib
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger('plan_file_manager')

class PlanFileManager:
    """Manages local storage of training plan files"""
    
    def __init__(self, base_path: str = "plan_files"):
        """
        Initialize the plan file manager
        
        Args:
            base_path: Base directory for storing plan files
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Plan file manager initialized with base path: {self.base_path}")
    
    def _get_file_hash(self, file_id: str) -> str:
        """Generate a unique hash for the file_id"""
        return hashlib.md5(file_id.encode()).hexdigest()[:12]
    
    def _get_file_path(self, file_id: str, filename: str, course_type: str = None) -> Path:
        """
        Get the local path where the file should be stored
        
        Args:
            file_id: Telegram file_id
            filename: Original filename
            course_type: Optional course type for organization
            
        Returns:
            Path object for the file location
        """
        # Extract file extension
        file_ext = Path(filename).suffix or '.pdf'
        
        # Create course-specific subdirectory if provided
        if course_type:
            course_dir = self.base_path / course_type
            course_dir.mkdir(parents=True, exist_ok=True)
            base_dir = course_dir
        else:
            base_dir = self.base_path
        
        # Generate unique filename using hash and timestamp
        file_hash = self._get_file_hash(file_id)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{file_hash}_{timestamp}{file_ext}"
        
        return base_dir / safe_filename
    
    async def download_and_save_plan(
        self, 
        bot,
        file_id: str, 
        filename: str,
        course_type: str = None,
        metadata: Dict[str, Any] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Download a plan file from Telegram and save it locally
        
        Args:
            bot: Telegram bot instance
            file_id: Telegram file_id to download
            filename: Original filename
            course_type: Course type for organization
            metadata: Additional metadata to store
            
        Returns:
            Dictionary with file info or None if failed
        """
        try:
            # Get file from Telegram
            file = await bot.get_file(file_id)
            
            # Determine local path
            local_path = self._get_file_path(file_id, filename, course_type)
            
            # Download the file
            await file.download_to_drive(str(local_path))
            
            # Get file size
            file_size = local_path.stat().st_size
            
            # Prepare file info
            file_info = {
                'file_id': file_id,
                'local_path': str(local_path),
                'original_filename': filename,
                'file_size': file_size,
                'course_type': course_type,
                'downloaded_at': datetime.now().isoformat(),
                'status': 'available'
            }
            
            # Add metadata if provided
            if metadata:
                file_info.update(metadata)
            
            logger.info(f"Successfully downloaded plan file: {local_path} ({file_size} bytes)")
            return file_info
            
        except Exception as e:
            logger.error(f"Failed to download plan file {file_id}: {e}")
            return None
    
    def get_file_info(self, local_path: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a locally stored file
        
        Args:
            local_path: Path to the local file
            
        Returns:
            File information dictionary or None if file doesn't exist
        """
        try:
            path = Path(local_path)
            if not path.exists():
                return None
            
            stat_info = path.stat()
            return {
                'local_path': str(path),
                'filename': path.name,
                'file_size': stat_info.st_size,
                'modified_at': datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
                'exists': True
            }
        except Exception as e:
            logger.error(f"Failed to get file info for {local_path}: {e}")
            return None
    
    def file_exists(self, local_path: str) -> bool:
        """Check if a file exists locally"""
        if not local_path:
            return False
        return Path(local_path).exists()
    
    def delete_file(self, local_path: str) -> bool:
        """
        Delete a local file
        
        Args:
            local_path: Path to the file to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            path = Path(local_path)
            if path.exists():
                path.unlink()
                logger.info(f"Deleted plan file: {local_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete file {local_path}: {e}")
            return False
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get statistics about plan file storage
        
        Returns:
            Dictionary with storage statistics
        """
        try:
            total_files = 0
            total_size = 0
            course_stats = {}
            
            # Walk through all files
            for file_path in self.base_path.rglob('*'):
                if file_path.is_file():
                    total_files += 1
                    file_size = file_path.stat().st_size
                    total_size += file_size
                    
                    # Track per-course stats
                    course = file_path.parent.name if file_path.parent != self.base_path else 'general'
                    if course not in course_stats:
                        course_stats[course] = {'count': 0, 'size': 0}
                    course_stats[course]['count'] += 1
                    course_stats[course]['size'] += file_size
            
            return {
                'total_files': total_files,
                'total_size': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'course_stats': course_stats,
                'base_path': str(self.base_path)
            }
        except Exception as e:
            logger.error(f"Failed to get storage stats: {e}")
            return {'error': str(e)}
    
    def cleanup_orphaned_files(self, valid_paths: list) -> int:
        """
        Clean up files that are no longer referenced in the database
        
        Args:
            valid_paths: List of paths that should be kept
            
        Returns:
            Number of files deleted
        """
        deleted_count = 0
        valid_paths_set = set(valid_paths)
        
        try:
            for file_path in self.base_path.rglob('*'):
                if file_path.is_file() and str(file_path) not in valid_paths_set:
                    file_path.unlink()
                    deleted_count += 1
                    logger.info(f"Cleaned up orphaned file: {file_path}")
            
            return deleted_count
        except Exception as e:
            logger.error(f"Failed to cleanup orphaned files: {e}")
            return deleted_count

# Create global instance
plan_file_manager = PlanFileManager()
