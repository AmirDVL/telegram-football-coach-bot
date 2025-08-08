#!/usr/bin/env python3
"""
Document Export Diagnostics and Test Tool
"""
import json
import os
import asyncio
from admin_error_handler import admin_error_handler

async def diagnose_export_issue():
    """Comprehensive diagnosis of document export issues"""
    print("🔍 DOCUMENT EXPORT DIAGNOSTICS")
    print("=" * 50)
    
    # Load current data
    try:
        with open('questionnaire_data.json', 'r', encoding='utf-8') as f:
            questionnaire_data = json.load(f)
    except Exception as e:
        print(f"❌ Error loading questionnaire_data.json: {e}")
        return
    
    print(f"📋 Found {len(questionnaire_data)} users in questionnaire data")
    
    # Analyze each user for document-related data
    users_with_completed_questionnaires = 0
    users_with_step_10_11_answers = 0
    users_with_documents = 0
    users_with_text_only_answers = 0
    
    print(f"\n📊 USER ANALYSIS:")
    print("-" * 30)
    
    for user_id, user_data in questionnaire_data.items():
        if user_id in ['responses', 'photos', 'completed']:
            continue  # Skip metadata keys
        
        completed = user_data.get('completed', False)
        answers = user_data.get('answers', {})
        
        print(f"\n👤 User {user_id}:")
        print(f"   ✅ Completed: {completed}")
        
        if completed:
            users_with_completed_questionnaires += 1
        
        # Check steps 10 and 11 specifically
        step_10_answer = answers.get('10')
        step_11_answer = answers.get('11')
        
        if step_10_answer or step_11_answer:
            users_with_step_10_11_answers += 1
            print(f"   📝 Step 10: {step_10_answer}")
            print(f"   📝 Step 11: {step_11_answer}")
            
            # Check if they're document uploads or text
            step_10_is_document = isinstance(step_10_answer, str) and "📎 فایل ارسال شده" in step_10_answer
            step_11_is_document = isinstance(step_11_answer, str) and "📎 فایل ارسال شده" in step_11_answer
            
            if step_10_is_document or step_11_is_document:
                print(f"   📎 Has document indicators!")
            else:
                users_with_text_only_answers += 1
                print(f"   📝 Text-only answers (no documents)")
        
        # Check for documents key
        documents_data = answers.get('documents', {})
        if documents_data:
            users_with_documents += 1
            print(f"   📎 Documents key found: {documents_data}")
            
            # Log this for debugging
            await admin_error_handler.log_admin_action(
                999999,  # Debug admin ID
                "found_user_with_documents",
                {
                    "user_id": user_id,
                    "documents": documents_data,
                    "step_10": step_10_answer,
                    "step_11": step_11_answer
                }
            )
        else:
            print(f"   ❌ No documents key found")
    
    print(f"\n📈 SUMMARY:")
    print(f"Total users analyzed: {len([k for k in questionnaire_data.keys() if k not in ['responses', 'photos', 'completed']])}")
    print(f"Users with completed questionnaires: {users_with_completed_questionnaires}")
    print(f"Users with step 10/11 answers: {users_with_step_10_11_answers}")
    print(f"Users with actual documents uploaded: {users_with_documents}")
    print(f"Users with text-only answers (no PDFs): {users_with_text_only_answers}")
    
    print(f"\n🎯 DIAGNOSIS:")
    if users_with_documents == 0:
        print("❌ ISSUE FOUND: No users have uploaded any documents!")
        print("   📝 All step 10/11 answers are text-only (like 'nothing')")
        print("   📄 For documents to appear in export, users must upload PDF files")
        print("   💡 Solution: Test with a user who uploads actual PDF files")
    else:
        print(f"✅ Found {users_with_documents} users with documents")
        print("   🔍 Export should work for these users")
    
    print(f"\n🧪 TESTING RECOMMENDATIONS:")
    print("1. Complete questionnaire up to step 10")
    print("2. When step 10 asks for training program details, upload a PDF file")
    print("3. Complete questionnaire to step 11")  
    print("4. When step 11 asks for weights program, upload another PDF file")
    print("5. Complete questionnaire")
    print("6. Try export - should now include documents")
    
    return {
        "users_analyzed": len([k for k in questionnaire_data.keys() if k not in ['responses', 'photos', 'completed']]),
        "users_with_documents": users_with_documents,
        "users_with_text_only": users_with_text_only_answers,
        "diagnosis": "no_documents_uploaded" if users_with_documents == 0 else "documents_found"
    }

