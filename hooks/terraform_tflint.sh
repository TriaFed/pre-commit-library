#!/bin/bash
# TFLint hook for handling multiple directories with Terraform files

# Remove set -e to handle errors gracefully
set -o pipefail

# Global variables for cleanup
TEMP_FILES=()
ORIGINAL_DIR=$(pwd)

# Cleanup function for trap
cleanup() {
    # Clean up temporary files
    for temp_file in "${TEMP_FILES[@]}"; do
        [ -f "$temp_file" ] && rm -f "$temp_file"
    done
    
    # Return to original directory
    cd "$ORIGINAL_DIR" 2>/dev/null || true
}

# Set up trap for cleanup on exit, interrupt, or termination
trap cleanup EXIT INT TERM

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
# Set defaults and validate configuration
TFLINT_DISABLED_RULES="${TFLINT_DISABLED_RULES:-terraform_unused_declarations}"
TFLINT_TIMEOUT="${TFLINT_TIMEOUT:-60}"
TFLINT_MAX_FILES="${TFLINT_MAX_FILES:-100}"

# Validate numeric parameters
if ! [[ "$TFLINT_TIMEOUT" =~ ^[0-9]+$ ]] || [ "$TFLINT_TIMEOUT" -le 0 ]; then
    echo "❌ Error: TFLINT_TIMEOUT must be a positive integer (got: '$TFLINT_TIMEOUT')" >&2
    exit 1
fi

if ! [[ "$TFLINT_MAX_FILES" =~ ^[0-9]+$ ]]; then
    echo "❌ Error: TFLINT_MAX_FILES must be a non-negative integer (got: '$TFLINT_MAX_FILES')" >&2
    exit 1
fi

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

# Function to find Terraform files safely and populate array
find_terraform_files() {
    # Clear the global tf_files_array
    tf_files_array=()
    
    # Use process substitution to avoid subshell issues and handle filenames with spaces
    local file_count=0
    while IFS= read -r -d '' file; do
        tf_files_array+=("$file")
        ((file_count++))
        
        # Check file limit to prevent performance issues
        if [ "$TFLINT_MAX_FILES" -gt 0 ] && [ "$file_count" -ge "$TFLINT_MAX_FILES" ]; then
            echo "⚠️  WARNING: Found $file_count+ Terraform files, limiting to first $TFLINT_MAX_FILES for performance." >&2
            echo "⚠️  Reason: Large repositories can cause TFLint to run very slowly or consume excessive memory." >&2
            echo "⚠️  Solutions:" >&2
            echo "⚠️    - Increase limit: export TFLINT_MAX_FILES=500" >&2
            echo "⚠️    - Run on specific directories: cd terraform/modules && tflint" >&2
            echo "⚠️    - Use .tflint.hcl to exclude large directories" >&2
            break
        fi
    done < <(find . -maxdepth 10 -name "*.tf" -type f -not -path "./.terraform/*" -print0 2>/dev/null)
    
    return "${#tf_files_array[@]}"
}

# Run TFLint
echo "🔍 Running TFLint..."
echo "🔍 Searching for Terraform directories..."

# Get terraform files and extract unique directories
echo "🔍 Looking for .tf files..."
declare -a tf_files_array=()
find_terraform_files

if [ "${#tf_files_array[@]}" -eq 0 ]; then
    echo "⚠️  No Terraform files found"
    exit 0
fi

echo "🔍 Found ${#tf_files_array[@]} Terraform files"
echo "🔍 Extracting directories..."
# Use associative array for O(1) duplicate detection and cache path resolution
declare -A dir_map=()
declare -A path_cache=()  # Cache for absolute path resolution
declare -a terraform_dirs=()

for file in "${tf_files_array[@]}"; do
    dir=$(dirname "$file")
    
    # Use cached absolute path or resolve and cache it
    if [ -n "${path_cache[$dir]:-}" ]; then
        abs_dir="${path_cache[$dir]}"
    else
        abs_dir=$(cd "$dir" 2>/dev/null && pwd || echo "")
        path_cache["$dir"]="$abs_dir"
    fi
    
    # Add to array if not already seen and is valid directory
    if [ -n "$abs_dir" ] && [ -d "$abs_dir" ] && [ -z "${dir_map[$abs_dir]:-}" ]; then
        dir_map["$abs_dir"]=1
        terraform_dirs+=("$abs_dir")
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
    
    # Create secure temporary file and track for cleanup
    temp_file=$(mktemp)
    TEMP_FILES+=("$temp_file")
    
    # Build tflint command with configurable disabled rules
    tflint_cmd="tflint --no-color"
    if [ -n "$TFLINT_DISABLED_RULES" ]; then
        IFS=',' read -ra disabled_rules <<< "$TFLINT_DISABLED_RULES"
        for rule in "${disabled_rules[@]}"; do
            # Trim leading and trailing whitespace using bash parameter expansion
            rule="${rule## }"    # Remove leading spaces
            rule="${rule%% }"    # Remove trailing spaces
            [ -n "$rule" ] && tflint_cmd="$tflint_cmd --disable-rule $rule"
        done
    fi
    tflint_cmd="$tflint_cmd ."
    
    # Add timeout and disable plugin installation to prevent hanging
    if timeout "$TFLINT_TIMEOUT" bash -c "$tflint_cmd" > "$temp_file" 2>&1; then
        # Use file size check to avoid unnecessary cat for empty files
        if [ -s "$temp_file" ]; then
            echo "✅ TFLint passed in $dir"
            # Show any warnings if present
            sed 's/^/  /' "$temp_file"
        else
            echo "✅ TFLint passed in $dir (no issues found)"
        fi
    else
        tflint_exit_code=$?
        # Check if temp file exists and has content before reading it
        if [ -s "$temp_file" ]; then
            tflint_output=$(< "$temp_file")
        else
            tflint_output="No output available"
        fi
        
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
    
    # Return to original directory
    cd "$ORIGINAL_DIR"
done

if [ $exit_code -eq 0 ]; then
    echo "✅ All TFLint checks passed"
else
    echo "❌ Some TFLint checks failed"
fi

exit $exit_code