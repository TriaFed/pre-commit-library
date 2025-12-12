# Dependencies Installation Guide

This guide helps developers install all necessary dependencies to run the pre-commit hooks on **macOS** and **Windows**.

## 🚀 Quick Setup Scripts

### macOS Setup

```bash
# Run this script to install all dependencies on macOS
curl -fsSL https://raw.githubusercontent.com/TriaFed/pre-commit-library/main/install-macos.sh | bash
```

### Windows Setup

```powershell
# Run this script to install all dependencies on Windows
irm https://raw.githubusercontent.com/TriaFed/pre-commit-library/main/install-windows.ps1 | iex
```

## 🎯 Selective Installation (Profile-Aware)

To avoid installing unnecessary tools, use the profile-aware installers which parse your `.pre-commit-config.yaml` and install only what’s needed.

macOS:

```bash
# Auto-detect from default config in current directory
bash install-macos.sh

# Force profiles (comma-separated) and optionally exclude
bash install-macos.sh --profiles python,node --exclude java

# Dry run to preview the plan
bash install-macos.sh --auto --config /abs/path/to/.pre-commit-config.yaml --dry-run
```

Windows (PowerShell):

```powershell
# Auto-detect from default config in current directory
./install-windows.ps1

# Force profiles (comma-separated) and optionally exclude
./install-windows.ps1 -Profiles python,node -Exclude java

# Dry run to preview the plan
./install-windows.ps1 -DryRun
```

Profiles: `core, python, node, dotnet, go, java, ansible, infrastructure`.

Notes:

- Optional tools like `trufflehog`, `hadolint`, and `cfn-lint` are installed only if the associated hooks are present in your config.
- The resolver (`scripts/resolve_deps.py`) can be pointed at any config with `--config` (macOS) or `-Config` (Windows).

## 📋 Manual Installation Instructions

### Core Requirements (Required for All)

#### 1. Python 3.8+

**macOS:**

```bash
# Using Homebrew
brew install python3

# Using pyenv
brew install pyenv
pyenv install 3.11.0
pyenv global 3.11.0
```

**Windows:**

```powershell
# Using winget
winget install Python.Python.3.11

# Using Chocolatey
choco install python

# Or download from: https://python.org/downloads/
```

#### 2. Git

**macOS:**

```bash
# Usually pre-installed, or:
brew install git
```

**Windows:**

```powershell
# Using winget
winget install Git.Git

# Using Chocolatey
choco install git
```

#### 3. Pre-commit

**Both platforms:**

```bash
pip install pre-commit
# or
pipx install pre-commit
```

### Language-Specific Dependencies

#### Python Development

**Both platforms:**

```bash
pip install black flake8 isort mypy bandit safety detect_secrets
```

#### AI-Powered Hooks (Optional)
**Both platforms:**
```bash
# Required for ai_commit_check hook
pip install opencode-ai rich

# Or install opencode CLI directly
npm install -g @sst/opencode
```

**Setup Opencode Authentication:**
```bash
# Authenticate with Opencode
opencode auth login
# Select: github-copilot

# Configure the AI model
# In the opencode interface, enter: /models
# Select: claude-sonnet-4.5
```

**⚠️ Required Security Configuration:**

Download the security configuration to your repository root:

**Setup:**

