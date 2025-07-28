#!/usr/bin/env python3
"""
JSON Data Clearing Script
Clears all JSON data files for fresh testing
"""

import os
import json
from pathlib import Path

def clear_json_data():
    """Clear all JSON data files"""
    
    print("🔄 Clearing JSON data files...")
    
    # JSON files that store bot data
    json_files = [
        'users.json',
        'payments.json', 
        'courses.json',
        'admins.json',
        'bot_settings.json',
        'user_profiles.json',
        'statistics.json'
    ]
    
    cleared_files = []
    
    for filename in json_files:
        filepath = Path(filename)
        
        if filepath.exists():
            try:
                # For admins.json, keep basic structure but clear data
                if filename == 'admins.json':
                    with open(filepath, 'w', encoding='utf-8') as f:
                        json.dump({}, f, ensure_ascii=False, indent=2)
                    print(f"  ✅ Cleared: {filename}")
                    cleared_files.append(filename)
                
                # For other files, create empty list/dict as appropriate
                elif filename in ['users.json', 'payments.json', 'courses.json']:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        json.dump([], f, ensure_ascii=False, indent=2)
                    print(f"  ✅ Cleared: {filename}")
                    cleared_files.append(filename)
                
                else:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        json.dump({}, f, ensure_ascii=False, indent=2)
                    print(f"  ✅ Cleared: {filename}")
                    cleared_files.append(filename)
                    
            except Exception as e:
                print(f"  ❌ Error clearing {filename}: {e}")
        else:
            print(f"  ⚠️  File not found: {filename}")
    
    return cleared_files

def main():
    """Main function for JSON clearing"""
    print("🚀 Football Coach Bot - JSON Data Clearing Tool")
    print("=" * 50)
    print("⚠️  This will clear all JSON data files!")
    print("=" * 50)
    
    # Get user confirmation
    while True:
        confirm = input("\n❓ Clear JSON files? (yes/no): ").lower().strip()
        
        if confirm in ['yes', 'y']:
            break
        elif confirm in ['no', 'n']:
            print("❌ Operation cancelled.")
            return
        else:
            print("Please enter 'yes' or 'no'")
    
    print("\n" + "=" * 50)
    
    cleared_files = clear_json_data()
    
    print(f"\n✅ Cleared {len(cleared_files)} JSON files!")
    print("🎯 JSON data reset complete!")
    print("=" * 50)

if __name__ == "__main__":
    main()
