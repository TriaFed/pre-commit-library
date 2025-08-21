#!/bin/bash
# Yarn audit for Node.js vulnerability scanning

set -e

# Function to check if Yarn is available
check_yarn() {
    if command -v yarn >/dev/null 2>&1; then
        return 0
    fi
    
    echo "❌ Yarn not found. Please install it:"
    echo "  # Using npm:"
    echo "  npm install -g yarn"
    echo ""
    echo "  # Using Homebrew (macOS):"
    echo "  brew install yarn"
    echo ""
    echo "  # Or download from:"
    echo "  https://yarnpkg.com/getting-started/install"
    return 1
}

# Check if Yarn is available
if ! check_yarn; then
    exit 1
fi

# Check if package.json exists
if [ ! -f package.json ]; then
    echo "⚠️  No package.json found, skipping yarn audit"
    exit 0
fi

# Check if yarn.lock exists (indicates Yarn is being used)
if [ ! -f yarn.lock ]; then
    echo "⚠️  No yarn.lock found, this might not be a Yarn project"
    echo "ℹ️  Consider using npm-audit instead"
fi

echo "🧶 Running Yarn audit..."

# Get Yarn version to determine audit command
YARN_VERSION=$(yarn --version)
YARN_MAJOR_VERSION=$(echo "$YARN_VERSION" | cut -d. -f1)

if [ "$YARN_MAJOR_VERSION" -ge 2 ]; then
    # Yarn 2+ uses different audit command
    if yarn npm audit; then
        echo "✅ Yarn audit passed - no vulnerabilities found"
        exit 0
    else
        echo "❌ Yarn audit found vulnerabilities!"
        echo ""
        echo "🔧 Try running 'yarn npm audit --fix' to automatically fix issues"
        echo "🔍 Run 'yarn npm audit' for detailed vulnerability information"
        exit 1
    fi
else
    # Yarn 1.x
    if yarn audit; then
        echo "✅ Yarn audit passed - no vulnerabilities found"
        exit 0
    else
        echo "❌ Yarn audit found vulnerabilities!"
        echo ""
        echo "🔧 Try running 'yarn audit --fix' to automatically fix issues"
        echo "🔍 Run 'yarn audit' for detailed vulnerability information"
        echo ""
        echo "💡 You can also:"
        echo "   - Set audit level: yarn audit --level moderate"
        echo "   - Create a .yarnrc file with audit settings"
        exit 1
    fi
fi
