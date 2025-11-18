#!/bin/bash
# TFLint hook for handling multiple directories with Terraform files

# Use pipefail to catch pipeline errors and handle them gracefully
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
    if ! cd "$ORIGINAL_DIR" 2>/dev/null; then
        echo "Warning: Failed to return to original directory '$ORIGINAL_DIR'. Current directory: $(pwd)" >&2
    fi
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
#                   Set to 0 for unlimited files, or specify a positive integer limit.
#                   This limit exists to prevent performance issues in large repositories
#                   with hundreds/thousands of .tf files. When exceeded, only the first
#                   N files are processed to maintain reasonable execution times.
#                   Solutions when limit is reached:
#                   - Remove limit: export TFLINT_MAX_FILES=0
#                   - Increase limit: export TFLINT_MAX_FILES=500
#                   - Run on specific directories: cd subdir && tflint
#                   - Use .tflint.hcl to exclude directories
#                   Examples: 
#                   - export TFLINT_MAX_FILES=0    # Unlimited files
#                   - export TFLINT_MAX_FILES=200  # Limit to 200 files
#
# TFLINT_MAX_DEPTH: Maximum directory depth to search for .tf files (default: 0 = unlimited)
#                   This prevents infinite recursion and improves performance in deep directory structures.
#                   Set to 0 for unlimited depth, or specify a positive integer.
#                   Examples:
#                   - export TFLINT_MAX_DEPTH=0   # Unlimited (searches entire tree)
#                   - export TFLINT_MAX_DEPTH=10  # Limit to 10 directory levels deep
#                   - export TFLINT_MAX_DEPTH=5   # Limit to 5 directory levels deep
#
# Set defaults and validate configuration
TFLINT_DISABLED_RULES="${TFLINT_DISABLED_RULES:-terraform_unused_declarations}"
TFLINT_TIMEOUT="${TFLINT_TIMEOUT:-60}"
TFLINT_MAX_FILES="${TFLINT_MAX_FILES:-100}"
TFLINT_MAX_DEPTH="${TFLINT_MAX_DEPTH:-0}"

# Validate numeric parameters
if ! [[ "$TFLINT_TIMEOUT" =~ ^[0-9]+$ ]] || [ "$TFLINT_TIMEOUT" -eq 0 ]; then
    echo "❌ Error: TFLINT_TIMEOUT must be a positive integer (got: '$TFLINT_TIMEOUT')" >&2
    exit 1
fi

if ! [[ "$TFLINT_MAX_FILES" =~ ^[0-9]+$ ]]; then
    echo "❌ Error: TFLINT_MAX_FILES must be a non-negative integer (got: '$TFLINT_MAX_FILES')" >&2
    exit 1
fi

if ! [[ "$TFLINT_MAX_DEPTH" =~ ^[0-9]+$ ]]; then
    echo "❌ Error: TFLINT_MAX_DEPTH must be a non-negative integer (got: '$TFLINT_MAX_DEPTH')" >&2
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

# Function to find Terraform files efficiently
find_terraform_files() {
    tf_files_array=()
    local count=0
    
    # Build find command with configurable depth (secure array-based approach)
    local find_args=("." "-name" "*.tf" "-type" "f" "!" "-path" "./.terraform/*")
    if [ "$TFLINT_MAX_DEPTH" -gt 0 ]; then
        # Insert maxdepth at the beginning for proper find syntax
        find_args=("." "-maxdepth" "$TFLINT_MAX_DEPTH" "-name" "*.tf" "-type" "f" "!" "-path" "./.terraform/*")
    fi
    
    # Use process substitution with secure array expansion
    # Capture find errors to temporary file for logging
    local find_errors
    find_errors=$(mktemp)
    TEMP_FILES+=("$find_errors")
    
    while IFS= read -r -d '' file && 
          [ "$TFLINT_MAX_FILES" -eq 0 ] || [ "$count" -lt "$TFLINT_MAX_FILES" ]; do
        tf_files_array+=("$file")
        ((count++))
    done < <(find "${find_args[@]}" -print0 2>"$find_errors")
    
    # Log find errors if any occurred
    if [ -s "$find_errors" ]; then
        echo "Warning: Errors occurred while searching for Terraform files:" >&2
        sed 's/^/  /' "$find_errors" >&2
    fi
    
    # Warn if limit was reached (count stops at exactly TFLINT_MAX_FILES due to loop condition)
    if [ "$TFLINT_MAX_FILES" -gt 0 ] && [ "$count" -eq "$TFLINT_MAX_FILES" ]; then
        printf "⚠️  Limited to %d files (found %d+)\\n" "$TFLINT_MAX_FILES" "$count" >&2
    fi
    
    # Show depth info if limited
    if [ "$TFLINT_MAX_DEPTH" -gt 0 ]; then
        printf "📏 Search depth limited to %d levels\\n" "$TFLINT_MAX_DEPTH" >&2
    fi
}

