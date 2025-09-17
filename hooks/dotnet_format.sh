#!/bin/bash
# .NET code formatter using dotnet format

set -e

# Function to check if .NET CLI is available
check_dotnet() {
    if command -v dotnet >/dev/null 2>&1; then
        return 0
    fi
    
    echo "❌ .NET CLI not found. Please install it:"
    echo "  # Download from:"
    echo "  https://dotnet.microsoft.com/download"
    echo ""
    echo "  # Or use package manager:"
    echo "  # Windows: winget install Microsoft.DotNet.SDK.8"
    echo "  # macOS: brew install --cask dotnet"
    echo "  # Ubuntu: apt-get install dotnet-sdk-8.0"
    return 1
}

# Check if .NET CLI is available
if ! check_dotnet; then
    exit 1
fi

# Check if this is a .NET project
if [ ! -f "*.sln" ] && [ ! -f "*.csproj" ] && [ ! -f "*.vbproj" ] && [ ! -f "*.fsproj" ] && [ ! -f "global.json" ]; then
    # Look for project files in subdirectories
    if ! find . -name "*.sln" -o -name "*.csproj" -o -name "*.vbproj" -o -name "*.fsproj" | head -1 | grep -q .; then
        echo "⚠️  No .NET project files found (*.sln, *.csproj, *.vbproj, *.fsproj)"
        exit 0
    fi
fi

echo "🔧 Running .NET format..."

# Run dotnet format
# --verify-no-changes will cause the command to exit with a non-zero code if formatting is needed
# --verbosity quiet reduces output noise
if dotnet format --verify-no-changes --verbosity quiet; then
    echo "✅ Code is properly formatted"
    exit 0
else
    echo "❌ Code formatting issues found"
    echo "🔧 Run 'dotnet format' to fix formatting issues"
    echo ""
    echo "💡 To automatically fix formatting:"
    echo "  dotnet format"
    echo ""
    echo "💡 To see what would be changed:"
    echo "  dotnet format --dry-run"
    exit 1
fi
