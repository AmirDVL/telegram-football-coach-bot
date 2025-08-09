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
                data = json.loads(content) if content else {}
                
                # Handle bot_data.json structure (nested under 'admins' key)
                if 'admins' in data and isinstance(data['admins'], dict):
                    return data['admins']
                # Handle direct admins.json structure  
                elif 'super_admin' in data:
                    return data
                else:
                    return {}
        except Exception as e:
            print(f"Error loading admins: {e}")
            return {}
    
    async def save_admins(self, data: Dict[str, Any]) -> bool:
        """Save admins data"""
        try:
            # Handle bot_data.json structure (need to update nested 'admins' key)
            if self.admins_file == 'bot_data.json':
                # Load full bot_data.json
                async with aiofiles.open(self.admins_file, 'r', encoding='utf-8') as f:
                    bot_data = json.loads(await f.read())
                
                # Update admins section
                bot_data['admins'] = data
                
                # Save full bot_data.json back
                async with aiofiles.open(self.admins_file, 'w', encoding='utf-8') as f:
                    await f.write(json.dumps(bot_data, ensure_ascii=False, indent=2))
            else:
                # Handle direct admins.json structure
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
        result = user_id in admins_list or str(user_id) in admins_list
        
        return result
    
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
    
    async def get_all_admin_ids(self) -> List[int]:
        """Get list of all admin IDs"""
        try:
            admins_data = await self.load_admins()
            admin_list = admins_data.get('admins', [])
            # Convert to integers and handle both string and int formats
            return [int(admin_id) for admin_id in admin_list]
        except Exception as e:
            print(f"Error getting admin IDs: {e}")
            return []
    
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
    
    async def set_super_admin(self, admin_id: int) -> bool:
        """Set admin as super admin"""
        try:
            admins_data = await self.load_admins()
            
            # Set as super admin
            admins_data['super_admin'] = admin_id
            
            # Update permissions to super admin level
            admin_id_str = str(admin_id)
            if admin_id_str in admins_data.get('admin_permissions', {}):
                admins_data['admin_permissions'][admin_id_str].update({
                    'can_add_admins': True,
                    'can_remove_admins': True,
                    'can_view_users': True,
                    'can_manage_payments': True,
                    'is_super_admin': True,
                    'updated_date': datetime.now().isoformat()
                })
            
            return await self.save_admins(admins_data)
        except Exception as e:
            print(f"Error setting super admin: {e}")
            return False
    
    async def demote_from_super_admin(self, admin_id: int) -> bool:
        """Demote admin from super admin (but keep as regular admin)"""
        try:
            admins_data = await self.load_admins()
            
            # Only demote if this admin is currently the super admin
            if admins_data.get('super_admin') == admin_id:
                # Find another admin to promote (prefer first in env)
                from config import Config
                env_admin_ids = Config.get_admin_ids()
                new_super_admin = env_admin_ids[0] if env_admin_ids else None
                
                admins_data['super_admin'] = new_super_admin
                
                # Update this admin's permissions to regular admin level
                admin_id_str = str(admin_id)
                if admin_id_str in admins_data.get('admin_permissions', {}):
                    admins_data['admin_permissions'][admin_id_str].update({
                        'can_add_admins': False,
                        'can_remove_admins': False,
                        'can_view_users': True,
                        'can_manage_payments': True,
                        'is_super_admin': False,
                        'updated_date': datetime.now().isoformat()
                    })
            
            return await self.save_admins(admins_data)
        except Exception as e:
            print(f"Error demoting from super admin: {e}")
            return False
    
    async def sync_admins_from_config(self, specific_admin_ids=None):
        """Comprehensive admin sync from Config.ADMIN_IDS with role detection"""
        try:
            from config import Config
            
            # Get admin IDs from config
            admin_ids = specific_admin_ids or Config.get_admin_ids()
            config_super_admin = Config.ADMIN_ID
            
            # Load current admins data
            admins_data = await self.load_admins()
            
            if not admins_data:
                admins_data = {
                    'super_admin': None,
                    'admins': [],
                    'admin_permissions': {}
                }
            
            # Ensure required keys exist
            if 'admins' not in admins_data:
                admins_data['admins'] = []
            if 'admin_permissions' not in admins_data:
                admins_data['admin_permissions'] = {}
            
            # Set/update super admin from config
            if config_super_admin and (admins_data.get('super_admin') != config_super_admin):
                old_super = admins_data.get('super_admin')
                admins_data['super_admin'] = config_super_admin
                print(f"🎖️ Super admin updated: {old_super} → {config_super_admin}")
            
            # Add each admin from config
            synced_count = 0
            updated_count = 0
            
            for admin_id in admin_ids:
                if admin_id not in admins_data['admins']:
                    admins_data['admins'].append(admin_id)
                    synced_count += 1
                    print(f"Admin with ID {admin_id} added successfully.")
                else:
                    print(f"Admin with ID {admin_id} already exists.")
                
                # Determine if this admin should be super admin
                is_super = (admin_id == config_super_admin)
                
                # Ensure admin has permissions entry with correct role
                admin_id_str = str(admin_id)
                existing_permissions = admins_data['admin_permissions'].get(admin_id_str, {})
                current_is_super = existing_permissions.get('is_super_admin', False)
                
                # Update permissions if role changed or missing
                if admin_id_str not in admins_data['admin_permissions'] or current_is_super != is_super:
                    admins_data['admin_permissions'][admin_id_str] = {
                        'can_add_admins': is_super,
                        'can_remove_admins': is_super,
                        'can_view_users': True,
                        'can_manage_payments': True,
                        'is_super_admin': is_super,
                        'added_by': 'config_sync',
                        'added_date': existing_permissions.get('added_date', datetime.now().isoformat()),
                        'updated_date': datetime.now().isoformat(),
                        'synced_from_config': True
                    }
                    if current_is_super != is_super:
                        role_change = "promoted to super admin" if is_super else "demoted from super admin"
                        print(f"Admin {admin_id} {role_change}")
                        updated_count += 1
            
            # CLEANUP: Remove admins that are no longer in config but were added by config_sync
            removed_count = 0
            current_admin_ids = set(admin_ids)
            admins_to_remove = []
            
            for admin_id in admins_data['admins'][:]:  # Create a copy to iterate over
                admin_id_int = int(admin_id)
                admin_permissions = admins_data['admin_permissions'].get(str(admin_id), {})
                
                # Only remove admins that were originally synced from config
                if (admin_id_int not in current_admin_ids and 
                    admin_permissions.get('synced_from_config', False)):
                    
                    admins_to_remove.append(admin_id_int)
                    admins_data['admins'].remove(admin_id)
                    if str(admin_id) in admins_data['admin_permissions']:
                        del admins_data['admin_permissions'][str(admin_id)]
                    removed_count += 1
                    print(f"Admin with ID {admin_id} removed (no longer in config).")
            
            # Save updated data
            await self.save_admins(admins_data)
            
            total_changes = synced_count + updated_count + removed_count
            if total_changes > 0:
                print(f"Admin sync completed. {synced_count} new admins added, {updated_count} roles updated, {removed_count} admins removed.")
            else:
                print(f"Admin sync completed. 0 new admins added.")
            return True
            
        except Exception as e:
            print(f"Error syncing admins from config: {e}")
            return False

    async def remove_config_admin(self, admin_id: int) -> bool:
        """Remove admin that was added from config (bypasses super admin protection)"""
        try:
            admins_data = await self.load_admins()
            
            # Remove from admins list
            if str(admin_id) in admins_data.get('admins', []):
                admins_data['admins'].remove(str(admin_id))
            
            # Remove permissions
            if str(admin_id) in admins_data.get('admin_permissions', {}):
                del admins_data['admin_permissions'][str(admin_id)]
            
            return await self.save_admins(admins_data)
            
        except Exception as e:
            print(f"Error removing config admin {admin_id}: {e}")
            return False

    async def sync_config_admins_full(self, config_admin_ids: List[int]) -> Dict[str, int]:
        """Full sync: add missing and remove outdated config admins"""
        try:
            admins_data = await self.load_admins()
            
            # Track changes
            added_count = 0
            removed_count = 0
            
            # Add missing admins from config
            for admin_id in config_admin_ids:
                if str(admin_id) not in admins_data.get('admins', []):
                    # Add to admins list
                    if 'admins' not in admins_data:
                        admins_data['admins'] = []
                    admins_data['admins'].append(str(admin_id))
                    
                    # Add permissions
                    if 'admin_permissions' not in admins_data:
                        admins_data['admin_permissions'] = {}
                    
                    admins_data['admin_permissions'][str(admin_id)] = {
                        'can_add_admins': True,
                        'can_remove_admins': True,
                        'can_view_users': True,
                        'can_manage_payments': True,
                        'added_by': 'config_sync',
                        'added_date': datetime.now().isoformat(),
                        'synced_from_config': True
                    }
                    added_count += 1
            
            # Remove admins that are no longer in config (only those added by config_sync)
            admins_to_remove = []
            for admin_id in admins_data.get('admins', []):
                admin_perms = admins_data.get('admin_permissions', {}).get(admin_id, {})
                # Remove if: not in config AND was added by config sync
                if (int(admin_id) not in config_admin_ids and 
                    admin_perms.get('added_by') == 'config_sync'):
                    admins_to_remove.append(admin_id)
            
            for admin_id in admins_to_remove:
                if admin_id in admins_data.get('admins', []):
                    admins_data['admins'].remove(admin_id)
                if admin_id in admins_data.get('admin_permissions', {}):
                    del admins_data['admin_permissions'][admin_id]
                removed_count += 1
            
            # Save updated data
            await self.save_admins(admins_data)
            
            return {'added': added_count, 'removed': removed_count}
            
        except Exception as e:
            print(f"Error in full admin sync: {e}")
            return {'added': 0, 'removed': 0}

    async def cleanup_non_env_admins(self, cleaned_by: int) -> Dict[str, int]:
        """Remove all non-environment admins (manual cleanup for super admins)"""
        try:
            admins_data = await self.load_admins()
            
            # Track changes
            removed_count = 0
            removal_details = []
            
            # Get list of admins to remove (non-config, non-super admins)
            admins_to_remove = []
            for admin_id in admins_data.get('admins', []):
                admin_perms = admins_data.get('admin_permissions', {}).get(admin_id, {})
                
                # Skip if this is a config admin
                if admin_perms.get('added_by') == 'config_sync':
                    continue
                
                # Skip super admin for safety (check both in permissions and super_admin field)
                if (admin_id == str(admins_data.get('super_admin')) or 
                    admin_perms.get('is_super_admin')):
                    continue
                    
                admins_to_remove.append(admin_id)
            
            # Remove the identified admins
            for admin_id in admins_to_remove:
                if admin_id in admins_data.get('admins', []):
                    admins_data['admins'].remove(admin_id)
                    removal_details.append(admin_id)
                    removed_count += 1
                
                if admin_id in admins_data.get('admin_permissions', {}):
                    del admins_data['admin_permissions'][admin_id]
            
            # Save updated data
            await self.save_admins(admins_data)
            
            return {
                'removed': removed_count, 
                'details': removal_details,
                'total_checked': len(admins_to_remove)
            }
            
        except Exception as e:
            print(f"Error in cleanup non-env admins: {e}")
            return {'removed': 0, 'details': [], 'total_checked': 0}
