"""
Admin Debug Utility for investigating callback and interaction issues
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

class AdminDebugger:
    """Debug utility for admin operations"""
    
    def __init__(self):
        self.debug_logs = []
        self.max_debug_logs = 50
        
    async def log_callback_attempt(self, update: Update, callback_data: str, 
                                 admin_id: int, success: bool = True, error: str = None):
        """Log callback attempts for debugging"""
        debug_entry = {
            'timestamp': datetime.now().isoformat(),
            'admin_id': admin_id,
            'callback_data': callback_data,
            'success': success,
            'error': error,
            'message_id': update.effective_message.message_id if update.effective_message else None,
            'chat_id': update.effective_chat.id if update.effective_chat else None
        }
        
        self.debug_logs.append(debug_entry)
        if len(self.debug_logs) > self.max_debug_logs:
            self.debug_logs.pop(0)
        
        # Save to file for persistence
        await self.save_debug_log(debug_entry)

    async def save_debug_log(self, debug_entry: Dict[str, Any]):
        """Save debug log to file"""
        try:
            os.makedirs('logs', exist_ok=True)
            debug_file = 'logs/admin_debug.json'
            
            if os.path.exists(debug_file):
                with open(debug_file, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
            else:
                logs = []
            
            logs.append(debug_entry)
            
            # Keep only last 200 entries
            if len(logs) > 200:
                logs = logs[-200:]
            
            with open(debug_file, 'w', encoding='utf-8') as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"Failed to save debug log: {e}")

    async def create_debug_report(self, admin_id: int = None) -> str:
        """Create comprehensive debug report for admin"""
        try:
            report = "🔍 Admin Debug Report\n"
            report += f"📅 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            
            # Recent callback attempts
            recent_callbacks = self.debug_logs[-10:] if not admin_id else [
                log for log in self.debug_logs[-20:] if log['admin_id'] == admin_id
            ]
            
            if recent_callbacks:
                report += "📋 Recent Callback Attempts:\n"
                for i, log in enumerate(recent_callbacks, 1):
                    status = "✅" if log['success'] else "❌"
                    timestamp = log['timestamp'][:16].replace('T', ' ')
                    callback = log['callback_data']
                    report += f"{i}. {status} {timestamp} | {callback}\n"
                    if not log['success'] and log['error']:
                        report += f"   Error: {log['error'][:50]}...\n"
                report += "\n"
            
            # Callback pattern analysis
            report += "🎯 Callback Pattern Analysis:\n"
            all_callbacks = [log['callback_data'] for log in self.debug_logs]
            patterns = {}
            for callback in all_callbacks:
                pattern = callback.split('_')[0] + '_*' if '_' in callback else callback
                patterns[pattern] = patterns.get(pattern, 0) + 1
            
            for pattern, count in sorted(patterns.items(), key=lambda x: x[1], reverse=True):
                report += f"• {pattern}: {count} times\n"
            
            report += "\n"
            
            # Success rate analysis
            success_rate = sum(1 for log in self.debug_logs if log['success']) / len(self.debug_logs) * 100 if self.debug_logs else 0
            report += f"📊 Overall Success Rate: {success_rate:.1f}%\n"
            
            failed_callbacks = [log for log in self.debug_logs if not log['success']]
            if failed_callbacks:
                report += f"❌ Failed Callbacks: {len(failed_callbacks)}\n"
                common_failures = {}
                for log in failed_callbacks:
                    pattern = log['callback_data'].split('_')[0] + '_*' if '_' in log['callback_data'] else log['callback_data']
                    common_failures[pattern] = common_failures.get(pattern, 0) + 1
                
                report += "Most Common Failures:\n"
                for pattern, count in sorted(common_failures.items(), key=lambda x: x[1], reverse=True)[:3]:
                    report += f"  • {pattern}: {count} times\n"
            
            return report
            
        except Exception as e:
            return f"❌ Error generating debug report: {e}"

    async def test_callback_routing(self) -> str:
        """Test callback routing patterns"""
        test_callbacks = [
            'admin_plans',
            'plan_course_online_weights',
            'upload_plan_online_cardio',
            'send_plan_in_person_weights',
            'view_plans_online_combo',
            'admin_stats',
            'admin_users'
        ]
        
        report = "🧪 Callback Routing Test:\n\n"
        
        for callback in test_callbacks:
            # Test pattern matching
            matches_admin = callback.startswith('admin_')
            matches_plan = callback.startswith(('plan_course_', 'upload_plan_', 'send_plan_', 'view_plans_'))
            
            status = "✅" if (matches_admin or matches_plan) else "❌"
            report += f"{status} {callback}\n"
            report += f"   Admin pattern: {matches_admin}\n"
            report += f"   Plan pattern: {matches_plan}\n\n"
        
        return report

    async def get_file_system_status(self) -> str:
        """Check file system status for plan management"""
        report = "📁 File System Status:\n\n"
        
        # Check plan files
        course_types = ['online_weights', 'online_cardio', 'online_combo', 'in_person_cardio', 'in_person_weights']
        
        for course_type in course_types:
            plan_file = f'course_plans_{course_type}.json'
            if os.path.exists(plan_file):
                try:
                    with open(plan_file, 'r', encoding='utf-8') as f:
                        plans = json.load(f)
                    report += f"✅ {course_type}: {len(plans)} plans\n"
                except Exception as e:
                    report += f"❌ {course_type}: Error reading ({str(e)[:30]})\n"
            else:
                report += f"⚠️ {course_type}: File missing\n"
        
        # Check logs directory
        report += "\n📊 Logs Directory:\n"
        if os.path.exists('logs'):
            log_files = os.listdir('logs')
            for log_file in log_files:
                size = os.path.getsize(f'logs/{log_file}')
                report += f"• {log_file}: {size} bytes\n"
        else:
            report += "❌ Logs directory missing\n"
        
        return report

# Create global instance
admin_debugger = AdminDebugger()
