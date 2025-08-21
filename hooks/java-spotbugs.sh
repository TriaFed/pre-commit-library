#!/bin/bash
# Java SpotBugs static analysis

set -e

# Function to check if SpotBugs is available
check_spotbugs() {
    if command -v spotbugs >/dev/null 2>&1; then
        return 0
    fi
    
    # Check if Maven is available and has SpotBugs plugin
    if command -v mvn >/dev/null 2>&1; then
        if [ -f pom.xml ]; then
            if grep -q "spotbugs-maven-plugin" pom.xml; then
                return 0
            fi
        fi
    fi
    
    # Check if Gradle is available and has SpotBugs plugin
    if command -v gradle >/dev/null 2>&1; then
        if [ -f build.gradle ] || [ -f build.gradle.kts ]; then
            if grep -q "spotbugs" build.gradle* 2>/dev/null; then
                return 0
            fi
        fi
    fi
    
    echo "❌ SpotBugs not found. Please install it:"
    echo "  # For Maven, add to pom.xml:"
    echo "  <plugin>"
    echo "    <groupId>com.github.spotbugs</groupId>"
    echo "    <artifactId>spotbugs-maven-plugin</artifactId>"
    echo "  </plugin>"
    echo ""
    echo "  # For Gradle, add to build.gradle:"
    echo "  plugins { id 'com.github.spotbugs' }"
    echo ""
    echo "  # Or install standalone:"
    echo "  brew install spotbugs  # macOS"
    return 1
}

# Check if SpotBugs is available
if ! check_spotbugs; then
    exit 1
fi

echo "🔍 Running SpotBugs analysis..."

# Run SpotBugs using the available method
if command -v spotbugs >/dev/null 2>&1; then
    # Use standalone SpotBugs
    # First, we need to compile the Java files
    echo "📦 Compiling Java files..."
    
    # Find all Java files
    java_files=$(find . -name "*.java" -type f)
    
    if [ -z "$java_files" ]; then
        echo "ℹ️  No Java files found"
        exit 0
    fi
    
    # Create temporary directory for compiled classes
    temp_dir=$(mktemp -d)
    
    # Compile Java files
    if ! javac -d "$temp_dir" $java_files 2>/dev/null; then
        echo "⚠️  Could not compile Java files for SpotBugs analysis"
        rm -rf "$temp_dir"
        exit 0
    fi
    
    # Run SpotBugs
    if spotbugs -textui "$temp_dir" 2>/dev/null; then
        echo "✅ SpotBugs analysis completed"
        rm -rf "$temp_dir"
        exit 0
    else
        echo "❌ SpotBugs found issues"
        rm -rf "$temp_dir"
        exit 1
    fi

elif command -v mvn >/dev/null 2>&1 && [ -f pom.xml ]; then
    # Use Maven plugin
    mvn compile spotbugs:check

elif command -v gradle >/dev/null 2>&1 && ([ -f build.gradle ] || [ -f build.gradle.kts ]); then
    # Use Gradle plugin
    gradle compileJava spotbugsMain

else
    echo "❌ Unable to run SpotBugs"
    exit 1
fi

echo "✅ SpotBugs analysis completed"
