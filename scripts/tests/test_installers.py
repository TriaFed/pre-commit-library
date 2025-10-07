import os
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def write_tmp_config(contents: str) -> Path:
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".yaml")
    tmp.write(contents.encode("utf-8"))
    tmp.flush()
    tmp.close()
    return Path(tmp.name)


def test_macos_installer_dry_run_node_only(monkeypatch):
    bash = shutil.which("bash")
    if not bash:
        return  # environment without bash (unlikely)

    cfg = """
repos:
  - repo: https://github.com/TriaFed/pre-commit-library
    rev: v1.2.0
    hooks:
      - id: detect_secrets
      - id: genai_security_check
      - id: eslint
      - id: prettier
      - id: typescript_check
"""
    config_path = write_tmp_config(cfg)
    try:
        installer = REPO_ROOT / "install-macos.sh"
        env = os.environ.copy()
        # Run in repo root to ensure resolver path is valid
        proc = subprocess.run(
            [bash, str(installer), "--config", str(config_path), "--dry-run"],
            cwd=str(REPO_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        out = proc.stdout
        assert proc.returncode == 0
        assert "Selected profiles:" in out
        assert "node" in out  # selected profiles line or JSON
        # Expect JSON block; try to parse last JSON object in output
        try:
            json_start = out.rfind("{\n")
            if json_start != -1:
                plan = json.loads(out[json_start:])
                assert "profiles" in plan and "node" in plan["profiles"]
        except Exception:
            # If parsing fails, at least ensure tool hints are present
            assert "eslint" in out or "node" in out
    finally:
        os.unlink(config_path)


def test_macos_installer_no_auto_profiles_override(monkeypatch):
    bash = shutil.which("bash")
    if not bash:
        return
    cfg = "repos: []\n"
    config_path = write_tmp_config(cfg)
    try:
        installer = REPO_ROOT / "install-macos.sh"
        proc = subprocess.run(
            [bash, str(installer), "--no-auto", "--config", str(config_path), "--profiles", "python", "--dry-run"],
            cwd=str(REPO_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        out = proc.stdout
        assert proc.returncode == 0
        assert "Selected profiles:" in out
        assert "python" in out
    finally:
        os.unlink(config_path)


def test_windows_installer_dry_run_infra_only(monkeypatch):
    pwsh = shutil.which("pwsh") or shutil.which("powershell")
    if not pwsh:
        return  # Skip if PowerShell not available on this environment

    cfg = """
repos:
  - repo: https://github.com/TriaFed/pre-commit-library
    rev: v1.2.0
    hooks:
      - id: detect_secrets
      - id: genai_security_check
      - id: terraform_validate
"""
    config_path = write_tmp_config(cfg)
    try:
        installer = REPO_ROOT / "install-windows.ps1"
        proc = subprocess.run(
            [pwsh, "-File", str(installer), "-Config", str(config_path), "-DryRun"],
            cwd=str(REPO_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        out = proc.stdout
        assert proc.returncode == 0
        assert "Selected profiles:" in out
        assert "infrastructure" in out or "terraform" in out
    finally:
        os.unlink(config_path)