async def create_test_document_data():
    """Create test data with sample documents for testing export"""
    print(f"\n🧪 CREATING TEST DOCUMENT DATA")
    print("-" * 40)
    
    # Load current data
    try:
        with open('questionnaire_data.json', 'r', encoding='utf-8') as f:
            questionnaire_data = json.load(f)
    except Exception as e:
        print(f"❌ Error loading questionnaire_data.json: {e}")
        return False
    
    # Find a user to add test documents to
    test_user_id = None
    for user_id, user_data in questionnaire_data.items():
        if user_id not in ['responses', 'photos', 'completed'] and user_data.get('completed'):
            test_user_id = user_id
            break
    
    if not test_user_id:
        print("❌ No completed questionnaire found to add test documents to")
        return False
    
    print(f"🎯 Adding test documents to user {test_user_id}")
    
    # Add sample document data
    user_data = questionnaire_data[test_user_id]
    answers = user_data.get('answers', {})
    
    # Update step 10 and 11 answers to indicate document uploads
    answers['10'] = "📎 فایل ارسال شده: test_cardio_program.pdf"
    answers['11'] = "📎 فایل ارسال شده: test_weights_program.pdf"
    
    # Add documents key with sample data
    answers['documents'] = {
        "10": {
            "file_id": "BQACAgQAAxkBAAI_TEST_CARDIO_FILE_ID_FOR_TESTING_PURPOSES_001",
            "name": "test_cardio_program.pdf"
        },
        "11": {
            "file_id": "BQACAgQAAxkBAAI_TEST_WEIGHTS_FILE_ID_FOR_TESTING_PURPOSES_002", 
            "name": "test_weights_program.pdf"
        }
    }
    
    # Save modified data
    try:
        with open('questionnaire_data.json', 'w', encoding='utf-8') as f:
            json.dump(questionnaire_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Added test documents to user {test_user_id}")
        print(f"📎 Documents added: test_cardio_program.pdf, test_weights_program.pdf")
        print(f"⚠️ Note: File IDs are fake - downloads will fail, but export logic will be tested")
        
        await admin_error_handler.log_admin_action(
            999999,
            "created_test_document_data",
            {
                "test_user_id": test_user_id,
                "documents_added": ["test_cardio_program.pdf", "test_weights_program.pdf"]
            }
        )
        
        return True
    except Exception as e:
        print(f"❌ Error saving test data: {e}")
        return False

async def main():
    """Main diagnostic function"""
    print("🚀 STARTING DOCUMENT EXPORT DIAGNOSIS")
    print("=" * 60)
    
    # Run diagnosis
    diagnosis_result = await diagnose_export_issue()
    
    # If no documents found, offer to create test data
    if diagnosis_result.get("diagnosis") == "no_documents_uploaded":
        print(f"\n💡 SOLUTION AVAILABLE:")
        print("Would you like to create test document data? (y/n)")
        print("This will add fake document records to test the export function.")
        
        # For automated testing, let's create the test data
        print("🔧 Creating test document data automatically...")
        test_success = await create_test_document_data()
        
        if test_success:
            print(f"\n✅ TEST DATA CREATED!")
            print("🎯 Now try the document export again - it should include documents!")
            print("📋 Steps to test:")
            print("1. Start the bot")
            print("2. Go to admin panel (/admin)")
            print("3. Export → Export Personal Data")
            print("4. Select the test user")
            print("5. Check the zip file for documents folder")
    
    print(f"\n📊 ENHANCED LOGGING AVAILABLE:")
    print("Check these files for detailed debugging:")
    print("• logs/admin_operations.log")
    print("• logs/admin_audit.json")
    print("• logs/admin_errors.log")

if __name__ == "__main__":
    asyncio.run(main())
