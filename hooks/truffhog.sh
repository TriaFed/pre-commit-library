#!/bin/bash
# TruffleHog secret scanning

set -e

# Function to check if TruffleHog is available
check_trufflehog() {
    if command -v trufflehog >/dev/null 2>&1; then
        return 0
    fi
    
    echo "❌ TruffleHog not found. Please install it:"
    echo "  # Using Go:"
    echo "  go install github.com/trufflesecurity/trufflehog/v3@latest"
    echo ""
    echo "  # Using Homebrew (macOS):"
    echo "  brew install trufflehog"
    echo ""
    echo "  # Using Docker:"
    echo "  docker pull trufflesecurity/trufflehog:latest"
    return 1
}

# Check if TruffleHog is available
if ! check_trufflehog; then
    exit 1
fi

echo "🔍 Running TruffleHog secret scan..."

# Run TruffleHog on the files
# Use --no-update to avoid checking for updates during pre-commit
# Use --fail to return non-zero exit code if secrets are found
if trufflehog --no-update --fail filesystem --directory=. --include-paths="$*" 2>/dev/null; then
    echo "✅ No secrets detected by TruffleHog"
    exit 0
else
    echo "❌ TruffleHog detected potential secrets!"
    echo "💡 Review the findings above and remove any actual secrets"
    echo "💡 Use .trufflehogignore file to ignore false positives"
    exit 1
fi
