#!/usr/bin/env python3
"""
Detect hardcoded URLs in code files.
Specifically designed to catch URLs that might be accidentally included by GenAI tools.
"""

import re
import sys
import os
import argparse
from typing import List, Tuple, Set, Optional, Pattern

# Protocol definitions - defined early to avoid circular dependencies
_WEB_PROTOCOLS = ['https', 'http']  # Standard web protocols

# Database protocols that can be used directly (not via JDBC)
_DIRECT_DB_PROTOCOLS = ['postgresql', 'mysql', 'mongodb']

# JDBC subprotocols that are allowed when using jdbc: prefix
_JDBC_SUBPROTOCOLS = ['postgresql', 'mysql', 'mariadb', 'h2', 'sqlite', 'oracle', 'sqlserver']

# All database protocols combined (direct + JDBC)
_DATABASE_PROTOCOLS = ['jdbc'] + _DIRECT_DB_PROTOCOLS

# All protocols combined - includes database protocols because:
# 1. Government/AWS systems often use managed database services (RDS, etc.)
# 2. Connection strings may legitimately reference these domains  
# 3. Infrastructure-as-code often includes database configurations
_ALL_PROTOCOLS = _WEB_PROTOCOLS + _DATABASE_PROTOCOLS

# Regex pattern components for URL matching
# RFC-compliant subdomain pattern: 1-63 chars, alphanumeric + hyphens (not at start/end)
# This prevents domain spoofing like badsite.com.legitimate.gov matching legitimate.gov
_SUBDOMAIN_PATTERN = r'[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?'

# Optional subdomain prefix: up to 5 levels of subdomains
# Each subdomain followed by a dot, entire group can appear 1-5 times, whole thing is optional
_OPTIONAL_SUBDOMAIN_PREFIX = f'(?:(?:{_SUBDOMAIN_PATTERN}\\.)+)?'

# URL component patterns
_PORT_PATTERN = r'(?::\d+)?'      # Optional port number (:80, :443, :8080, etc.)
_PATH_PATTERN = r'(?:/.*)?'       # Optional path and query string (/path?query=value)

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
    
    # Strip protocols once to avoid redundant operations in the loop
    stripped_protocols = [protocol.strip() for protocol in protocols]
    
    # Convert plain protocol names to regex patterns
    regex_protocols = []
    for protocol in stripped_protocols:
        if protocol == 'jdbc':
            # JDBC URLs have format jdbc:subprotocol://...
            # Use the centrally defined JDBC subprotocols for consistency
            # This prevents inadvertent whitelisting of malicious URLs
            jdbc_patterns = [f'jdbc:{re.escape(subprotocol)}' for subprotocol in _JDBC_SUBPROTOCOLS]
            regex_protocols.extend(jdbc_patterns)
        else:
            # For other protocols, escape any special regex characters to treat them as literals
            escaped_protocol = re.escape(protocol)
            regex_protocols.append(escaped_protocol)
    
    protocol_group = f'(?:{"|".join(regex_protocols)})'
    
    for domain in domains:
        # Escape dots in domain names for regex
        escaped_domain = domain.replace('.', r'\.')
        
        # Build URL pattern with clear components:
        # 1. Protocol group (https, http, jdbc:mysql, etc.)
        # 2. Optional subdomain prefix (api., secure.login., etc.) - prevents domain spoofing
        # 3. Base domain (cms.gov, github.com, etc.)
        # 4. Optional port number (:80, :443, :8080, etc.)
        # 5. Optional path and query string (/path?query=value, etc.)
        url_pattern = f"{protocol_group}://{_OPTIONAL_SUBDOMAIN_PREFIX}{escaped_domain}{_PORT_PATTERN}{_PATH_PATTERN}"
        patterns.append(url_pattern)
    
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

# Domain definitions
_GOVERNMENT_DOMAINS = ['cms.gov', 'cmscloud.local']
_AWS_DOMAINS = ['amazonaws.com']

# Function to generate URL detection patterns based on our protocol definitions
def _generate_url_detection_patterns() -> List[str]:
    """Generate URL detection patterns using our centralized protocol definitions."""
    patterns = [
        # HTTP/HTTPS URLs
        r'https?://[^\s\'">\\]]+',
        # FTP URLs  
        r'ftp://[^\s\'">\\]]+',
        # API endpoints patterns
        r'(?:api\.|www\.)[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:/[^\s\'">\\]]*)?',
    ]
    
    # Add direct database protocol patterns
    for protocol in _DIRECT_DB_PROTOCOLS:
        patterns.append(f'{re.escape(protocol)}://[^\\s\'">\\\\]]+')
    
    # Add JDBC patterns for all allowed subprotocols
    for subprotocol in _JDBC_SUBPROTOCOLS:
        patterns.append(f'jdbc:{re.escape(subprotocol)}://[^\\s\'">\\\\]]+')
    
    return patterns

# URL patterns that indicate hardcoded URLs (pre-compiled for performance)
def _compile_patterns_safely(patterns: List[str], pattern_type: str = "URL detection") -> List[Pattern[str]]:
    """Compile regex patterns with error handling and user warnings."""
    compiled = []
    for pattern in patterns:
        try:
            compiled.append(re.compile(pattern, re.IGNORECASE))
        except re.error as err:
            # Log a warning to stderr when skipping malformed regex patterns
            print(f"Warning: Malformed {pattern_type} regex pattern ignored: '{pattern}' ({err})", file=sys.stderr)
    return compiled

