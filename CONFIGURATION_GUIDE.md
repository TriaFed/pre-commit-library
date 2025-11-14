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

**Solution**: Configure for pre-commit (manual/automatic) or pre-push stages

#### Mode Selection

The hook automatically determines which mode to use:
1. **Pre-commit mode**: If staged changes exist (`git diff --cached`), reviews only those changes
2. **Pre-push mode**: If no staged changes, assumes pre-push and compares current branch to `origin/main` or `origin/master`

#### Configuration Options

**Option 1: Manual pre-commit (recommended for frequent commits)**
```yaml
repos:
  - repo: https://github.com/TriaFed/pre-commit-library
    rev: v1.1.7
    hooks:
      - id: ai_commit_check
        stages: [manual]
```

Run with: `pre-commit run --hook-stage manual ai_commit_check`

**Option 2: Automatic pre-push (recommended for comprehensive review)**
```yaml
repos:
  - repo: https://github.com/MattDonnellySoftrams/pre-commit-library
    rev: 5be00901f2e761de24f46ce97bc8566703e9ee49
    hooks:
      - id: ai_commit_check
        stages:
          - pre-push
```

**IMPORTANT**: For pre-push mode, you must install the pre-push hooks:
```bash
pre-commit install --hook-type pre-push
```

This runs automatically on `git push` and reviews all changes in your branch.

**Option 3: Both modes**
```yaml
repos:
  - repo: https://github.com/TriaFed/pre-commit-library
    rev: v1.1.7
    hooks:
      - id: ai_commit_check
        stages: [pre-commit, pre-push]
```

Install both hook types:
```bash
pre-commit install              # For pre-commit
pre-commit install --hook-type pre-push  # For pre-push
```

#### Required Setup

**⚠️ Security Requirement:** You must create an `opencode.jsonc` file in your repository root before using this hook.

```bash
# Download the recommended configuration
curl -o opencode.jsonc https://raw.githubusercontent.com/TriaFed/pre-commit-library/main/examples/opencode.jsonc

# Or create minimal security config
cat > opencode.jsonc <<EOF
{
  "\$schema": "https://opencode.ai/config.json",
  "permission": {
    "webfetch": "deny",
    "bash": {
      "aws *": "deny",
      "az *": "deny",
      "gcloud *": "deny",
      "terraform *": "deny",
      "curl *": "deny",
      "wget *": "deny"
    }
  }
}
EOF

# Commit the config file
git add opencode.jsonc
git commit -m "Add opencode security configuration"
```

The hook will fail if `opencode.jsonc` is not present to ensure safe operation.

#### Environment Variables

```bash
# Set in your shell profile or CI/CD
export OPENCODE_PORT=61164              # Port for opencode server
export OPENCODE_MODEL=claude-sonnet-4.5 # Model selection
export OPENCODE_PROVIDER=github-copilot # Provider (github-copilot, anthropic, etc.)
export OPENCODE_TIMEOUT=90              # Timeout in seconds
```

#### Permissions Configuration

The recommended `opencode.jsonc` includes safe defaults. Customize as needed:

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "permission": {
    "edit": "allow",      // Allow AI to suggest/apply fixes
    "bash": {
      "*": "deny",        // Deny all by default (REQUIRED)
      "git status": "allow",
      "git diff": "allow",
      "npm run test": "ask",
      "aws *": "deny",    // REQUIRED: Block AWS commands
      "az *": "deny",     // REQUIRED: Block Azure CLI
      "gcloud *": "deny", // REQUIRED: Block Google Cloud CLI
      "terraform *": "deny", // REQUIRED: Block Terraform
      "curl *": "deny",   // REQUIRED: Block curl
      "wget *": "deny"    // REQUIRED: Block wget
    },
    "webfetch": "deny"    // REQUIRED: Block external requests
  }
}
```

Available permission levels:
- `"allow"` - Execute without approval
- `"ask"` - Prompt for approval before execution
- `"deny"` - Disable the tool entirely

Learn more: [OpenCode Permissions Documentation](https://opencode.ai/docs/permissions/)

#### Custom Instructions

Create instruction files for project-specific AI context:

**Option 1: Use `/init` command (Recommended)**
```bash
# Start opencode
opencode

# Then in the opencode window, type:
/init
```
This generates default AI instruction files for your project.

**Option 2: Create custom instruction files manually**
```markdown
# AGENTS.md - Your project-specific guidelines

## Project Standards
- Follow TypeScript strict mode
- Use React hooks best practices
- All functions must have JSDoc comments

## Security Rules
- No hardcoded credentials
- All API calls need error handling
```

Reference instruction files in `opencode.jsonc`:

```jsonc
{
  "instruction": ["AGENTS.md", "CLAUDE.md", "docs/CODING_STANDARDS.md"]
}
```

**Usage in .pre-commit-config.yaml:**
```yaml
# Manual pre-commit mode
- id: ai_commit_check
  stages: [manual]

# Automatic pre-push mode
- id: ai_commit_check
  stages: [pre-push]
```

**Running the hook:**
```bash
# Manual pre-commit
pre-commit run --hook-stage manual ai_commit_check

# Pre-push (runs automatically on git push)
git push

# Or run pre-push manually
pre-commit run --hook-stage pre-push ai_commit_check
```

Or skip for urgent commits:
```bash
# Skip AI validation for urgent commits
git commit --no-verify -m "Quick fix"

# Skip pre-push validation
git push --no-verify
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
