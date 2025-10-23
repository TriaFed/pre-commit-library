#!/bin/bash
# npm audit for Node.js vulnerability scanning

set -e

# Function to check if npm is available
check_npm() {
    if command -v npm >/dev/null 2>&1; then
        return 0
    fi
    
    echo "❌ npm not found. Please install Node.js and npm:"
    echo "  # macOS:"
    echo "  brew install node"
    echo ""
    echo "  # Or download from:"
    echo "  https://nodejs.org/"
    return 1
}

# Check if npm is available
if ! check_npm; then
    exit 1
fi

# Check if package.json exists
if [ ! -f package.json ]; then
    echo "⚠️  No package.json found, skipping npm audit"
    exit 0
fi

echo "📦 Running npm audit..."

# Run npm audit
# Use --audit-level to control which vulnerabilities fail the check
# moderate: fail on moderate and above
# high: fail on high and above  
# critical: fail only on critical
# Default to 'high' to reduce false positives while still catching serious issues
AUDIT_LEVEL="${NPM_AUDIT_LEVEL:-high}"

if npm audit --audit-level="$AUDIT_LEVEL"; then
    echo "✅ npm audit passed - no vulnerabilities found at $AUDIT_LEVEL level or above"
    exit 0
else
    echo "❌ npm audit found vulnerabilities!"
    echo ""
    echo "🔧 Try running 'npm audit fix' to automatically fix issues"
    echo "🔍 Run 'npm audit' for detailed vulnerability information"
    echo ""
    echo "💡 If you need to ignore specific vulnerabilities, consider:"
    echo "   - Using npm audit fix --force (with caution)"
    echo "   - Creating an .npmrc file with audit-level settings"
    echo "   - Using npm audit --audit-level=high for less strict checking"
    exit 1
fi