URL_PATTERNS = _compile_patterns_safely(_generate_url_detection_patterns(), "URL detection")

# Build the final SAFE_URL_PATTERNS by combining static and dynamic patterns
SAFE_URL_PATTERNS = _STATIC_SAFE_PATTERNS.copy()
SAFE_URL_PATTERNS.extend(generate_domain_patterns(_GOVERNMENT_DOMAINS, _ALL_PROTOCOLS))
SAFE_URL_PATTERNS.extend(generate_domain_patterns(_AWS_DOMAINS, _ALL_PROTOCOLS))

# Pre-compile safe patterns for performance and security
_COMPILED_SAFE_PATTERNS = _compile_patterns_safely(SAFE_URL_PATTERNS, "safe URL whitelist")

# File extensions to skip
SKIP_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg', '.pdf', '.zip', '.tar', '.gz'}

# Patterns that suggest this might be in a comment or documentation
_COMMENT_PATTERN_STRINGS = [
    r'^\s*#',     # Python, shell comments
    r'^\s*//',    # JavaScript, Java, C++ comments
    r'^\s*/\*',   # Multi-line comment start
    r'^\s*\*',    # Multi-line comment continuation
    r'^\s*<!--',  # HTML comments
]

# Pre-compile regex patterns for performance
def _compile_comment_patterns_safely(patterns: List[str]) -> List[Pattern[str]]:
    """Compile comment regex patterns with error handling (no IGNORECASE flag)."""
    compiled = []
    for pattern in patterns:
        try:
            compiled.append(re.compile(pattern))
        except re.error as err:
            # Log a warning to stderr when skipping malformed regex patterns
            print(f"Warning: Malformed comment detection regex pattern ignored: '{pattern}' ({err})", file=sys.stderr)
    return compiled

COMMENT_PATTERNS = _compile_comment_patterns_safely(_COMMENT_PATTERN_STRINGS)


def is_in_comment(line: str) -> bool:
    """Check if the line appears to be a comment.
    
    Args:
        line: The line of text to check
        
    Returns:
        True if the line matches any comment pattern (Python, Java, C++, HTML, etc.)
    """
    return any(pattern.match(line) for pattern in COMMENT_PATTERNS)


def is_safe_url(url: str, additional_patterns: Optional[List[str]] = None) -> bool:
    """Check if URL matches safe patterns (whitelisted domains/protocols).
    
    Args:
        url: The URL string to check
        additional_patterns: Optional list of additional regex patterns to consider safe
        
    Returns:
        True if the URL matches any safe pattern (government domains, AWS, localhost, etc.)
    """
    # Check pre-compiled safe patterns first (fastest path)
    for pattern in _COMPILED_SAFE_PATTERNS:
        if pattern.match(url):
            return True
    
    # Only compile additional patterns if needed (slower path)
    if additional_patterns:
        for pattern_str in additional_patterns:
            try:
                if re.match(pattern_str, url, re.IGNORECASE):
                    return True
            except re.error as err:
                # Log a warning to stderr when skipping malformed regex patterns
                print(f"Warning: Malformed additional safe pattern ignored: '{pattern_str}' ({err})", file=sys.stderr)
    
    return False


def find_hardcoded_urls(file_path: str, skip_files: Optional[Set[str]] = None, additional_safe_patterns: Optional[List[str]] = None) -> List[Tuple[int, str, str]]:
    """
    Find hardcoded URLs in a file.
    Returns list of (line_number, line_content, url) tuples.
    """
    if skip_files is None:
        skip_files = set()
    if additional_safe_patterns is None:
        additional_safe_patterns = []
    issues = []
    
    # Skip binary files and certain extensions (O(1) lookup)
    _, ext = os.path.splitext(file_path.lower())
    if ext in SKIP_EXTENSIONS:
        return issues
    
    # Skip files specified by user
    filename = os.path.basename(file_path)
    if filename in skip_files:
        return issues
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line_num, line in enumerate(f, 1):
                # Pre-strip line once for efficiency
                stripped_line = line.strip()
                if not stripped_line:
                    continue
                
                # Check for URL patterns (already compiled with IGNORECASE)
                for pattern in URL_PATTERNS:
                    matches = pattern.finditer(line)
                    for match in matches:
                        url = match.group()
                        
                        # Skip safe URLs
                        if is_safe_url(url, additional_safe_patterns):
                            continue
                        
                        # Be more lenient with URLs in comments/documentation
                        is_comment = is_in_comment(line)
                        if is_comment:
                            # Only flag suspicious URLs even in comments (pre-compute lower case)
                            url_lower = url.lower()
                            if any(keyword in url_lower for keyword in 
                                   ['api', 'prod', 'staging', 'internal', 'admin']):
                                issues.append((line_num, stripped_line, url))
                        else:
                            issues.append((line_num, stripped_line, url))
    
    except (FileNotFoundError, PermissionError) as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)
    except UnicodeDecodeError as e:
        print(f"Encoding error in {file_path}: {e}", file=sys.stderr)
    except Exception as e:
        print(f"Unexpected error reading {file_path}: {e}", file=sys.stderr)
    
    return issues


def main() -> int:
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
    parser.add_argument('--safe-protocols', type=str, 
                        default=','.join(_ALL_PROTOCOLS),
                        help=f'Comma-separated list of protocol names for safe domains (default: {",".join(_ALL_PROTOCOLS)})')
    args = parser.parse_args()
    
    # Input validation
    if not args.files:
        print("No files specified to check", file=sys.stderr)
        return 0
    
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
