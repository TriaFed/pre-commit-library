import os
import tempfile
from pathlib import Path
from subprocess import CalledProcessError
from scripts.resolve_deps import resolve_plan, main as resolve_main
import sys
import json


def write_tmp_config(contents: str) -> Path:
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".yaml")
    tmp.write(contents.encode("utf-8"))
    tmp.flush()
    tmp.close()
    return Path(tmp.name)


def run_resolver(config_path: Path, os_name: str, profiles: str = "", exclude: str = "") -> dict:
    include_list = [p.strip() for p in profiles.split(",") if p.strip()]
    exclude_list = [p.strip() for p in exclude.split(",") if p.strip()]
    return resolve_plan(
        config_path=config_path,
        os_name=os_name,
        include_profiles=include_list,
        exclude_profiles=exclude_list,
    )


def test_node_only_profiles_and_tools_darwin():
    cfg = """
repos:
  - repo: https://github.com/TriaFed/pre-commit-library
    rev: v1.1.4
    hooks:
      - id: detect_secrets
      - id: genai_security_check
      - id: eslint
      - id: prettier
      - id: typescript_check
      - id: npm_audit
"""
    path = write_tmp_config(cfg)
    try:
        result = run_resolver(path, "darwin")
        profiles = set(result["profiles"])  # core + node expected
        assert "core" in profiles
        assert "node" in profiles
        tools = result["tools"]
        assert "brew" in tools and "node" in tools["brew"]
        assert "npm" in tools and "eslint" in tools["npm"]
        # ensure no dotnet/go/java tooling
        assert "dotnet" not in ",".join(sum(tools.values(), []))
    finally:
        os.unlink(path)


def test_infra_only_profiles_and_tools_windows():
    cfg = """
repos:
  - repo: https://github.com/TriaFed/pre-commit-library
    rev: v1.1.4
    hooks:
      - id: detect_secrets
      - id: genai_security_check
      - id: terraform_fmt
      - id: terraform_validate
      - id: terraform_tflint
      - id: cloudformation_validate
      - id: dockerfile_lint
"""
    path = write_tmp_config(cfg)
    try:
        result = run_resolver(path, "windows")
        profiles = set(result["profiles"])  # core + infrastructure expected
        assert "core" in profiles
        assert "infrastructure" in profiles
        tools = result["tools"]
        # windows plan should include winget/choco/pip entries
        assert any(k in tools for k in ("winget", "choco", "pip"))
        # ensure terraform present
        flat = ",".join(sum(tools.values(), []))
        assert "Terraform" in flat or "terraform" in flat
    finally:
        os.unlink(path)


def test_optional_trufflehog_not_installed_if_hook_absent_darwin():
    cfg = """
repos:
  - repo: https://github.com/TriaFed/pre-commit-library
    rev: v1.1.4
    hooks:
      - id: detect_secrets
      - id: genai_security_check
"""
    path = write_tmp_config(cfg)
    try:
        result = run_resolver(path, "darwin")
        tools = result["tools"]
        brew_list = tools.get("brew", [])
        assert "trufflehog" not in brew_list
    finally:
        os.unlink(path)


def test_profiles_include_exclude_merge():
    # Config with only node hooks; include python, exclude node
    cfg = """
repos:
  - repo: https://github.com/TriaFed/pre-commit-library
    rev: v1.1.4
    hooks:
      - id: eslint
      - id: prettier
"""
    path = write_tmp_config(cfg)
    try:
        result = run_resolver(path, "darwin", profiles="python", exclude="node")
        profiles = set(result["profiles"])  # should include python, not node
        assert "python" in profiles
        assert "node" not in profiles
    finally:
        os.unlink(path)


def test_platform_specific_packages_match_map_windows():
    cfg = """
repos:
  - repo: https://github.com/TriaFed/pre-commit-library
    rev: v1.1.4
    hooks:
      - id: dotnet_format
      - id: dotnet_test
"""
    path = write_tmp_config(cfg)
    try:
        result = run_resolver(path, "windows")
        profiles = set(result["profiles"])  # dotnet expected
        assert "dotnet" in profiles
        tools = result["tools"]
        # dotnet SDK installed via winget on windows per map
        winget = ",".join(tools.get("winget", []))
        assert "Microsoft.DotNet.SDK" in winget or "Microsoft.DotNet.SDK.8" in winget
        # no brew entries on windows
        assert "brew" not in tools
    finally:
        os.unlink(path)


def test_invalid_missing_config_errors(tmp_path: Path):
    # Calling resolve_plan with non-existent path should raise FileNotFoundError
    try:
        resolve_plan(config_path=(tmp_path / "nope.yaml"), os_name="darwin")
        assert False, "Expected failure for missing config"
    except FileNotFoundError:
        pass


