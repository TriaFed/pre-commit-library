#!/bin/bash
# Go linting using golangci-lint

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

# Function to check if golangci-lint is available
check_golangci_lint() {
    if command -v golangci-lint >/dev/null 2>&1; then
        return 0
    fi
    
    echo "❌ golangci-lint not found. Please install it:"
    echo "  # Using go install:"
    echo "  go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest"
    echo ""
    echo "  # Using Homebrew (macOS):"
    echo "  brew install golangci-lint"
    echo ""
    echo "  # Using curl:"
    echo "  curl -sSfL https://raw.githubusercontent.com/golangci/golangci-lint/master/install.sh | sh -s -- -b \$(go env GOPATH)/bin v1.54.2"
    echo ""
    echo "  # Using Docker:"
    echo "  docker run --rm -v \$(pwd):/app -w /app golangci/golangci-lint:v1.54.2 golangci-lint run"
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

# Check if golangci-lint is available
if ! check_golangci_lint; then
    echo "⚠️  Falling back to basic Go tools..."
    
    # Use basic go tools if golangci-lint is not available
    echo "🔍 Running go vet..."
    if ! go vet ./...; then
        echo "❌ go vet found issues"
        exit 1
    fi
    
    # Check if staticcheck is available
    if command -v staticcheck >/dev/null 2>&1; then
        echo "🔍 Running staticcheck..."
        if ! staticcheck ./...; then
            echo "❌ staticcheck found issues"
            exit 1
        fi
    else
        echo "💡 Consider installing staticcheck for additional checks:"
        echo "  go install honnef.co/go/tools/cmd/staticcheck@latest"
    fi
    
    echo "✅ Basic Go checks passed"
    exit 0
fi

echo "🔍 Running golangci-lint..."

# Create basic golangci-lint config if none exists
create_golangci_config() {
    if [ ! -f .golangci.yml ] && [ ! -f .golangci.yaml ] && [ ! -f .golangci.toml ]; then
        echo "⚠️  No golangci-lint configuration found. Creating basic .golangci.yml..."
        cat > .golangci.yml << 'EOF'
run:
  timeout: 5m
  tests: true
  skip-dirs:
    - vendor
    - .git

linters:
  enable:
    - errcheck
    - gosimple
    - govet
    - ineffassign
    - staticcheck
    - typecheck
    - unused
    - gosec
    - misspell
    - gofmt
    - goimports
    - gocritic
    - revive
    - unparam

linters-settings:
  gosec:
    excludes:
      - G104 # Audit errors not checked - can be noisy
  gocritic:
    enabled-tags:
      - diagnostic
      - experimental
      - opinionated
      - performance
      - style
  revive:
    rules:
      - name: exported
        disabled: true

issues:
  exclude-rules:
    - path: _test\.go
      linters:
        - gosec
        - errcheck
  max-issues-per-linter: 0
  max-same-issues: 0

output:
  format: colored-line-number
  print-issued-lines: true
  print-linter-name: true
EOF
    fi
}

# Create basic config if none exists
create_golangci_config

# Run golangci-lint
if golangci-lint run; then
    echo "✅ golangci-lint passed"
    exit 0
else
    echo "❌ golangci-lint found issues"
    echo ""
    echo "💡 To see detailed output:"
    echo "  golangci-lint run --verbose"
    echo ""
    echo "💡 To fix auto-fixable issues:"
    echo "  golangci-lint run --fix"
    exit 1
fi
