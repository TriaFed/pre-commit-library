# Configuration Guide: Handling False Positives

This guide helps you configure the pre-commit hooks to minimize false positives while maintaining security.

## Quick Start: Practical Configuration

Use the `examples/practical-security.yaml` configuration for a balanced approach that reduces false positives.

## Common False Positive Issues and Solutions

### 1. detect-secrets and hardcoded-credentials

**Problem**: Flags development passwords and test credentials
```bash
# Example false positive
ERROR: Potential secrets about to be committed to git repo!
Secret Type: Secret Keyword
Location: scripts/db-setup.sh:8
```

**Solutions**:

#### Option A: Create a secrets baseline (Recommended)
```bash
# Create baseline file to exclude known false positives
detect-secrets scan --baseline .secrets.baseline
```

Then add to your `.pre-commit-config.yaml`:
```yaml
- id: detect-secrets
  args: ['--baseline', '.secrets.baseline']
```

#### Option B: Use inline comments

Add suppression comments directly in your code for false positives:

```python
# Python example
DB_PASSWORD = "local_dev_password"  # pragma: allowlist secret
api_config = {
    "key": "AppStorageKey"  # pragma: allowlist secret
}
```

```javascript
// JavaScript/TypeScript example
const DB_PASSWORD = 'local_dev_password'; // pragma: allowlist secret
persistState(store, {
  key: 'UserPreferences', // pragma: allowlist secret
});
```

```java
// Java example
String key = "ConfigKey";  // pragma: allowlist secret
```

**Supported suppression formats:**
- `pragma: allowlist secret` - Compatible with detect-secrets & hardcoded-credentials 

These comments work for both `detect-secrets` and `hardcoded-credentials` hooks.

#### Option C: Exclude patterns
```yaml
- id: hardcoded-credentials
  args: ['--exclude-patterns', 'test,example,demo,local,docker,dev']
```

### 2. genai-security-check Issues

**Problem 1**: Flags relative imports as path traversal
```javascript
// False positive:
import { Model } from '../models/model.js';
```

**Solution**: The updated genai-security-check now excludes import statements automatically.

**Problem 2**: Flags parameterized SQL queries
```javascript
// False positive:
query += ' and cp.CYCLE = :cycle';  // This is actually safe (parameterized)
```

**Solution**: Use inline comments to exclude:
```javascript
query += ' and cp.CYCLE = :cycle';  // genai:ignore - parameterized query
```

**Problem 3**: Flags all console.error statements
```javascript
// False positive:
console.error('Error creating email:', emailInput.status);
```

**Solution**: The updated version only flags console.error with sensitive data patterns.

#### Configure severity levels:
```yaml
- id: genai-security-check
  args: ['--severity', 'medium']  # Only report medium/high issues
```

### 3. npm-audit Issues

**Problem**: Fails on any vulnerability, even low-severity ones

**Solution**: Configure audit level
```yaml
- id: npm-audit
  env:
    NPM_AUDIT_LEVEL: high  # Only fail on high/critical vulnerabilities
```

Available levels:
- `low`: All vulnerabilities (very strict)
- `moderate`: Moderate and above (previous default)
- `high`: High and critical only (default, recommended)
- `critical`: Only critical vulnerabilities

### 4. File-specific Exclusions

Exclude entire files or directories:

```yaml
repos:
  - repo: https://github.com/TriaFed/pre-commit-library
    rev: v1.1.7
    hooks:
      - id: genai-security-check
        exclude: '^(tests/|spec/|__tests__/|\.test\.|\.spec\.)'
      - id: detect-secrets
        exclude: '^(docker/|scripts/setup/|migrations/)'
```

### 5. Safe Context Detection

The hooks automatically detect safe contexts and are more lenient in:
- Test files (`test`, `spec`, `__tests__`)
- Development files (`dev`, `development`, `local`)
- Setup files (`setup`, `migration`, `seed`)
- Docker files (`docker`, `compose`)

## Environment-Specific Configuration

### Development Environment (Lenient)
```yaml
- id: genai-security-check
  args: ['--severity', 'high']  # Only critical issues
- id: npm-audit
  env:
    NPM_AUDIT_LEVEL: critical
```

### CI/Production Environment (Strict)
```yaml
- id: genai-security-check
  args: ['--severity', 'low']   # All issues
- id: npm-audit
  env:
    NPM_AUDIT_LEVEL: moderate
```

## Troubleshooting Specific Patterns

### SQL Injection False Positives
If you're getting SQL injection warnings on safe parameterized queries:

```javascript
// Add genai:ignore comment:
query += ' WHERE id = :userId';  // genai:ignore - parameterized query

// Or use this pattern (automatically excluded):
const query = 'SELECT * FROM users WHERE id = $1';
```

### Path Traversal False Positives
For legitimate relative imports:

```javascript
// These are now automatically excluded:
import { utils } from '../utils/helper.js';
const config = require('../../config/database.js');
```

### Information Disclosure False Positives
For legitimate error logging:

```javascript
// This will NOT be flagged (no sensitive keywords):
console.error('Error creating email:', error.message);

// This WILL be flagged (contains 'password'):
console.error('Login failed:', user.password);  // Don't do this!
```

## Best Practices

1. **Start with practical-security.yaml**: Use the practical configuration as a starting point
2. **Create baselines**: Use detect-secrets baseline for known false positives
3. **Use inline comments**: Add `genai:ignore` comments for legitimate exceptions
4. **Configure severity levels**: Start with medium/high severity, adjust as needed
5. **Exclude test files**: Most security rules should be relaxed in test contexts
6. **Regular reviews**: Periodically review your exclusions to ensure they're still valid

## Example: Complete Practical Configuration

```yaml
repos:
  - repo: https://github.com/TriaFed/pre-commit-library
    rev: v1.1.7
    hooks:
      # Security with baselines and exclusions
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']
      - id: hardcoded-credentials
        args: ['--exclude-patterns', 'test,demo,local,docker']
        exclude: '^(tests/|scripts/dev/)'
      - id: genai-security-check
        args: ['--severity', 'medium']
        exclude: '^(tests/|spec/|__tests__/)'
      
      # Vulnerability scanning with reasonable thresholds
      - id: npm-audit
        env:
          NPM_AUDIT_LEVEL: high
      
      # Code quality (optional)
      - id: eslint
        args: ['--fix']
        files: '\.(js|ts|jsx|tsx)$'

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: check-yaml
        exclude: '^docker-compose'
      - id: check-json
      - id: trailing-whitespace
        types: [python, javascript, typescript]
      - id: end-of-file-fixer
        types: [python, javascript, typescript]
```

This configuration provides strong security while minimizing false positives for real-world development workflows.
