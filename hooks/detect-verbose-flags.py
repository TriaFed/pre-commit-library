#!/usr/bin/env python3
"""
Detect verbose flags and debug logging that should not be committed to production.
Specifically designed to catch verbose flags that GenAI tools might include.
"""

import re
import sys
import argparse
import json
from typing import List, Tuple, Dict, Set
from pathlib import Path

# Verbose flag patterns by language/framework
VERBOSE_PATTERNS = {
    'debug_flags': {
        'patterns': [
            # Python
            r'logging\.basicConfig\([^)]*level\s*=\s*logging\.DEBUG',
            r'logger\.setLevel\(logging\.DEBUG\)',
            r'debug\s*=\s*True',
            r'verbose\s*=\s*True',
            r'DJANGO_DEBUG\s*=\s*True',
            r'DEBUG\s*=\s*True',
            
            # JavaScript/TypeScript
            r'console\.debug\(',
            r'console\.trace\(',
            r'logger\.debug\(',
            r'debug:\s*true',
            r'verbose:\s*true',
            r'NODE_ENV.*development',
            r'process\.env\.DEBUG',
            
            # Java
            r'Logger\.getLogger\([^)]*\)\.setLevel\(Level\.DEBUG\)',
            r'Logger\.getLogger\([^)]*\)\.setLevel\(Level\.ALL\)',
            r'System\.setProperty\(["\']java\.util\.logging\.level["\'],\s*["\']DEBUG["\']',
            r'@EnableDebugLogs',
            r'\.debug\(.*\)',
            
            # .NET/C#
            r'LogLevel\.Debug',
            r'LogLevel\.Trace',
            r'\.AddDebug\(\)',
            r'\.SetMinimumLevel\(LogLevel\.Debug\)',
            r'#if\s+DEBUG',
            r'Debugger\.IsAttached',
            r'Environment\.GetEnvironmentVariable\(["\']ASPNETCORE_ENVIRONMENT["\'].*["\']Development["\']',
            
            # Go
            r'log\.SetLevel\(logrus\.DebugLevel\)',
            r'log\.SetLevel\(logrus\.TraceLevel\)',
            r'gin\.SetMode\(gin\.DebugMode\)',
            r'debug:\s*true',
            r'verbose:\s*true',
            
            # PHP
            r'error_reporting\(E_ALL\)',
            r'ini_set\(["\']display_errors["\'],\s*["\']1["\']',
            r'ini_set\(["\']display_startup_errors["\'],\s*["\']1["\']',
            r'WP_DEBUG.*true',
            r'define\(["\']WP_DEBUG["\'],\s*true\)',
            
            # Ruby
            r'Rails\.logger\.level\s*=\s*Logger::DEBUG',
            r'config\.log_level\s*=\s*:debug',
            r'logger\.level\s*=\s*Logger::DEBUG',
            
            # Shell/Bash
            r'set\s+-x',
            r'bash\s+-x',
            r'sh\s+-x',
            r'set\s+-v',
            r'PS4=',
        ],
        'description': 'Debug/verbose logging enabled - should be disabled in production',
        'severity': 'medium'
    },
    'verbose_cli_flags': {
        'patterns': [
            # Command line verbose flags
            r'\s-v\s',
            r'\s--verbose\s',
            r'\s-vv\s',
            r'\s-vvv\s',
            r'\s--debug\s',
            r'\s-d\s',
            r'\s--trace\s',
            r'VERBOSE=1',
            r'DEBUG=1',
            r'TRACE=1',
            
            # Docker
            r'docker.*--log-level\s*debug',
            r'docker.*--debug',
            r'dockerfile.*--progress=plain',
            
            # Kubernetes
            r'kubectl.*--v=[5-9]',
            r'kubectl.*--v=1[0-9]',
            r'helm.*--debug',
            
            # Terraform
            r'TF_LOG=DEBUG',
            r'TF_LOG=TRACE',
            r'terraform.*-verbose',
            
            # Ansible
            r'ansible.*-vvv',
            r'ansible.*-vv',
            r'ansible.*--verbose',
            r'ANSIBLE_DEBUG=1',
            
            # Git
            r'git.*--verbose',
            r'GIT_TRACE=1',
            r'GIT_CURL_VERBOSE=1',
        ],
        'description': 'Verbose command line flags detected - may expose sensitive information',
        'severity': 'low'
    },
    'configuration_debug': {
        'patterns': [
            # Configuration files
            r'log_level:\s*debug',
            r'log_level:\s*trace',
            r'verbosity:\s*[3-9]',
            r'debug_mode:\s*true',
            r'enable_debug:\s*true',
            r'development_mode:\s*true',
            
            # Environment variables in configs
            r'ENV\s+DEBUG\s*=\s*true',
            r'ENV\s+VERBOSE\s*=\s*true',
            r'environment:\s*development',
            
            # Database debug
            r'SHOW_SQL\s*=\s*true',
            r'hibernate\.show_sql\s*=\s*true',
            r'spring\.jpa\.show-sql\s*=\s*true',
            r'DATABASE_DEBUG\s*=\s*true',
            
            # Web server debug
            r'ErrorDocument\s+500.*debug',
            r'display_errors\s*=\s*On',
            r'display_startup_errors\s*=\s*On',
        ],
        'description': 'Debug configuration detected - should be disabled in production',
        'severity': 'medium'
    },
    'test_debug_remnants': {
        'patterns': [
            # Test debugging left in code
            r'console\.log\([^)]*["\']DEBUG["\']',
            r'print\([^)]*["\']DEBUG["\']',
            r'System\.out\.println\([^)]*["\']DEBUG["\']',
            r'fmt\.Println\([^)]*["\']DEBUG["\']',
            r'echo\s+["\']DEBUG',
            r'logger\.[^(]*\([^)]*["\']DEBUG["\']',
            
            # Temporary debugging
            r'\/\/\s*TODO:?\s*remove.*debug',
            r'\/\/\s*FIXME:?\s*remove.*debug',
            r'#\s*TODO:?\s*remove.*debug',
            r'\/\*.*DEBUG.*\*\/',
            r'<!--.*DEBUG.*-->',
            
            # Performance debugging
            r'console\.time\(',
            r'console\.timeEnd\(',
            r'performance\.now\(\)',
            r'System\.currentTimeMillis\(\).*print',
            r'time\.time\(\).*print',
        ],
        'description': 'Debug/test code remnants - should be removed before production',
        'severity': 'low'
    }
}

