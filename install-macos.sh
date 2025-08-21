#!/bin/bash
# macOS Dependency Installation Script for Pre-commit Hooks Library
# Supports macOS 10.15+ (Catalina and later)

set -e

echo "🍎 Installing dependencies for Pre-commit Hooks Library on macOS..."
echo "=================================================="

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "❌ This script is for macOS only"
    exit 1
fi

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to install Homebrew if not present
install_homebrew() {
    if ! command_exists brew; then
        echo "📦 Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        
        # Add to PATH for Apple Silicon Macs
        if [[ $(uname -m) == "arm64" ]]; then
            echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
            eval "$(/opt/homebrew/bin/brew shellenv)"
        fi
    else
        echo "✅ Homebrew already installed"
    fi
}

# Install core dependencies
install_core_deps() {
    echo ""
    echo "🔧 Installing core dependencies..."
    
    # Install Homebrew
    install_homebrew
    
    # Update Homebrew
    brew update
    
    # Install core tools
    if ! command_exists python3; then
        echo "🐍 Installing Python 3..."
        brew install python3
    else
        echo "✅ Python 3 already installed"
    fi
    
    if ! command_exists git; then
        echo "📚 Installing Git..."
        brew install git
    else
        echo "✅ Git already installed"
    fi
    
    # Install pre-commit
    if ! command_exists pre-commit; then
        echo "🪝 Installing pre-commit..."
        pip3 install pre-commit
    else
        echo "✅ pre-commit already installed"
    fi
}

# Install Python tools
install_python_tools() {
    echo ""
    echo "🐍 Installing Python development tools..."
    
    pip3 install --upgrade pip
    pip3 install black flake8 isort mypy bandit safety detect-secrets semgrep
    
    echo "✅ Python tools installed"
}

# Install Node.js and tools
install_nodejs_tools() {
    echo ""
    echo "📱 Installing Node.js and tools..."
    
    if ! command_exists node; then
        brew install node
    else
        echo "✅ Node.js already installed"
    fi
    
    # Install global packages
    npm install -g eslint prettier typescript @angular/cli
    
    echo "✅ Node.js tools installed"
}

# Install .NET
install_dotnet() {
    echo ""
    echo "⚡ Installing .NET..."
    
    if ! command_exists dotnet; then
        brew install --cask dotnet
    else
        echo "✅ .NET already installed"
    fi
    
    echo "✅ .NET installed"
}

# Install Go and tools
install_go_tools() {
    echo ""
    echo "🐹 Installing Go and tools..."
    
    if ! command_exists go; then
        brew install go
    else
        echo "✅ Go already installed"
    fi
    
    # Install Go tools
    go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest
    go install github.com/securecodewarrior/gosec/v2/cmd/gosec@latest
    go install honnef.co/go/tools/cmd/staticcheck@latest
    
    echo "✅ Go tools installed"
}

# Install Java
install_java() {
    echo ""
    echo "☕ Installing Java..."
    
    if ! command_exists java; then
        brew install openjdk@17
        # Link Java for macOS
        sudo ln -sfn /opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk /Library/Java/JavaVirtualMachines/openjdk-17.jdk
    else
        echo "✅ Java already installed"
    fi
    
    # Install build tools
    if ! command_exists mvn; then
        brew install maven
    fi
    
    if ! command_exists gradle; then
        brew install gradle
    fi
    
    echo "✅ Java tools installed"
}

# Install infrastructure tools
install_infra_tools() {
    echo ""
    echo "🏗️ Installing infrastructure tools..."
    
    # Terraform
    if ! command_exists terraform; then
        brew install terraform
    else
        echo "✅ Terraform already installed"
    fi
    
    # TFLint
    if ! command_exists tflint; then
        brew install tflint
    else
        echo "✅ TFLint already installed"
    fi
    
    # Hadolint (Docker linter)
    if ! command_exists hadolint; then
        brew install hadolint
    else
        echo "✅ Hadolint already installed"
    fi
    
    echo "✅ Infrastructure tools installed"
}

# Install Ansible
install_ansible() {
    echo ""
    echo "📋 Installing Ansible..."
    
    pip3 install ansible ansible-lint
    
    echo "✅ Ansible installed"
}

# Install security tools
install_security_tools() {
    echo ""
    echo "🛡️ Installing security tools..."
    
    # TruffleHog
    if ! command_exists trufflehog; then
        brew install trufflehog
    else
        echo "✅ TruffleHog already installed"
    fi
    
    # AWS CLI (optional)
    if ! command_exists aws; then
        echo "☁️ Installing AWS CLI..."
        pip3 install awscli
    else
        echo "✅ AWS CLI already installed"
    fi
    
    # CloudFormation tools
    pip3 install cfn-lint
    
    echo "✅ Security tools installed"
}

# Verify installations
verify_tools() {
    echo ""
    echo "🔍 Verifying installations..."
    echo "================================"
    
    tools=(
        "python3 --version"
        "git --version"
        "pre-commit --version"
        "black --version"
        "eslint --version"
        "dotnet --version"
        "go version"
        "java --version"
        "terraform --version"
        "ansible --version"
    )
    
    for tool in "${tools[@]}"; do
        if $tool >/dev/null 2>&1; then
            echo "✅ $tool"
        else
            echo "❌ $tool (not available)"
        fi
    done
}

# Add PATH exports to shell profile
setup_shell_profile() {
    echo ""
    echo "🐚 Setting up shell profile..."
    
    SHELL_PROFILE=""
    if [[ $SHELL == *"zsh"* ]]; then
        SHELL_PROFILE="$HOME/.zshrc"
    elif [[ $SHELL == *"bash"* ]]; then
        SHELL_PROFILE="$HOME/.bashrc"
    fi
    
    if [[ -n "$SHELL_PROFILE" ]]; then
        echo "# Go tools PATH" >> "$SHELL_PROFILE"
        echo 'export PATH=$PATH:$(go env GOPATH)/bin' >> "$SHELL_PROFILE"
        echo ""
        echo "✅ Added Go tools to PATH in $SHELL_PROFILE"
        echo "💡 Run 'source $SHELL_PROFILE' or restart your terminal"
    fi
}

# Main installation flow
main() {
    echo "Starting installation..."
    echo ""
    
    install_core_deps
    install_python_tools
    install_nodejs_tools
    install_dotnet
    install_go_tools
    install_java
    install_infra_tools
    install_ansible
    install_security_tools
    setup_shell_profile
    
    echo ""
    echo "🎉 Installation complete!"
    echo "================================"
    echo ""
    echo "Next steps:"
    echo "1. Restart your terminal or run: source ~/.zshrc (or ~/.bashrc)"
    echo "2. Verify tools with: pre-commit --version"
    echo "3. Set up pre-commit in your project:"
    echo "   cd your-project"
    echo "   pre-commit install"
    echo ""
    echo "📚 Documentation: https://github.com/TriaFed/pre-commit-library"
    
    verify_tools
}

# Run main function
main
