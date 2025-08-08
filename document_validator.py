#!/usr/bin/env python3
"""
Comprehensive Document Reference Validation
Checks all document storage and references in the bot system
"""

import json
import os
import asyncio
from datetime import datetime
from pathlib import Path

async def validate_documents():
    """Validate all document references and storage consistency"""
    print("📋 COMPREHENSIVE DOCUMENT VALIDATION\n")
    
    # 1. Check bot_data.json user references
    print("1. 🗂️ USER DATA & RECEIPTS:")
    try:
        with open('bot_data.json', 'r', encoding='utf-8') as f:
            bot_data = json.load(f)
        
        users = bot_data.get('users', {})
        payments = bot_data.get('payments', {})
        
        print(f"   👥 Total users: {len(users)}")
        print(f"   💳 Total payments: {len(payments)}")
        
        # Check receipt references
        receipt_refs = []
        for user_id, user_data in users.items():
            if 'receipt_file_id' in user_data:
                receipt_refs.append({
                    'user_id': user_id,
                    'name': user_data.get('name', 'Unknown'),
                    'file_id': user_data['receipt_file_id'],
                    'course': user_data.get('course_selected', 'None'),
                    'status': user_data.get('payment_status', 'Unknown')
                })
        
        print(f"   📷 Receipt references: {len(receipt_refs)}")
        for ref in receipt_refs:
            print(f"      - User {ref['name']} ({ref['user_id']}): {ref['course']} -> {ref['status']}")
            print(f"        File ID: {ref['file_id'][:20]}...")
        
    except Exception as e:
        print(f"   ❌ Error reading bot_data.json: {e}")
    
    print()
    
    # 2. Check questionnaire_data.json
    print("2. 📝 QUESTIONNAIRE DATA & PHOTOS:")
    try:
        with open('questionnaire_data.json', 'r', encoding='utf-8') as f:
            quest_data = json.load(f)
        
        responses = quest_data.get('responses', {})
        photos = quest_data.get('photos', {})
        completed = quest_data.get('completed', [])
        
        print(f"   ✏️ User responses: {len(responses)}")
        print(f"   📸 Photo storage: {len(photos)}")
        print(f"   ✅ Completed questionnaires: {len(completed)}")
        
        # Check photo references in questionnaire
        for user_id, user_photos in photos.items():
            print(f"      - User {user_id}: {len(user_photos)} photos")
            for step, photo_data in user_photos.items():
                if isinstance(photo_data, dict) and 'file_id' in photo_data:
                    print(f"        Step {step}: {photo_data['file_id'][:20]}... -> {photo_data.get('file_path', 'No path')}")
        
    except Exception as e:
        print(f"   ❌ Error reading questionnaire_data.json: {e}")
    
    print()
    
    # 3. Check course plans
    print("3. 📋 COURSE PLANS:")
    plan_dir = Path("admin_data/course_plans")
    if plan_dir.exists():
        plan_files = list(plan_dir.glob("*.json"))
        print(f"   📁 Plan files found: {len(plan_files)}")
        
        total_plans = 0
        for plan_file in plan_files:
            try:
                with open(plan_file, 'r', encoding='utf-8') as f:
                    plans = json.load(f)
                
                course_name = plan_file.stem
                plan_count = len(plans) if isinstance(plans, list) else 0
                total_plans += plan_count
                
                print(f"      - {course_name}: {plan_count} plans")
                
                # Show plan details
                if isinstance(plans, list) and plans:
                    for i, plan in enumerate(plans[:3]):  # Show first 3
                        if isinstance(plan, dict):
                            filename = plan.get('filename', 'No name')
                            target_user = plan.get('target_user_id', 'No target')
                            plan_id = plan.get('id', 'No ID')[:8]
                            print(f"         {i+1}. {filename} -> User {target_user} (ID: {plan_id}...)")
                    
                    if len(plans) > 3:
                        print(f"         ... and {len(plans)-3} more plans")
                
            except Exception as e:
                print(f"      ❌ Error reading {plan_file}: {e}")
        
        print(f"   📊 Total plans across all courses: {total_plans}")
    else:
        print("   ❌ Plan directory not found!")
    
    print()
    
    # 4. Check admin data
    print("4. 👑 ADMIN CONFIGURATION:")
    admin_sources = ['admins.json', 'bot_data.json']
    
    for source in admin_sources:
        try:
            with open(source, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if source == 'admins.json':
                admins = data.get('admins', [])
                super_admin = data.get('super_admin')
                permissions = data.get('admin_permissions', {})
            else:  # bot_data.json
                admin_section = data.get('admins', {})
                admins = admin_section.get('admins', [])
                super_admin = admin_section.get('super_admin')
                permissions = admin_section.get('admin_permissions', {})
            
            print(f"   📁 {source}:")
            print(f"      Super Admin: {super_admin}")
            print(f"      Admins: {admins}")
            print(f"      Permissions: {len(permissions)} entries")
            
        except Exception as e:
            print(f"   ❌ Error reading {source}: {e}")
    
    print()
    
    # 5. Check file system storage
    print("5. 💾 FILE SYSTEM STORAGE:")
    storage_dirs = [
        "questionnaire_photos",
        "user_data", 
        "admin_data",
        "logs",
        "uploads"
    ]
    
    for dir_name in storage_dirs:
        if os.path.exists(dir_name):
            try:
                files = []
                for root, dirs, filenames in os.walk(dir_name):
                    files.extend([os.path.join(root, f) for f in filenames])
                
                print(f"   📁 {dir_name}: {len(files)} files")
                if files and len(files) <= 5:
                    for file in files:
                        size = os.path.getsize(file)
                        print(f"      - {file} ({size} bytes)")
                elif files:
                    print(f"      - Showing first 3 of {len(files)} files:")
                    for file in files[:3]:
                        size = os.path.getsize(file)
                        print(f"        - {file} ({size} bytes)")
            except Exception as e:
                print(f"   ❌ Error scanning {dir_name}: {e}")
        else:
            print(f"   ❌ {dir_name}: Directory not found")
    
    print("\n" + "="*50)
    print("📋 VALIDATION COMPLETE")
    print("="*50)

if __name__ == "__main__":
    asyncio.run(validate_documents())
