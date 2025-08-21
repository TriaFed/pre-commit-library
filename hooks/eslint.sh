#!/bin/bash
# ESLint hook for JavaScript/TypeScript linting

set -e

# Function to check if ESLint is available
check_eslint() {
    if command -v npx >/dev/null 2>&1; then
        if npx eslint --version >/dev/null 2>&1; then
            return 0
        fi
    fi
    
    if command -v eslint >/dev/null 2>&1; then
        return 0
    fi
    
    echo "❌ ESLint not found. Please install it:"
    echo "  npm install -g eslint"
    echo "  # or"
    echo "  npm install --save-dev eslint"
    return 1
}

# Check if ESLint is available
if ! check_eslint; then
    exit 1
fi

# Check if .eslintrc exists, if not create a basic one
create_eslint_config() {
    if [ ! -f .eslintrc.js ] && [ ! -f .eslintrc.json ] && [ ! -f .eslintrc.yml ] && [ ! -f .eslintrc.yaml ] && [ ! -f package.json ]; then
        echo "⚠️  No ESLint configuration found. Creating basic .eslintrc.js..."
        cat > .eslintrc.js << 'EOF'
module.exports = {
    env: {
        browser: true,
        es2021: true,
        node: true
    },
    extends: [
        'eslint:recommended'
    ],
    parserOptions: {
        ecmaVersion: 12,
        sourceType: 'module'
    },
    rules: {
        // Security rules
        'no-eval': 'error',
        'no-implied-eval': 'error',
        'no-new-func': 'error',
        'no-script-url': 'error',
        
        // Code quality rules
        'no-unused-vars': 'warn',
        'no-console': 'warn',
        'prefer-const': 'error',
        'no-var': 'error',
        
        // GenAI-specific rules
        'no-alert': 'error',
        'no-debugger': 'error'
    }
};
EOF
    fi
}

# Create basic config if none exists
create_eslint_config

# Run ESLint
echo "🔍 Running ESLint..."

# Try to use npx first, fall back to direct command
if command -v npx >/dev/null 2>&1 && npx eslint --version >/dev/null 2>&1; then
    npx eslint "$@"
else
    eslint "$@"
fi

echo "✅ ESLint check completed"
