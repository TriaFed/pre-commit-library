#!/bin/bash
# Semgrep SAST scanning

set -e

# Function to check if Semgrep is available
check_semgrep() {
    if command -v semgrep >/dev/null 2>&1; then
        return 0
    fi
    
    echo "❌ Semgrep not found. Please install it:"
    echo "  # Using pip:"
    echo "  pip install semgrep"
    echo ""
    echo "  # Using Homebrew (macOS):"
    echo "  brew install semgrep"
    echo ""
    echo "  # Using Docker:"
    echo "  docker pull returntocorp/semgrep"
    return 1
}

# Check if Semgrep is available
if ! check_semgrep; then
    exit 1
fi

echo "🛡️  Running Semgrep SAST scan..."

# Create a temporary semgrep config if none exists
create_semgrep_config() {
    if [ ! -f .semgrep.yml ] && [ ! -f .semgrep.yaml ]; then
        echo "⚠️  No Semgrep configuration found. Using security rulesets..."
        return 1
    fi
    return 0
}

# Run Semgrep with security-focused rulesets
run_semgrep() {
    local exit_code=0
    
    # Security rulesets for different languages
    RULESETS=(
        "p/security-audit"
        "p/secrets"
        "p/owasp-top-ten"
        "p/cwe-top-25"
    )
    
    # Language-specific rulesets
    if find . -name "*.py" -type f | head -1 | grep -q .; then
        RULESETS+=("p/python")
    fi
    
    if find . -name "*.js" -o -name "*.ts" -o -name "*.jsx" -o -name "*.tsx" -type f | head -1 | grep -q .; then
        RULESETS+=("p/javascript" "p/typescript")
    fi
    
    if find . -name "*.java" -type f | head -1 | grep -q .; then
        RULESETS+=("p/java")
    fi
    
    if find . -name "*.go" -type f | head -1 | grep -q .; then
        RULESETS+=("p/golang")
    fi
    
    if find . -name "*.tf" -type f | head -1 | grep -q .; then
        RULESETS+=("p/terraform")
    fi
    
    # Check if custom config exists
    if create_semgrep_config; then
        echo "📋 Using custom Semgrep configuration"
        if ! semgrep --config=.semgrep.yml --error --quiet "$@"; then
            exit_code=1
        fi
    else
        # Use predefined rulesets
        for ruleset in "${RULESETS[@]}"; do
            echo "🔍 Running ruleset: $ruleset"
            if ! semgrep --config="$ruleset" --error --quiet "$@" 2>/dev/null; then
                exit_code=1
            fi
        done
    fi
    
    return $exit_code
}

# Run the scan
if run_semgrep "$@"; then
    echo "✅ Semgrep scan completed successfully"
    exit 0
else
    echo "❌ Semgrep found security issues!"
    echo "💡 Review the findings above and fix any security vulnerabilities"
    echo "💡 Use // nosemgrep: rule-id to ignore false positives"
    exit 1
fi
