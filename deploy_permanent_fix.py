#!/usr/bin/env python3
"""
DEPLOY PERMANENT CORRUPTION FIX TO SERVER

This script deploys the permanent corruption fix to the production server:
1. Uploads the fixed main.py with corruption-free /start command
2. Runs the user recovery for 1688724731
3. Creates server-side documentation
"""

import subprocess
import sys
from pathlib import Path

def run_ssh_command(command, description):
    """Run SSH command on server"""
    full_command = f'ssh root@46.249.102.158 "cd /root/football_coach_bot && {command}"'
    print(f"\n🔧 {description}")
    print(f"Command: {command}")
    
    try:
        result = subprocess.run(full_command, shell=True, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print(f"✅ Success")
            if result.stdout.strip():
                print(f"Output: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ Error (code {result.returncode})")
            if result.stderr:
                print(f"Error: {result.stderr.strip()}")
            return False
    except subprocess.TimeoutExpired:
        print(f"❌ Timeout after 30 seconds")
        return False
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def upload_file(local_path, remote_path, description):
    """Upload file to server"""
    command = f"scp {local_path} root@46.249.102.158:/root/football_coach_bot/{remote_path}"
    print(f"\n📤 {description}")
    print(f"Uploading: {local_path} -> {remote_path}")
    
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print(f"✅ Upload successful")
            return True
        else:
            print(f"❌ Upload failed (code {result.returncode})")
            if result.stderr:
                print(f"Error: {result.stderr.strip()}")
            return False
    except Exception as e:
        print(f"❌ Upload exception: {e}")
        return False

def main():
    print("🚀 DEPLOYING PERMANENT CORRUPTION FIX TO SERVER")
    print("=" * 60)
    
    # Step 1: Upload fixed main.py
    main_uploaded = upload_file("main.py", "main.py", "Uploading fixed main.py with corruption-free /start command")
    
    # Step 2: Upload fix script
    fix_uploaded = upload_file("permanent_corruption_fix.py", "permanent_corruption_fix.py", "Uploading permanent corruption fix script")
    
    if not (main_uploaded and fix_uploaded):
        print("\n❌ Upload failed - aborting deployment")
        return False
    
    # Step 3: Stop bot
    print("\n🛑 Stopping bot for update...")
    run_ssh_command("pkill -f 'python.*main.py' || true", "Stopping bot process")
    
    # Step 4: Run the corruption fix
    fix_success = run_ssh_command("python3 permanent_corruption_fix.py", "Running permanent corruption fix for user 1688724731")
    
    # Step 5: Start bot
    start_success = run_ssh_command("nohup python3 main.py > bot.log 2>&1 &", "Starting bot with corruption fix")
    
    # Step 6: Verify bot is running
    verify_success = run_ssh_command("sleep 3 && ps aux | grep 'python.*main.py' | grep -v grep", "Verifying bot is running")
    
    # Step 7: Create server documentation
    doc_success = run_ssh_command("echo 'PERMANENT CORRUPTION FIX DEPLOYED - $(date)' > CORRUPTION_FIX_DEPLOYED.md", "Creating deployment documentation")
    
    print("\n" + "=" * 60)
    print("🎯 DEPLOYMENT RESULTS:")
    print(f"{'✅' if main_uploaded else '❌'} Fixed main.py uploaded")
    print(f"{'✅' if fix_uploaded else '❌'} Fix script uploaded")
    print(f"{'✅' if fix_success else '❌'} User 1688724731 recovery executed")
    print(f"{'✅' if start_success else '❌'} Bot restarted with fix")
    print(f"{'✅' if verify_success else '❌'} Bot verified running")
    print(f"{'✅' if doc_success else '❌'} Server documentation created")
    
    if all([main_uploaded, fix_uploaded, fix_success, start_success, verify_success]):
        print("\n🔒 PERMANENT CORRUPTION FIX DEPLOYED SUCCESSFULLY")
        print("   - User 1688724731 can now proceed with payment")
        print("   - ALL future users protected from corruption")
        print("   - /start command no longer destroys payment data")
    else:
        print("\n❌ DEPLOYMENT ISSUES DETECTED")
        print("   Manual intervention may be required")
    
    return True

if __name__ == "__main__":
    main()