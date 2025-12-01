#!/usr/bin/env python3
"""
AI-powered commit validation using Opencode AI.
Reviews staged changes for code quality, security, and best practices.
"""

from opencode_ai import Opencode
from typing import Optional, Iterable
import subprocess
import sys
import time
import socket
import os
from datetime import datetime
from pathlib import Path

try:
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
except ImportError:
    Console = None
    Markdown = None
    Panel = None

def find_available_port(start_port=61164, max_attempts=10):
    for i in range(max_attempts):
        port = start_port + i
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(('localhost', port))
            sock.close()
            return port
        except OSError:
            continue
    return None

def wait_for_port(port, timeout=30):
    start = time.time()
    while time.time() - start < timeout:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            sock.connect(('localhost', port))
            sock.close()
            return True
        except (socket.error, socket.timeout):
            time.sleep(0.5)
    return False

def main():
    OPENCODE_PORT = int(os.getenv('OPENCODE_PORT', '61164'))
    OPENCODE_MODEL = os.getenv('OPENCODE_MODEL', 'github-copilot/claude-sonnet-4-5')
    OPENCODE_PROVIDER = os.getenv('OPENCODE_PROVIDER', 'github-copilot')
    OPENCODE_TIMEOUT = int(os.getenv('OPENCODE_TIMEOUT', '90'))
    OPENCODE_BEDROCK_REGION = os.getenv('OPENCODE_BEDROCK_REGION', 'us-east-1')

    if not (1024 <= OPENCODE_PORT <= 65535):
        print(f"Error: Invalid port {OPENCODE_PORT}. Port must be between 1024 and 65535.", file=sys.stderr)
        return 3

    if not (1 <= OPENCODE_TIMEOUT <= 300):
        print(f"Error: Invalid timeout {OPENCODE_TIMEOUT}. Timeout must be between 1 and 300 seconds.", file=sys.stderr)
        return 3

    # Validate Bedrock region if using Bedrock provider
    if OPENCODE_PROVIDER == 'bedrock':
        if not OPENCODE_BEDROCK_REGION:
            print("Error: OPENCODE_BEDROCK_REGION environment variable is required when using bedrock provider.", file=sys.stderr)
            print("", file=sys.stderr)
            print("Amazon Bedrock requires explicit region configuration for security and compliance.", file=sys.stderr)
            print("", file=sys.stderr)
            print("Allowed regions:", file=sys.stderr)
            print("  - us-east-1 (US East - N. Virginia)", file=sys.stderr)
            print("  - us-gov-west-1 (AWS GovCloud US-West)", file=sys.stderr)
            print("  - us-gov-east-1 (AWS GovCloud US-East)", file=sys.stderr)
            print("", file=sys.stderr)
            print("To use Amazon Bedrock:", file=sys.stderr)
            print("  1. Authenticate to AWS with the correct region:", file=sys.stderr)
            print("     aws configure set region us-east-1", file=sys.stderr)
            print("", file=sys.stderr)
            print("  2. Set the region environment variable:", file=sys.stderr)
            print("     export OPENCODE_BEDROCK_REGION=us-east-1", file=sys.stderr)
            print("", file=sys.stderr)
            print("  3. Authenticate with OpenCode:", file=sys.stderr)
            print("     opencode auth login", file=sys.stderr)
            print("     Select: Amazon Bedrock", file=sys.stderr)
            print("", file=sys.stderr)
            return 3
        
        # Validate region is in allowed list
        allowed_regions = ['us-east-1']
        is_govcloud = OPENCODE_BEDROCK_REGION.startswith('us-gov-')
        
        if not (OPENCODE_BEDROCK_REGION in allowed_regions or is_govcloud):
            print(f"Error: Amazon Bedrock region '{OPENCODE_BEDROCK_REGION}' is not allowed.", file=sys.stderr)
            print("", file=sys.stderr)
            print("For security and compliance reasons, only the following regions are permitted:", file=sys.stderr)
            print("  ✓ us-east-1 (US East - N. Virginia)", file=sys.stderr)
            print("  ✓ us-gov-* (AWS GovCloud regions)", file=sys.stderr)
            print("", file=sys.stderr)
            print(f"Current region: {OPENCODE_BEDROCK_REGION}", file=sys.stderr)
            print("", file=sys.stderr)
            print("To fix:", file=sys.stderr)
            print("  export OPENCODE_BEDROCK_REGION=us-east-1", file=sys.stderr)
            print("", file=sys.stderr)
            return 3

    serve_process = None
    try:
        repo_root = subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], text=True).strip()
        
        # Use the bundled opencode.jsonc from the hooks directory
        hook_script_path = Path(__file__).resolve()
        bundled_config_path = hook_script_path.parent / 'opencode.jsonc'
        
        # Verify bundled config exists
        if not bundled_config_path.exists():
            print(f"Error: Bundled config not found at {bundled_config_path}", file=sys.stderr)
            print("This is a bug in the pre-commit hook installation.", file=sys.stderr)
            return 3
        
        # Set OPENCODE_CONFIG to force OpenCode to use our bundled config
        os.environ['OPENCODE_CONFIG'] = str(bundled_config_path)
        print(f"✓ Using bundled security configuration: {bundled_config_path}", file=sys.stderr)
        
        available_port = find_available_port(OPENCODE_PORT)
        if not available_port:
            print(f"Error: No available ports found starting from port {OPENCODE_PORT}. "
                  f"Please check if ports {OPENCODE_PORT}-{OPENCODE_PORT+9} are available.", file=sys.stderr)
            return 3

        if available_port != OPENCODE_PORT:
            OPENCODE_PORT = available_port

        OPENCODE_BASE_URL = f'http://127.0.0.1:{OPENCODE_PORT}'
        os.environ['OPENCODE_BASE_URL'] = OPENCODE_BASE_URL

        # Set AWS region environment variables for Bedrock if needed
        if OPENCODE_PROVIDER == 'bedrock':
            os.environ['AWS_DEFAULT_REGION'] = OPENCODE_BEDROCK_REGION
            os.environ['AWS_REGION'] = OPENCODE_BEDROCK_REGION

        try:
            serve_process = subprocess.Popen(
                ['opencode', 'serve', '--port', str(OPENCODE_PORT)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=repo_root  # Run in repo root so it can see git diffs
            )
        except FileNotFoundError:
            print("Error: opencode is not installed.", file=sys.stderr)
            print("", file=sys.stderr)
            print("To install opencode:", file=sys.stderr)
            print("  Visit: https://opencode.ai", file=sys.stderr)
            print("", file=sys.stderr)
            print("After installation, authenticate with:", file=sys.stderr)
            print("  opencode auth login", file=sys.stderr)
            print("  Select: GitHub Public", file=sys.stderr)
            print("", file=sys.stderr)
            return 3

        if not wait_for_port(OPENCODE_PORT, timeout=OPENCODE_TIMEOUT):
            stdout, stderr = serve_process.communicate(timeout=5)
            error_msg = stderr.decode() if stderr else "Unknown error"
            print(f"Error: Opencode server failed to start within {OPENCODE_TIMEOUT} seconds.", file=sys.stderr)
            print(f"Server error: {error_msg}", file=sys.stderr)
            print("\nTroubleshooting:", file=sys.stderr)
            print("  1. Install opencode: Visit https://opencode.ai", file=sys.stderr)
            print("  2. Authenticate: opencode auth login (select GitHub Public)", file=sys.stderr)
            print("  3. Increase timeout: export OPENCODE_TIMEOUT=120", file=sys.stderr)
            return 3

        client = Opencode()

        repo_name = os.path.basename(repo_root)
        commit_hash = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'], text=True).strip()
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        session_name = f"Commit Review - {repo_name} {commit_hash} - {timestamp}"

        new_session = client.session.create(
            extra_body={
                'name': session_name,
            }
        )

        new_session_id = new_session.id

        # Determine review mode: pre-commit (staged changes) or pre-push (branch comparison)
        try:
            staged_diff = subprocess.check_output(
                ['git', 'diff', '--cached', '--name-only'],
                text=True,
                cwd=repo_root
            ).strip()
            has_staged_changes = bool(staged_diff)
        except subprocess.CalledProcessError:
            has_staged_changes = False

        # Determine which mode and construct appropriate prompt
        if has_staged_changes:
            # Pre-commit mode: review staged changes
            review_mode = "pre-commit"
            review_target = "the staged changes for this commit"
            review_context = """
            **REVIEW MODE:** Pre-commit (staged changes)
            
            Use `git diff --cached` to see the staged changes that are about to be committed.
            """
        else:
            # Pre-push mode: compare current branch to origin/main or origin/master
            review_mode = "pre-push"
            
            # Determine the default branch (main or master)
            default_branch = None
            for branch in ['main', 'master']:
                try:
                    subprocess.check_output(
                        ['git', 'rev-parse', '--verify', f'origin/{branch}'],
                        stderr=subprocess.DEVNULL,
                        text=True,
                        cwd=repo_root
                    )
                    default_branch = branch
                    break
                except subprocess.CalledProcessError:
                    continue
            
            if not default_branch:
                print("Error: Could not find origin/main or origin/master branch for comparison.", file=sys.stderr)
                print("Please ensure you have a remote tracking branch set up.", file=sys.stderr)
                return 3
            
            review_target = f"all changes in the current branch compared to origin/{default_branch}"
            review_context = f"""
            **REVIEW MODE:** Pre-push (branch comparison)
            
            Use `git diff origin/{default_branch}...HEAD` to see all changes in the current branch 
            that differ from origin/{default_branch}. Review ALL commits and changes since branching.
            """

        new_session_chat = client.session.chat(id=new_session_id, parts=[
            {'type': 'text', 'text': f"""
            Review {review_target}, focusing on these critical issues:
            {review_context}
            **CRITICAL ISSUES TO CHECK:**
            1. **Unused Variables/Imports/Code**: Variables declared but never used, unused imports, dead code
            2. **Logic Bugs**: Incorrect implementations, missing null checks, wrong conditions, off-by-one errors
            3. **Security Issues**: Input validation missing, potential injection vulnerabilities, hardcoded credentials
            4. **Performance Problems**: Inefficient patterns, potential memory leaks, unnecessary computations
            5. **Type/Syntax Issues**: Incorrect types, missing error handling, type mismatches
            6. **Configuration Issues**: Problems in config files (JSON, YAML, Jenkinsfile, package.json, etc.)
            7. **Build/CI Issues**: Problems with build scripts, pipelines, dependencies

            **REVIEW INSTRUCTIONS:**
            - Analyze BOTH the diff changes AND the complete file contents provided
            - Focus ONLY on code that has actual problems
            - Pay special attention to variables that are declared but never referenced
            - Look for imports that aren't used anywhere in the file
            - Check for functions or code blocks that serve no purpose
            - Review configuration files thoroughly for syntax and logic issues
            - Consider how changes in one file might affect other files
            - If you find unused variables, clearly state which variables are unused and suggest removing them

            **RESPONSE FORMAT:**
            - If you find critical issues that should block the commit, start your response with "-COMMIT REJECTED-"
              followed by a clear explanation of the blocking issues with specific file names and line numbers
            - If the code has no significant issues, respond with exactly: "✅ **Code looks good!** No significant issues found."
            - If you have suggestions but no blockers, provide constructive feedback with specific suggestions
             """}
        ], model_id=OPENCODE_MODEL, provider_id=OPENCODE_PROVIDER)

        new_session_chat_messages = client.session.messages(id=new_session_id)

        def get_last_assistant_message(messages: Iterable) -> Optional[str]:
            last_text: Optional[str] = None
            for item in messages:
                info = getattr(item, 'info', None)
                role = getattr(info, 'role', None)
                if role == 'assistant':
                    parts = getattr(item, 'parts', []) or []
                    text_segments = []
                    for part in parts:
                        if getattr(part, 'type', None) == 'text':
                            text_segments.append((getattr(part, 'text', '') or '').strip())
                    combined = '\n'.join(s for s in text_segments if s)
                    if combined:
                        last_text = combined
            return last_text

        def render_markdown_terminal(message: Optional[str]) -> None:
            title = 'AI Commit Review'
            if Console and Markdown and Panel:
                console = Console()
                if not message:
                    console.print(Panel('_(no assistant message found)_', title=title, border_style='red'))
                    return
                md = Markdown(message)
                console.print(Panel(md, title=title, border_style='cyan'))
            else:
                if not message:
                    print(f"{title}\n(no assistant message found)")
                else:
                    print(f"{title}\n\n{message}")

        last_msg = get_last_assistant_message(new_session_chat_messages)
        
        is_rejected = last_msg and '-COMMIT REJECTED-' in last_msg
        if is_rejected and last_msg:
            last_msg = last_msg.replace('-COMMIT REJECTED-', '').strip()
        
        render_markdown_terminal(last_msg)

        continue_command = f"opencode --session {new_session_id}"

        if is_rejected:
            fix_command = f"opencode run \"resolve these issues\" --session {new_session_id}"

            if Console and Panel:
                console = Console()
                console.print('\n')
                console.print(Panel(
                    f"[bold red]Critical issues found that block this commit/push.[/bold red]",
                    border_style='bold red',
                    padding=(1, 2)
                ))
                console.print('\n[bold yellow]To automatically resolve these issues:[/bold yellow]')
                console.print(f'[bold green]{fix_command}[/bold green]\n')
                console.print('[bold yellow]To continue chatting with this session:[/bold yellow]')
                console.print(f'[bold cyan]{continue_command}[/bold cyan]')
            else:
                print('\n' + '='*80)
                print('COMMIT REJECTED - Critical issues found')
                print('='*80)
                print('\nTo automatically resolve these issues:')
                print(f"{fix_command}\n")
                print('To continue chatting with this session:')
                print(f"{continue_command}")
                print('='*80)

            return 1
        else:
            improve_command = f"opencode run \"apply the suggested improvements\" --session {new_session_id}"

            if Console and Panel:
                console = Console()
                console.print('\n')
                console.print(Panel(
                    f"[bold green]✓ No blocking issues found.[/bold green]",
                    border_style='green',
                    padding=(1, 2)
                ))
                console.print('\n[bold yellow]To apply suggested improvements:[/bold yellow]')
                console.print(f'[bold green]{improve_command}[/bold green]\n')
                console.print('[bold yellow]To continue chatting with this session:[/bold yellow]')
                console.print(f'[bold cyan]{continue_command}[/bold cyan]')
            else:
                print('\n' + '='*80)
                print('No blocking issues found')
                print('='*80)
                print('\nTo apply suggested improvements:')
                print(f"{improve_command}\n")
                print('To continue chatting with this session:')
                print(f"{continue_command}")
                print('='*80)

            return 0
    finally:
        if serve_process:
            serve_process.terminate()
            try:
                serve_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                serve_process.kill()
                serve_process.wait()

if __name__ == '__main__':
    sys.exit(main())
