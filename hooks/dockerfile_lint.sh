#!/bin/bash
# Dockerfile linting and security checks

set -e

# Function to check if hadolint is available
check_hadolint() {
    if command -v hadolint >/dev/null 2>&1; then
        return 0
    fi
    
    echo "❌ hadolint not found. Please install it:"
    echo "  # macOS:"
    echo "  brew install hadolint"
    echo ""
    echo "  # Linux:"
    echo "  wget -O /usr/local/bin/hadolint https://github.com/hadolint/hadolint/releases/latest/download/hadolint-Linux-x86_64"
    echo "  chmod +x /usr/local/bin/hadolint"
    echo ""
    echo "  # Docker:"
    echo "  docker pull hadolint/hadolint"
    return 1
}

# Function to run basic Dockerfile checks
basic_dockerfile_checks() {
    local dockerfile="$1"
    local issues=0
    
    echo "🔍 Running basic Dockerfile security checks on $dockerfile..."
    
    # Check for root user
    if grep -q "USER root" "$dockerfile" || ! grep -q "USER " "$dockerfile"; then
        echo "⚠️  Consider using non-root user (add USER directive)"
        issues=$((issues + 1))
    fi
    
    # Check for latest tag
    if grep -q ":latest" "$dockerfile"; then
        echo "⚠️  Avoid using 'latest' tag, specify exact versions"
        issues=$((issues + 1))
    fi
    
    # Check for apt-get update without install
    if grep -q "apt-get update" "$dockerfile" && ! grep -q "apt-get install" "$dockerfile"; then
        echo "⚠️  apt-get update should be combined with install in same RUN"
        issues=$((issues + 1))
    fi
    
    # Check for missing apt-get clean
    if grep -q "apt-get install" "$dockerfile" && ! grep -q "apt-get clean\|rm -rf /var/lib/apt/lists" "$dockerfile"; then
        echo "⚠️  Consider cleaning apt cache to reduce image size"
        issues=$((issues + 1))
    fi
    
    # Check for COPY/ADD with broad wildcards
    if grep -q "COPY \. \|ADD \. " "$dockerfile"; then
        echo "⚠️  Broad COPY/ADD may include unwanted files, consider .dockerignore"
        issues=$((issues + 1))
    fi
    
    # Check for hardcoded secrets patterns
    if grep -E -i "password|secret|key|token" "$dockerfile" | grep -v "^#"; then
        echo "⚠️  Potential hardcoded secrets detected"
        issues=$((issues + 1))
    fi
    
    return $issues
}

# Check if any Dockerfiles are provided
if [ $# -eq 0 ]; then
    # Find Dockerfiles in current directory
    dockerfiles=$(find . -name "Dockerfile*" -type f)
    if [ -z "$dockerfiles" ]; then
        echo "ℹ️  No Dockerfiles found"
        exit 0
    fi
    set -- $dockerfiles
fi

echo "🐳 Running Dockerfile linting..."

exit_code=0
total_issues=0

for dockerfile in "$@"; do
    if [ ! -f "$dockerfile" ]; then
        echo "❌ File not found: $dockerfile"
        exit_code=1
        continue
    fi
    
    echo "📄 Checking: $dockerfile"
    
    # Run hadolint if available
    if check_hadolint 2>/dev/null; then
        if ! hadolint "$dockerfile"; then
            echo "❌ hadolint found issues in $dockerfile"
            exit_code=1
        else
            echo "✅ hadolint passed for $dockerfile"
        fi
    else
        echo "⚠️  hadolint not available, running basic checks only"
    fi
    
    # Run basic checks
    basic_dockerfile_checks "$dockerfile"
    issues=$?
    total_issues=$((total_issues + issues))
    
    if [ $issues -eq 0 ]; then
        echo "✅ Basic checks passed for $dockerfile"
    else
        echo "⚠️  Found $issues potential issues in $dockerfile"
        exit_code=1
    fi
    
    echo ""
done

if [ $exit_code -eq 0 ]; then
    echo "✅ All Dockerfile checks passed"
else
    echo "❌ Some Dockerfile checks failed"
    if [ $total_issues -gt 0 ]; then
        echo "💡 Consider installing hadolint for comprehensive Dockerfile linting"
        echo "💡 Review Docker security best practices"
    fi
fi

exit $exit_code
