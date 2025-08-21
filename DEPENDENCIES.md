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
pip install black flake8 isort mypy bandit safety detect-secrets
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
pip install ansible ansible-lint

# Using pipx (recommended)
pipx install ansible
pipx install ansible-lint
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
- pip packages: `detect-secrets bandit safety semgrep`

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
- **ansible-lint** → falls back to `ansible-playbook --syntax-check`
- **hadolint** → falls back to basic Dockerfile checks

## 📱 IDE Integration

Many tools integrate with popular IDEs for real-time feedback:
- **VS Code**: Extensions for ESLint, Prettier, Go, .NET, Python
- **JetBrains**: Built-in support for most linters
- **Vim/Neovim**: ALE, coc.nvim plugins

This ensures developers catch issues before pre-commit even runs!
