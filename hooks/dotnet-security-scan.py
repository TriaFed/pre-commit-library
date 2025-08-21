#!/usr/bin/env python3
"""
.NET specific security scanning for common vulnerabilities and anti-patterns.
Focused on ASP.NET, .NET Core, and .NET Framework security issues.
"""

import re
import sys
import argparse
import json
from typing import List, Tuple, Dict
from pathlib import Path

# .NET specific security patterns
DOTNET_SECURITY_PATTERNS = {
    'sql_injection': {
        'patterns': [
            r'new\s+SqlCommand\s*\([^)]*\+[^)]*\)',
            r'CommandText\s*=\s*[^;]*\+[^;]*',
            r'ExecuteQuery\s*\([^)]*\+[^)]*\)',
            r'ExecuteScalar\s*\([^)]*\+[^)]*\)',
            r'string\.Format\s*\([^)]*SELECT[^)]*\)',
            r'string\.Concat\s*\([^)]*SELECT[^)]*\)',
        ],
        'description': 'Potential SQL injection - use parameterized queries',
        'severity': 'high'
    },
    'path_traversal': {
        'patterns': [
            r'Path\.Combine\s*\([^)]*Request\.',
            r'File\.ReadAllText\s*\([^)]*Request\.',
            r'File\.WriteAllText\s*\([^)]*Request\.',
            r'FileStream\s*\([^)]*Request\.',
            r'\.\.[\\/]',
        ],
        'description': 'Potential path traversal vulnerability',
        'severity': 'high'
    },
    'deserialization': {
        'patterns': [
            r'BinaryFormatter\.Deserialize',
            r'XmlSerializer\.Deserialize.*untrusted',
            r'JsonConvert\.DeserializeObject.*Request\.',
            r'JavaScriptSerializer\.Deserialize',
            r'DataContractJsonSerializer\.ReadObject',
        ],
        'description': 'Insecure deserialization - validate input sources',
        'severity': 'high'
    },
    'weak_crypto': {
        'patterns': [
            r'MD5\.Create\(\)',
            r'SHA1\.Create\(\)',
            r'DESCryptoServiceProvider',
            r'RC2CryptoServiceProvider',
            r'new\s+MD5CryptoServiceProvider',
            r'new\s+SHA1CryptoServiceProvider',
        ],
        'description': 'Weak cryptographic algorithm - use SHA-256 or stronger',
        'severity': 'medium'
    },
    'hardcoded_secrets': {
        'patterns': [
            r'connectionString\s*=\s*["\'][^"\']*password[^"\']*["\']',
            r'Password\s*=\s*["\'][^"\']{3,}["\']',
            r'ApiKey\s*=\s*["\'][^"\']{10,}["\']',
            r'SecretKey\s*=\s*["\'][^"\']{10,}["\']',
        ],
        'description': 'Hardcoded credentials detected - use configuration/secrets',
        'severity': 'high'
    },
    'request_validation': {
        'patterns': [
            r'ValidateRequest\s*=\s*false',
            r'RequestValidationMode\.Disabled',
            r'\[ValidateInput\s*\(\s*false\s*\)\]',
            r'HttpRequestValidationException.*ignore',
        ],
        'description': 'Request validation disabled - security risk',
        'severity': 'medium'
    },
    'csrf_missing': {
        'patterns': [
            r'\[HttpPost\](?!.*\[ValidateAntiForgeryToken\])',
            r'\.MapPost\(',
            r'app\.Post\(',
        ],
        'description': 'POST action without CSRF protection',
        'severity': 'medium'
    },
    'debug_info': {
        'patterns': [
            r'customErrors\s*mode\s*=\s*["\']Off["\']',
            r'debug\s*=\s*["\']true["\']',
            r'compilation.*debug\s*=\s*["\']true["\']',
            r'<system\.web>.*<compilation.*debug="true"',
        ],
        'description': 'Debug mode enabled in production config',
        'severity': 'low'
    },
    'open_redirect': {
        'patterns': [
            r'Response\.Redirect\s*\([^)]*Request\.',
            r'RedirectToAction\s*\([^)]*Request\.',
            r'Redirect\s*\([^)]*Request\.QueryString',
        ],
        'description': 'Potential open redirect vulnerability',
        'severity': 'medium'
    },
    'xxe_vulnerability': {
        'patterns': [
            r'XmlDocument\.Load.*Request\.',
            r'XmlTextReader.*Request\.',
            r'XPathDocument.*Request\.',
            r'XmlReaderSettings.*DtdProcessing.*Parse',
        ],
        'description': 'Potential XXE vulnerability - disable external entities',
        'severity': 'medium'
    },
    'information_disclosure': {
        'patterns': [
            r'Exception\.ToString\(\)',
            r'ex\.Message.*Response\.Write',
            r'Exception.*InnerException',
            r'StackTrace.*Response',
        ],
        'description': 'Potential information disclosure through error messages',
        'severity': 'low'
    }
}

# File extensions to analyze
DOTNET_EXTENSIONS = {'.cs', '.vb', '.fs', '.aspx', '.ascx', '.ashx', '.asmx', '.config'}

# Configuration files that need special attention
CONFIG_FILES = {'web.config', 'app.config', 'appsettings.json', 'appsettings.*.json'}


