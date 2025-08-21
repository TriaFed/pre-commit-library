#!/usr/bin/env python3
"""
Ansible-specific security scanning for common vulnerabilities and misconfigurations.
Focuses on security best practices for Ansible playbooks, roles, and configurations.
"""

import re
import sys
import argparse
import json
import yaml
from typing import List, Tuple, Dict, Any
from pathlib import Path

# Ansible-specific security patterns
ANSIBLE_SECURITY_PATTERNS = {
    'hardcoded_secrets': {
        'patterns': [
            r'password:\s*["\']?[^"\'\s]{8,}["\']?\s*$',
            r'secret:\s*["\']?[^"\'\s]{8,}["\']?\s*$',
            r'api_key:\s*["\']?[^"\'\s]{10,}["\']?\s*$',
            r'private_key:\s*["\']?-----BEGIN',
            r'token:\s*["\']?[^"\'\s]{10,}["\']?\s*$',
        ],
        'description': 'Hardcoded secrets detected - use ansible-vault or variables',
        'severity': 'high'
    },
    'unencrypted_vars': {
        'patterns': [
            r'vars:\s*\n.*password:',
            r'vars:\s*\n.*secret:',
            r'group_vars.*password',
            r'host_vars.*password',
        ],
        'description': 'Unencrypted sensitive variables - consider ansible-vault',
        'severity': 'medium'
    },
    'shell_injection': {
        'patterns': [
            r'shell:\s*.*\{\{.*\}\}.*',
            r'command:\s*.*\{\{.*\}\}.*',
            r'raw:\s*.*\{\{.*\}\}.*',
            r'shell:.*\|.*unsafe',
        ],
        'description': 'Potential shell injection through templating',
        'severity': 'high'
    },
    'file_permissions': {
        'patterns': [
            r'mode:\s*["\']?777["\']?',
            r'mode:\s*["\']?666["\']?',
            r'mode:\s*["\']?o\+w["\']?',
            r'mode:\s*["\']?a\+w["\']?',
        ],
        'description': 'Overly permissive file permissions',
        'severity': 'medium'
    },
    'http_usage': {
        'patterns': [
            r'url:\s*http://(?!localhost|127\.0\.0\.1|example\.)',
            r'src:\s*http://(?!localhost|127\.0\.0\.1|example\.)',
            r'repo:\s*http://(?!localhost|127\.0\.0\.1|example\.)',
        ],
        'description': 'HTTP usage instead of HTTPS for external resources',
        'severity': 'medium'
    },
    'sudo_without_validate': {
        'patterns': [
            r'become:\s*yes(?!.*validate)',
            r'become_user:\s*root(?!.*validate)',
            r'sudo:.*NOPASSWD:ALL',
        ],
        'description': 'Sudo usage without validation or with NOPASSWD',
        'severity': 'medium'
    },
    'debug_exposure': {
        'patterns': [
            r'debug:\s*yes',
            r'debug:\s*true',
            r'verbosity:\s*[3-9]',
            r'-vvv',
        ],
        'description': 'Debug mode enabled - may expose sensitive information',
        'severity': 'low'
    },
    'weak_crypto': {
        'patterns': [
            r'algorithm:\s*md5',
            r'algorithm:\s*sha1',
            r'checksum_algorithm:\s*md5',
            r'checksum_algorithm:\s*sha1',
        ],
        'description': 'Weak cryptographic algorithm usage',
        'severity': 'medium'
    },
    'unsafe_privileges': {
        'patterns': [
            r'become_flags:.*-n',
            r'become_flags:.*--non-interactive',
            r'privilege_escalation:.*unsafe',
        ],
        'description': 'Unsafe privilege escalation configuration',
        'severity': 'high'
    },
    'inventory_exposure': {
        'patterns': [
            r'ansible_ssh_pass:\s*[^{]',
            r'ansible_become_pass:\s*[^{]',
            r'ansible_password:\s*[^{]',
        ],
        'description': 'Passwords in inventory files - use vault or ssh keys',
        'severity': 'high'
    },
    'template_injection': {
        'patterns': [
            r'template:.*\{\{.*\|.*safe.*\}\}',
            r'template:.*\{\{.*\|.*raw.*\}\}',
            r'lineinfile:.*\{\{.*\|.*unsafe.*\}\}',
        ],
        'description': 'Unsafe template filters that disable auto-escaping',
        'severity': 'high'
    }
}

# File patterns to analyze
ANSIBLE_FILE_PATTERNS = {
    'playbooks': ['.yml', '.yaml'],
    'inventory': ['hosts', 'inventory'],
    'vars': ['group_vars', 'host_vars'],
    'roles': ['tasks', 'handlers', 'vars', 'defaults'],
    'config': ['ansible.cfg']
}

# YAML keys that indicate Ansible content
ANSIBLE_INDICATORS = [
    'hosts', 'tasks', 'handlers', 'vars', 'roles', 'plays',
    'become', 'gather_facts', 'connection', 'ansible_'
]


def is_ansible_file(file_path: str) -> bool:
    """Determine if file is an Ansible-related file."""
    path = Path(file_path)
    
    # Check file extensions
    if path.suffix.lower() in ['.yml', '.yaml']:
        return True
    
    # Check specific filenames
    if path.name.lower() in ['ansible.cfg', 'hosts', 'inventory', 'site.yml', 'site.yaml']:
        return True
    
    # Check if in Ansible directories
    path_parts = [p.lower() for p in path.parts]
    ansible_dirs = ['group_vars', 'host_vars', 'roles', 'playbooks', 'inventories']
    if any(ansible_dir in path_parts for ansible_dir in ansible_dirs):
        return True
    
    return False


