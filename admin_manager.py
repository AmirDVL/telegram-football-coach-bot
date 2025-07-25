import json
import os
from typing import List, Dict, Any
import aiofiles
from datetime import datetime

class AdminManager:
    def __init__(self, admins_file='admins.json'):
        self.admins_file = admins_file
        self.ensure_admins_file()
    
    def ensure_admins_file(self):
        """Ensure admins file exists"""
        if not os.path.exists(self.admins_file):
            # Get initial admin from .env
            from config import Config
            initial_admin = Config.ADMIN_ID
            
            initial_data = {
                'super_admin': initial_admin,
                'admins': [initial_admin] if initial_admin else [],
                'admin_permissions': {
                    str(initial_admin): {
                        'can_add_admins': True,
                        'can_remove_admins': True,
                        'can_view_users': True,
                        'can_manage_payments': True,
                        'added_by': 'system',
                        'added_date': datetime.now().isoformat()
                    }
                } if initial_admin else {}
            }
            
            with open(self.admins_file, 'w', encoding='utf-8') as f:
                json.dump(initial_data, f, ensure_ascii=False, indent=2)
    
    async def load_admins(self) -> Dict[str, Any]:
        """Load admins data"""
        try:
            async with aiofiles.open(self.admins_file, 'r', encoding='utf-8') as f:
                content = await f.read()
                return json.loads(content) if content else {}
        except Exception as e:
            print(f"Error loading admins: {e}")
            return {}
    
    async def save_admins(self, data: Dict[str, Any]) -> bool:
        """Save admins data"""
        try:
            async with aiofiles.open(self.admins_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(data, ensure_ascii=False, indent=2))
            return True
        except Exception as e:
            print(f"Error saving admins: {e}")
            return False
    
    async def is_admin(self, user_id: int) -> bool:
        """Check if user is admin"""
        admins_data = await self.load_admins()
        admins_list = admins_data.get('admins', [])
        # Check both string and integer versions for compatibility
        return user_id in admins_list or str(user_id) in admins_list
    
    async def is_super_admin(self, user_id: int) -> bool:
        """Check if user is super admin"""
        admins_data = await self.load_admins()
        return str(user_id) == str(admins_data.get('super_admin'))
    
    async def can_add_admins(self, user_id: int) -> bool:
        """Check if user can add admins"""
        if await self.is_super_admin(user_id):
            return True
        
        admins_data = await self.load_admins()
        permissions = admins_data.get('admin_permissions', {}).get(str(user_id), {})
        return permissions.get('can_add_admins', False)
    
    async def can_remove_admins(self, user_id: int) -> bool:
        """Check if user can remove admins"""
        if await self.is_super_admin(user_id):
            return True
        
        admins_data = await self.load_admins()
        permissions = admins_data.get('admin_permissions', {}).get(str(user_id), {})
        return permissions.get('can_remove_admins', False)
    
    async def add_admin(self, new_admin_id: int, added_by: int, permissions: Dict[str, bool] = None) -> bool:
        """Add new admin"""
        if not await self.can_add_admins(added_by):
            return False
        
        admins_data = await self.load_admins()
        
        if str(new_admin_id) not in admins_data.get('admins', []):
            admins_data.setdefault('admins', []).append(str(new_admin_id))
        
        # Default permissions for new admin
        default_permissions = {
            'can_add_admins': False,
            'can_remove_admins': False,
            'can_view_users': True,
            'can_manage_payments': True
        }
        
        if permissions:
            default_permissions.update(permissions)
        
        admins_data.setdefault('admin_permissions', {})[str(new_admin_id)] = {
            **default_permissions,
            'added_by': str(added_by),
            'added_date': datetime.now().isoformat()
        }
        
        return await self.save_admins(admins_data)
    
    async def remove_admin(self, admin_id: int, removed_by: int) -> bool:
        """Remove admin"""
        if not await self.can_remove_admins(removed_by):
            return False
        
        # Cannot remove super admin
        if await self.is_super_admin(admin_id):
            return False
        
        admins_data = await self.load_admins()
        
        # Remove from admins list
        if str(admin_id) in admins_data.get('admins', []):
            admins_data['admins'].remove(str(admin_id))
        
        # Remove permissions
        if str(admin_id) in admins_data.get('admin_permissions', {}):
            del admins_data['admin_permissions'][str(admin_id)]
        
        return await self.save_admins(admins_data)
    
    async def get_all_admins(self) -> List[Dict[str, Any]]:
        """Get all admins with their permissions"""
        admins_data = await self.load_admins()
        admins_list = []
        
        for admin_id in admins_data.get('admins', []):
            permissions = admins_data.get('admin_permissions', {}).get(admin_id, {})
            is_super = admin_id == str(admins_data.get('super_admin'))
            
            admins_list.append({
                'id': admin_id,
                'is_super_admin': is_super,
                'permissions': permissions
            })
        
        return admins_list
    
    async def update_permissions(self, admin_id: int, updated_by: int, new_permissions: Dict[str, bool]) -> bool:
        """Update admin permissions"""
        if not await self.can_add_admins(updated_by):
            return False
        
        # Cannot modify super admin
        if await self.is_super_admin(admin_id):
            return False
        
        admins_data = await self.load_admins()
        
        if str(admin_id) in admins_data.get('admin_permissions', {}):
            current_perms = admins_data['admin_permissions'][str(admin_id)]
            current_perms.update(new_permissions)
            current_perms['modified_by'] = str(updated_by)
            current_perms['modified_date'] = datetime.now().isoformat()
            
            return await self.save_admins(admins_data)
        
        return False
