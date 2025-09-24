#!/usr/bin/env python3
"""
Test script to verify JSON fixing logic works correctly
"""

import json

def fix_malformed_json(body_str: str) -> str:
    """Fix common JSON formatting issues in webhook payload"""
    lines = body_str.split('\n')
    fixed_lines = []
    
    for line in lines:
        # Skip empty lines and braces
        if not line.strip() or line.strip() in ['{', '}']:
            fixed_lines.append(line)
            continue
        
        # Handle key-value pairs
        if ':' in line:
            # Split on first colon to separate key and value
            parts = line.split(':', 1)
            if len(parts) == 2:
                key_part = parts[0].strip()
                value_part = parts[1].strip()
                
                # Remove trailing comma from value if present
                has_comma = value_part.rstrip().endswith(',')
                if has_comma:
                    value_part = value_part.rstrip(' ,')
                
                # Fix the value part - quote it if it's not already quoted and not a number/boolean
                if (not value_part.startswith('"') and 
                    not value_part.startswith('{') and 
                    not value_part.replace('.', '').replace('-', '').isdigit() and
                    value_part not in ['true', 'false', 'null']):
                    value_part = f'"{value_part}"'
                
                # Reconstruct the line
                fixed_line = f'  {key_part}: {value_part}'
                if has_comma:
                    fixed_line += ','
                
                fixed_lines.append(fixed_line)
            else:
                fixed_lines.append(line)
        else:
            fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)

# Test with the actual problematic payload from logs
test_json = """{
  "event": "lark_form_submission",
  "record_id":  recIDcWVji,
  "submitted_at":  2025/09/24 14:52, 
  "fields": {
    "SN":  17,
    "TMK Agent ID":  nnnnnnnnnnnnn,
    "Submitted on":  2025/09/24,
    "Respondents":  Guest User 31145,
    "Customer Name": nnnn ,
    "Customer ID":  nnnnn,
    "Customer Contact": nnnn ,
    "Issue":  nnn,
    "Date" :2025/09/23
  }
}"""

print("Original JSON:")
print(test_json)
print("\nFixed JSON:")
fixed = fix_malformed_json(test_json)
print(fixed)

try:
    parsed = json.loads(fixed)
    print("\n✅ JSON parsing successful!")
    print("Parsed data:", json.dumps(parsed, indent=2))
except Exception as e:
    print(f"\n❌ JSON parsing failed: {e}")