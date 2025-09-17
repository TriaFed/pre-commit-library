#!/bin/bash
# TypeScript compiler check

set -e

# Function to check if TypeScript is available
check_typescript() {
    if command -v npx >/dev/null 2>&1; then
        if npx tsc --version >/dev/null 2>&1; then
            return 0
        fi
    fi
    
    if command -v tsc >/dev/null 2>&1; then
        return 0
    fi
    
    echo "❌ TypeScript compiler not found. Please install it:"
    echo "  npm install -g typescript"
    echo "  # or"
    echo "  npm install --save-dev typescript"
    return 1
}

# Check if TypeScript is available
if ! check_typescript; then
    exit 1
fi

# Check if tsconfig.json exists
if [ ! -f tsconfig.json ]; then
    echo "⚠️  No tsconfig.json found. Creating basic configuration..."
    cat > tsconfig.json << 'EOF'
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "ESNext",
    "moduleResolution": "node",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "noImplicitReturns": true,
    "noImplicitOverride": true,
    "noPropertyAccessFromIndexSignature": true,
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true
  },
  "include": [
    "src/**/*",
    "*.ts",
    "*.tsx"
  ],
  "exclude": [
    "node_modules",
    "dist",
    "build"
  ]
}
EOF
fi

# Run TypeScript compiler check
echo "🔍 Running TypeScript compiler check..."

# Try to use npx first, fall back to direct command
if command -v npx >/dev/null 2>&1 && npx tsc --version >/dev/null 2>&1; then
    npx tsc --noEmit
else
    tsc --noEmit
fi

echo "✅ TypeScript check completed"
