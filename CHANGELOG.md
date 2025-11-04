# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- AI-powered commit validation hook (`ai_commit_check`) using Opencode AI
  - Reviews staged changes for code quality, security, and best practices
  - Interactive feedback with suggestions for improvements
  - Configurable via environment variables (model, provider, timeout)
- New dependencies: `opencode-ai>=0.1.0a36` and `rich>=13.7.0`

## [1.0.0] - 2024-01-XX

### Added
- Initial release of pre-commit hooks library for GenAI code validation
- Security hooks for detecting hardcoded credentials, URLs, and secrets
- GenAI-specific security validation patterns
- Multi-language support (Python, JavaScript/TypeScript, Java, Terraform, CloudFormation)
- Comprehensive linting and formatting hooks
- Vulnerability scanning with npm audit, Safety, Bandit
- SAST scanning with Semgrep
- Secret scanning with detect_secrets and TruffleHog
- Infrastructure as Code validation (Terraform, CloudFormation, Docker)
- Example configurations for different project types
- Comprehensive documentation and setup guides

### Security Hooks
- `detect_secrets` - Yelp's secret detection tool
- `truffhog` - Advanced secret scanning
- `hardcoded_urls` - Custom URL detection for GenAI code
- `hardcoded_credentials` - Custom credential detection
- `genai_security_check` - GenAI-specific security patterns
- `bandit` - Python security linter
- `safety_python` - Python dependency vulnerability scanner
- `npm_audit` - Node.js vulnerability scanner
- `yarn_audit` - Yarn vulnerability scanner
- `semgrep` - Multi-language SAST scanner

### Code Quality Hooks
- `python_black` - Python code formatter
- `python_flake8` - Python linter
- `python_isort` - Python import sorter
- `python_mypy` - Python type checker
- `eslint` - JavaScript/TypeScript linter
- `prettier` - Code formatter for multiple languages
- `typescript_check` - TypeScript compiler validation
- `angular_lint` - Angular-specific linting
- `java_checkstyle` - Java style checker
- `java_spotbugs` - Java bug detector

### Infrastructure Hooks
- `terraform_fmt` - Terraform formatter
- `terraform_validate` - Terraform validation
- `terraform_tflint` - Terraform linter
- `cloudformation_validate` - CloudFormation template validation
- `dockerfile_lint` - Dockerfile linting and security

### File Validation Hooks
- `check_yaml` - YAML syntax validation
- `check_json` - JSON syntax validation
- `check_xml` - XML syntax validation
- `check_toml` - TOML syntax validation
- `trailing_whitespace` - Remove trailing whitespace
- `end_of_file_fixer` - Ensure files end with newline
- `check_merge_conflict` - Check for merge conflicts
- `mixed_line_ending` - Check for mixed line endings
- `check-large-files` - Prevent large files from being committed
- `check_license` - Validate license headers in source files

### Documentation
- Comprehensive README with installation and usage instructions
- Example configurations for different project types
- Security best practices for GenAI development
- Troubleshooting guide
- Contributing guidelines

### Features
- Automatic tool detection and installation guidance
- Configurable severity levels and exclusion patterns
- Support for multiple build systems (Maven, Gradle, npm, yarn)
- Cross-platform compatibility (Linux, macOS, Windows)
- Integration with popular development tools and IDEs
