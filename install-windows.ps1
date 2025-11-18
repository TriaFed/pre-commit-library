# Windows Dependency Installation Script for Pre-commit Hooks Library
# Supports Windows 10/11 with PowerShell 5.1+

param(
    [switch]$SkipChocolatey,
    [switch]$UseWinget,
    [switch]$Verbose,
    [switch]$Auto = $true,
    [string]$Config,
    [string]$Profiles,
    [string]$Exclude,
    [switch]$DryRun,
    [switch]$Yes
)

# Set error action
$ErrorActionPreference = "Stop"

Write-Host "🪟 Installing dependencies for Pre-commit Hooks Library on Windows..." -ForegroundColor Cyan
Write-Host "====================================================================" -ForegroundColor Cyan

# Function to check if running as administrator
function Test-Administrator {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# Function to check if a command exists
function Test-CommandExists {
    param([string]$Command)
    try {
        Get-Command $Command -ErrorAction Stop | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

# Function to install Chocolatey
function Install-Chocolatey {
    if (-not (Test-CommandExists "choco")) {
        Write-Host "📦 Installing Chocolatey..." -ForegroundColor Yellow
        Set-ExecutionPolicy Bypass -Scope Process -Force
        [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
        Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
        
        # Refresh environment
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    }
    else {
        Write-Host "✅ Chocolatey already installed" -ForegroundColor Green
    }
}

# Function to install via winget
function Install-ViaWinget {
    param([string]$Package, [string]$Name)
    
    if (Test-CommandExists "winget") {
        Write-Host "📦 Installing $Name via winget..." -ForegroundColor Yellow
        try {
            winget install $Package --accept-package-agreements --accept-source-agreements
            Write-Host "✅ $Name installed via winget" -ForegroundColor Green
        }
        catch {
            Write-Host "❌ Failed to install $Name via winget: $_" -ForegroundColor Red
            return $false
        }
    }
    else {
        Write-Host "❌ winget not available" -ForegroundColor Red
        return $false
    }
    return $true
}

# Function to install via Chocolatey
function Install-ViaChocolatey {
    param([string]$Package, [string]$Name)
    
    Write-Host "📦 Installing $Name via Chocolatey..." -ForegroundColor Yellow
    try {
        choco install $Package -y
        Write-Host "✅ $Name installed via Chocolatey" -ForegroundColor Green
    }
    catch {
        Write-Host "❌ Failed to install $Name via Chocolatey: $_" -ForegroundColor Red
        return $false
    }
    return $true
}

# Function to install core dependencies
function Install-CoreDependencies {
    Write-Host "`n🔧 Installing core dependencies..." -ForegroundColor Blue
    
    # Install package manager
    if ($UseWinget) {
        Write-Host "Using winget for installations..." -ForegroundColor Cyan
    }
    elseif (-not $SkipChocolatey) {
        Install-Chocolatey
    }
    
    # Install Python
    if (-not (Test-CommandExists "python")) {
        if ($UseWinget) {
            Install-ViaWinget "Python.Python.3.11" "Python 3.11"
        }
        else {
            Install-ViaChocolatey "python" "Python"
        }
    }
    else {
        Write-Host "✅ Python already installed" -ForegroundColor Green
    }
    
    # Install Git
    if (-not (Test-CommandExists "git")) {
        if ($UseWinget) {
            Install-ViaWinget "Git.Git" "Git"
        }
        else {
            Install-ViaChocolatey "git" "Git"
        }
    }
    else {
        Write-Host "✅ Git already installed" -ForegroundColor Green
    }
    
    # Refresh PATH
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    
    # Install pre-commit
    if (-not (Test-CommandExists "pre-commit")) {
        Write-Host "🪝 Installing pre-commit..." -ForegroundColor Yellow
        python -m pip install pre-commit
    }
    else {
        Write-Host "✅ pre-commit already installed" -ForegroundColor Green
    }
}

# Function to install Python tools
function Install-PythonTools {
    Write-Host "`n🐍 Installing Python development tools..." -ForegroundColor Blue
    
    python -m pip install --upgrade pip
    python -m pip install black flake8 isort mypy bandit safety detect-secrets semgrep
    
    Write-Host "✅ Python tools installed" -ForegroundColor Green
}

# Function to install Node.js tools
function Install-NodeJSTools {
    Write-Host "`n📱 Installing Node.js and tools..." -ForegroundColor Blue
    
    if (-not (Test-CommandExists "node")) {
        if ($UseWinget) {
            Install-ViaWinget "OpenJS.NodeJS" "Node.js"
        }
        else {
            Install-ViaChocolatey "nodejs" "Node.js"
        }
        
        # Refresh PATH
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    }
    else {
        Write-Host "✅ Node.js already installed" -ForegroundColor Green
    }
    
    # Install global packages unless Yarn is detected in the project
    $yarnLockPresent = Test-Path (Join-Path (Get-Location) "yarn.lock")
    $yarnCliPresent = (Test-CommandExists "yarn")
    if ($yarnLockPresent -or $yarnCliPresent) {
        Write-Host "ℹ️  Yarn detected (yarn.lock or yarn CLI). Skipping npm -g installs for eslint/prettier/typescript/@angular/cli." -ForegroundColor Yellow
        Write-Host "💡 Ensure these tools are available via devDependencies in your project." -ForegroundColor Yellow
    } else {
        npm install -g eslint prettier typescript "@angular/cli"
    }
    
    Write-Host "✅ Node.js tools installed" -ForegroundColor Green
}

# Function to install .NET
function Install-DotNet {
    Write-Host "`n⚡ Installing .NET..." -ForegroundColor Blue
    
    if (-not (Test-CommandExists "dotnet")) {
        if ($UseWinget) {
            Install-ViaWinget "Microsoft.DotNet.SDK.8" ".NET SDK"
        }
        else {
            Install-ViaChocolatey "dotnet" ".NET"
        }
    }
    else {
        Write-Host "✅ .NET already installed" -ForegroundColor Green
    }
}

# Function to install Go and tools
function Install-GoTools {
    Write-Host "`n🐹 Installing Go and tools..." -ForegroundColor Blue
    
    if (-not (Test-CommandExists "go")) {
        if ($UseWinget) {
            Install-ViaWinget "GoLang.Go" "Go"
        }
        else {
            Install-ViaChocolatey "golang" "Go"
        }
        
        # Refresh PATH
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    }
    else {
        Write-Host "✅ Go already installed" -ForegroundColor Green
    }
    
    # Install Go tools
    go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest
    go install github.com/securego/gosec/v2/cmd/gosec@latest
    go install honnef.co/go/tools/cmd/staticcheck@latest
    
    Write-Host "✅ Go tools installed" -ForegroundColor Green
}

# Function to install Java
function Install-Java {
    Write-Host "`n☕ Installing Java..." -ForegroundColor Blue
    
    if (-not (Test-CommandExists "java")) {
        if ($UseWinget) {
            Install-ViaWinget "Microsoft.OpenJDK.17" "OpenJDK 17"
        }
        else {
            Install-ViaChocolatey "openjdk17" "OpenJDK 17"
        }
    }
    else {
        Write-Host "✅ Java already installed" -ForegroundColor Green
    }
    
    # Install build tools
    if (-not (Test-CommandExists "mvn")) {
        if ($UseWinget) {
            Install-ViaWinget "Apache.Maven" "Maven"
        }
        else {
            Install-ViaChocolatey "maven" "Maven"
        }
    }
    
    if (-not (Test-CommandExists "gradle")) {
        if ($UseWinget) {
            Install-ViaWinget "Gradle.Gradle" "Gradle"
        }
        else {
            Install-ViaChocolatey "gradle" "Gradle"
        }
    }
    
    Write-Host "✅ Java tools installed" -ForegroundColor Green
}

# Function to install infrastructure tools
function Install-InfraTools {
    Write-Host "`n🏗️ Installing infrastructure tools..." -ForegroundColor Blue
    
    # Terraform
    if (-not (Test-CommandExists "terraform")) {
        if ($UseWinget) {
            Install-ViaWinget "Hashicorp.Terraform" "Terraform"
        }
        else {
            Install-ViaChocolatey "terraform" "Terraform"
        }
    }
    else {
        Write-Host "✅ Terraform already installed" -ForegroundColor Green
    }
    
    # TFLint
    if (-not (Test-CommandExists "tflint")) {
        Install-ViaChocolatey "tflint" "TFLint"
    }
    else {
        Write-Host "✅ TFLint already installed" -ForegroundColor Green
    }
    
    # Hadolint
    if (-not (Test-CommandExists "hadolint")) {
        if ($UseWinget) {
            Install-ViaWinget "Hadolint.Hadolint" "Hadolint"
        }
        else {
            Install-ViaChocolatey "hadolint" "Hadolint"
        }
    }
    else {
        Write-Host "✅ Hadolint already installed" -ForegroundColor Green
    }
    
    Write-Host "✅ Infrastructure tools installed" -ForegroundColor Green
}

# Function to install Ansible
function Install-Ansible {
    Write-Host "`n📋 Installing Ansible..." -ForegroundColor Blue
    
    python -m pip install ansible ansible-lint
    
    Write-Host "✅ Ansible installed" -ForegroundColor Green
}

# Function to install security tools
function Install-SecurityTools {
    Write-Host "`n🛡️ Installing security tools..." -ForegroundColor Blue
    
    # TruffleHog
    if (-not (Test-CommandExists "trufflehog")) {
        if ($UseWinget) {
            Install-ViaWinget "trufflesecurity.trufflehog" "TruffleHog"
        }
        else {
            # Fallback to Go install
            go install github.com/trufflesecurity/trufflehog/v3@latest
        }
    }
    else {
        Write-Host "✅ TruffleHog already installed" -ForegroundColor Green
    }
    
    # AWS CLI
    if (-not (Test-CommandExists "aws")) {
        Write-Host "☁️ Installing AWS CLI..." -ForegroundColor Yellow
        python -m pip install awscli
    }
    else {
        Write-Host "✅ AWS CLI already installed" -ForegroundColor Green
    }
    
    # CloudFormation tools
    python -m pip install cfn-lint
    
    Write-Host "✅ Security tools installed" -ForegroundColor Green
}

# Function to verify installations
function Test-Installations {
    Write-Host "`n🔍 Verifying installations..." -ForegroundColor Blue
    Write-Host "================================" -ForegroundColor Blue
    
    $tools = @(
        @{Command = "python"; Args = "--version"; Name = "Python"}
        @{Command = "git"; Args = "--version"; Name = "Git"}
        @{Command = "pre-commit"; Args = "--version"; Name = "pre-commit"}
        @{Command = "black"; Args = "--version"; Name = "Black"}
        @{Command = "eslint"; Args = "--version"; Name = "ESLint"}
        @{Command = "dotnet"; Args = "--version"; Name = ".NET"}
        @{Command = "go"; Args = "version"; Name = "Go"}
        @{Command = "java"; Args = "--version"; Name = "Java"}
        @{Command = "terraform"; Args = "--version"; Name = "Terraform"}
        @{Command = "ansible"; Args = "--version"; Name = "Ansible"}
    )
    
    foreach ($tool in $tools) {
        try {
            & $tool.Command $tool.Args.Split() > $null 2>&1
            Write-Host "✅ $($tool.Name)" -ForegroundColor Green
        }
        catch {
            Write-Host "❌ $($tool.Name) (not available)" -ForegroundColor Red
        }
    }
}

# Function to setup environment
function Set-Environment {
    Write-Host "`n🔧 Setting up environment..." -ForegroundColor Blue
    
    # Add Go tools to PATH
    $goPath = go env GOPATH
    if ($goPath) {
        $goBinPath = Join-Path $goPath "bin"
        $currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
        if ($currentPath -notlike "*$goBinPath*") {
            [Environment]::SetEnvironmentVariable("Path", "$currentPath;$goBinPath", "User")
            Write-Host "✅ Added Go tools to PATH" -ForegroundColor Green
        }
    }
    
    Write-Host "💡 Please restart your terminal to ensure all PATH changes take effect" -ForegroundColor Yellow
}

# Main function
function Main {
    try {
        Write-Host "Starting installation..." -ForegroundColor Cyan
        Write-Host ""
        
        # Resolve profiles via resolver if requested
        $selectedProfiles = $null
        $resolverResult = $null
        $scriptDir = Join-Path $PSScriptRoot "scripts"
        if ($Auto) {
            if (-not $Config) {
                $defaultConfig = Join-Path (Get-Location) ".pre-commit-config.yaml"
                if (Test-Path $defaultConfig) { $Config = $defaultConfig }
            }
            $resolverPath = Join-Path $scriptDir "resolve_deps.py"
            if ($Config -and (Test-Path $Config) -and (Test-Path $resolverPath)) {
                try {
                    $profilesArg = if ($Profiles) { $Profiles } else { "" }
                    $excludeArg = if ($Exclude) { $Exclude } else { "" }
                    $py = Get-Command python -ErrorAction SilentlyContinue
                    if (-not $py) { $py = Get-Command python3 -ErrorAction SilentlyContinue }
                    if ($py) {
                        $resolverJson = & $py.Path $resolverPath --config $Config --os windows --profiles $profilesArg --exclude $excludeArg 2>$null
                        if ($LASTEXITCODE -eq 0 -and $resolverJson) {
                            $resolverResult = $resolverJson | ConvertFrom-Json
                            $selectedProfiles = ($resolverResult.profiles -join ",")
                        }
                    } else {
                        Write-Host "⚠️  Python not available; cannot auto-resolve. Falling back to manual selection." -ForegroundColor Yellow
                    }
                } catch {
                    Write-Host "⚠️  Resolver failed; falling back to manual selection." -ForegroundColor Yellow
                }
            }
        }

        if (-not $selectedProfiles) {
            if ($Profiles) {
                $selectedProfiles = $Profiles
            } else {
                if ($Yes) {
                    $selectedProfiles = "core"
                } else {
                    Write-Host "Select profiles to install (comma-separated):" -ForegroundColor Cyan
                    Write-Host "  core, python, node, dotnet, go, java, ansible, infrastructure" -ForegroundColor White
                    $selectedProfiles = Read-Host
                }
            }
        }

        Write-Host "📋 Selected profiles: $selectedProfiles" -ForegroundColor Cyan

        if ($DryRun) {
            if (-not $resolverResult -and $Config) {
                $resolverPath = Join-Path $scriptDir "resolve_deps.py"
                $py = Get-Command python -ErrorAction SilentlyContinue
                if (-not $py) { $py = Get-Command python3 -ErrorAction SilentlyContinue }
                if ($py -and (Test-Path $resolverPath)) {
                    $resolverJson = & $py.Path $resolverPath --config $Config --os windows --profiles $selectedProfiles --exclude ($Exclude ?? "") 2>$null
                    if ($LASTEXITCODE -eq 0 -and $resolverJson) { $resolverResult = $resolverJson | ConvertFrom-Json }
                }
            }
            Write-Host "🔎 Dry run - planned installs:" -ForegroundColor Cyan
            if ($resolverResult) {
                $resolverResult | ConvertTo-Json -Depth 6 | Write-Output
            } else {
                Write-Host "(Resolver unavailable; will install groups corresponding to: $selectedProfiles)" -ForegroundColor Yellow
            }
            return
        }

        if (-not (Test-Administrator)) {
            Write-Host "⚠️  Running without administrator privileges. Some installations may fail." -ForegroundColor Yellow
            Write-Host "💡 Consider running as administrator for best results." -ForegroundColor Yellow
            Write-Host ""
        }
        
        Install-CoreDependencies

        $profilesList = "," + $selectedProfiles + ","
        if ($profilesList -like "*,core,*") { Install-SecurityTools }
        if ($profilesList -like "*,python,*") { Install-PythonTools }
        if ($profilesList -like "*,node,*") { Install-NodeJSTools }
        if ($profilesList -like "*,dotnet,*") { Install-DotNet }
        if ($profilesList -like "*,go,*") { Install-GoTools }
        if ($profilesList -like "*,java,*") { Install-Java }
        if ($profilesList -like "*,infrastructure,*") { Install-InfraTools }
        if ($profilesList -like "*,ansible,*") { Install-Ansible }

        Set-Environment
        
        Write-Host "`n🎉 Installation complete!" -ForegroundColor Green
        Write-Host "================================" -ForegroundColor Green
        Write-Host ""
        Write-Host "Next steps:" -ForegroundColor Cyan
        Write-Host "1. Restart your terminal/PowerShell" -ForegroundColor White
        Write-Host "2. Verify tools with: pre-commit --version" -ForegroundColor White
        Write-Host "3. Set up pre-commit in your project:" -ForegroundColor White
        Write-Host "   cd your-project" -ForegroundColor White
        Write-Host "   pre-commit install" -ForegroundColor White
        Write-Host ""
        Write-Host "📚 Documentation: https://github.com/TriaFed/pre-commit-library" -ForegroundColor Cyan
        
        # Build verification commands based on selected profiles
        $verifyCmds = @(
            @{Command = "python"; Args = "--version"; Name = "Python"},
            @{Command = "git"; Args = "--version"; Name = "Git"},
            @{Command = "pre-commit"; Args = "--version"; Name = "pre-commit"}
        )
        if ($profilesList -like "*,python,*") { $verifyCmds += @(@{Command="black";Args="--version";Name="Black"}, @{Command="flake8";Args="--version";Name="Flake8"}) }
        if ($profilesList -like "*,node,*") { $verifyCmds += @(@{Command="node";Args="--version";Name="Node"}, @{Command="npm";Args="--version";Name="npm"}, @{Command="eslint";Args="--version";Name="ESLint"}) }
        if ($profilesList -like "*,dotnet,*") { $verifyCmds += @(@{Command="dotnet";Args="--version";Name=".NET"}) }
        if ($profilesList -like "*,go,*") { $verifyCmds += @(@{Command="go";Args="version";Name="Go"}, @{Command="golangci-lint";Args="--version";Name="golangci-lint"}) }
        if ($profilesList -like "*,java,*") { $verifyCmds += @(@{Command="java";Args="--version";Name="Java"}, @{Command="mvn";Args="-v";Name="Maven"}, @{Command="gradle";Args="-v";Name="Gradle"}) }
        if ($profilesList -like "*,infrastructure,*") { $verifyCmds += @(@{Command="terraform";Args="--version";Name="Terraform"}, @{Command="tflint";Args="--version";Name="TFLint"}, @{Command="hadolint";Args="--version";Name="Hadolint"}, @{Command="aws";Args="--version";Name="AWS CLI"}) }
        if ($profilesList -like "*,ansible,*") { $verifyCmds += @(@{Command="ansible";Args="--version";Name="Ansible"}, @{Command="ansible-lint";Args="--version";Name="ansible-lint"}) }

        Write-Host "`n🔍 Verifying selected tools..." -ForegroundColor Blue
        Write-Host "================================" -ForegroundColor Blue
        foreach ($tool in $verifyCmds) {
            try {
                & $tool.Command $tool.Args.Split() > $null 2>&1
                Write-Host "✅ $($tool.Name)" -ForegroundColor Green
            }
            catch {
                Write-Host "❌ $($tool.Name) (not available)" -ForegroundColor Red
            }
        }
    }
    catch {
        Write-Host "❌ Installation failed: $_" -ForegroundColor Red
        exit 1
    }
}

# Run main function
Main
