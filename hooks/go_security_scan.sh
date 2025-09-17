#!/bin/bash
# Go security scanning using gosec

set -e

# Function to check if Go is available
check_go() {
    if command -v go >/dev/null 2>&1; then
        return 0
    fi
    
    echo "❌ Go not found. Please install it:"
    echo "  https://golang.org/dl/"
    return 1
}

# Function to check if gosec is available
check_gosec() {
    if command -v gosec >/dev/null 2>&1; then
        return 0
    fi
    
    echo "❌ gosec not found. Please install it:"
    echo "  # Using go install:"
    echo "  go install github.com/securego/gosec/v2/cmd/gosec@latest"
    echo ""
    echo "  # Using Homebrew (macOS):"
    echo "  brew install gosec"
    echo ""
    echo "  # Using Docker:"
    echo "  docker run --rm -it -v \$(pwd):/src securego/gosec /src"
    return 1
}

# Check if Go is available
if ! check_go; then
    exit 1
fi

# Check if any Go files exist
if ! find . -name "*.go" -not -path "./vendor/*" -not -path "./.git/*" | head -1 | grep -q .; then
    echo "ℹ️  No Go files found"
    exit 0
fi

# Check if gosec is available
if ! check_gosec; then
    exit 1
fi

echo "🛡️  Running Go security scan with gosec..."

# Create basic gosec config if none exists
create_gosec_config() {
    if [ ! -f .gosec.json ]; then
        echo "⚠️  No gosec configuration found. Creating basic .gosec.json..."
        cat > .gosec.json << 'EOF'
{
    "severity": "medium",
    "confidence": "medium",
    "exclude": {
        "G104": "Audit errors not checked can be noisy in some contexts",
        "G204": "Subprocess launched with variable - context dependent",
        "G304": "File path provided as taint input - context dependent"
    },
    "include": [
        "G101", "G102", "G103", "G106", "G107", "G108", "G109", "G110",
        "G201", "G202", "G203", "G301", "G302", "G303", "G305", "G306", "G307",
        "G401", "G402", "G403", "G404", "G501", "G502", "G503", "G504", "G505", "G506", "G507",
        "G601", "G602"
    ],
    "exclude-generated": true,
    "tests": false
}
EOF
        echo "💡 Created .gosec.json with recommended security rules"
    fi
}

# Create basic config if none exists
create_gosec_config

# Run gosec with configuration
if [ -f .gosec.json ]; then
    echo "📋 Using gosec configuration from .gosec.json"
    gosec_args="-conf .gosec.json"
else
    # Use default settings with reasonable exclusions
    gosec_args="-exclude=G104,G204,G304 -severity=medium -confidence=medium"
fi

# Run gosec
if gosec $gosec_args ./...; then
    echo "✅ No security issues found by gosec"
    exit 0
else
    echo "❌ Security issues found by gosec"
    echo ""
    echo "💡 To see detailed output:"
    echo "  gosec -fmt=json ./... | jq"
    echo ""
    echo "💡 To exclude specific rules:"
    echo "  gosec -exclude=G101,G104 ./..."
    echo ""
    echo "💡 Common gosec rules:"
    echo "  G101: Look for hardcoded credentials"
    echo "  G102: Bind to all interfaces"
    echo "  G103: Audit the use of unsafe block"
    echo "  G104: Audit errors not checked"
    echo "  G201: SQL query construction using format string"
    echo "  G202: SQL query construction using string concatenation"
    echo "  G204: Audit use of command execution"
    echo "  G301: Poor file permissions used when creating a directory"
    echo "  G302: Poor file permissions used with chmod"
    echo "  G401: Detect the usage of DES, RC4, MD5 or SHA1"
    echo "  G402: Look for bad TLS connection settings"
    echo "  G403: Ensure minimum RSA key length of 2048 bits"
    echo "  G501: Import blacklist: crypto/md5"
    echo "  G502: Import blacklist: crypto/des"
    echo "  G503: Import blacklist: crypto/rc4"
    echo "  G601: Implicit memory aliasing of items from a range statement"
    exit 1
fi
