import io
import os
from PIL import Image
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class ImageProcessor:
    """Handle image compression and processing for user uploads"""
    
    def __init__(self, max_size_mb: float = 1.0, quality: int = 85, max_dimension: int = 1920):
        """
        Initialize image processor
        
        Args:
            max_size_mb: Maximum file size in MB after compression
            quality: JPEG quality (1-100)
            max_dimension: Maximum width or height in pixels
        """
        self.max_size_bytes = int(max_size_mb * 1024 * 1024)
        self.quality = quality
        self.max_dimension = max_dimension
    
    def compress_image(self, image_bytes: bytes) -> Tuple[bytes, dict]:
        """
        Compress image to reduce file size
        
        Args:
            image_bytes: Original image bytes
            
        Returns:
            Tuple of (compressed_image_bytes, compression_info)
        """
        try:
            # Open image
            image = Image.open(io.BytesIO(image_bytes))
            original_size = len(image_bytes)
            
            # Get original dimensions
            original_width, original_height = image.size
            
            # Convert to RGB if necessary (for JPEG compression)
            if image.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', image.size, (255, 255, 255))
                background.paste(image, mask=image.split()[-1] if image.mode in ('RGBA', 'LA') else None)
                image = background
            elif image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Resize if too large
            if max(original_width, original_height) > self.max_dimension:
                ratio = self.max_dimension / max(original_width, original_height)
                new_width = int(original_width * ratio)
                new_height = int(original_height * ratio)
                image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Compress image
            output = io.BytesIO()
            quality = self.quality
            
            # Try different quality levels if file is still too large
            while quality > 20:
                output.seek(0)
                output.truncate()
                image.save(output, format='JPEG', quality=quality, optimize=True)
                
                if output.tell() <= self.max_size_bytes:
                    break
                    
                quality -= 10
            
            compressed_bytes = output.getvalue()
            compressed_size = len(compressed_bytes)
            
            compression_info = {
                'original_size': original_size,
                'compressed_size': compressed_size,
                'compression_ratio': round(compressed_size / original_size, 3),
                'size_reduction_percent': round((1 - compressed_size / original_size) * 100, 1),
                'original_dimensions': (original_width, original_height),
                'final_dimensions': image.size,
                'quality_used': quality
            }
            
            logger.info(f"Image compressed: {original_size} -> {compressed_size} bytes "
                       f"({compression_info['size_reduction_percent']}% reduction)")
            
            return compressed_bytes, compression_info
            
        except Exception as e:
            logger.error(f"Error compressing image: {e}")
            # Return original if compression fails
            return image_bytes, {
                'original_size': len(image_bytes),
                'compressed_size': len(image_bytes),
                'compression_ratio': 1.0,
                'size_reduction_percent': 0,
                'error': str(e)
            }
    
    def validate_image(self, image_bytes: bytes) -> Tuple[bool, str]:
        """
        Validate if the image is acceptable
        
        Args:
            image_bytes: Image bytes to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Check file size (before compression)
            max_upload_size = 20 * 1024 * 1024  # 20MB max upload
            if len(image_bytes) > max_upload_size:
                return False, f"تصویر خیلی بزرگ است. حداکثر سایز مجاز {max_upload_size // (1024*1024)}MB می‌باشد."
            
            # Try to open image
            image = Image.open(io.BytesIO(image_bytes))
            
            # Check dimensions
            width, height = image.size
            if width < 100 or height < 100:
                return False, "تصویر خیلی کوچک است. حداقل ابعاد ۱۰۰x۱۰۰ پیکسل مورد نیاز است."
            
            if width > 5000 or height > 5000:
                return False, "تصویر خیلی بزرگ است. حداکثر ابعاد ۵۰۰۰x۵۰۰۰ پیکسل مجاز است."
            
            # Check format
            if image.format not in ['JPEG', 'PNG', 'WEBP']:
                return False, f"فرمت تصویر پشتیبانی نمی‌شود. فرمت‌های مجاز: JPEG, PNG, WEBP"
            
            return True, ""
            
        except Exception as e:
            return False, f"فایل تصویر نامعتبر است: {str(e)}"
    
    async def save_compressed_image(self, image_bytes: bytes, filename: str, 
                                  save_directory: str = "compressed_images") -> Optional[str]:
        """
        Save compressed image to disk
        
        Args:
            image_bytes: Original image bytes
            filename: Name for the saved file
            save_directory: Directory to save the file
            
        Returns:
            Path to saved file or None if failed
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(save_directory, exist_ok=True)
            
            # Compress image
            compressed_bytes, compression_info = self.compress_image(image_bytes)
            
            # Save to file
            file_path = os.path.join(save_directory, filename)
            with open(file_path, 'wb') as f:
                f.write(compressed_bytes)
            
            logger.info(f"Compressed image saved: {file_path} "
                       f"({compression_info['compressed_size']} bytes)")
            
            return file_path
            
        except Exception as e:
            logger.error(f"Error saving compressed image: {e}")
            return None
