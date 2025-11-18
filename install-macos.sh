#!/bin/bash
# macOS Dependency Installation Script for Pre-commit Hooks Library
# Supports macOS 10.15+ (Catalina and later)

set -e

# Args and defaults
AUTO=1
CONFIG=""
EXPLICIT_PROFILES=""
EXCLUDE_PROFILES=""
DRY_RUN=0
ASSUME_YES=0
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

print_usage() {
    echo "Usage: install-macos.sh [--no-auto] [--config /abs/path/.pre-commit-config.yaml] [--profiles p1,p2] [--exclude p3] [--dry-run] [--assume-yes]"
}

parse_args() {
    while [ $# -gt 0 ]; do
        case "$1" in
            --auto)
                AUTO=1
                shift
                ;;
            --no-auto)
                AUTO=0
                shift
                ;;
            --config)
                CONFIG="$2"
                shift 2
                ;;
            --profiles)
                EXPLICIT_PROFILES="$2"
                shift 2
                ;;
            --exclude)
                EXCLUDE_PROFILES="$2"
                shift 2
                ;;
            --dry-run)
                DRY_RUN=1
                shift
                ;;
            --assume-yes)
                ASSUME_YES=1
                shift
                ;;
            -h|--help)
                print_usage
                exit 0
                ;;
            *)
                echo "Unknown option: $1"; print_usage; exit 1
                ;;
        esac
    done
}

resolve_with_config() {
    local config_path="$1"
    if ! command -v python3 >/dev/null 2>&1; then
        echo "⚠️  Python3 not available; cannot auto-resolve. Falling back to manual selection."
        return 1
    fi
    if [ ! -f "$SCRIPT_DIR/resolve_deps.py" ]; then
        echo "❌ Resolver script not found at $SCRIPT_DIR/resolve_deps.py"
        return 1
    fi
    local resolver_out
    if ! resolver_out=$(python3 "$SCRIPT_DIR/resolve_deps.py" --config "$config_path" --os darwin --profiles "$EXPLICIT_PROFILES" --exclude "$EXCLUDE_PROFILES" 2>/dev/null); then
        echo "⚠️  Resolver failed; falling back to manual selection."
        return 1
    fi
    echo "$resolver_out"
    return 0
}

prompt_profiles() {
    echo "Select profiles to install (comma-separated):"
    echo "  core, python, node, dotnet, go, java, ansible, infrastructure"
    if [ $ASSUME_YES -eq 1 ]; then
        # default minimal
        echo "core"
        return 0
    fi
    read -r selection
    echo "$selection"
}

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
        pip3 install --user pre-commit
    else
        echo "✅ pre-commit already installed"
    fi
}

