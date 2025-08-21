#!/bin/bash
# Ansible syntax validation using ansible-playbook --syntax-check

set -e

# Function to check if Ansible is available
check_ansible() {
    if command -v ansible-playbook >/dev/null 2>&1; then
        return 0
    fi
    
    echo "❌ Ansible not found. Please install it:"
    echo "  # Using pip:"
    echo "  pip install ansible"
    echo "  # or"
    echo "  pip3 install ansible"
    echo ""
    echo "  # Using Homebrew (macOS):"
    echo "  brew install ansible"
    echo ""
    echo "  # Using system package manager:"
    echo "  # Ubuntu: apt-get install ansible"
    echo "  # CentOS/RHEL: yum install ansible"
    return 1
}

# Check if Ansible is available
if ! check_ansible; then
    exit 1
fi

# Find Ansible playbook files
playbook_files=""

# Look for obvious playbooks
for pattern in "playbook*.yml" "playbook*.yaml" "site.yml" "site.yaml" "*playbook.yml" "*playbook.yaml"; do
    found_files=$(find . -name "$pattern" -not -path "./venv/*" -not -path "./.git/*" -not -path "./node_modules/*" -not -path "./roles/*/molecule/*" 2>/dev/null || true)
    if [ -n "$found_files" ]; then
        playbook_files="$playbook_files $found_files"
    fi
done

# Look in common playbook directories
for dir in "playbooks" "."; do
    if [ -d "$dir" ]; then
        # Look for YAML files that contain playbook indicators
        for file in $(find "$dir" -maxdepth 2 -name "*.yml" -o -name "*.yaml" 2>/dev/null || true); do
            if [ -f "$file" ] && grep -q -E "^\s*-\s*(hosts|name):" "$file" 2>/dev/null; then
                playbook_files="$playbook_files $file"
            fi
        done
    fi
done

# Remove duplicates and clean up
playbook_files=$(echo $playbook_files | tr ' ' '\n' | sort -u | tr '\n' ' ')

if [ -z "$playbook_files" ]; then
    echo "ℹ️  No Ansible playbooks found for syntax checking"
    exit 0
fi

echo "🔍 Running Ansible syntax checks..."

exit_code=0
checked_count=0
failed_count=0

# Check each playbook
for playbook in $playbook_files; do
    if [ ! -f "$playbook" ]; then
        continue
    fi
    
    echo "📄 Checking syntax: $playbook"
    checked_count=$((checked_count + 1))
    
    # Run syntax check with minimal output
    if ansible-playbook --syntax-check "$playbook" >/dev/null 2>&1; then
        echo "  ✅ Syntax OK"
    else
        echo "  ❌ Syntax Error"
        failed_count=$((failed_count + 1))
        exit_code=1
        
        # Show the actual error
        echo "  Error details:"
        ansible-playbook --syntax-check "$playbook" 2>&1 | sed 's/^/    /'
        echo ""
    fi
done

# Summary
echo ""
echo "📊 Syntax Check Summary:"
echo "  Total playbooks checked: $checked_count"
echo "  Failed: $failed_count"
echo "  Passed: $((checked_count - failed_count))"

if [ $exit_code -eq 0 ]; then
    echo "✅ All Ansible syntax checks passed"
else
    echo "❌ Some Ansible syntax checks failed"
    echo ""
    echo "💡 Fix syntax errors and try again"
    echo "💡 You can also run manually:"
    echo "  ansible-playbook --syntax-check <playbook-file>"
fi

exit $exit_code
