#!/bin/bash
# CloudFormation template validation

set -e

# Function to check if AWS CLI is available
check_aws_cli() {
    if command -v aws >/dev/null 2>&1; then
        return 0
    fi
    
    echo "❌ AWS CLI not found. Please install it:"
    echo "  # macOS:"
    echo "  brew install awscli"
    echo ""
    echo "  # Or:"
    echo "  pip install awscli"
    return 1
}

# Function to check if cfn-lint is available
check_cfn_lint() {
    if command -v cfn-lint >/dev/null 2>&1; then
        return 0
    fi
    
    echo "⚠️  cfn-lint not found. Install for better validation:"
    echo "  pip install cfn-lint"
    return 1
}

# Function to validate JSON syntax
validate_json() {
    local file="$1"
    if ! python3 -m json.tool "$file" >/dev/null 2>&1; then
        echo "❌ Invalid JSON syntax in $file"
        return 1
    fi
    return 0
}

# Function to validate YAML syntax
validate_yaml() {
    local file="$1"
    if command -v python3 >/dev/null 2>&1; then
        if ! python3 -c "import yaml; yaml.safe_load(open('$file'))" 2>/dev/null; then
            echo "❌ Invalid YAML syntax in $file"
            return 1
        fi
    fi
    return 0
}

# Function to check if file looks like CloudFormation
is_cloudformation_template() {
    local file="$1"
    
    # Check for CloudFormation-specific keys
    if grep -q -i "AWSTemplateFormatVersion\|Resources\|Parameters\|Outputs" "$file" 2>/dev/null; then
        return 0
    fi
    
    return 1
}

# Check if AWS CLI is available
if ! check_aws_cli; then
    exit 1
fi

# Check if cfn-lint is available (optional)
cfn_lint_available=0
if check_cfn_lint; then
    cfn_lint_available=1
fi

echo "☁️  Running CloudFormation validation..."

exit_code=0

for file in "$@"; do
    # Skip if file doesn't exist
    if [ ! -f "$file" ]; then
        continue
    fi
    
    # Check if it looks like a CloudFormation template
    if ! is_cloudformation_template "$file"; then
        echo "⏭️  Skipping $file (doesn't appear to be a CloudFormation template)"
        continue
    fi
    
    echo "📄 Validating: $file"
    
    # Basic syntax validation
    if [[ "$file" == *.json ]]; then
        if ! validate_json "$file"; then
            exit_code=1
            continue
        fi
    elif [[ "$file" == *.yaml ]] || [[ "$file" == *.yml ]]; then
        if ! validate_yaml "$file"; then
            exit_code=1
            continue
        fi
    fi
    
    # AWS CLI validation
    if ! aws cloudformation validate-template --template-body "file://$file" >/dev/null 2>&1; then
        echo "❌ AWS CloudFormation validation failed for $file"
        # Show the error
        aws cloudformation validate-template --template-body "file://$file" 2>&1 || true
        exit_code=1
    else
        echo "✅ AWS validation passed for $file"
    fi
    
    # cfn-lint validation (if available)
    if [ $cfn_lint_available -eq 1 ]; then
        if ! cfn-lint "$file"; then
            echo "❌ cfn-lint validation failed for $file"
            exit_code=1
        else
            echo "✅ cfn-lint validation passed for $file"
        fi
    fi
done

if [ $exit_code -eq 0 ]; then
    echo "✅ All CloudFormation validations passed"
else
    echo "❌ Some CloudFormation validations failed"
fi

exit $exit_code
