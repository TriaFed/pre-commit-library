#!/bin/bash
# Ansible linting using ansible-lint

set -e

# Function to check if Python is available
check_python() {
    if command -v python3 >/dev/null 2>&1; then
        return 0
    elif command -v python >/dev/null 2>&1; then
        return 0
    fi
    
    echo "❌ Python not found. Please install Python 3.6+ for ansible-lint"
    return 1
}

# Function to check if ansible-lint is available
check_ansible_lint() {
    if command -v ansible-lint >/dev/null 2>&1; then
        return 0
    fi
    
    echo "❌ ansible-lint not found. Please install it:"
    echo "  # Using pip:"
    echo "  pip install ansible-lint"
    echo "  # or"
    echo "  pip3 install ansible-lint"
    echo ""
    echo "  # Using Homebrew (macOS):"
    echo "  brew install ansible-lint"
    echo ""
    echo "  # Using pipx (recommended):"
    echo "  pipx install ansible-lint"
    return 1
}

# Function to check if Ansible is available
check_ansible() {
    if command -v ansible >/dev/null 2>&1; then
        return 0
    fi
    
    echo "⚠️  Ansible not found. Some features may be limited."
    echo "  # Install Ansible:"
    echo "  pip install ansible"
    echo "  # or"
    echo "  brew install ansible"
    return 1
}

# Check dependencies
if ! check_python; then
    exit 1
fi

if ! check_ansible_lint; then
    exit 1
fi

# Check for Ansible (optional but recommended)
check_ansible || true

# Find Ansible files
ansible_files=""

# Look for playbooks (*.yml, *.yaml in typical locations)
for pattern in "*.yml" "*.yaml" "playbook*.yml" "playbook*.yaml" "site.yml" "site.yaml"; do
    found_files=$(find . -name "$pattern" -not -path "./venv/*" -not -path "./.git/*" -not -path "./node_modules/*" 2>/dev/null || true)
    if [ -n "$found_files" ]; then
        ansible_files="$ansible_files $found_files"
    fi
done

# Look for Ansible directories and files
for dir in "playbooks" "roles" "group_vars" "host_vars" "inventories"; do
    if [ -d "$dir" ]; then
        found_files=$(find "$dir" -name "*.yml" -o -name "*.yaml" 2>/dev/null || true)
        if [ -n "$found_files" ]; then
            ansible_files="$ansible_files $found_files"
        fi
    fi
done

# Look for ansible.cfg or requirements files
for file in "ansible.cfg" "requirements.yml" "requirements.yaml" "galaxy.yml"; do
    if [ -f "$file" ]; then
        ansible_files="$ansible_files $file"
    fi
done

# Remove duplicates and clean up
ansible_files=$(echo $ansible_files | tr ' ' '\n' | sort -u | tr '\n' ' ')

if [ -z "$ansible_files" ]; then
    echo "ℹ️  No Ansible files found"
    exit 0
fi

echo "🔍 Running ansible-lint..."

# Create basic ansible-lint config if none exists
create_ansible_lint_config() {
    if [ ! -f .ansible-lint ] && [ ! -f .ansible-lint.yml ] && [ ! -f .ansible-lint.yaml ]; then
        echo "⚠️  No ansible-lint configuration found. Creating basic .ansible-lint..."
        cat > .ansible-lint << 'EOF'
---
# ansible-lint configuration

# List of additional kind:pattern to be added at the top of the default
# match list, first match determines the file kind.
kinds:
  - yaml: "*.yaml-too"

# Exclude certain rules
skip_list:
  - yaml[line-length]  # Allow longer lines in YAML
  - name[casing]       # Allow different naming conventions

# Enable progressive mode (less strict for existing projects)
progressive: false

# Offline mode (don't download external requirements)
offline: true

# Use rules from specific tags
# tags:
#   - security
#   - formatting

# Exclude certain paths
exclude_paths:
  - .cache/
  - .github/
  - .gitlab-ci.yml
  - .travis.yml
  - molecule/
  - venv/
  - node_modules/

# Set warning behavior
warn_list:
  - yaml[comments]
  - yaml[line-length]
  - name[template]
  - risky-file-permissions

# Treat these as errors
# enable_list:
#   - no-changed-when
#   - no-handler
EOF
    fi
}

# Create basic config if none exists
create_ansible_lint_config

# Run ansible-lint
echo "📋 Checking files: $(echo $ansible_files | wc -w) Ansible files found"

# Run with different options based on what's available
if ansible-lint --version | grep -q "6\|7"; then
    # ansible-lint v6/v7
    if ansible-lint $ansible_files; then
        echo "✅ ansible-lint passed"
        exit 0
    else
        echo "❌ ansible-lint found issues"
        echo ""
        echo "💡 To see only errors (ignore warnings):"
        echo "  ansible-lint --severity-threshold error"
        echo ""
        echo "💡 To see detailed output:"
        echo "  ansible-lint --verbose"
        echo ""
        echo "💡 To auto-fix some issues:"
        echo "  ansible-lint --write"
        exit 1
    fi
else
    # Older versions of ansible-lint
    if ansible-lint -v $ansible_files; then
        echo "✅ ansible-lint passed"
        exit 0
    else
        echo "❌ ansible-lint found issues"
        echo ""
        echo "💡 To see parseable output:"
        echo "  ansible-lint -p"
        echo ""
        echo "💡 To exclude specific rules:"
        echo "  ansible-lint -x RULE_ID"
        exit 1
    fi
fi
