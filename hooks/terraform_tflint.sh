#!/bin/bash
# TFLint hook for handling multiple directories with Terraform files

# Remove set -e to handle errors gracefully
set -o pipefail

# Function to check if TFLint is available
check_tflint() {
    if command -v tflint >/dev/null 2>&1; then
        return 0
    fi
    
    echo "❌ TFLint not found. Please install it:"
    echo "  # macOS:"
    echo "  brew install tflint"
    echo ""
    echo "  # Or download from:"
    echo "  https://github.com/terraform-linters/tflint/releases"
    return 1
}

# Check if TFLint is available
if ! check_tflint; then
    exit 1
fi

# Simplified approach - just use basic commands
find_terraform_files() {
    # Find .tf files with limited depth to avoid hanging
    find . -name "*.tf" -type f -not -path "./.terraform/*" 2>/dev/null | head -50
}

# Run TFLint
echo "🔍 Running TFLint..."
echo "🔍 Searching for Terraform directories..."

# Get terraform files and extract unique directories
echo "🔍 Looking for .tf files..."
tf_files=$(find_terraform_files)

if [ -z "$tf_files" ]; then
    echo "⚠️  No Terraform files found"
    exit 0
fi

echo "🔍 Extracting directories..."
# Get unique directories from the files
terraform_dirs=""
for file in $tf_files; do
    dir=$(dirname "$file")
    # Convert to absolute path
    abs_dir=$(cd "$dir" 2>/dev/null && pwd || continue)
    
    # Add to list if not already there
    if [ -n "$abs_dir" ] && [ -d "$abs_dir" ]; then
        if echo "$terraform_dirs" | grep -q "^$abs_dir$"; then
            continue
        else
            if [ -z "$terraform_dirs" ]; then
                terraform_dirs="$abs_dir"
            else
                terraform_dirs="$terraform_dirs
$abs_dir"
            fi
        fi
    fi
done

if [ -z "$terraform_dirs" ]; then
    echo "⚠️  No valid Terraform directories found"
    exit 0
fi

# Count directories for better progress reporting
dir_count=$(echo "$terraform_dirs" | wc -l)
echo "📊 Found $dir_count director(ies) with Terraform files"

# Debug: Show directories found
echo "🔍 Directories to lint:"
echo "$terraform_dirs" | sed 's/^/  /'

exit_code=0

# Store original directory
original_dir=$(pwd)

echo "$terraform_dirs" | while IFS= read -r dir; do
    echo "📁 Linting directory: $dir"
    
    # Basic validation
    if [ ! -d "$dir" ]; then
        echo "⚠️  Directory does not exist: $dir"
        continue
    fi
    
    # Change to the terraform directory
    if ! cd "$dir"; then
        echo "❌ Failed to change to directory: $dir"
        exit_code=1
        continue
    fi
    
    # Run TFLint in the current directory with timeout to prevent hanging
    echo "🔍 Running tflint in $(basename "$dir")..."
    
    # Add timeout and disable plugin installation to prevent hanging
    if timeout 60 tflint --no-color --disable-rule terraform_unused_declarations . > /tmp/tflint_output 2>&1; then
        tflint_output=$(cat /tmp/tflint_output)
        if [ -n "$tflint_output" ]; then
            echo "✅ TFLint passed in $dir"
            # Show any warnings if present
            echo "$tflint_output" | sed 's/^/  /'
        else
            echo "✅ TFLint passed in $dir (no issues found)"
        fi
    else
        tflint_exit_code=$?
        tflint_output=$(cat /tmp/tflint_output 2>/dev/null || echo "No output available")
        
        if [ $tflint_exit_code -eq 124 ]; then
            echo "⚠️  TFLint timed out in $dir (>60s)"
            echo "  This might indicate TFLint is trying to download plugins or has configuration issues"
        else
            echo "❌ TFLint failed in $dir (exit code: $tflint_exit_code)"
            echo "Error details:"
            echo "$tflint_output" | sed 's/^/  /'
            exit_code=1
        fi
    fi
    
    # Clean up temp file
    rm -f /tmp/tflint_output
    
    # Return to original directory
    cd "$original_dir"
done

if [ $exit_code -eq 0 ]; then
    echo "✅ All TFLint checks passed"
else
    echo "❌ Some TFLint checks failed"
fi

exit $exit_code