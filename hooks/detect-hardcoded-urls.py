#!/usr/bin/env python3
"""
Detect hardcoded URLs in code files.
Specifically designed to catch URLs that might be accidentally included by GenAI tools.
"""

import re
import sys
import argparse
from typing import List, Tuple, Set

# Common patterns that indicate hardcoded URLs
URL_PATTERNS = [
    # HTTP/HTTPS URLs
    r'https?://[^\s\'">\]]+',
    # FTP URLs
    r'ftp://[^\s\'">\]]+',
    # Database connection strings with URLs
    r'(?:jdbc|mongodb|mysql|postgresql)://[^\s\'">\]]+',
    # API endpoints patterns
    r'(?:api\.|www\.)[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:/[^\s\'">\]]*)?',
]

# URLs that are typically safe to ignore
SAFE_URL_PATTERNS = [
    r'https?://localhost',
    r'https?://127\.0\.0\.1',
    r'https?://0\.0\.0\.0',
    r'https?://example\.com',
    r'https?://example\.org',
    r'https?://example\.net',
    r'https?://.*\.example\.com',
    r'https?://.*\.test',
    r'https?://.*\.local',
    r'https?://.*\.localhost',
    # Common documentation URLs
    r'https?://github\.com/.*',
    r'https?://docs\..*',
    r'https?://www\.w3\.org/.*',
    r'https?://tools\.ietf\.org/.*',
    r'https?://schemas\..*',
    # Package registries
    r'https?://registry\.npmjs\.org/.*',
    r'https?://pypi\.org/.*',
    r'https?://central\.maven\.org/.*',
]

# File extensions to skip
SKIP_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg', '.pdf', '.zip', '.tar', '.gz'}

# Patterns that suggest this might be in a comment or documentation
COMMENT_PATTERNS = [
    r'^\s*#',     # Python, shell comments
    r'^\s*//',    # JavaScript, Java, C++ comments
    r'^\s*/\*',   # Multi-line comment start
    r'^\s*\*',    # Multi-line comment continuation
    r'^\s*<!--',  # HTML comments
]


def is_in_comment(line: str) -> bool:
    """Check if the line appears to be a comment."""
    return any(re.match(pattern, line) for pattern in COMMENT_PATTERNS)


def is_safe_url(url: str) -> bool:
    """Check if URL matches safe patterns."""
    return any(re.match(pattern, url, re.IGNORECASE) for pattern in SAFE_URL_PATTERNS)


def find_hardcoded_urls(file_path: str) -> List[Tuple[int, str, str]]:
    """
    Find hardcoded URLs in a file.
    Returns list of (line_number, line_content, url) tuples.
    """
    issues = []
    
    # Skip binary files and certain extensions
    if any(file_path.endswith(ext) for ext in SKIP_EXTENSIONS):
        return issues
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line_num, line in enumerate(f, 1):
                # Skip empty lines
                if not line.strip():
                    continue
                
                # Check for URL patterns
                for pattern in URL_PATTERNS:
                    matches = re.finditer(pattern, line, re.IGNORECASE)
                    for match in matches:
                        url = match.group()
                        
                        # Skip safe URLs
                        if is_safe_url(url):
                            continue
                        
                        # Be more lenient with URLs in comments/documentation
                        if is_in_comment(line):
                            # Only flag suspicious URLs even in comments
                            if any(keyword in url.lower() for keyword in 
                                   ['api', 'prod', 'staging', 'internal', 'admin']):
                                issues.append((line_num, line.strip(), url))
                        else:
                            issues.append((line_num, line.strip(), url))
    
    except Exception as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)
    
    return issues


def main():
    parser = argparse.ArgumentParser(description='Detect hardcoded URLs in code')
    parser.add_argument('files', nargs='*', help='Files to check')
    parser.add_argument('--exclude-comments', action='store_true',
                        help='Exclude URLs found in comments')
    args = parser.parse_args()
    
    exit_code = 0
    total_issues = 0
    
    for file_path in args.files:
        issues = find_hardcoded_urls(file_path)
        
        if issues:
            print(f"\n🚨 Hardcoded URLs found in {file_path}:")
            for line_num, line_content, url in issues:
                print(f"  Line {line_num}: {url}")
                print(f"    Context: {line_content}")
            
            total_issues += len(issues)
            exit_code = 1
    
    if total_issues > 0:
        print(f"\n❌ Found {total_issues} hardcoded URL(s)")
        print("💡 Consider using environment variables or configuration files for URLs")
        print("💡 If these URLs are intentional, add them to the safe patterns or use comments")
    else:
        print("✅ No hardcoded URLs detected")
    
    return exit_code


if __name__ == '__main__':
    sys.exit(main())
