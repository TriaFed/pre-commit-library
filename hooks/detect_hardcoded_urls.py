#!/usr/bin/env python3
"""
Detect hardcoded URLs in code files.
Specifically designed to catch URLs that might be accidentally included by GenAI tools.
"""

import re
import sys
import os
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

def generate_domain_patterns(domains: List[str], protocols: List[str]) -> List[str]:
    """Generate URL patterns for given domains and protocols.
    
    Args:
        domains: List of domain names (e.g., ['cms.gov', 'github.com'])
        protocols: List of plain protocol names (e.g., ['https', 'http', 'jdbc', 'postgresql'])
                  Protocol names are automatically escaped for regex safety, except 'jdbc' 
                  which is treated specially to match 'jdbc:subprotocol' patterns.
    
    Returns:
        List of regex patterns that match URLs with the specified protocols and domains.
    """
    patterns = []
    
    # Convert plain protocol names to regex patterns
    regex_protocols = []
    for protocol in protocols:
        if protocol == 'jdbc':
            # JDBC URLs have format jdbc:subprotocol://...
            # Special case: don't escape this pattern as it's intentionally a regex
            regex_protocols.append('jdbc:[^:]+')
        else:
            # For other protocols, escape any special regex characters to treat them as literals
            escaped_protocol = re.escape(protocol.strip())
            regex_protocols.append(escaped_protocol)
    
    protocol_group = f"(?:{'|'.join(regex_protocols)})"
    
    for domain in domains:
        # Escape dots in domain names for regex
        escaped_domain = domain.replace('.', r'\.')
        # Pattern for subdomains
        patterns.append(f"{protocol_group}://.*\\.{escaped_domain}(?::\\d+)?(?:/.*)?")
        # Pattern for main domain
        patterns.append(f"{protocol_group}://{escaped_domain}(?::\\d+)?(?:/.*)?")
    
    return patterns


# URLs that are typically safe to ignore
# Static patterns for common localhost and development URLs
_STATIC_SAFE_PATTERNS = [
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
    # Git URLs (common version control systems)
    r'https?://github\.com/.*',
    r'https?://gitlab\.com/.*',
    r'https?://bitbucket\.org/.*',
    r'https?://.*\.github\.io/.*',
    r'git://.*',
    r'ssh://git@.*',
    # Schema and specification URLs (HTTP only)
    r'https?://adaptivecards\.io/.*',
    r'https?://.*\.adaptivecards\.io/.*',
    # Common documentation URLs (HTTP only)
    r'https?://docs\..*',
    r'https?://www\.w3\.org/.*',
    r'https?://tools\.ietf\.org/.*',
    r'https?://schemas\..*',
    # Package registries
    r'https?://registry\.npmjs\.org/.*',
    r'https?://pypi\.org/.*',
    r'https?://central\.maven\.org/.*',
]

# Generate dynamic patterns for common domains with multiple protocols
# This reduces duplication and improves maintainability
_COMMON_PROTOCOLS = ['https', 'http', 'jdbc', 'postgresql', 'mysql', 'mongodb']

# Government domains (cms.gov and related)
_GOVERNMENT_DOMAINS = ['cms.gov', 'cmscloud.local']

# AWS domains
_AWS_DOMAINS = ['amazonaws.com']

# Build the final SAFE_URL_PATTERNS by combining static and dynamic patterns
SAFE_URL_PATTERNS = _STATIC_SAFE_PATTERNS.copy()
SAFE_URL_PATTERNS.extend(generate_domain_patterns(_GOVERNMENT_DOMAINS, _COMMON_PROTOCOLS))
SAFE_URL_PATTERNS.extend(generate_domain_patterns(_AWS_DOMAINS, _COMMON_PROTOCOLS))

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


def is_safe_url(url: str, additional_patterns: List[str] = None) -> bool:
    """Check if URL matches safe patterns."""
    all_patterns = SAFE_URL_PATTERNS[:]
    if additional_patterns:
        all_patterns.extend(additional_patterns)
    return any(re.match(pattern, url, re.IGNORECASE) for pattern in all_patterns)


def find_hardcoded_urls(file_path: str, skip_files: Set[str] = None, additional_safe_patterns: List[str] = None) -> List[Tuple[int, str, str]]:
    """
    Find hardcoded URLs in a file.
    Returns list of (line_number, line_content, url) tuples.
    """
    if skip_files is None:
        skip_files = set()
    if additional_safe_patterns is None:
        additional_safe_patterns = []
    issues = []
    
    # Skip binary files and certain extensions
    if any(file_path.endswith(ext) for ext in SKIP_EXTENSIONS):
        return issues
    
    # Skip files specified by user
    if skip_files:
        filename = os.path.basename(file_path)
        if filename in skip_files:
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
                        if is_safe_url(url, additional_safe_patterns):
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
    parser.add_argument('--exclude-patterns', type=str,
                        help='Comma-separated list of URL patterns to exclude (e.g., "localhost,127.0.0.1,docker")')
    parser.add_argument('--exclude-files', type=str,
                        help='Comma-separated list of filenames to exclude (e.g., "README.md,CHANGELOG.md,docs.txt")')
    parser.add_argument('--safe-domains', type=str,
                        help='Comma-separated list of domains to whitelist with all protocols (e.g., "cms.gov,amazonaws.com,github.com")')
    parser.add_argument('--safe-protocols', type=str, default='https,http,jdbc,postgresql,mysql,mongodb',
                        help='Comma-separated list of protocol names to support for safe domains (default: "https,http,jdbc,postgresql,mysql,mongodb"). Provide plain protocol names - the function handles regex conversion internally. Note: "jdbc" is automatically expanded to match "jdbc:subprotocol" patterns.')
    args = parser.parse_args()
    
    exit_code = 0
    total_issues = 0
    
    # Parse exclusion patterns
    exclude_patterns = []
    if args.exclude_patterns:
        exclude_patterns = [p.strip().lower() for p in args.exclude_patterns.split(',')]
    
    # Parse file exclusions
    exclude_files = set()
    if args.exclude_files:
        exclude_files = {f.strip() for f in args.exclude_files.split(',')}
    
    # Parse dynamic safe domains and protocols
    additional_safe_patterns = []
    if args.safe_domains:
        safe_domains = [d.strip() for d in args.safe_domains.split(',')]
        safe_protocols = [p.strip() for p in args.safe_protocols.split(',')]
        additional_safe_patterns = generate_domain_patterns(safe_domains, safe_protocols)
    
    for file_path in args.files:
        issues = find_hardcoded_urls(file_path, exclude_files, additional_safe_patterns)
        
        # Filter out excluded URL patterns
        if exclude_patterns:
            filtered_issues = []
            for line_num, line_content, url in issues:
                if not any(pattern in url.lower() for pattern in exclude_patterns):
                    filtered_issues.append((line_num, line_content, url))
            issues = filtered_issues
        
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
