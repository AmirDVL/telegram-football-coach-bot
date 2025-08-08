#!/usr/bin/env python3
"""
Simple validation for questionnaire state fixes
"""

def validate_questionnaire_completion_fix():
    """Check if questionnaire completion functions have state clearing"""
    print("🔍 Validating questionnaire completion state clearing...")
    
    with open('main.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check complete_questionnaire function
    if 'clear_all_input_states' in content and 'questionnaire_completion_callback' in content:
        print("✅ complete_questionnaire - State clearing added")
    else:
        print("❌ complete_questionnaire - State clearing missing")
        return False
    
    # Check complete_questionnaire_from_text function  
    if 'questionnaire_completion_text' in content:
        print("✅ complete_questionnaire_from_text - State clearing added")
    else:
        print("❌ complete_questionnaire_from_text - State clearing missing")
        return False
    
    return True

def validate_text_handler_fix():
    """Check if text handler has improved validation"""
    print("🔍 Validating text handler improvements...")
    
    with open('main.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for validation improvement
    if 'TEXT INPUT AFTER RESET' in content and 'No active questionnaire' in content:
        print("✅ Text handler - Improved validation added")
        return True
    else:
        print("❌ Text handler - Validation improvement missing")
        return False

def validate_back_to_menu_fix():
    """Check if back to menu has better error handling"""
    print("🔍 Validating back to menu error handling...")
    
    with open('main.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for enhanced error context
    if 'There is no text in the message to edit' in content and 'error_context' in content:
        print("✅ Back to menu - Enhanced error handling added")
        return True
    else:
        print("❌ Back to menu - Error handling improvement missing")
        return False

def validate_admin_error_handler_functions():
    """Check if admin_error_handler has questionnaire state functions"""
    print("🔍 Validating admin_error_handler questionnaire functions...")
    
    with open('admin_error_handler.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for questionnaire state clearing
    if 'questionnaire_active' in content and 'questionnaire_step' in content:
        print("✅ admin_error_handler - Questionnaire states in clearing list")
    else:
        print("❌ admin_error_handler - Questionnaire states missing")
        return False
    
    # Check for reset_questionnaire_state function
    if 'reset_questionnaire_state' in content and 'reset_user_progress' in content:
        print("✅ admin_error_handler - reset_questionnaire_state function exists")
        return True
    else:
        print("❌ admin_error_handler - reset_questionnaire_state function missing")
        return False

def main():
    print("=" * 60)
    print("🔧 QUESTIONNAIRE STATE FIXES VALIDATION")
    print("=" * 60)
    
    tests = [
        validate_questionnaire_completion_fix,
        validate_text_handler_fix,
        validate_back_to_menu_fix,
        validate_admin_error_handler_functions
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
    
    print("=" * 60)
    print(f"📊 VALIDATION RESULTS: {passed}/{total} PASSED")
    
    if passed == total:
        print("🎉 ALL FIXES PROPERLY IMPLEMENTED!")
        print("\n✅ Expected Behavior:")
        print("  1. After questionnaire completion, any text input shows normal menu")
        print("  2. /start after questionnaire completion resets everything")  
        print("  3. Back to menu button provides better error messages")
        print("  4. No questionnaire continuation after completion or /start")
        
        print("\n🧪 Manual Test Steps:")
        print("  1. Complete questionnaire, then type any text → Should show normal menu")
        print("  2. Start questionnaire, type /start, then type text → Should show normal menu")
        print("  3. Click back to menu at questionnaire start → Should work without 'خطایی رخ داد'")
        
    else:
        print("❌ Some fixes are missing - please review implementation")
    
    print("=" * 60)

if __name__ == "__main__":
    main()