def analyze_yaml_content(content: str) -> bool:
    """Check if YAML content appears to be Ansible-related."""
    try:
        # Try to parse as YAML
        data = yaml.safe_load(content)
        if not data:
            return False
        
        # Convert to string for pattern matching
        content_str = str(data).lower()
        
        # Check for Ansible indicators
        return any(indicator in content_str for indicator in ANSIBLE_INDICATORS)
    
    except yaml.YAMLError:
        # If it's not valid YAML, check content as text
        content_lower = content.lower()
        return any(indicator in content_lower for indicator in ANSIBLE_INDICATORS)


def check_vault_encryption(file_path: str, content: str) -> List[Tuple[int, str, str, str]]:
    """Check for files that should be encrypted with ansible-vault."""
    issues = []
    
    # Files that commonly contain secrets
    sensitive_files = ['vault', 'secret', 'password', 'credential', 'key']
    
    if any(sensitive in Path(file_path).name.lower() for sensitive in sensitive_files):
        if not content.startswith('$ANSIBLE_VAULT'):
            issues.append((
                1,
                "File appears to contain secrets but is not vault-encrypted",
                'unencrypted_vault',
                'File should be encrypted with ansible-vault'
            ))
    
    return issues


def check_ansible_security(file_path: str) -> List[Tuple[int, str, str, str]]:
    """Check for Ansible-specific security patterns."""
    issues = []
    
    if not is_ansible_file(file_path):
        return issues
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            lines = content.split('\n')
        
        # Skip if not actually Ansible content (for .yml/.yaml files)
        if file_path.endswith(('.yml', '.yaml')):
            if not analyze_yaml_content(content):
                return issues
        
        # Check for vault encryption
        issues.extend(check_vault_encryption(file_path, content))
        
        # Pattern-based analysis
        for line_num, line in enumerate(lines, 1):
            if not line.strip() or line.strip().startswith('#'):
                continue
            
            # Check security patterns
            for pattern_name, pattern_info in ANSIBLE_SECURITY_PATTERNS.items():
                for pattern in pattern_info['patterns']:
                    if re.search(pattern, line, re.IGNORECASE):
                        issues.append((
                            line_num,
                            line.strip(),
                            pattern_name,
                            pattern_info['description']
                        ))
        
        # Additional YAML-specific checks
        if file_path.endswith(('.yml', '.yaml')):
            try:
                data = yaml.safe_load(content)
                if data:
                    yaml_issues = analyze_yaml_structure(data, file_path)
                    issues.extend(yaml_issues)
            except yaml.YAMLError:
                pass
    
    except Exception as e:
        print(f"Error analyzing {file_path}: {e}", file=sys.stderr)
    
    return issues


def analyze_yaml_structure(data: Any, file_path: str) -> List[Tuple[int, str, str, str]]:
    """Analyze YAML structure for security issues."""
    issues = []
    
    # This is a simplified analysis - in practice, you'd want more sophisticated
    # traversal of the YAML structure
    if isinstance(data, dict):
        # Check for no_log usage with sensitive tasks
        if 'tasks' in data:
            for i, task in enumerate(data['tasks']):
                if isinstance(task, dict):
                    # Check for tasks that should use no_log
                    sensitive_modules = ['user', 'mysql_user', 'postgresql_user', 'uri', 'get_url']
                    if any(module in task for module in sensitive_modules):
                        if not task.get('no_log', False):
                            issues.append((
                                i + 1,
                                f"Task with {[m for m in sensitive_modules if m in task]} should use no_log",
                                'missing_no_log',
                                'Sensitive task should use no_log to prevent credential exposure'
                            ))
    
    return issues


def get_severity_emoji(pattern_name: str) -> str:
    """Get emoji based on severity."""
    if pattern_name in ANSIBLE_SECURITY_PATTERNS:
        severity = ANSIBLE_SECURITY_PATTERNS[pattern_name]['severity']
    else:
        severity = 'medium'
    
    return {
        'high': '🚨',
        'medium': '⚠️',
        'low': '💡'
    }.get(severity, '⚠️')


def main():
    parser = argparse.ArgumentParser(description='Ansible security validation')
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
        issues = check_ansible_security(file_path)
        
        # Filter by severity if specified
        if args.severity:
            filtered_issues = []
            for line_num, line_content, pattern_name, description in issues:
                if pattern_name in ANSIBLE_SECURITY_PATTERNS:
                    pattern_severity = ANSIBLE_SECURITY_PATTERNS[pattern_name]['severity']
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
                print(f"\n📋 Ansible security issues found in {file_path}:")
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
        print(f"\n❌ Found {total_issues} potential Ansible security issue(s)")
        print("💡 Review Ansible playbooks and configurations for security vulnerabilities")
        print("💡 Consider using ansible-vault for sensitive data")
        print("💡 Follow Ansible security best practices: https://docs.ansible.com/ansible/latest/user_guide/playbooks_best_practices.html")
    else:
        print("✅ No Ansible security issues detected")
    
    return exit_code


if __name__ == '__main__':
    sys.exit(main())
