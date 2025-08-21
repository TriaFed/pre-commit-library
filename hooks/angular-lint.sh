#!/bin/bash
# Angular specific linting

set -e

# Function to check if Angular CLI is available
check_angular() {
    if command -v npx >/dev/null 2>&1; then
        if npx ng version >/dev/null 2>&1; then
            return 0
        fi
    fi
    
    if command -v ng >/dev/null 2>&1; then
        return 0
    fi
    
    echo "❌ Angular CLI not found. Please install it:"
    echo "  npm install -g @angular/cli"
    echo "  # or"
    echo "  npm install --save-dev @angular/cli"
    return 1
}

# Check if this is an Angular project
check_angular_project() {
    if [ ! -f angular.json ] && [ ! -f .angular-cli.json ]; then
        echo "❌ Not an Angular project (no angular.json found)"
        exit 1
    fi
}

# Check if Angular CLI is available
if ! check_angular; then
    exit 1
fi

# Check if this is an Angular project
check_angular_project

# Run Angular linting
echo "🅰️  Running Angular lint..."

# Try to use npx first, fall back to direct command
if command -v npx >/dev/null 2>&1 && npx ng version >/dev/null 2>&1; then
    npx ng lint
else
    ng lint
fi

echo "✅ Angular lint completed"
