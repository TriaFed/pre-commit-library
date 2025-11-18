Param(
  [switch]$Html
)

$ErrorActionPreference = "Stop"

Write-Host "🧪 Setting up test environment (Windows)..." -ForegroundColor Cyan

$python = Get-Command py -ErrorAction SilentlyContinue
if (-not $python) { $python = Get-Command python -ErrorAction SilentlyContinue }
if (-not $python) { $python = Get-Command python3 -ErrorAction SilentlyContinue }
if (-not $python) { Write-Host "❌ Python not found" -ForegroundColor Red; exit 1 }

& $python.Path -m pip install --upgrade pip *> $null
& $python.Path -m pip install pytest pytest-cov pyyaml -q

Write-Host "✅ Dependencies installed" -ForegroundColor Green

Write-Host "🔍 Running tests with coverage..." -ForegroundColor Cyan

$covArgs = @("--cov=scripts", "--cov-report=term-missing")
if ($Html) { $covArgs = @("--cov=scripts", "--cov-report=term-missing", "--cov-report=html") }

& $python.Path -m pytest "scripts/tests" @covArgs -q

if ($Html) { Write-Host "📄 HTML coverage at htmlcov/index.html" -ForegroundColor Cyan }