# File extensions to analyze
SUPPORTED_EXTENSIONS = {
    '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cs', '.vb', '.fs', 
    '.go', '.php', '.rb', '.sh', '.bash', '.zsh', '.yml', '.yaml', 
    '.json', '.xml', '.config', '.properties', '.env', '.dockerfile',
    '.tf', '.tfvars'
}

# Files that commonly contain debug configurations
DEBUG_CONFIG_FILES = {
    'docker-compose.yml', 'docker-compose.yaml', 'dockerfile', 'makefile',
    'package.json', 'webpack.config.js', 'gulpfile.js', 'gruntfile.js',
    'ansible.cfg', 'playbook.yml', 'playbook.yaml', '.env', '.env.local',
    'appsettings.json', 'appsettings.development.json', 'web.config',
    'application.properties', 'application.yml', 'logback.xml', 'log4j.xml'
}

# Safe contexts where verbose flags might be acceptable
SAFE_CONTEXTS = [
    r'test.*', r'.*test.*', r'spec.*', r'.*spec.*', r'mock.*', r'.*mock.*',
    r'example.*', r'.*example.*', r'sample.*', r'.*sample.*', r'demo.*',
    r'debug.*', r'.*debug.*', r'dev.*', r'.*dev.*', r'development.*',
    r'local.*', r'.*local.*'
]


def is_safe_context(file_path: str) -> bool:
    """Check if file is in a safe context where debug flags might be acceptable."""
    path_lower = file_path.lower()
    return any(re.match(pattern, path_lower) for pattern in SAFE_CONTEXTS)


def should_check_file(file_path: str) -> bool:
    """Determine if file should be checked for verbose flags."""
    path = Path(file_path)
    
    # Check file extension
    if path.suffix.lower() in SUPPORTED_EXTENSIONS:
        return True
    
    # Check specific filenames
    if path.name.lower() in DEBUG_CONFIG_FILES:
        return True
    
    return False


def check_verbose_flags(file_path: str) -> List[Tuple[int, str, str, str]]:
    """Check for verbose flags and debug logging in a file."""
    issues = []
    
    if not should_check_file(file_path):
        return issues
    
    # Be more lenient with files in safe contexts
    in_safe_context = is_safe_context(file_path)
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            lines = content.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            stripped_line = line.strip()
            if not stripped_line or stripped_line.startswith('#'):
                continue
            
            # Check each pattern type
            for pattern_name, pattern_info in VERBOSE_PATTERNS.items():
                for pattern in pattern_info['patterns']:
                    if re.search(pattern, line, re.IGNORECASE):
                        # In safe contexts, only flag high severity issues
                        if in_safe_context and pattern_info['severity'] == 'low':
                            continue
                        
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
    if pattern_name in VERBOSE_PATTERNS:
        severity = VERBOSE_PATTERNS[pattern_name]['severity']
    else:
        severity = 'medium'
    
    return {
        'high': '🚨',
        'medium': '⚠️',
        'low': '💡'
    }.get(severity, '⚠️')


def main():
    parser = argparse.ArgumentParser(description='Detect verbose flags and debug logging')
    parser.add_argument('files', nargs='*', help='Files to check')
    parser.add_argument('--severity', choices=['low', 'medium', 'high'],
                        help='Minimum severity level to report')
    parser.add_argument('--json', action='store_true',
                        help='Output results in JSON format')
    parser.add_argument('--exclude-safe-contexts', action='store_true',
                        help='Exclude files in safe contexts (test, dev, example directories)')
    args = parser.parse_args()
    
    exit_code = 0
    total_issues = 0
    all_results = {}
    
    severity_levels = {'low': 1, 'medium': 2, 'high': 3}
    min_severity = severity_levels.get(args.severity, 1) if args.severity else 1
    
    for file_path in args.files:
        # Skip safe contexts if requested
        if args.exclude_safe_contexts and is_safe_context(file_path):
            continue
        
        issues = check_verbose_flags(file_path)
        
        # Filter by severity if specified
        if args.severity:
            filtered_issues = []
            for line_num, line_content, pattern_name, description in issues:
                if pattern_name in VERBOSE_PATTERNS:
                    pattern_severity = VERBOSE_PATTERNS[pattern_name]['severity']
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
                print(f"\n🔍 Verbose flags detected in {file_path}:")
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
        print(f"\n❌ Found {total_issues} verbose flag(s) or debug configuration(s)")
        print("💡 Remove debug/verbose flags before production deployment")
        print("💡 Use environment variables or configuration files for debug settings")
        print("💡 Consider using logging levels instead of hardcoded debug flags")
    else:
        print("✅ No problematic verbose flags detected")
    
    return exit_code


if __name__ == '__main__':
    sys.exit(main())

