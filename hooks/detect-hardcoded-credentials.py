#!/usr/bin/env python3
"""
Detect hardcoded credentials and sensitive information in code files.
Enhanced for GenAI-generated code which might accidentally include credentials.
"""

import re
import sys
import argparse
from typing import List, Tuple, Dict, Set
import base64

# Patterns for common credential types
CREDENTIAL_PATTERNS = {
    'password': [
        r'password\s*[:=]\s*["\'][^"\']{3,}["\']',
        r'pwd\s*[:=]\s*["\'][^"\']{3,}["\']',
        r'passwd\s*[:=]\s*["\'][^"\']{3,}["\']',
        r'secret\s*[:=]\s*["\'][^"\']{8,}["\']',
    ],
    'api_key': [
        r'api[_-]?key\s*[:=]\s*["\'][^"\']{10,}["\']',
        r'apikey\s*[:=]\s*["\'][^"\']{10,}["\']',
        r'key\s*[:=]\s*["\'][A-Za-z0-9]{20,}["\']',
    ],
    'token': [
        r'token\s*[:=]\s*["\'][^"\']{10,}["\']',
        r'auth[_-]?token\s*[:=]\s*["\'][^"\']{10,}["\']',
        r'access[_-]?token\s*[:=]\s*["\'][^"\']{10,}["\']',
        r'bearer\s*[:=]\s*["\'][^"\']{10,}["\']',
    ],
    'database': [
        r'db[_-]?password\s*[:=]\s*["\'][^"\']{3,}["\']',
        r'database[_-]?password\s*[:=]\s*["\'][^"\']{3,}["\']',
        r'connection[_-]?string\s*[:=]\s*["\'][^"\']*password[^"\']*["\']',
    ],
    'private_key': [
        r'private[_-]?key\s*[:=]\s*["\'][^"\']{20,}["\']',
        r'-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----',
        r'-----BEGIN\s+OPENSSH\s+PRIVATE\s+KEY-----',
    ],
    'aws': [
        r'aws[_-]?secret[_-]?access[_-]?key\s*[:=]\s*["\'][^"\']{20,}["\']',
        r'aws[_-]?access[_-]?key[_-]?id\s*[:=]\s*["\']AKIA[0-9A-Z]{16}["\']',
    ],
    'generic_secret': [
        r'secret[_-]?key\s*[:=]\s*["\'][^"\']{10,}["\']',
        r'client[_-]?secret\s*[:=]\s*["\'][^"\']{10,}["\']',
        r'app[_-]?secret\s*[:=]\s*["\'][^"\']{10,}["\']',
    ]
}

# Common safe values that can be ignored
SAFE_VALUES = {
    'password', 'secret', 'key', 'token', 'your_password_here', 'change_me',
    'example', 'sample', 'test', 'demo', 'placeholder', 'dummy', 'fake',
    '***', '...', 'xxx', 'yyy', 'zzz', 'your_api_key_here', 'your_secret_here',
    'insert_your_key_here', 'replace_with_your_key', 'your_token_here',
    '12345', '123456', 'qwerty', 'admin', 'root', 'user'
}

# File extensions to skip
SKIP_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg', '.pdf', '.zip', '.tar', '.gz'}

# Patterns that suggest this might be in a comment or test
SAFE_CONTEXT_PATTERNS = [
    r'^\s*#',     # Comments
    r'^\s*//',    
    r'^\s*/\*',   
    r'^\s*\*',    
    r'^\s*<!--',  
    r'test.*',    # Test files/variables
    r'.*test.*',
    r'example.*', # Example code
    r'.*example.*',
    r'sample.*',  # Sample code
    r'.*sample.*',
    r'mock.*',    # Mock data
    r'.*mock.*',
    r'placeholder.*',
    r'.*placeholder.*',
]


def is_safe_context(line: str, file_path: str) -> bool:
    """Check if the line/file appears to be in a safe context."""
    # Check if file is a test file
    if any(test_indicator in file_path.lower() for test_indicator in 
           ['test', 'spec', 'mock', 'example', 'sample', 'demo']):
        return True
    
    # Check if line appears to be in a safe context
    return any(re.match(pattern, line.lower()) for pattern in SAFE_CONTEXT_PATTERNS)


