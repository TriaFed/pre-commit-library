#!/usr/bin/env python3
"""
Check for license headers in source code files.
"""

import sys
import argparse
import re
from typing import List, Set, Dict
from pathlib import Path

# Common license header patterns
LICENSE_PATTERNS = {
    'apache': [
        r'Licensed under the Apache License',
        r'Apache License.*Version 2\.0',
    ],
    'mit': [
        r'MIT License',
        r'Permission is hereby granted, free of charge',
    ],
    'gpl': [
        r'GNU General Public License',
        r'This program is free software',
    ],
    'bsd': [
        r'BSD License',
        r'Redistribution and use in source and binary forms',
    ],
    'copyright': [
        r'Copyright.*\d{4}',
        r'\(c\).*\d{4}',
        r'©.*\d{4}',
    ]
}

# File extensions that should have license headers
HEADER_REQUIRED_EXTENSIONS = {
    '.py', '.java', '.js', '.ts', '.cpp', '.c', '.h', '.hpp', 
    '.cs', '.go', '.rs', '.php', '.rb', '.scala', '.swift'
}

# File extensions to skip
SKIP_EXTENSIONS = {
    '.md', '.txt', '.json', '.xml', '.yaml', '.yml', '.toml',
    '.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg', '.pdf'
}

# Directories to skip
SKIP_DIRECTORIES = {
    'node_modules', '.git', 'vendor', 'build', 'dist', 'target',
    '.pytest_cache', '__pycache__', '.venv', 'venv'
}


def should_check_file(file_path: str) -> bool:
    """Determine if file should be checked for license headers."""
    path = Path(file_path)
    
    # Skip if in excluded directory
    for part in path.parts:
        if part in SKIP_DIRECTORIES:
            return False
    
    # Skip if excluded extension
    if path.suffix in SKIP_EXTENSIONS:
        return False
    
    # Only check files that require headers
    return path.suffix in HEADER_REQUIRED_EXTENSIONS


def read_file_head(file_path: str, lines: int = 20) -> str:
    """Read the first N lines of a file."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            head_lines = []
            for i, line in enumerate(f):
                if i >= lines:
                    break
                head_lines.append(line)
            return ''.join(head_lines)
    except Exception:
        return ""


def has_license_header(file_path: str) -> tuple[bool, List[str]]:
    """Check if file has a license header."""
    head_content = read_file_head(file_path)
    found_licenses = []
    
    for license_type, patterns in LICENSE_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, head_content, re.IGNORECASE | re.MULTILINE):
                found_licenses.append(license_type)
                break
    
    return len(found_licenses) > 0, found_licenses


def main():
    parser = argparse.ArgumentParser(description='Check for license headers in source files')
    parser.add_argument('files', nargs='*', help='Files to check')
    parser.add_argument('--require-license', action='store_true',
                        help='Require license headers (fail if missing)')
    parser.add_argument('--license-type', choices=list(LICENSE_PATTERNS.keys()),
                        help='Require specific license type')
    args = parser.parse_args()
    
    exit_code = 0
    checked_files = 0
    files_with_license = 0
    files_without_license = []
    
    for file_path in args.files:
        if not should_check_file(file_path):
            continue
        
        checked_files += 1
        has_license, found_licenses = has_license_header(file_path)
        
        if has_license:
            files_with_license += 1
            if args.license_type and args.license_type not in found_licenses:
                print(f"⚠️  {file_path}: Has license but not {args.license_type} (found: {', '.join(found_licenses)})")
                if args.require_license:
                    exit_code = 1
            else:
                print(f"✅ {file_path}: License header found ({', '.join(found_licenses)})")
        else:
            files_without_license.append(file_path)
            if args.require_license:
                print(f"❌ {file_path}: Missing license header")
                exit_code = 1
            else:
                print(f"⚠️  {file_path}: No license header found")
    
    # Summary
    if checked_files > 0:
        print(f"\n📊 Summary:")
        print(f"   Files checked: {checked_files}")
        print(f"   With license: {files_with_license}")
        print(f"   Without license: {len(files_without_license)}")
        
        if files_without_license and not args.require_license:
            print(f"\n💡 Consider adding license headers to:")
            for file_path in files_without_license[:5]:  # Show first 5
                print(f"   - {file_path}")
            if len(files_without_license) > 5:
                print(f"   ... and {len(files_without_license) - 5} more")
    else:
        print("ℹ️  No source files found to check for license headers")
    
    return exit_code


if __name__ == '__main__':
    sys.exit(main())
