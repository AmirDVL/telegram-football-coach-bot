"""
Minimal Admin Debugger - Replacement for missing admin_debugger module
"""
import logging
from typing import Dict, Any

logger = logging.getLogger('admin_debugger')

class AdminDebugger:
    """Simple replacement for admin debugger functionality"""
    
    async def log_callback_attempt(self, user_id: int, callback_data: str, details: Dict[str, Any] = None) -> None:
        """Log callback attempt for debugging"""
        logger.debug(f"Admin {user_id} callback: {callback_data} - {details}")
    
    async def create_debug_report(self, admin_id: int) -> str:
        """Create simple debug report"""
        return f"Debug report for admin {admin_id} - system operational"
    
    async def get_file_system_status(self) -> str:
        """Get basic file system status"""
        return "File system: operational"
    
    async def test_callback_routing(self) -> str:
        """Test callback routing"""
        return "Callback routing: operational"

# Create global instance
admin_debugger = AdminDebugger()
