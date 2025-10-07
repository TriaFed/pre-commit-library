#!/usr/bin/env python3
"""
Parse a .pre-commit-config.yaml, determine used hook IDs, map them to profiles,
and output a plan of tools to install per platform (darwin/windows) as JSON.

Usage:
  python scripts/resolve_deps.py --config /abs/path/.pre-commit-config.yaml --os darwin [--profiles python,node] [--exclude java] [--only-tools]

Exit code 0 on success, 1 on parse/mapping error.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Set, Any

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover - defensive import guard
    print("Missing dependency: pyyaml is required to parse YAML (pip install pyyaml)", file=sys.stderr)
    sys.exit(1)


def load_yaml_config(config_path: Path) -> Dict[str, Any]:
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")
    with config_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def extract_hook_ids(cfg: Dict[str, Any]) -> Set[str]:
    hook_ids: Set[str] = set()
    repos = cfg.get("repos", [])
    if not isinstance(repos, list):
        return hook_ids
    for repo in repos:
        hooks = repo.get("hooks", []) if isinstance(repo, dict) else []
        for hook in hooks:
            hook_id = hook.get("id") if isinstance(hook, dict) else None
            if isinstance(hook_id, str):
                hook_ids.add(hook_id)
    return hook_ids


def load_mapping(mapping_path: Path) -> Dict[str, Any]:
    with mapping_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def hook_ids_to_profiles(hook_ids: Set[str], hook_to_profiles: Dict[str, List[str]]) -> Set[str]:
    profiles: Set[str] = set()
    for hid in hook_ids:
        mapped = hook_to_profiles.get(hid)
        if mapped:
            profiles.update(mapped)
    return profiles


def merge_profiles(base: Set[str], include: List[str] | None, exclude: List[str] | None) -> Set[str]:
    result = set(base)
    if include:
        result.update(include)
    if exclude:
        result.difference_update(exclude)
    return result


def tools_for_profiles(profiles: Set[str], mp: Dict[str, Any], platform: str) -> Dict[str, List[str]]:
    tool_plan: Dict[str, List[str]] = {}
    allowed_managers: Set[str] = {
        "brew", "brew_cask", "winget", "choco", "pip", "npm", "go"
    }
    for profile in sorted(profiles):
        pdata = mp.get("profiles", {}).get(profile, {})
        ptools = pdata.get(platform, {}) if isinstance(pdata, dict) else {}
        for mgr, pkgs in ptools.items():
            # Only include known managers and list-valued entries
            if mgr not in allowed_managers or not isinstance(pkgs, list):
                continue
            tool_plan.setdefault(mgr, [])
            for pkg in pkgs:
                if pkg not in tool_plan[mgr]:
                    tool_plan[mgr].append(pkg)
    return tool_plan


def detect_node_package_manager(project_dir: Path) -> str:
    if (project_dir / "yarn.lock").exists():
        return "yarn"
    return "npm"


def adjust_for_node_pm(tool_plan: Dict[str, List[str]], node_pm: str) -> None:
    # If yarn is selected, npm global installs are not mandatory; keep CLI presence minimal.
    if node_pm == "yarn":
        # no-op for now; installers can choose to skip npm -g when yarn detected
        pass


def resolve_plan(
    config_path: Path,
    os_name: str,
    project_dir: Path | None = None,
    include_profiles: List[str] | None = None,
    exclude_profiles: List[str] | None = None,
    mapping_path: Path | None = None,
    only_tools: bool = False,
    explain: bool = True,
) -> Dict[str, Any]:
    if project_dir is None:
        project_dir = Path(os.getcwd())
    if mapping_path is None:
        mapping_path = Path(__file__).parent / "hooks_profile_map.json"

    cfg = load_yaml_config(config_path)
    mapping = load_mapping(mapping_path)
    hook_ids = extract_hook_ids(cfg)

    hook_to_profiles_map = mapping.get("hookIdToProfiles", {})
    profiles_from_hooks = hook_ids_to_profiles(hook_ids, hook_to_profiles_map)
    profiles = merge_profiles(
        profiles_from_hooks,
        include_profiles or [],
        exclude_profiles or [],
    )

    tool_plan = tools_for_profiles(profiles, mapping, os_name)

    # Node package manager heuristics
    if "node" in profiles:
        node_pm = detect_node_package_manager(project_dir)
        adjust_for_node_pm(tool_plan, node_pm)
    else:
        node_pm = "none"

    # Optional tools adjustments
    removed_optional: Dict[str, List[str]] = {}
    if "core" in profiles:
        if "trufflehog" not in hook_ids:
            # Remove trufflehog from plan if not explicitly used
            if os_name == "darwin":
                brew_list = tool_plan.get("brew", [])
                if "trufflehog" in brew_list:
                    removed_optional.setdefault("brew", []).append("trufflehog")
                tool_plan["brew"] = [p for p in brew_list if p != "trufflehog"]
            elif os_name == "windows":
                winget_list = tool_plan.get("winget", [])
                if "trufflesecurity.trufflehog" in winget_list:
                    removed_optional.setdefault("winget", []).append("trufflesecurity.trufflehog")
                tool_plan["winget"] = [p for p in winget_list if p != "trufflesecurity.trufflehog"]

    explanation: Dict[str, Any] = {}
    if explain:
        # How hooks map to profiles
        hook_profile_details = []
        for hid in sorted(hook_ids):
            hook_profile_details.append({
                "hook": hid,
                "profiles": hook_to_profiles_map.get(hid, []),
            })

        # How profiles map to tools
        profile_tool_details = []
        profiles_block = mapping.get("profiles", {})
        for profile in sorted(profiles):
            platform_block = profiles_block.get(profile, {}).get(os_name, {}) if isinstance(profiles_block.get(profile, {}), dict) else {}
            # Filter only the managers we will actually honor
            managers = {k: v for k, v in platform_block.items() if isinstance(v, list) and k in {"brew","brew_cask","winget","choco","pip","npm","go"}}
            profile_tool_details.append({
                "profile": profile,
                "managers": managers,
            })

        explanation = {
            "inputs": {
                "configPath": str(config_path),
                "os": os_name,
                "includeProfiles": include_profiles or [],
                "excludeProfiles": exclude_profiles or [],
            },
            "detected": {
                "nodePackageManager": node_pm,
                "hasMaven": (project_dir / "pom.xml").exists(),
                "hasGradle": (project_dir / "build.gradle").exists() or (project_dir / "build.gradle.kts").exists(),
            },
            "mapping": {
                "hooksToProfiles": hook_profile_details,
                "profilesToManagers": profile_tool_details,
            },
            "optionalToolsRemoved": removed_optional,
            "deduplication": "Packages are unique per manager; duplicates removed.",
        }

    result = {
        "hooks": sorted(hook_ids),
        "profiles": sorted(list(profiles)),
        "os": os_name,
        "tools": tool_plan,
        "detected": {
            "nodePackageManager": node_pm,
            "hasMaven": (project_dir / "pom.xml").exists(),
            "hasGradle": (project_dir / "build.gradle").exists() or (project_dir / "build.gradle.kts").exists(),
        },
        "explain": explanation if explain else None,
    }

    if only_tools:
        return tool_plan
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve tools to install from pre-commit config")
    parser.add_argument(
        "--config",
        default=str(Path(os.getcwd()) / ".pre-commit-config.yaml"),
        help="Path to pre-commit config (defaults to ./ .pre-commit-config.yaml)",
    )
    parser.add_argument("--os", required=True, choices=["darwin", "windows"], help="Target OS")
    parser.add_argument("--project", default=os.getcwd(), help="Project root to detect build files")
    parser.add_argument("--profiles", default="", help=",-separated profile overrides to include")
    parser.add_argument("--exclude", default="", help=",-separated profiles to exclude")
    parser.add_argument("--mapping", default=str(Path(__file__).parent / "hooks_profile_map.json"))
    parser.add_argument("--only-tools", action="store_true", help="Only output tool plan (omit hooks/profiles)")
    parser.add_argument("--no-explain", action="store_true", help="Disable detailed reasoning output")
    args = parser.parse_args()

    try:
        include = [p.strip() for p in args.profiles.split(",") if p.strip()]
        exclude = [p.strip() for p in args.exclude.split(",") if p.strip()]
        result = resolve_plan(
            config_path=Path(args.config),
            os_name=args.os,
            project_dir=Path(args.project),
            include_profiles=include,
            exclude_profiles=exclude,
            mapping_path=Path(args.mapping),
            only_tools=args.only_tools,
            explain=(False if args.no_explain else True),
        )
        print(json.dumps(result, indent=2))
        return 0
    except Exception as exc:
        print(f"resolve_deps error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover - CLI bootstrap
    sys.exit(main())


