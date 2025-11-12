#!/bin/bash
# TFLint hook for handling multiple directories with Terraform files

# Remove set -e to handle errors gracefully
set -o pipefail

# Configuration through environment variables
# 
# TFLINT_DISABLED_RULES: Comma-separated list of rules to disable 
#                        (default: terraform_unused_declarations)
#                        Examples: 
#                        - "terraform_unused_declarations"
#                        - "terraform_unused_declarations,terraform_deprecated_syntax"
#                        - "" (empty to disable no rules)
# 
# TFLINT_TIMEOUT: Timeout in seconds for tflint execution (default: 60)
#                 Example: export TFLINT_TIMEOUT=120
# 
# TFLINT_MAX_FILES: Maximum number of Terraform files to process (default: 100)
#                   This limit exists to prevent performance issues in large repositories
#                   with hundreds/thousands of .tf files. When exceeded, only the first
#                   N files are processed to maintain reasonable execution times.
#                   Solutions when limit is reached:
#                   - Increase limit: export TFLINT_MAX_FILES=500
#                   - Run on specific directories: cd subdir && tflint
#                   - Use .tflint.hcl to exclude directories
#                   Example: export TFLINT_MAX_FILES=200
TFLINT_DISABLED_RULES="${TFLINT_DISABLED_RULES:-terraform_unused_declarations}"
TFLINT_TIMEOUT="${TFLINT_TIMEOUT:-60}"
TFLINT_MAX_FILES="${TFLINT_MAX_FILES:-100}"

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

# Function to find Terraform files safely
find_terraform_files() {
    # Find .tf files with reasonable depth limit to avoid hanging
    local all_files=$(find . -maxdepth 10 -name "*.tf" -type f -not -path "./.terraform/*" 2>/dev/null)
    
    # Check if we found any files first
    if [ -z "$all_files" ]; then
        return 0  # No files found, return empty
    fi
    
    local file_count=$(echo "$all_files" | wc -l)
    
    # Check if we have too many files and need to limit
    if [ "$file_count" -gt "$TFLINT_MAX_FILES" ]; then
        echo "⚠️  WARNING: Found $file_count Terraform files, limiting to first $TFLINT_MAX_FILES for performance." >&2
        echo "⚠️  Reason: Large repositories can cause TFLint to run very slowly or consume excessive memory." >&2
        echo "⚠️  Solutions:" >&2
        echo "⚠️    - Increase limit: export TFLINT_MAX_FILES=500" >&2
        echo "⚠️    - Run on specific directories: cd terraform/modules && tflint" >&2
        echo "⚠️    - Use .tflint.hcl to exclude large directories" >&2
        echo "$all_files" | head -"$TFLINT_MAX_FILES"
    else
        echo "$all_files"
    fi
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
# Get unique directories from the files using array for robustness
declare -a terraform_dirs=()
for file in $tf_files; do
    dir=$(dirname "$file")
    # Convert to absolute path
    abs_dir=$(cd "$dir" 2>/dev/null && pwd || continue)
    
    # Add to array if not already there and is valid directory
    if [ -n "$abs_dir" ] && [ -d "$abs_dir" ]; then
        # Check if directory already exists in array
        found=false
        for existing_dir in "${terraform_dirs[@]}"; do
            if [ "$existing_dir" = "$abs_dir" ]; then
                found=true
                break
            fi
        done
        
        # Add to array if not found
        if [ "$found" = false ]; then
            terraform_dirs+=("$abs_dir")
        fi
    fi
done

if [ ${#terraform_dirs[@]} -eq 0 ]; then
    echo "⚠️  No valid Terraform directories found"
    exit 0
fi

# Count directories for better progress reporting
dir_count=${#terraform_dirs[@]}
echo "📊 Found $dir_count director(ies) with Terraform files"

# Debug: Show directories found
echo "🔍 Directories to lint:"
for dir in "${terraform_dirs[@]}"; do
    echo "  $dir"
done

exit_code=0

# Store original directory
original_dir=$(pwd)

for dir in "${terraform_dirs[@]}"; do
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
    
    # Create secure temporary file
    temp_file=$(mktemp)
    
    # Build tflint command with configurable disabled rules
    tflint_cmd="tflint --no-color"
    if [ -n "$TFLINT_DISABLED_RULES" ]; then
        IFS=',' read -ra disabled_rules <<< "$TFLINT_DISABLED_RULES"
        for rule in "${disabled_rules[@]}"; do
            rule=$(echo "$rule" | xargs)  # Trim whitespace
            [ -n "$rule" ] && tflint_cmd="$tflint_cmd --disable-rule $rule"
        done
    fi
    tflint_cmd="$tflint_cmd ."
    
    # Add timeout and disable plugin installation to prevent hanging
    if timeout "$TFLINT_TIMEOUT" bash -c "$tflint_cmd" > "$temp_file" 2>&1; then
        tflint_output=$(cat "$temp_file")
        if [ -n "$tflint_output" ]; then
            echo "✅ TFLint passed in $dir"
            # Show any warnings if present
            echo "$tflint_output" | sed 's/^/  /'
        else
            echo "✅ TFLint passed in $dir (no issues found)"
        fi
    else
        tflint_exit_code=$?
        tflint_output=$(cat "$temp_file" 2>/dev/null || echo "No output available")
        
        if [ $tflint_exit_code -eq 124 ]; then
            echo "⚠️  TFLint timed out in $dir (>${TFLINT_TIMEOUT}s)"
            echo "  This might indicate TFLint is trying to download plugins or has configuration issues"
        else
            echo "❌ TFLint failed in $dir (exit code: $tflint_exit_code)"
            echo "Error details:"
            echo "$tflint_output" | sed 's/^/  /'
            exit_code=1
        fi
    fi
    
    # Clean up temp file
    rm -f "$temp_file"
    
    # Return to original directory
    cd "$original_dir"
done

if [ $exit_code -eq 0 ]; then
    echo "✅ All TFLint checks passed"
else
    echo "❌ Some TFLint checks failed"
fi

exit $exit_code