#!/usr/bin/env python3
"""Update main.py admin references to use unified panel"""

# Read the file
with open('main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace all references to use unified admin panel
content = content.replace("callback_data='admin_back_start'", "callback_data='admin_back_main'")

# Write back
with open('main.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Updated main.py admin_back_start references to admin_back_main (unified panel)")
