import json
import os
from datetime import datetime
from typing import Dict, Any
import aiofiles

class DataManager:
    def __init__(self, data_file='bot_data.json'):
        self.data_file = data_file
        self.ensure_data_file()
    
    def ensure_data_file(self):
        """Ensure data file exists"""
        if not os.path.exists(self.data_file):
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'users': {},
                    'payments': {},
                    'statistics': {
                        'total_users': 0,
                        'total_payments': 0,
                        'course_stats': {}
                    }
                }, f, ensure_ascii=False, indent=2)
    
    async def save_user_data(self, user_id: int, data: Dict[str, Any]):
        """Save user data to file"""
        try:
            async with aiofiles.open(self.data_file, 'r', encoding='utf-8') as f:
                content = await f.read()
                bot_data = json.loads(content) if content else {}
            
            if 'users' not in bot_data:
                bot_data['users'] = {}
            
            bot_data['users'][str(user_id)] = {
                **data,
                'last_updated': datetime.now().isoformat(),
                'user_id': user_id
            }
            
            async with aiofiles.open(self.data_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(bot_data, ensure_ascii=False, indent=2))
            
            return True
        except Exception as e:
            print(f"Error saving user data: {e}")
            return False
    
    async def get_user_data(self, user_id: int) -> Dict[str, Any]:
        """Get user data from file"""
        try:
            async with aiofiles.open(self.data_file, 'r', encoding='utf-8') as f:
                content = await f.read()
                bot_data = json.loads(content) if content else {}
            
            return bot_data.get('users', {}).get(str(user_id), {})
        except Exception as e:
            print(f"Error loading user data: {e}")
            return {}
    
    async def save_payment_data(self, user_id: int, payment_data: Dict[str, Any]):
        """Save payment data"""
        try:
            async with aiofiles.open(self.data_file, 'r', encoding='utf-8') as f:
                content = await f.read()
                bot_data = json.loads(content) if content else {}
            
            if 'payments' not in bot_data:
                bot_data['payments'] = {}
            
            payment_id = f"{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            bot_data['payments'][payment_id] = {
                **payment_data,
                'timestamp': datetime.now().isoformat(),
                'user_id': user_id,
                'payment_id': payment_id
            }
            
            async with aiofiles.open(self.data_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(bot_data, ensure_ascii=False, indent=2))
            
            return payment_id
        except Exception as e:
            print(f"Error saving payment data: {e}")
            return None
    
    async def update_statistics(self, stat_type: str, value: Any = 1):
        """Update bot statistics"""
        try:
            async with aiofiles.open(self.data_file, 'r', encoding='utf-8') as f:
                content = await f.read()
                bot_data = json.loads(content) if content else {}
            
            if 'statistics' not in bot_data:
                bot_data['statistics'] = {}
            
            if stat_type in bot_data['statistics']:
                if isinstance(bot_data['statistics'][stat_type], (int, float)):
                    bot_data['statistics'][stat_type] += value
                else:
                    bot_data['statistics'][stat_type] = value
            else:
                bot_data['statistics'][stat_type] = value
            
            async with aiofiles.open(self.data_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(bot_data, ensure_ascii=False, indent=2))
            
            return True
        except Exception as e:
            print(f"Error updating statistics: {e}")
            return False
