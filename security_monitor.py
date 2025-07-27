#!/usr/bin/env python3
# security_monitor.py - Real-time Security Monitoring Script

import asyncio
import asyncpg
import smtplib
import os
import sys
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List
import logging

class SecurityMonitor:
    def __init__(self):
        self.db_connection_string = self._build_connection_string()
        self.alert_thresholds = {
            'failed_logins': 5,
            'rate_limit_violations': 10,
            'injection_attempts': 1,
            'large_file_uploads': 5,
            'blocked_users_increase': 3
        }
        self.last_check = datetime.now() - timedelta(hours=1)
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - SECURITY_MONITOR - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('security_monitor.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def _build_connection_string(self) -> str:
        """Build database connection string"""
        host = os.getenv('DB_HOST', 'localhost')
        port = os.getenv('DB_PORT', '5432')
        database = os.getenv('DB_NAME', 'football_coach_bot')
        user = os.getenv('DB_USER', 'footballbot_app')
        password = os.getenv('DB_PASSWORD', '')
        
        return f"postgresql://{user}:{password}@{host}:{port}/{database}"
    
    async def check_security_threats(self) -> Dict[str, any]:
        """Check for security threats in the database"""
        try:
            conn = await asyncpg.connect(self.db_connection_string)
            
            threats = {
                'critical_alerts': [],
                'warnings': [],
                'info': [],
                'statistics': {}
            }
            
            # Check for failed login attempts
            failed_logins = await conn.fetch("""
                SELECT user_id, COUNT(*) as attempts
                FROM security_audit_log 
                WHERE action LIKE '%failed%' 
                    AND timestamp > $1
                GROUP BY user_id
                HAVING COUNT(*) > $2
            """, self.last_check, self.alert_thresholds['failed_logins'])
            
            if failed_logins:
                threats['critical_alerts'].append({
                    'type': 'failed_logins',
                    'count': len(failed_logins),
                    'details': [dict(row) for row in failed_logins]
                })
            
            # Check for injection attempts
            injection_attempts = await conn.fetch("""
                SELECT user_id, details, timestamp
                FROM security_audit_log 
                WHERE action LIKE '%injection%' 
                    AND timestamp > $1
                    AND severity = 'CRITICAL'
            """, self.last_check)
            
            if injection_attempts:
                threats['critical_alerts'].append({
                    'type': 'injection_attempts',
                    'count': len(injection_attempts),
                    'details': [dict(row) for row in injection_attempts]
                })
            
            # Check for rate limit violations
            rate_violations = await conn.fetchval("""
                SELECT COUNT(*)
                FROM security_audit_log 
                WHERE action = 'rate_limit_exceeded' 
                    AND timestamp > $1
            """, self.last_check)
            
            if rate_violations > self.alert_thresholds['rate_limit_violations']:
                threats['warnings'].append({
                    'type': 'rate_limit_violations',
                    'count': rate_violations
                })
            
            # Check for suspicious file uploads
            large_uploads = await conn.fetchval("""
                SELECT COUNT(*)
                FROM security_audit_log 
                WHERE action = 'oversized_image_upload' 
                    AND timestamp > $1
            """, self.last_check)
            
            if large_uploads > self.alert_thresholds['large_file_uploads']:
                threats['warnings'].append({
                    'type': 'large_file_uploads',
                    'count': large_uploads
                })
            
            # Check database health
            db_size = await conn.fetchval("""
                SELECT pg_size_pretty(pg_database_size(current_database()))
            """)
            
            active_connections = await conn.fetchval("""
                SELECT count(*) FROM pg_stat_activity WHERE state = 'active'
            """)
            
            total_users = await conn.fetchval("SELECT COUNT(*) FROM users")
            blocked_users = await conn.fetchval("SELECT COUNT(*) FROM users WHERE is_blocked = TRUE")
            
            threats['statistics'] = {
                'database_size': db_size,
                'active_connections': active_connections,
                'total_users': total_users,
                'blocked_users': blocked_users,
                'check_time': datetime.now().isoformat()
            }
            
            await conn.close()
            return threats
            
        except Exception as e:
            self.logger.error(f"Error checking security threats: {e}")
            return {'error': str(e)}
    
    async def send_security_alert(self, threats: Dict[str, any]):
        """Send security alert via email or telegram"""
        try:
            if not threats.get('critical_alerts') and not threats.get('warnings'):
                return  # No alerts to send
            
            alert_message = self._format_alert_message(threats)
            
            # Log the alert
            self.logger.warning(f"SECURITY ALERT: {alert_message}")
            
            # Send email if configured
            if os.getenv('ALERT_EMAIL'):
                await self._send_email_alert(alert_message)
            
            # Send Telegram message to admin if configured
            if os.getenv('ADMIN_ID') and os.getenv('BOT_TOKEN'):
                await self._send_telegram_alert(alert_message)
                
        except Exception as e:
            self.logger.error(f"Error sending security alert: {e}")
    
    def _format_alert_message(self, threats: Dict[str, any]) -> str:
        """Format security alert message"""
        message = "🚨 SECURITY ALERT - Football Coach Bot\n\n"
        message += f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        if threats.get('critical_alerts'):
            message += "🔴 CRITICAL ALERTS:\n"
            for alert in threats['critical_alerts']:
                message += f"- {alert['type']}: {alert['count']} incidents\n"
            message += "\n"
        
        if threats.get('warnings'):
            message += "🟡 WARNINGS:\n"
            for warning in threats['warnings']:
                message += f"- {warning['type']}: {warning['count']} incidents\n"
            message += "\n"
        
        if threats.get('statistics'):
            stats = threats['statistics']
            message += "📊 SYSTEM STATUS:\n"
            message += f"- Database Size: {stats['database_size']}\n"
            message += f"- Active Connections: {stats['active_connections']}\n"
            message += f"- Total Users: {stats['total_users']}\n"
            message += f"- Blocked Users: {stats['blocked_users']}\n"
        
        return message
    
    async def _send_email_alert(self, message: str):
        """Send email alert"""
        try:
            email = os.getenv('ALERT_EMAIL')
            password = os.getenv('ALERT_EMAIL_PASSWORD')
            smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
            smtp_port = int(os.getenv('SMTP_PORT', '587'))
            
            if not email or not password:
                return
            
            msg = MIMEMultipart()
            msg['From'] = email
            msg['To'] = email
            msg['Subject'] = "Football Coach Bot - Security Alert"
            
            msg.attach(MIMEText(message, 'plain', 'utf-8'))
            
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(email, password)
            server.send_message(msg)
            server.quit()
            
            self.logger.info("Security alert email sent successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to send email alert: {e}")
    
    async def _send_telegram_alert(self, message: str):
        """Send Telegram alert to admin"""
        try:
            import aiohttp
            
            bot_token = os.getenv('BOT_TOKEN')
            admin_id = os.getenv('ADMIN_ID')
            
            if not bot_token or not admin_id:
                return
            
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            data = {
                'chat_id': admin_id,
                'text': message,
                'parse_mode': 'HTML'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=data) as response:
                    if response.status == 200:
                        self.logger.info("Security alert sent via Telegram")
                    else:
                        self.logger.error(f"Failed to send Telegram alert: {response.status}")
                        
        except Exception as e:
            self.logger.error(f"Failed to send Telegram alert: {e}")
    
    async def run_security_check(self):
        """Run a complete security check"""
        self.logger.info("Starting security check...")
        
        threats = await self.check_security_threats()
        
        if threats.get('error'):
            self.logger.error(f"Security check failed: {threats['error']}")
            return
        
        # Send alerts if necessary
        await self.send_security_alert(threats)
        
        # Update last check time
        self.last_check = datetime.now()
        
        # Log summary
        critical_count = len(threats.get('critical_alerts', []))
        warning_count = len(threats.get('warnings', []))
        
        if critical_count > 0 or warning_count > 0:
            self.logger.warning(f"Security check completed: {critical_count} critical, {warning_count} warnings")
        else:
            self.logger.info("Security check completed: No threats detected")
    
    async def continuous_monitoring(self, check_interval: int = 300):
        """Run continuous security monitoring"""
        self.logger.info(f"Starting continuous security monitoring (check every {check_interval} seconds)")
        
        while True:
            try:
                await self.run_security_check()
                await asyncio.sleep(check_interval)
            except KeyboardInterrupt:
                self.logger.info("Security monitoring stopped by user")
                break
            except Exception as e:
                self.logger.error(f"Error in continuous monitoring: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying
    
    async def generate_daily_report(self):
        """Generate daily security report"""
        try:
            conn = await asyncpg.connect(self.db_connection_string)
            
            yesterday = datetime.now() - timedelta(days=1)
            
            # Get daily statistics
            daily_stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_events,
                    COUNT(*) FILTER (WHERE severity = 'CRITICAL') as critical_events,
                    COUNT(*) FILTER (WHERE severity = 'ERROR') as error_events,
                    COUNT(*) FILTER (WHERE severity = 'WARNING') as warning_events,
                    COUNT(DISTINCT user_id) as affected_users
                FROM security_audit_log 
                WHERE timestamp > $1
            """, yesterday)
            
            # Get top security events
            top_events = await conn.fetch("""
                SELECT action, COUNT(*) as count
                FROM security_audit_log 
                WHERE timestamp > $1
                GROUP BY action
                ORDER BY count DESC
                LIMIT 10
            """, yesterday)
            
            # Get user activity summary
            user_activity = await conn.fetchrow("""
                SELECT 
                    COUNT(DISTINCT user_id) as active_users,
                    COUNT(*) FILTER (WHERE last_activity > $1) as daily_active_users
                FROM users
            """, yesterday)
            
            # Format report
            report = f"""
📊 DAILY SECURITY REPORT - {datetime.now().strftime('%Y-%m-%d')}

🔢 EVENT SUMMARY:
- Total Security Events: {daily_stats['total_events']}
- Critical Events: {daily_stats['critical_events']}
- Error Events: {daily_stats['error_events']}
- Warning Events: {daily_stats['warning_events']}
- Affected Users: {daily_stats['affected_users']}

👥 USER ACTIVITY:
- Total Users: {user_activity['active_users']}
- Daily Active Users: {user_activity['daily_active_users']}

🔝 TOP SECURITY EVENTS:
"""
            
            for event in top_events:
                report += f"- {event['action']}: {event['count']} occurrences\n"
            
            await conn.close()
            
            # Save report to file
            report_file = f"security_report_{datetime.now().strftime('%Y%m%d')}.txt"
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report)
            
            self.logger.info(f"Daily security report generated: {report_file}")
            
            # Send report via email/telegram if configured
            if os.getenv('DAILY_REPORTS', 'false').lower() == 'true':
                await self._send_telegram_alert(report)
            
            return report
            
        except Exception as e:
            self.logger.error(f"Error generating daily report: {e}")
            return None


async def main():
    """Main function for running security monitor"""
    monitor = SecurityMonitor()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'check':
            await monitor.run_security_check()
        elif command == 'monitor':
            interval = int(sys.argv[2]) if len(sys.argv) > 2 else 300
            await monitor.continuous_monitoring(interval)
        elif command == 'report':
            await monitor.generate_daily_report()
        else:
            print("Usage: python security_monitor.py [check|monitor|report] [interval]")
    else:
        # Default: run single check
        await monitor.run_security_check()


if __name__ == "__main__":
    asyncio.run(main())
