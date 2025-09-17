#!/bin/bash
# Terraform validation hook

set -e

# Function to check if Terraform is available
check_terraform() {
    if command -v terraform >/dev/null 2>&1; then
        return 0
    fi
    
    echo "❌ Terraform not found. Please install it:"
    echo "  # macOS:"
    echo "  brew install terraform"
    echo ""
    echo "  # Or download from:"
    echo "  https://www.terraform.io/downloads.html"
    return 1
}

# Check if Terraform is available
if ! check_terraform; then
    exit 1
fi

# Function to find Terraform directories
find_terraform_dirs() {
    find . -name "*.tf" -exec dirname {} \; | sort -u
}

# Run Terraform validation
echo "🏗️  Running Terraform validation..."

# Get all directories containing .tf files
terraform_dirs=$(find_terraform_dirs)

if [ -z "$terraform_dirs" ]; then
    echo "⚠️  No Terraform files found"
    exit 0
fi

exit_code=0

for dir in $terraform_dirs; do
    echo "📁 Validating directory: $dir"
    
    cd "$dir"
    
    # Initialize if needed (but don't download providers in CI)
    if [ ! -d ".terraform" ]; then
        echo "🔄 Initializing Terraform..."
        terraform init -backend=false
    fi
    
    # Validate
    if ! terraform validate; then
        echo "❌ Validation failed in $dir"
        exit_code=1
    else
        echo "✅ Validation passed in $dir"
    fi
    
    # Return to original directory
    cd - >/dev/null
done

if [ $exit_code -eq 0 ]; then
    echo "✅ All Terraform validations passed"
else
    echo "❌ Some Terraform validations failed"
fi

exit $exit_code