# Install Python tools
install_python_tools() {
    echo ""
    echo "🐍 Installing Python development tools..."
    
    pip3 install --upgrade pip
    pip3 install --user black flake8 isort mypy bandit safety detect-secrets semgrep
    
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
    
    # Install global packages unless Yarn is detected in the project
    if [ -f yarn.lock ] || command -v yarn >/dev/null 2>&1; then
        echo "ℹ️  Yarn detected (yarn.lock or yarn CLI). Skipping npm -g installs for eslint/prettier/typescript/@angular/cli."
        echo "💡 Ensure these tools are available via devDependencies in your project."
    else
        npm install -g eslint prettier typescript @angular/cli
    fi
    
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
    go install github.com/securego/gosec/v2/cmd/gosec@latest
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
    
    pip3 install --user ansible ansible-lint
    
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
        pip3 install --user awscli
    else
        echo "✅ AWS CLI already installed"
    fi
    
    # CloudFormation tools
    pip3 install --user cfn-lint
    
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
        "dotnet --info"
        "go version"
        "java -version"
        "terraform --version"
        "ansible --version"
    )

    HAS_ERRORS=0
    
    for tool in "${tools[@]}"; do
        if $tool >/dev/null 2>&1; then
            echo "✅ $tool"
        else
            HAS_ERRORS=1
            echo "❌ $tool (not available)"
        fi
    done

    if [ $HAS_ERRORS -eq 1 ]; then
        echo ""
        echo "❗ Some tools are missing. Please check the errors above."
        echo "💡 You may need to add some tools to your PATH manually."
        echo "For Go tools, ensure $(go env GOPATH)/bin is in your PATH."
        echo "For Python tools like pre-commit, black, terraform, or ansible. Make sure $(python3 -m site --user-base)/bin is in your PATH."
    fi 
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
    
    parse_args "$@"

    selected_profiles=""
    tools_plan_json=""

    if [ $AUTO -eq 1 ]; then
        if [ -z "$CONFIG" ]; then
            if [ -f ".pre-commit-config.yaml" ]; then
                CONFIG="$(pwd)/.pre-commit-config.yaml"
            fi
        fi
        if [ -n "$CONFIG" ] && [ -f "$CONFIG" ]; then
            resolved=$(resolve_with_config "$CONFIG" || true)
            if [ -n "$resolved" ]; then
                tools_plan_json="$resolved"
                selected_profiles=$(echo "$resolved" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(",".join(d.get("profiles", [])))')
            fi
        fi
    fi

    if [ -z "$selected_profiles" ]; then
        if [ -n "$EXPLICIT_PROFILES" ]; then
            selected_profiles="$EXPLICIT_PROFILES"
        else
            selected_profiles=$(prompt_profiles)
        fi
    fi

    echo "📋 Selected profiles: $selected_profiles"

    if [ $DRY_RUN -eq 1 ]; then
        if [ -z "$tools_plan_json" ] && [ -n "$CONFIG" ] && command -v python3 >/dev/null 2>&1; then
            tools_plan_json=$(python3 "$SCRIPT_DIR/resolve_deps.py" --config "$CONFIG" --os darwin --profiles "$selected_profiles" --exclude "$EXCLUDE_PROFILES" 2>/dev/null || true)
        fi
        echo "🔎 Dry run - planned installs:"
        if [ -n "$tools_plan_json" ]; then
            echo "$tools_plan_json"
        else
            echo "(Resolver unavailable; will install groups corresponding to: $selected_profiles)"
        fi
        exit 0
    fi

    install_core_deps

    # Dispatch per selected profiles
    case ",$selected_profiles," in
        *",core,"*) install_security_tools ;; 
    esac
    case ",$selected_profiles," in
        *",python,"*) install_python_tools ;;
    esac
    case ",$selected_profiles," in
        *",node,"*) install_nodejs_tools ;;
    esac
    case ",$selected_profiles," in
        *",dotnet,"*) install_dotnet ;;
    esac
    case ",$selected_profiles," in
        *",go,"*) install_go_tools ;;
    esac
    case ",$selected_profiles," in
        *",java,"*) install_java ;;
    esac
    case ",$selected_profiles," in
        *",infrastructure,"*) install_infra_tools ;;
    esac
    case ",$selected_profiles," in
        *",ansible,"*) install_ansible ;;
    esac

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
    
    # Build a minimal verification list based on selected profiles
    VERIFY_CMDS=(
        "python3 --version"
        "git --version"
        "pre-commit --version"
    )
    case ",$selected_profiles," in
        *",python,"*) VERIFY_CMDS+=("black --version" "flake8 --version" "bandit --version") ;;
    esac
    case ",$selected_profiles," in
        *",node,"*) VERIFY_CMDS+=("node --version" "npm --version" "eslint --version") ;;
    esac
    case ",$selected_profiles," in
        *",dotnet,"*) VERIFY_CMDS+=("dotnet --info") ;;
    esac
    case ",$selected_profiles," in
        *",go,"*) VERIFY_CMDS+=("go version" "golangci-lint --version") ;;
    esac
    case ",$selected_profiles," in
        *",java,"*) VERIFY_CMDS+=("java -version" "mvn -v" "gradle -v") ;;
    esac
    case ",$selected_profiles," in
        *",infrastructure,"*) VERIFY_CMDS+=("terraform --version" "tflint --version" "hadolint --version" "aws --version") ;;
    esac
    case ",$selected_profiles," in
        *",ansible,"*) VERIFY_CMDS+=("ansible --version" "ansible-lint --version") ;;
    esac

    echo ""
    echo "🔍 Verifying selected tools..."
    echo "================================"
    HAS_ERRORS=0
    for cmd in "${VERIFY_CMDS[@]}"; do
        if $cmd >/dev/null 2>&1; then
            echo "✅ $cmd"
        else
            HAS_ERRORS=1
            echo "❌ $cmd (not available)"
        fi
    done
    if [ $HAS_ERRORS -eq 1 ]; then
        echo ""
        echo "❗ Some tools are missing. You may need to add them to PATH or re-run the installer."
    fi 
}

# Run main function
main
