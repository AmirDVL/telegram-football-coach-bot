#!/usr/bin/env python3
# Quick debug script to check questionnaire system

import sys
import os
import json

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("Python version:", sys.version)
print("Current working directory:", os.getcwd())
print("Script directory:", os.path.dirname(os.path.abspath(__file__)))

# Check files exist
questionnaire_file = 'questionnaire_data.json'
bot_data_file = 'bot_data.json'

abs_questionnaire = os.path.join(os.path.dirname(os.path.abspath(__file__)), questionnaire_file)
abs_bot_data = os.path.join(os.path.dirname(os.path.abspath(__file__)), bot_data_file)

print(f"Questionnaire file path: {abs_questionnaire}")
print(f"Questionnaire file exists: {os.path.exists(abs_questionnaire)}")
print(f"Bot data file path: {abs_bot_data}")
print(f"Bot data file exists: {os.path.exists(abs_bot_data)}")

if os.path.exists(abs_questionnaire):
    with open(abs_questionnaire, 'r', encoding='utf-8') as f:
        data = json.load(f)
        print("Questionnaire data keys:", list(data.keys()))
        if '6451449152' in data:
            print("User 6451449152 data:", data['6451449152'])

# Test imports
try:
    from questionnaire_manager import QuestionnaireManager
    print("QuestionnaireManager import: SUCCESS")
    
    qm = QuestionnaireManager()
    print(f"QuestionnaireManager data file: {qm.data_file}")
    print(f"QuestionnaireManager questions count: {len(qm.questions)}")
    
    # Check question 1
    q1 = qm.questions.get(1)
    if q1:
        print(f"Question 1 text: {q1.get('text', 'No text')[:50]}...")
        print(f"Question 1 type: {q1.get('type', 'No type')}")
    else:
        print("Question 1 not found!")
        
except Exception as e:
    print(f"QuestionnaireManager import FAILED: {e}")
    import traceback
    traceback.print_exc()