1. Copy the contents of [`examples/opencode.jsonc`](https://github.com/TriaFed/pre-commit-library/blob/main/examples/opencode.jsonc) from this repository
2. Create a file named `opencode.jsonc` in your repository root
3. Paste the contents into your `opencode.jsonc` file
4. Commit the configuration to your repository

**Optional:** Initialize AI instructions for your project by running `opencode` and typing `/init` in the OpenCode window.

The `opencode.jsonc` file is **required** and must deny dangerous operations:
- `webfetch: "deny"` - Blocks external network requests
- `aws *: "deny"` - Blocks AWS CLI commands
- `az *: "deny"` - Blocks Azure CLI commands
- `gcloud *: "deny"` - Blocks Google Cloud CLI commands
- `terraform *: "deny"` - Blocks Terraform commands
- `curl/wget *: "deny"` - Blocks curl and wget

Learn more: [OpenCode Permissions Documentation](https://opencode.ai/docs/permissions/)

**Environment Variables:**
```bash
# Configure AI hook behavior (optional)
export OPENCODE_PORT=61164          # Port for opencode server (default: 61164)
export OPENCODE_MODEL=claude-sonnet-4.5  # AI model to use (default: claude-sonnet-4.5)
export OPENCODE_PROVIDER=github-copilot  # AI provider (default: github-copilot)
export OPENCODE_TIMEOUT=90          # Server startup timeout in seconds (default: 90)
```

#### JavaScript/TypeScript/Node.js

**macOS:**

```bash
# Using Homebrew
brew install node

# Using nvm
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
nvm install --lts
```

**Windows:**

```powershell
# Using winget
winget install OpenJS.NodeJS

# Using Chocolatey
choco install nodejs

# Using nvs (Node Version Switcher)
winget install jasongin.nvs
```

**Global packages (both platforms):**

```bash
npm install -g eslint prettier typescript @angular/cli
```

#### .NET Development

**macOS:**

```bash
# Using Homebrew
brew install --cask dotnet

# Or download from: https://dotnet.microsoft.com/download
```

**Windows:**

```powershell
# Using winget
winget install Microsoft.DotNet.SDK.8

# Using Chocolatey
choco install dotnet

# Or download from: https://dotnet.microsoft.com/download
```

#### Go Development

**macOS:**

```bash
# Using Homebrew
brew install go

# Manual installation
curl -L https://go.dev/dl/go1.21.0.darwin-amd64.tar.gz | tar -C /usr/local -xz
export PATH=$PATH:/usr/local/go/bin
```

**Windows:**

```powershell
# Using winget
winget install GoLang.Go

# Using Chocolatey
choco install golang

# Or download from: https://golang.org/dl/
```

**Go tools (both platforms):**

```bash
go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest
go install github.com/securecodewarrior/gosec/v2/cmd/gosec@latest
go install honnef.co/go/tools/cmd/staticcheck@latest
```

#### Java Development

**macOS:**

```bash
# Using Homebrew
brew install openjdk@17

# Using SDKMAN
curl -s "https://get.sdkman.io" | bash
sdk install java 17.0.2-open
```

**Windows:**

```powershell
# Using winget
winget install Microsoft.OpenJDK.17

# Using Chocolatey
choco install openjdk17
```

**Build tools:**

```bash
# Maven
# macOS: brew install maven
# Windows: winget install Apache.Maven

# Gradle
# macOS: brew install gradle
# Windows: winget install Gradle.Gradle
```

#### Terraform/Infrastructure

**macOS:**

```bash
# Using Homebrew
brew install terraform tflint

# Using tfenv for version management
brew install tfenv
tfenv install 1.5.0
tfenv use 1.5.0
```

**Windows:**

```powershell
# Using winget
winget install Hashicorp.Terraform

# Using Chocolatey
choco install terraform tflint

# Or download from: https://terraform.io/downloads
```

#### Ansible

**Both platforms:**

```bash
# Using pip
pip install ansible ansible_lint

# Using pipx (recommended)
pipx install ansible
pipx install ansible_lint
```

### Security Scanning Tools

#### Multi-language SAST

**Both platforms:**

```bash
# Semgrep
pip install semgrep

# TruffleHog
# macOS: brew install trufflehog
# Windows: winget install trufflesecurity.trufflehog
# Both: go install github.com/trufflesecurity/trufflehog/v3@latest
```

#### Docker Tools

**macOS:**

```bash
# Using Homebrew
brew install hadolint

# Using Docker
docker pull hadolint/hadolint
```

**Windows:**

```powershell
# Using Chocolatey
choco install hadolint

# Using winget
winget install Hadolint.Hadolint

# Using Docker
docker pull hadolint/hadolint
```

### AWS Tools (Optional)

**Both platforms:**

```bash
# AWS CLI
pip install awscli

# CloudFormation tools
pip install cfn-lint
```

## 🔧 Tool Verification

After installation, verify tools are working:

```bash
# Core tools
python3 --version
git --version
pre-commit --version

# Python tools
black --version
flake8 --version
bandit --version

# Node.js tools
node --version
npm --version
eslint --version

# .NET tools
dotnet --version

# Go tools
go version
golangci-lint --version
gosec --help

# Infrastructure tools
terraform --version
ansible --version

# Security tools
semgrep --version
trufflehog --version
```

## 🐳 Docker Alternative

If you prefer not to install dependencies locally, most tools can run via Docker:

```bash
# Example: Run linting via Docker
docker run --rm -v $(pwd):/app -w /app node:18 npm install && npm run lint

# Example: Run Go checks via Docker
docker run --rm -v $(pwd):/app -w /app golang:1.21 go vet ./...

# Example: Run Python checks via Docker
docker run --rm -v $(pwd):/app -w /app python:3.11 pip install black && black --check .
```

## 🚨 Minimum Requirements by Hook Type

### Security-Only Setup (Minimal)

- Python 3.8+
- pip packages: `detect_secrets bandit safety semgrep`

### Full Stack Development

- All language runtimes (.NET, Go, Node.js, Python, Java)
- All linting tools
- Security scanning tools

### CI/CD Pipeline Setup

- Docker + pre-commit Docker images
- Or language-specific CI images with tools pre-installed

## 🔍 Troubleshooting

### Common Issues

**Windows PATH Issues:**

```powershell
# Add to PATH manually or use:
$env:PATH += ";C:\Program Files\dotnet"
$env:PATH += ";C:\Program Files\Go\bin"
```

**macOS Permission Issues:**

```bash
# Fix Python/pip permissions
sudo chown -R $(whoami) $(python3 -m site --user-base)

# Fix npm permissions
npm config set prefix ~/.npm-global
export PATH=~/.npm-global/bin:$PATH
```

**Tool Not Found After Installation:**

```bash
# Reload shell or source profile
source ~/.bashrc  # or ~/.zshrc
# or restart terminal
```

### Tool-Specific Alternatives

If primary tools aren't available, hooks will suggest alternatives:

- **golangci-lint** → falls back to `go vet` + `staticcheck`
- **ansible_lint** → falls back to `ansible-playbook --syntax-check`
- **hadolint** → falls back to basic Dockerfile checks

## 📱 IDE Integration

Many tools integrate with popular IDEs for real-time feedback:

- **VS Code**: Extensions for ESLint, Prettier, Go, .NET, Python
- **JetBrains**: Built-in support for most linters
- **Vim/Neovim**: ALE, coc.nvim plugins

This ensures developers catch issues before pre-commit even runs!