def test_empty_hooks_returns_minimal_profiles_when_forced():
    cfg = """
repos: []
"""
    path = write_tmp_config(cfg)
    try:
        # No hooks in config; force core profile via include
        result = run_resolver(path, "darwin", profiles="core")
        assert set(result["profiles"]) == {"core"}
    finally:
        os.unlink(path)


def test_duplicate_tools_removed_in_plan():
    # Two hooks mapping to same profile should not duplicate packages
    cfg = """
repos:
  - repo: https://github.com/TriaFed/pre-commit-library
    rev: v1.1.4
    hooks:
      - id: python_black
      - id: python_flake8
"""
    path = write_tmp_config(cfg)
    try:
        result = run_resolver(path, "darwin")
        tools = result["tools"].get("pip", [])
        # both profiles request black/flake8 but list must be unique
        assert tools.count("black") == 1
        assert tools.count("flake8") == 1
    finally:
        os.unlink(path)


def test_mixed_stacks_union_of_profiles():
    cfg = """
repos:
  - repo: https://github.com/TriaFed/pre-commit-library
    rev: v1.1.4
    hooks:
      - id: eslint
      - id: python_black
      - id: terraform_validate
      - id: detect_secrets
"""
    path = write_tmp_config(cfg)
    try:
        result = run_resolver(path, "darwin")
        profiles = set(result["profiles"])  # expect node, python, infrastructure, core
        assert {"node", "python", "infrastructure", "core"}.issubset(profiles)
    finally:
        os.unlink(path)


