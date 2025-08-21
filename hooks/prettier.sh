#!/bin/bash
# Prettier hook for code formatting

set -e

# Function to check if Prettier is available
check_prettier() {
    if command -v npx >/dev/null 2>&1; then
        if npx prettier --version >/dev/null 2>&1; then
            return 0
        fi
    fi
    
    if command -v prettier >/dev/null 2>&1; then
        return 0
    fi
    
    echo "❌ Prettier not found. Please install it:"
    echo "  npm install -g prettier"
    echo "  # or"
    echo "  npm install --save-dev prettier"
    return 1
}

# Check if Prettier is available
if ! check_prettier; then
    exit 1
fi

# Create basic Prettier config if none exists
create_prettier_config() {
    if [ ! -f .prettierrc ] && [ ! -f .prettierrc.json ] && [ ! -f .prettierrc.js ] && [ ! -f prettier.config.js ]; then
        echo "⚠️  No Prettier configuration found. Creating basic .prettierrc..."
        cat > .prettierrc << 'EOF'
{
  "semi": true,
  "trailingComma": "es5",
  "singleQuote": true,
  "printWidth": 100,
  "tabWidth": 2,
  "useTabs": false,
  "bracketSpacing": true,
  "arrowParens": "avoid"
}
EOF
    fi
}

# Create basic config if none exists
create_prettier_config

# Run Prettier
echo "🎨 Running Prettier..."

# Check if files need formatting
if command -v npx >/dev/null 2>&1 && npx prettier --version >/dev/null 2>&1; then
    if ! npx prettier --check "$@" 2>/dev/null; then
        echo "❌ Files are not formatted correctly. Running formatter..."
        npx prettier --write "$@"
        echo "✅ Files have been formatted. Please add the changes and commit again."
        exit 1
    fi
else
    if ! prettier --check "$@" 2>/dev/null; then
        echo "❌ Files are not formatted correctly. Running formatter..."
        prettier --write "$@"
        echo "✅ Files have been formatted. Please add the changes and commit again."
        exit 1
    fi
fi

echo "✅ Prettier check completed"