def is_safe_value(value: str) -> bool:
    """Check if the extracted value is a safe placeholder."""
    clean_value = value.strip('\'"').lower()
    
    # Check against known safe values
    if clean_value in SAFE_VALUES:
        return True
    
    # Check if it's too short to be a real credential
    if len(clean_value) < 4:
        return True
    
    # Check if it's all the same character (like ***)
    if len(set(clean_value)) == 1:
        return True
    
    # Check if it contains placeholder-like text
    placeholder_indicators = ['your_', 'insert_', 'replace_', 'change_', 'enter_', 'add_', 'put_']
    if any(indicator in clean_value for indicator in placeholder_indicators):
        return True
    
    return False


def extract_credential_value(match_text: str) -> str:
    """Extract the actual credential value from the match."""
    # Look for quoted strings
    quote_match = re.search(r'["\']([^"\']+)["\']', match_text)
    if quote_match:
        return quote_match.group(1)
    
    # Look for unquoted values after = or :
    value_match = re.search(r'[:=]\s*([^\s\'"]+)', match_text)
    if value_match:
        return value_match.group(1)
    
    return match_text


def is_base64_encoded(text: str) -> bool:
    """Check if text appears to be base64 encoded data."""
    try:
        if len(text) % 4 == 0 and re.match(r'^[A-Za-z0-9+/]*={0,2}$', text):
            decoded = base64.b64decode(text)
            # Check if decoded content looks like text
            try:
                decoded.decode('utf-8')
                return len(text) > 20  # Only flag longer base64 strings
            except UnicodeDecodeError:
                return False
    except:
        pass
    return False


def find_hardcoded_credentials(file_path: str) -> List[Tuple[int, str, str, str]]:
    """
    Find hardcoded credentials in a file.
    Returns list of (line_number, line_content, credential_type, value) tuples.
    """
    issues = []
    
    # Skip binary files and certain extensions
    if any(file_path.endswith(ext) for ext in SKIP_EXTENSIONS):
        return issues
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            lines = content.split('\n')
            
            for line_num, line in enumerate(lines, 1):
                # Skip empty lines
                if not line.strip():
                    continue
                
                # Check each credential pattern type
                for cred_type, patterns in CREDENTIAL_PATTERNS.items():
                    for pattern in patterns:
                        matches = re.finditer(pattern, line, re.IGNORECASE)
                        for match in matches:
                            match_text = match.group()
                            credential_value = extract_credential_value(match_text)
                            
                            # Skip if it's a safe value
                            if is_safe_value(credential_value):
                                continue
                            
                            # Be more lenient in safe contexts (tests, examples, comments)
                            if is_safe_context(line, file_path):
                                # Only flag very suspicious patterns in safe contexts
                                if len(credential_value) > 30 or is_base64_encoded(credential_value):
                                    issues.append((line_num, line.strip(), cred_type, credential_value))
                            else:
                                issues.append((line_num, line.strip(), cred_type, credential_value))
    
    except Exception as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)
    
    return issues


def main():
    parser = argparse.ArgumentParser(description='Detect hardcoded credentials in code')
    parser.add_argument('files', nargs='*', help='Files to check')
    parser.add_argument('--show-values', action='store_true',
                        help='Show the actual credential values (use with caution)')
    args = parser.parse_args()
    
    exit_code = 0
    total_issues = 0
    
    for file_path in args.files:
        issues = find_hardcoded_credentials(file_path)
        
        if issues:
            print(f"\n🔐 Hardcoded credentials found in {file_path}:")
            for line_num, line_content, cred_type, value in issues:
                print(f"  Line {line_num}: {cred_type.upper()}")
                if args.show_values:
                    print(f"    Value: {value}")
                else:
                    print(f"    Value: {'*' * min(len(value), 20)}")
                print(f"    Context: {line_content}")
            
            total_issues += len(issues)
            exit_code = 1
    
    if total_issues > 0:
        print(f"\n❌ Found {total_issues} potential hardcoded credential(s)")
        print("💡 Use environment variables or secure vaults for credentials")
        print("💡 Never commit real credentials to version control")
        print("💡 Consider using tools like .env files with .gitignore")
    else:
        print("✅ No hardcoded credentials detected")
    
    return exit_code


if __name__ == '__main__':
    sys.exit(main())
