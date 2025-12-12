# Configuration Guide: Handling False Positives

This guide helps you configure the pre-commit hooks to minimize false positives while maintaining security.

## Quick Start: Practical Configuration

Use the `examples/practical-security.yaml` configuration for a balanced approach that reduces false positives.

## AI-Powered Commit Validation

### ai_commit_check Configuration

The `ai_commit_check` hook intelligently adapts to two modes:
- **Pre-commit mode**: Reviews staged changes before committing
- **Pre-push mode**: Reviews all branch changes compared to `origin/main` or `origin/master`

**Problem**: AI validation may be too slow for every commit, or you want comprehensive branch review before pushing

**Solution**: Choose the stage that fits your workflow

#### Configuration Options

**Option 1: Manual pre-commit (recommended for frequent commits)**
```yaml
repos:
  - repo: https://github.com/TriaFed/pre-commit-library
    rev: v1.1.7
    hooks:
      - id: ai_commit_check
        stages: [manual]  # Default: disabled, opt-in required
```

**Note:** The hook is **disabled by default**. This is the default behavior - users must explicitly opt-in.

Run with: `pre-commit run --hook-stage manual ai_commit_check`

**Option 2: Automatic pre-push (recommended for comprehensive review)**
```yaml
repos:
  - repo: https://github.com/TriaFed/pre-commit-library
    rev: <version>  # Replace with latest release version
    hooks:
      - id: ai_commit_check
        stages: [pre-push]
```

**IMPORTANT**: For pre-push mode, install the pre-push hooks:
```bash
pre-commit install --hook-type pre-push
```

This runs automatically on `git push` and reviews all changes in your branch.

#### Required Setup

**Required: Security Configuration File:**

The AI commit check hook **requires** an `opencode.jsonc` configuration file in your repository root to enforce security policies.

**Setup:**

1. Copy the contents of [`examples/opencode.jsonc`](https://github.com/TriaFed/pre-commit-library/blob/main/examples/opencode.jsonc) from this repository
2. Create a file named `opencode.jsonc` in your repository root
3. Paste the contents into your `opencode.jsonc` file
4. Commit the configuration to your repository

**What's included:**
- Share disabled
- Auto-updates disabled  
- Only GitHub Copilot and Amazon Bedrock allowed
- All other AI providers blocked
- Dangerous operations denied (webfetch, cloud CLIs, curl, wget, terraform)

**Runtime Output:**

The hook displays:
```
✓ Using opencode.jsonc from repository root
```

If the file is missing, the hook will exit with an error and instructions on how to set it up.

#### Environment Variables

```bash
export OPENCODE_PORT=61164              # Port for opencode server (default: 61164)
export OPENCODE_MODEL=github-copilot/claude-sonnet-4.5 # AI model to use (default)
export OPENCODE_PROVIDER=github-copilot # Provider: github-copilot, amazon-bedrock (default: github-copilot)
export OPENCODE_TIMEOUT=90              # Timeout in seconds (default: 90)
export OPENCODE_BEDROCK_REGION=us-east-1 # Required for amazon-bedrock provider
```

#### Permissions and Custom Instructions

The required `opencode.jsonc` includes safe defaults that deny dangerous operations.

**To customize permissions**: See [OpenCode Permissions Documentation](https://opencode.ai/docs/permissions/)

**To add custom AI instructions**:
```bash
# Start opencode and use the /init command
opencode
# Then type: /init
```

This creates instruction files with project-specific coding standards that the AI will follow during reviews.

#### Usage

| Mode | Command |
|------|---------|
| Manual pre-commit | `pre-commit run --hook-stage manual ai_commit_check` |
| Pre-push (automatic) | `git push` (runs automatically) |
| Pre-push (manual) | `pre-commit run --hook-stage pre-push ai_commit_check` |
| Skip validation | `git commit --no-verify` or `git push --no-verify` |

#### Amazon Bedrock Provider

**Problem**: Need to use Amazon Bedrock instead of GitHub Copilot

**Solution**: Configure Bedrock with required region validation

```yaml
repos:
  - repo: https://github.com/TriaFed/pre-commit-library
    rev: v1.2.0
    hooks:
      - id: ai_commit_check
        stages: [manual]
```

**Set environment variables:**
```bash
export OPENCODE_PROVIDER=amazon-bedrock
export OPENCODE_MODEL=amazon-bedrock/anthropic.claude-sonnet-4-5-20250929-v1:0
export OPENCODE_BEDROCK_REGION=us-east-1
```

**Required AWS Setup:**
```bash
# 1. Configure AWS region (required)
aws configure set region us-east-1

# 2. Verify AWS credentials
aws sts get-caller-identity

# 3. Authenticate with OpenCode
opencode auth login  # Select: Amazon Bedrock

# 4. Test the connection
opencode run "hello world"
```

**Allowed Regions**: `us-east-1`, `us-gov-west-1`, `us-gov-east-1`

**Security Note**: Region validation is enforced for compliance. The hook will exit with an error if an unauthorized region is specified.

**Example Usage:**
```bash
# Set environment for the session
export OPENCODE_PROVIDER=amazon-bedrock
export OPENCODE_BEDROCK_REGION=us-east-1

# Run the AI commit check
pre-commit run --hook-stage manual ai_commit_check
```

**Troubleshooting:**

If you see:
```
Error: Amazon Bedrock region 'eu-west-1' is not allowed.
```

Fix with:
```bash
export OPENCODE_BEDROCK_REGION=us-east-1
aws configure set region us-east-1
```

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
query += ' and cp.CYCLE = :cycle'; // This is actually safe (parameterized)
```

**Solution**: Use inline comments to exclude:

```javascript
query += ' and cp.CYCLE = :cycle'; // genai:ignore - parameterized query
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
  args: ['--severity', 'medium'] # Only report medium/high issues
```

### 3. npm-audit Issues

**Problem**: Fails on any vulnerability, even low-severity ones

**Solution**: Configure audit level

```yaml
- id: npm-audit
  env:
    NPM_AUDIT_LEVEL: high # Only fail on high/critical vulnerabilities
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
    rev: v1.2.0
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
  args: ['--severity', 'high'] # Only critical issues
- id: npm-audit
  env:
    NPM_AUDIT_LEVEL: critical
```

### CI/Production Environment (Strict)

```yaml
- id: genai-security-check
  args: ['--severity', 'low'] # All issues
- id: npm-audit
  env:
    NPM_AUDIT_LEVEL: moderate
```

## Troubleshooting Specific Patterns

### SQL Injection False Positives

If you're getting SQL injection warnings on safe parameterized queries:

```javascript
// Add genai:ignore comment:
query += ' WHERE id = :userId'; // genai:ignore - parameterized query

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
console.error('Login failed:', user.password); // Don't do this!
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
    rev: v1.2.0
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
