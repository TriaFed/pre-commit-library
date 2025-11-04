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
    OPENCODE_MODEL = os.getenv('OPENCODE_MODEL', 'claude-sonnet-4.5')
    OPENCODE_PROVIDER = os.getenv('OPENCODE_PROVIDER', 'github-copilot')
    OPENCODE_TIMEOUT = int(os.getenv('OPENCODE_TIMEOUT', '90'))

    if not (1024 <= OPENCODE_PORT <= 65535):
        print(f"Error: Invalid port {OPENCODE_PORT}. Port must be between 1024 and 65535.", file=sys.stderr)
        return 3

    if not (1 <= OPENCODE_TIMEOUT <= 300):
        print(f"Error: Invalid timeout {OPENCODE_TIMEOUT}. Timeout must be between 1 and 300 seconds.", file=sys.stderr)
        return 3

    serve_process = None
    try:
        available_port = find_available_port(OPENCODE_PORT)
        if not available_port:
            print(f"Error: No available ports found starting from port {OPENCODE_PORT}. "
                  f"Please check if ports {OPENCODE_PORT}-{OPENCODE_PORT+9} are available.", file=sys.stderr)
            return 3

        if available_port != OPENCODE_PORT:
            OPENCODE_PORT = available_port

        OPENCODE_BASE_URL = f'http://127.0.0.1:{OPENCODE_PORT}'
        os.environ['OPENCODE_BASE_URL'] = OPENCODE_BASE_URL

        repo_root = subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], text=True).strip()

        serve_process = subprocess.Popen(
            ['opencode', 'serve', '--port', str(OPENCODE_PORT)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=repo_root
        )

        if not wait_for_port(OPENCODE_PORT, timeout=OPENCODE_TIMEOUT):
            stdout, stderr = serve_process.communicate(timeout=5)
            error_msg = stderr.decode() if stderr else "Unknown error"
            print(f"Error: Opencode server failed to start within {OPENCODE_TIMEOUT} seconds.", file=sys.stderr)
            print(f"Server error: {error_msg}", file=sys.stderr)
            print("\nTroubleshooting:", file=sys.stderr)
            print("  1. Check if opencode is installed: opencode --version", file=sys.stderr)
            print("  2. Verify authentication: opencode auth login", file=sys.stderr)
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

        new_session_chat = client.session.chat(id=new_session_id, parts=[
            {'type': 'text', 'text': """
            Please review the currently staged changes for this commit. Evaluate the changes for:

            - Code quality and best practices
            - Potential bugs or issues
            - Security concerns
            - Performance implications
            - Test coverage
            - Documentation needs
            - Adherence to project conventions

            If there are any critical issues that should prevent this commit, start your response with "-COMMIT REJECTED-"
            followed by a clear explanation of the blocking issues.

            If the changes are acceptable, provide constructive feedback and suggestions for improvement.
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
                    f"[bold yellow]To automatically resolve these issues:[/bold yellow]\n"
                    f"[bold green]{fix_command}[/bold green]\n\n"
                    f"[bold yellow]To continue chatting with this session:[/bold yellow]\n"
                    f"[bold cyan]{continue_command}[/bold cyan]",
                    border_style='bold red',
                    padding=(1, 2)
                ))
            else:
                print('\n' + '='*80)
                print('To automatically resolve these issues:')
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
                    f"[bold yellow]To apply suggested improvements:[/bold yellow]\n"
                    f"[bold green]{improve_command}[/bold green]\n\n"
                    f"[bold yellow]To continue chatting with this session:[/bold yellow]\n"
                    f"[bold cyan]{continue_command}[/bold cyan]",
                    border_style='green',
                    padding=(1, 2)
                ))
            else:
                print('\n' + '='*80)
                print('To apply suggested improvements:')
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
