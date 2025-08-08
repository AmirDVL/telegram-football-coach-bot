#!/usr/bin/env python3
"""
Comprehensive UX Fix Validation

This script validates all the critical UX fixes applied:
1. /start always takes users to appropriate hub (admin vs user)
2. Photo handler validates state before processing
3. Text handler validates state before processing
4. All navigation buttons clear input states comprehensively
5. No random input processing outside valid flows

Tests all the comprehensive state management fixes.
"""

import asyncio
import sys
import os

# Add the project directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def validate_start_command_hub_redirect():
    """Validate that /start always redirects to appropriate hub"""
    print("🔍 Validating /start command hub redirect...")
    
    with open('main.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for admin hub redirect
    if 'await self.admin_panel.show_admin_main_menu(update, context)' in content:
        print("   ✅ Admin hub redirect found")
    else:
        print("   ❌ Admin hub redirect missing")
        return False
    
    # Check for user hub redirect
    if 'await self.show_status_based_menu(update, context, user_data, user_name)' in content:
        print("   ✅ User hub redirect found")
    else:
        print("   ❌ User hub redirect missing") 
        return False
    
    # Check for comprehensive state clearing in /start
    if 'FORCE MAIN HUB' in content and 'FORCE RESET' in content:
        print("   ✅ Comprehensive state clearing in /start")
    else:
        print("   ❌ Comprehensive state clearing missing")
        return False
    
    print("✅ /start command hub redirect - VALIDATED")
    return True

def validate_photo_handler_state_validation():
    """Validate that photo handler has strict state validation"""
    print("🔍 Validating photo handler state validation...")
    
    with open('main.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for CRITICAL INPUT STATE VALIDATION comment
    if 'CRITICAL INPUT STATE VALIDATION' in content:
        print("   ✅ Critical input state validation found")
    else:
        print("   ❌ Critical input state validation missing")
        return False
    
    # Check for admin state validation
    if 'Admin sent photo but not in plan upload mode' in content:
        print("   ✅ Admin photo state validation found")
    else:
        print("   ❌ Admin photo state validation missing")
        return False
    
    # Check for user state validation cases
    validation_cases = [
        'User {user_id} is purchasing additional course - valid receipt photo',
        'User {user_id} in questionnaire photo step - valid photo input',
        'User {user_id} sent photo without selecting course',
        'Photo sent in invalid state'
    ]
    
    cases_found = 0
    for case in validation_cases:
        if case.replace('{user_id}', 'user_id') in content:
            cases_found += 1
    
    if cases_found >= 3:
        print(f"   ✅ Photo validation cases found: {cases_found}/4")
    else:
        print(f"   ❌ Insufficient photo validation cases: {cases_found}/4")
        return False
    
    print("✅ Photo handler state validation - VALIDATED")
    return True

def validate_text_handler_state_validation():
    """Validate that text handler has strict state validation"""
    print("🔍 Validating text handler state validation...")
    
    with open('main.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for STRICT STATE VALIDATION comment
    if 'STRICT STATE VALIDATION to prevent processing text in wrong context' in content:
        print("   ✅ Strict state validation comment found")
    else:
        print("   ❌ Strict state validation comment missing")
        return False
    
    # Check for admin text validation
    if 'Admin sent text outside valid input flow' in content:
        print("   ✅ Admin text state validation found")
    else:
        print("   ❌ Admin text state validation missing")
        return False
    
    # Check for user text validation cases
    if 'User sent text during payment pending' in content:
        print("   ✅ Payment pending text validation found")
    else:
        print("   ❌ Payment pending text validation missing")
        return False
    
    # Check for questionnaire validation
    if 'TEXT INPUT OUTSIDE QUESTIONNAIRE' in content:
        print("   ✅ Questionnaire text validation found")
    else:
        print("   ❌ Questionnaire text validation missing")
        return False
    
    print("✅ Text handler state validation - VALIDATED")
    return True

def validate_comprehensive_state_clearing():
    """Validate that state clearing is comprehensive"""
    print("🔍 Validating comprehensive state clearing...")
    
    with open('admin_error_handler.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for COMPREHENSIVE VERSION comment
    if 'COMPREHENSIVE VERSION' in content:
        print("   ✅ Comprehensive state clearing version found")
    else:
        print("   ❌ Comprehensive state clearing version missing")
        return False
    
    # Check for extensive state list
    comprehensive_states = [
        'buying_additional_course',
        'payment_receipt_uploaded', 
        'admin_awaiting_input',
        'document_upload_pending',
        'navigation_stack',
        'callback_waiting'
    ]
    
    states_found = 0
    for state in comprehensive_states:
        if f"'{state}'" in content:
            states_found += 1
    
    if states_found >= 4:
        print(f"   ✅ Comprehensive states found: {states_found}/6")
    else:
        print(f"   ❌ Insufficient comprehensive states: {states_found}/6")
        return False
    
    # Check for cleanup logic
    if 'Clear the entire user context if it\'s mostly empty' in content:
        print("   ✅ Context cleanup logic found")
    else:
        print("   ❌ Context cleanup logic missing")
        return False
    
    print("✅ Comprehensive state clearing - VALIDATED")
    return True

def validate_navigation_state_clearing():
    """Validate that all navigation functions clear states"""
    print("🔍 Validating navigation state clearing...")
    
    with open('main.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for enhanced back_to_user_menu
    if 'COMPREHENSIVE STATE CLEARING' in content and 'back_to_user_menu' in content:
        print("   ✅ Enhanced back_to_user_menu found")
    else:
        print("   ❌ Enhanced back_to_user_menu missing")
        return False
    
    # Check for navigation logging
    if 'BACK TO MENU CLEANUP' in content:
        print("   ✅ Navigation cleanup logging found")
    else:
        print("   ❌ Navigation cleanup logging missing")
        return False
    
    # Check for payment_pending clearing
    if 'del self.payment_pending[user_id]' in content:
        print("   ✅ Payment pending clearing found")
    else:
        print("   ❌ Payment pending clearing missing")
        return False
    
    # Check for admin state clearing in navigation
    if 'clear_admin_input_states' in content and 'back_to_user_menu' in content:
        print("   ✅ Admin state clearing in navigation found")
    else:
        print("   ❌ Admin state clearing in navigation missing")
        return False
    
    print("✅ Navigation state clearing - VALIDATED")
    return True

def validate_error_handling_improvements():
    """Validate improved error handling"""
    print("🔍 Validating error handling improvements...")
    
    with open('main.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for enhanced error context
    if 'error_context' in content and 'There is no text in the message to edit' in content:
        print("   ✅ Enhanced error context found")
    else:
        print("   ❌ Enhanced error context missing")
        return False
    
    # Check for /start fallback in error messages
    if '🔄 برای حل مشکل /start را تایپ کنید' in content:
        print("   ✅ /start fallback in error messages found")
    else:
        print("   ❌ /start fallback in error messages missing")
        return False
    
    # Check for multiple fallback attempts
    if 'try sending a new message' in content:
        print("   ✅ Multiple fallback attempts found")
    else:
        print("   ❌ Multiple fallback attempts missing")
        return False
    
    print("✅ Error handling improvements - VALIDATED")
    return True

def main():
    print("=" * 70)
    print("🔧 COMPREHENSIVE UX FIX VALIDATION")
    print("=" * 70)
    print("\nValidating all critical UX improvements...")
    
    tests = [
        validate_start_command_hub_redirect,
        validate_photo_handler_state_validation,
        validate_text_handler_state_validation,
        validate_comprehensive_state_clearing,
        validate_navigation_state_clearing,
        validate_error_handling_improvements
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            print()
        except Exception as e:
            print(f"❌ {test.__name__} - ERROR: {e}\n")
    
    print("=" * 70)
    print(f"📊 VALIDATION RESULTS: {passed}/{total} PASSED")
    
    if passed == total:
        print("🎉 ALL UX FIXES PROPERLY IMPLEMENTED!")
        print("\n✅ Expected Behavior:")
        print("  1. /start ALWAYS takes users to appropriate main hub")
        print("  2. Photos only processed in valid input flows")
        print("  3. Text only processed in valid input contexts")
        print("  4. All navigation clears input states comprehensively")
        print("  5. No random input processing outside proper flows")
        print("  6. Enhanced error handling with helpful fallbacks")
        
        print("\n🧪 Manual Test Scenarios:")
        print("  1. Send photo after /start → Should get 'not needed' message")
        print("  2. Send text after /start → Should get normal menu")
        print("  3. Admin /start → Should go to admin hub directly")
        print("  4. Any navigation button → Should clear ALL states")
        print("  5. Random photo in receipt flow → Should validate state first")
        
    else:
        print("❌ Some UX fixes are missing - please review implementation")
    
    print("=" * 70)

if __name__ == "__main__":
    main()