def should_check_file(file_path: str) -> bool:
    """Determine if file should be checked for .NET security issues."""
    path = Path(file_path)
    
    # Check file extension
    if path.suffix.lower() in DOTNET_EXTENSIONS:
        return True
    
    # Check configuration files
    if path.name.lower() in CONFIG_FILES:
        return True
    
    # Check appsettings pattern
    if re.match(r'appsettings\..*\.json$', path.name.lower()):
        return True
    
    return False


def analyze_config_file(file_path: str, content: str) -> List[Tuple[int, str, str, str]]:
    """Analyze .NET configuration files for security issues."""
    issues = []
    lines = content.split('\n')
    
    for line_num, line in enumerate(lines, 1):
        line_lower = line.lower()
        
        # Check for sensitive data in config files
        if any(keyword in line_lower for keyword in ['password=', 'pwd=', 'secret=', 'key=']):
            if not any(safe in line_lower for safe in ['$(', '${', '%', 'placeholder', 'your_']):
                issues.append((
                    line_num,
                    line.strip(),
                    'config_secrets',
                    'Potential hardcoded secret in configuration file'
                ))
        
        # Check for insecure settings
        if 'customerrors' in line_lower and 'mode="off"' in line_lower:
            issues.append((
                line_num,
                line.strip(),
                'debug_info',
                'Custom errors disabled - may expose sensitive information'
            ))
        
        if 'debug="true"' in line_lower:
            issues.append((
                line_num,
                line.strip(),
                'debug_info',
                'Debug mode enabled - should be disabled in production'
            ))
    
    return issues


def check_dotnet_security(file_path: str) -> List[Tuple[int, str, str, str]]:
    """Check for .NET specific security patterns."""
    issues = []
    
    if not should_check_file(file_path):
        return issues
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            lines = content.split('\n')
        
        # Special handling for config files
        if any(config in Path(file_path).name.lower() for config in CONFIG_FILES):
            issues.extend(analyze_config_file(file_path, content))
        
        # Pattern-based analysis for source files
        for line_num, line in enumerate(lines, 1):
            if not line.strip():
                continue
            
            # Check security patterns
            for pattern_name, pattern_info in DOTNET_SECURITY_PATTERNS.items():
                for pattern in pattern_info['patterns']:
                    if re.search(pattern, line, re.IGNORECASE):
                        issues.append((
                            line_num,
                            line.strip(),
                            pattern_name,
                            pattern_info['description']
                        ))
    
    except Exception as e:
        print(f"Error analyzing {file_path}: {e}", file=sys.stderr)
    
    return issues


def get_severity_emoji(pattern_name: str) -> str:
    """Get emoji based on severity."""
    if pattern_name in DOTNET_SECURITY_PATTERNS:
        severity = DOTNET_SECURITY_PATTERNS[pattern_name]['severity']
    else:
        severity = 'medium'
    
    return {
        'high': '🚨',
        'medium': '⚠️',
        'low': '💡'
    }.get(severity, '⚠️')


def main():
    parser = argparse.ArgumentParser(description='.NET security validation')
    parser.add_argument('files', nargs='*', help='Files to check')
    parser.add_argument('--severity', choices=['low', 'medium', 'high'],
                        help='Minimum severity level to report')
    parser.add_argument('--json', action='store_true',
                        help='Output results in JSON format')
    args = parser.parse_args()
    
    exit_code = 0
    total_issues = 0
    all_results = {}
    
    severity_levels = {'low': 1, 'medium': 2, 'high': 3}
    min_severity = severity_levels.get(args.severity, 1) if args.severity else 1
    
    for file_path in args.files:
        issues = check_dotnet_security(file_path)
        
        # Filter by severity if specified
        if args.severity:
            filtered_issues = []
            for line_num, line_content, pattern_name, description in issues:
                if pattern_name in DOTNET_SECURITY_PATTERNS:
                    pattern_severity = DOTNET_SECURITY_PATTERNS[pattern_name]['severity']
                    if severity_levels.get(pattern_severity, 1) >= min_severity:
                        filtered_issues.append((line_num, line_content, pattern_name, description))
                else:
                    filtered_issues.append((line_num, line_content, pattern_name, description))
            issues = filtered_issues
        
        if issues:
            if args.json:
                all_results[file_path] = [
                    {
                        'line': line_num,
                        'content': line_content,
                        'pattern': pattern_name,
                        'description': description
                    }
                    for line_num, line_content, pattern_name, description in issues
                ]
            else:
                print(f"\n⚡ .NET security issues found in {file_path}:")
                for line_num, line_content, pattern_name, description in issues:
                    emoji = get_severity_emoji(pattern_name)
                    print(f"  {emoji} Line {line_num}: {pattern_name.replace('_', ' ').title()}")
                    print(f"    Description: {description}")
                    if line_content:
                        print(f"    Code: {line_content}")
            
            total_issues += len(issues)
            exit_code = 1
    
    if args.json:
        print(json.dumps(all_results, indent=2))
    elif total_issues > 0:
        print(f"\n❌ Found {total_issues} potential .NET security issue(s)")
        print("💡 Review .NET code for security vulnerabilities")
        print("💡 Consider using static analysis tools like Security Code Scan")
        print("💡 Follow OWASP guidelines for .NET security")
    else:
        print("✅ No .NET security issues detected")
    
    return exit_code


if __name__ == '__main__':
    sys.exit(main())
