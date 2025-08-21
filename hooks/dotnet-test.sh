#!/bin/bash
# .NET test runner

set -e

# Function to check if .NET CLI is available
check_dotnet() {
    if command -v dotnet >/dev/null 2>&1; then
        return 0
    fi
    
    echo "❌ .NET CLI not found. Please install it:"
    echo "  https://dotnet.microsoft.com/download"
    return 1
}

# Check if .NET CLI is available
if ! check_dotnet; then
    exit 1
fi

# Check if this is a .NET project with tests
test_projects=$(find . -name "*Test*.csproj" -o -name "*Tests*.csproj" -o -name "*.Test.csproj" -o -name "*.Tests.csproj" 2>/dev/null)

if [ -z "$test_projects" ]; then
    echo "ℹ️  No test projects found (looking for *Test*.csproj, *Tests*.csproj patterns)"
    exit 0
fi

echo "🧪 Running .NET tests..."

# Run tests with minimal output for CI scenarios
# --no-build assumes the project was already built (faster for pre-commit)
# --verbosity quiet reduces noise
# --logger "console;verbosity=minimal" provides concise output
if dotnet test --no-build --verbosity quiet --logger "console;verbosity=minimal" 2>/dev/null; then
    echo "✅ All tests passed"
    exit 0
else
    echo "❌ Some tests failed"
    echo ""
    echo "🔍 Run full test output:"
    echo "  dotnet test --verbosity normal"
    echo ""
    echo "💡 Run specific test project:"
    echo "  dotnet test path/to/TestProject.csproj"
    exit 1
fi
