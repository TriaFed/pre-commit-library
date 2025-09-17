#!/bin/bash
# Go code formatter using gofmt

set -e

# Function to check if Go is available
check_go() {
    if command -v go >/dev/null 2>&1; then
        return 0
    fi
    
    echo "❌ Go not found. Please install it:"
    echo "  # Download from:"
    echo "  https://golang.org/dl/"
    echo ""
    echo "  # Or use package manager:"
    echo "  # macOS: brew install go"
    echo "  # Ubuntu: apt-get install golang-go"
    echo "  # Windows: winget install GoLang.Go"
    return 1
}

# Check if Go is available
if ! check_go; then
    exit 1
fi

# Check if any Go files exist
go_files=$(find . -name "*.go" -not -path "./vendor/*" -not -path "./.git/*" 2>/dev/null || true)

if [ -z "$go_files" ]; then
    echo "ℹ️  No Go files found"
    exit 0
fi

echo "🔧 Running gofmt..."

# Check if files are properly formatted
unformatted_files=()
for file in $go_files; do
    if ! gofmt -l "$file" | grep -q .; then
        continue
    else
        unformatted_files+=("$file")
    fi
done

if [ ${#unformatted_files[@]} -eq 0 ]; then
    echo "✅ All Go files are properly formatted"
    exit 0
else
    echo "❌ The following Go files are not properly formatted:"
    for file in "${unformatted_files[@]}"; do
        echo "  - $file"
    done
    echo ""
    echo "🔧 Run the following to fix formatting:"
    echo "  gofmt -w ."
    echo ""
    echo "💡 Or format specific files:"
    for file in "${unformatted_files[@]}"; do
        echo "  gofmt -w $file"
    done
    exit 1
fi
