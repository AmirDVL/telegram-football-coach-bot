"""
Coupon management system for the football coach bot
"""
import json
import os
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from config import Config

class CouponManager:
    def __init__(self, data_file: str = "coupons.json"):
        self.data_file = data_file
        self.coupons = self._load_coupons()
    
    def _load_coupons(self) -> Dict:
        """Load coupons from file or create default ones"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                pass
        
        # Create default coupons
        default_coupons = {}
        for code, details in Config.DEFAULT_COUPONS.items():
            default_coupons[code] = {
                **details,
                'created_by': 'system',
                'created_at': datetime.now().isoformat(),
                'usage_count': 0,
                'max_uses': None,  # None = unlimited
                'expires_at': None  # None = no expiry
            }
        
        self._save_coupons(default_coupons)
        return default_coupons
    
    def _save_coupons(self, coupons: Dict = None) -> None:
        """Save coupons to file"""
        if coupons is None:
            coupons = self.coupons
        
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(coupons, f, ensure_ascii=False, indent=2)
    
    def create_coupon(self, code: str, discount_percent: int, description: str = "", 
                     max_uses: Optional[int] = None, expires_days: Optional[int] = None,
                     created_by: str = "admin") -> bool:
        """Create a new coupon"""
        if code in self.coupons:
            return False  # Coupon already exists
        
        expires_at = None
        if expires_days:
            expires_at = (datetime.now() + timedelta(days=expires_days)).isoformat()
        
        self.coupons[code] = {
            'discount_percent': discount_percent,
            'active': True,
            'description': description,
            'created_by': created_by,
            'created_at': datetime.now().isoformat(),
            'usage_count': 0,
            'max_uses': max_uses,
            'expires_at': expires_at
        }
        
        self._save_coupons()
        return True
    
    def validate_coupon(self, code: str) -> Tuple[bool, str, int]:
        """
        Validate a coupon code
        Returns: (is_valid, message, discount_percent)
        """
        if code not in self.coupons:
            return False, "کد تخفیف معتبر نیست", 0
        
        coupon = self.coupons[code]
        
        if not coupon.get('active', False):
            return False, "کد تخفیف غیرفعال است", 0
        
        # Check expiry
        if coupon.get('expires_at'):
            expiry_date = datetime.fromisoformat(coupon['expires_at'])
            if datetime.now() > expiry_date:
                return False, "کد تخفیف منقضی شده است", 0
        
        # Check usage limit
        if coupon.get('max_uses'):
            if coupon.get('usage_count', 0) >= coupon['max_uses']:
                return False, "کد تخفیف به حد مجاز رسیده است", 0
        
        return True, "کد تخفیف معتبر است", coupon.get('discount_percent', 0)
    
    def use_coupon(self, code: str) -> bool:
        """Mark a coupon as used (increment usage count)"""
        if code not in self.coupons:
            return False
        
        self.coupons[code]['usage_count'] = self.coupons[code].get('usage_count', 0) + 1
        self._save_coupons()
        return True
    
    def get_all_coupons(self) -> Dict:
        """Get all coupons"""
        return self.coupons.copy()
    
    def toggle_coupon(self, code: str) -> Optional[bool]:
        """Toggle coupon active status. Returns new status or None if not found"""
        if code not in self.coupons:
            return None
        
        self.coupons[code]['active'] = not self.coupons[code].get('active', False)
        self._save_coupons()
        return self.coupons[code]['active']
    
    def delete_coupon(self, code: str) -> bool:
        """Delete a coupon"""
        if code not in self.coupons:
            return False
        
        del self.coupons[code]
        self._save_coupons()
        return True
    
    def calculate_discounted_price(self, original_price: int, code: str) -> Tuple[int, int]:
        """
        Calculate discounted price
        Returns: (final_price, discount_amount)
        """
        is_valid, _, discount_percent = self.validate_coupon(code)
        
        if not is_valid:
            return original_price, 0
        
        discount_amount = int(original_price * discount_percent / 100)
        final_price = original_price - discount_amount
        
        return final_price, discount_amount