# Run TFLint
echo "🔍 Running TFLint on Terraform files..."
declare -a tf_files_array=()
find_terraform_files

if [ "${#tf_files_array[@]}" -eq 0 ]; then
    echo "⚠️  No Terraform files found"
    exit 0
fi

echo "📁 Found ${#tf_files_array[@]} Terraform files, extracting directories..."
# Extract unique directories efficiently
declare -A unique_dirs=()

for file in "${tf_files_array[@]}"; do
    # Extract directory and convert to absolute path in one step
    dir="${file%/*}"  # Faster than dirname
    [ "$dir" = "$file" ] && dir="."  # Handle files in current directory
    
    # Skip if already processed
    [ -n "${unique_dirs[$dir]:-}" ] && continue
    
    # Resolve absolute path
    if abs_dir=$(cd "$dir" 2>/dev/null && pwd); then
        unique_dirs["$abs_dir"]=1
    else
        echo "Warning: Unable to access directory '$dir', skipping" >&2
    fi
done

# Convert to array for iteration
terraform_dirs=("${!unique_dirs[@]}")

if [ ${#terraform_dirs[@]} -eq 0 ]; then
    echo "⚠️  No valid Terraform directories found"
    exit 0
fi

# Count directories for better progress reporting
dir_count=${#terraform_dirs[@]}
echo "📊 Found $dir_count director(ies) with Terraform files"

# Show directories found (only if more than 1 for cleaner output)
if [ "$dir_count" -gt 1 ]; then
    echo "🔍 Directories to lint:"
    for dir in "${terraform_dirs[@]}"; do
        echo "  $dir"
    done
fi

exit_code=0

current_dir=0
for dir in "${terraform_dirs[@]}"; do
    ((current_dir++))
    echo "📁 [$current_dir/$dir_count] Linting: $dir"
    
    # Basic validation
    if [ ! -d "$dir" ]; then
        echo "⚠️  Directory does not exist: $dir"
        continue
    fi
    
    # Change to the terraform directory with error handling
    if ! cd "$dir" 2>/dev/null; then
        echo "❌ Failed to change to directory: $dir ($(pwd))" >&2
        exit_code=1
        continue
    fi
    
    # Run TFLint in the current directory with timeout to prevent hanging
    echo "🔍 Running tflint in $(basename "$dir")..."
    
    # Create secure temporary file and track for cleanup
    temp_file=$(mktemp)
    TEMP_FILES+=("$temp_file")
    
    # Build tflint command efficiently
    tflint_args=("--no-color")
    
    # Process disabled rules if any
    if [ -n "$TFLINT_DISABLED_RULES" ]; then
        IFS=',' read -ra rules <<< "$TFLINT_DISABLED_RULES"
        for rule in "${rules[@]}"; do
            # POSIX-compliant whitespace trimming using bash parameter expansion
            # This avoids external commands (sed/awk/tr) for better performance and portability
            # Pattern: ${var#pattern} removes shortest match from beginning
            #          ${var%pattern} removes shortest match from end
            rule="${rule#"${rule%%[![:space:]]*}"}"  # Remove leading whitespace
            rule="${rule%"${rule##*[![:space:]]}"}"  # Remove trailing whitespace
            
            # Validate rule name before adding (prevent empty rules and basic validation)
            if [ -n "$rule" ] && [[ "$rule" =~ ^[a-zA-Z0-9_-]+$ ]]; then
                tflint_args+=("--disable-rule" "$rule")
            elif [ -n "$rule" ]; then
                echo "⚠️  Skipping invalid rule name: '$rule'" >&2
            fi
        done
    fi
    
    tflint_args+=(".")
    
    # Execute tflint with proper argument array
    if timeout "$TFLINT_TIMEOUT" tflint "${tflint_args[@]}" > "$temp_file" 2>&1; then
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
    
    # Return to original directory with error handling
    if ! cd "$ORIGINAL_DIR"; then
        echo "❌ Fatal: Failed to return to original directory '$ORIGINAL_DIR'" >&2
        exit 1
    fi
done

if [ $exit_code -eq 0 ]; then
    echo "✅ All TFLint checks passed"
else
    echo "❌ Some TFLint checks failed"
fi

exit $exit_code