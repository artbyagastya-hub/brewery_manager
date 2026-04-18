import re
import os

files_to_update = [
    'web/static/ai_chat.css',
    'web/static/ai_dashboard.css'
]

replacements = [
    # Gradients
    (r'linear-gradient\(135deg,\s*#f59e0b,\s*#d97706\)', 'linear-gradient(135deg, #777777, #555555)'),
    (r'linear-gradient\(135deg,\s*#d97706,\s*#b45309\)', 'linear-gradient(135deg, #555555, #333333)'),
    (r'linear-gradient\(135deg,\s*#d97706,\s*#f59e0b\)', 'linear-gradient(135deg, #555555, #777777)'),
    (r'linear-gradient\(135deg,\s*#fffbeb,\s*#fef3c7\)', 'linear-gradient(135deg, #f5f5f5, #e0e0e0)'),
    
    # Specific Hexes
    (r'#f59e0b', '#777777'), # Light amber
    (r'#ff9800', '#777777'), # Orange
    (r'#d97706', '#555555'), # Mid amber
    (r'#b45309', '#333333'), # Dark amber
    
    # RGBAs
    (r'rgba\(245,\s*158,\s*11', 'rgba(119, 119, 119'),
    (r'rgba\(217,\s*119,\s*6', 'rgba(85, 85, 85')
]

for filepath in files_to_update:
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            content = f.read()
            
        original_content = content
        for pattern, replacement in replacements:
            content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)
            
        with open(filepath, 'w') as f:
            f.write(content)
        
        changed = "Yes" if original_content != content else "No"
        print(f"Updated {filepath} - Changed: {changed}")
    else:
        print(f"File not found: {filepath}")

