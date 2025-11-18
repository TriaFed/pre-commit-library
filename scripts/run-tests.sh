#!/bin/bash
set -e

echo "🧪 Setting up test environment (macOS/Linux)..."

if ! command -v python3 >/dev/null 2>&1; then
  echo "❌ python3 not found"
  exit 1
fi

python3 -m pip install --upgrade pip >/dev/null
python3 -m pip install -q pytest pytest-cov pyyaml

echo "✅ Dependencies installed"

echo "🔍 Running tests with coverage..."
python3 -m pytest scripts/tests --cov=scripts --cov-report=term-missing -q

echo "📄 HTML coverage: htmlcov/index.html (generated if --cov-report=html is added)"