def test_invalid_yaml_raises(tmp_path: Path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(":-: not: yaml: [ :\n")
    try:
        resolve_plan(config_path=bad, os_name="darwin")
        assert False, "Expected YAML error"
    except Exception:
        pass


def test_nonlist_repos_graceful():
    cfg = "repos: {}\n"
    path = write_tmp_config(cfg)
    try:
        result = resolve_plan(path, "darwin")
        assert result["profiles"] == []
    finally:
        os.unlink(path)


def test_tools_notes_ignored_in_mapping(tmp_path: Path):
    # Custom mapping with notes (non-list entries) should be ignored
    mapping = {
        "hookIdToProfiles": {"eslint": ["custom"]},
        "profiles": {
            "custom": {
                "darwin": {"brew": ["pkg-a"], "notes": ["ignore me"]}
            }
        }
    }
    mapping_path = tmp_path / "map.json"
    mapping_path.write_text(json.dumps(mapping))
    cfg = """
repos:
  - repo: https://github.com/TriaFed/pre-commit-library
    rev: v1.1.4
    hooks:
      - id: eslint
"""
    path = write_tmp_config(cfg)
    try:
        result = resolve_plan(path, "darwin", mapping_path=mapping_path)
        assert "brew" in result["tools"] and result["tools"]["brew"] == ["pkg-a"]
        assert "notes" not in result["tools"]
    finally:
        os.unlink(path)


def test_only_tools_true_returns_tools_dict():
    cfg = "repos: []\n"
    path = write_tmp_config(cfg)
    try:
        tools = resolve_plan(path, "darwin", only_tools=True)
        assert isinstance(tools, dict)
        assert "profiles" not in tools
    finally:
        os.unlink(path)


def test_trufflehog_removed_if_absent_windows():
    cfg = """
repos:
  - repo: https://github.com/TriaFed/pre-commit-library
    rev: v1.1.4
    hooks:
      - id: detect_secrets
      - id: genai_security_check
"""
    path = write_tmp_config(cfg)
    try:
        result = resolve_plan(path, "windows")
        winget = result["tools"].get("winget", [])
        assert "trufflesecurity.trufflehog" not in winget
    finally:
        os.unlink(path)


def test_main_success_outputs_json(monkeypatch, tmp_path: Path, capsys):
    cfg = tmp_path / ".pre-commit-config.yaml"
    cfg.write_text("repos: []\n")
    argv = [
        "resolve_deps.py",
        "--config", str(cfg),
        "--os", "darwin",
    ]
    monkeypatch.setattr(sys, "argv", argv)
    rc = resolve_main()
    assert rc == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["os"] == "darwin"
    # explain enabled by default
    assert isinstance(data.get("explain"), dict)


def test_main_uses_default_config_in_cwd(monkeypatch, tmp_path: Path, capsys):
    # Write default-named config into temp cwd and run without --config
    cfg = tmp_path / ".pre-commit-config.yaml"
    cfg.write_text("repos: []\n")
    monkeypatch.chdir(tmp_path)
    argv = [
        "resolve_deps.py",
        "--os", "darwin",
    ]
    monkeypatch.setattr(sys, "argv", argv)
    rc = resolve_main()
    assert rc == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["os"] == "darwin"


def test_main_failure_missing_config(monkeypatch, capsys, tmp_path: Path):
    argv = [
        "resolve_deps.py",
        "--config", str(tmp_path / "nope.yaml"),
        "--os", "darwin",
    ]
    monkeypatch.setattr(sys, "argv", argv)
    rc = resolve_main()
    assert rc == 1
    err = capsys.readouterr().err
    assert "resolve_deps error" in err


def test_no_explain_flag_disables_explanation(monkeypatch, tmp_path: Path, capsys):
    cfg = tmp_path / ".pre-commit-config.yaml"
    cfg.write_text("repos: []\n")
    argv = [
        "resolve_deps.py",
        "--config", str(cfg),
        "--os", "darwin",
        "--no-explain",
    ]
    monkeypatch.setattr(sys, "argv", argv)
    rc = resolve_main()
    assert rc == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data.get("explain") is None


def test_resolve_plan_explain_true_and_false(tmp_path: Path):
    cfg = tmp_path / ".pre-commit-config.yaml"
    cfg.write_text("repos: []\n")
    # default explain True
    res_explain = resolve_plan(cfg, "darwin")
    assert isinstance(res_explain.get("explain"), dict)
    # explicitly disable
    res_no_explain = resolve_plan(cfg, "darwin", explain=False)
    assert res_no_explain.get("explain") is None


def test_malformed_repos_and_hooks_are_ignored(tmp_path: Path):
    # repos is list with non-dict entries; hooks contain non-dict entries
    cfg = """
repos:
  - not-a-dict
  - repo: https://github.com/TriaFed/pre-commit-library
    rev: v1.1.5
    hooks:
      - not-a-dict
"""
    path = write_tmp_config(cfg)
    try:
        result = resolve_plan(path, "darwin")
        # No valid hooks detected
        assert result["hooks"] == []
        assert result["profiles"] == []
    finally:
        os.unlink(path)


def test_unknown_manager_keys_are_ignored_in_mapping(tmp_path: Path):
    mapping = {
        "hookIdToProfiles": {"eslint": ["custom"]},
        "profiles": {
            "custom": {
                "darwin": {"foo": ["x"], "brew": ["pkg-a"]}
            }
        }
    }
    mapping_path = tmp_path / "map.json"
    mapping_path.write_text(json.dumps(mapping))
    cfg = """
repos:
  - repo: https://github.com/TriaFed/pre-commit-library
    rev: v1.1.5
    hooks:
      - id: eslint
"""
    path = write_tmp_config(cfg)
    try:
        result = resolve_plan(path, "darwin", mapping_path=mapping_path)
        assert "brew" in result["tools"] and result["tools"]["brew"] == ["pkg-a"]
        assert "foo" not in result["tools"]
    finally:
        os.unlink(path)


def test_node_pm_detection_without_yarn_lock(tmp_path: Path):
    cfg = """
repos:
  - repo: https://github.com/TriaFed/pre-commit-library
    rev: v1.1.5
    hooks:
      - id: eslint
"""
    path = write_tmp_config(cfg)
    try:
        result = resolve_plan(path, "darwin", project_dir=tmp_path)
        assert result["detected"]["nodePackageManager"] == "npm"
    finally:
        os.unlink(path)


def test_node_pm_detection_with_yarn_lock(tmp_path: Path):
    (tmp_path / "yarn.lock").write_text("")
    cfg = """
repos:
  - repo: https://github.com/TriaFed/pre-commit-library
    rev: v1.1.5
    hooks:
      - id: eslint
"""
    path = write_tmp_config(cfg)
    try:
        result = resolve_plan(path, "darwin", project_dir=tmp_path)
        assert result["detected"]["nodePackageManager"] == "yarn"
    finally:
        os.unlink(path)


def test_trufflehog_retained_when_hook_present_both_platforms(tmp_path: Path):
    cfg = """
repos:
  - repo: https://github.com/TriaFed/pre-commit-library
    rev: v1.1.5
    hooks:
      - id: detect_secrets
      - id: truffhog
"""
    path = write_tmp_config(cfg)
    try:
        darwin_res = resolve_plan(path, "darwin")
        brew = darwin_res["tools"].get("brew", [])
        assert "trufflehog" in brew
        win_res = resolve_plan(path, "windows")
        winget = win_res["tools"].get("winget", [])
        # On windows, trufflehog may be in winget mapping
        assert any("trufflehog" in p for p in winget)
    finally:
        os.unlink(path)


def test_optional_block_not_entered_when_core_not_selected():
    cfg = """
repos:
  - repo: https://github.com/TriaFed/pre-commit-library
    rev: v1.1.5
    hooks:
      - id: eslint
"""
    path = write_tmp_config(cfg)
    try:
        # profiles from hooks yields node only
        result = resolve_plan(path, "darwin")
        assert "core" not in result["profiles"]
        # No optional removal should have been recorded; explain still present
        assert isinstance(result.get("explain"), dict)
    finally:
        os.unlink(path)


def test_python_profile_tools_darwin():
    cfg = """
repos:
  - repo: https://github.com/TriaFed/pre-commit-library
    rev: v1.1.5
    hooks:
      - id: python_black
      - id: bandit
"""
    path = write_tmp_config(cfg)
    try:
        result = resolve_plan(path, "darwin")
        profiles = set(result["profiles"])  # expect python (+ maybe core if detect_secrets not present; it's not)
        assert "python" in profiles
        pip_tools = result["tools"].get("pip", [])
        assert "black" in pip_tools and "bandit" in pip_tools
    finally:
        os.unlink(path)


def test_go_profile_tools_darwin():
    cfg = """
repos:
  - repo: https://github.com/TriaFed/pre-commit-library
    rev: v1.1.5
    hooks:
      - id: go_lint
      - id: go_security_scan
"""
    path = write_tmp_config(cfg)
    try:
        result = resolve_plan(path, "darwin")
        profiles = set(result["profiles"])  # expect go
        assert "go" in profiles
        brew_tools = result["tools"].get("brew", [])
        assert "go" in brew_tools
        go_tools = result["tools"].get("go", [])
        assert any("golangci-lint" in t for t in go_tools)
        assert any("gosec" in t for t in go_tools)
    finally:
        os.unlink(path)


def test_java_profile_tools_darwin():
    cfg = """
repos:
  - repo: https://github.com/TriaFed/pre-commit-library
    rev: v1.1.5
    hooks:
      - id: java_checkstyle
"""
    path = write_tmp_config(cfg)
    try:
        result = resolve_plan(path, "darwin")
        profiles = set(result["profiles"])  # expect java
        assert "java" in profiles
        brew_tools = result["tools"].get("brew", [])
        # mapping includes openjdk@17 and build tools
        assert any("openjdk@17" in t for t in brew_tools)
    finally:
        os.unlink(path)


def test_ansible_profile_tools_darwin():
    cfg = """
repos:
  - repo: https://github.com/TriaFed/pre-commit-library
    rev: v1.1.5
    hooks:
      - id: ansible_lint
"""
    path = write_tmp_config(cfg)
    try:
        result = resolve_plan(path, "darwin")
        profiles = set(result["profiles"])  # expect ansible
        assert "ansible" in profiles
        pip_tools = result["tools"].get("pip", [])
        assert "ansible" in pip_tools and "ansible-lint" in pip_tools
    finally:
        os.unlink(path)


def test_semgrep_in_core_without_trufflehog():
    cfg = """
repos:
  - repo: https://github.com/TriaFed/pre-commit-library
    rev: v1.1.5
    hooks:
      - id: semgrep
"""
    path = write_tmp_config(cfg)
    try:
        result = resolve_plan(path, "darwin")
        profiles = set(result["profiles"])  # expect core
        assert "core" in profiles
        pip_tools = result["tools"].get("pip", [])
        assert "semgrep" in pip_tools
        brew_tools = result["tools"].get("brew", [])
        assert "trufflehog" not in brew_tools
    finally:
        os.unlink(path)


def test_missing_profile_mapping_is_graceful(tmp_path: Path):
    # Provide mapping that lacks entries for a detected profile
    mapping = {
        "hookIdToProfiles": {"python_black": ["python"]},
        "profiles": {
            # intentionally omit 'python' profile block
        }
    }
    mapping_path = tmp_path / "map.json"
    mapping_path.write_text(json.dumps(mapping))
    cfg = """
repos:
  - repo: https://github.com/TriaFed/pre-commit-library
    rev: v1.1.5
    hooks:
      - id: python_black
"""
    path = write_tmp_config(cfg)
    try:
        result = resolve_plan(path, "darwin", mapping_path=mapping_path)
        # Profiles still includes 'python', but tools empty
        assert "python" in result["profiles"]
        assert result["tools"] == {}
    finally:
        os.unlink(path)


def test_include_then_exclude_core_removes_core():
    cfg = "repos: []\n"
    path = write_tmp_config(cfg)
    try:
        result = resolve_plan(path, "darwin", include_profiles=["core"], exclude_profiles=["core"])
        assert "core" not in result["profiles"]
    finally:
        os.unlink(path)


