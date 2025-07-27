#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re

def fix_triple_quotes():
    """Fix all triple-quoted f-strings in main.py"""
    
    with open('main.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Pattern to match f"""...""" strings
    pattern = r'f"""([^"]*?)"""'
    
    def replace_func(match):
        text = match.group(1)
        # Split into lines
        lines = text.split('\n')
        
        # Remove empty lines at start and end
        while lines and not lines[0].strip():
            lines.pop(0)
        while lines and not lines[-1].strip():
            lines.pop()
        
        # Join with \n and wrap in parentheses for readability
        if len(lines) == 1:
            return f'"{lines[0]}"'
        else:
            escaped_lines = []
            for i, line in enumerate(lines):
                if i == len(lines) - 1:  # Last line
                    escaped_lines.append(f'"{line}"')
                else:
                    escaped_lines.append(f'"{line}\\n"')
            return '(' + '\n                             '.join(escaped_lines) + ')'
    
    # Replace all f""" strings
    new_content = re.sub(pattern, replace_func, content, flags=re.DOTALL)
    
    # Also fix regular """ strings with emojis
    pattern2 = r'"""([^"]*?[^\x00-\x7F][^"]*?)"""'
    
    def replace_func2(match):
        text = match.group(1)
        lines = text.split('\n')
        
        # Remove empty lines at start and end
        while lines and not lines[0].strip():
            lines.pop(0)
        while lines and not lines[-1].strip():
            lines.pop()
        
        if len(lines) == 1:
            return f'"{lines[0]}"'
        else:
            escaped_lines = []
            for i, line in enumerate(lines):
                if i == len(lines) - 1:
                    escaped_lines.append(f'"{line}"')
                else:
                    escaped_lines.append(f'"{line}\\n"')
            return '(' + '\n                             '.join(escaped_lines) + ')'
    
    new_content = re.sub(pattern2, replace_func2, new_content, flags=re.DOTALL)
    
    with open('main.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("Fixed all triple-quoted strings!")

if __name__ == "__main__":
    fix_triple_quotes()
