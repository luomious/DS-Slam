#!/usr/bin/env python3
"""Shared configuration loader for DS-SLAM scripts.

The loader prefers PyYAML. A small fallback parser is included for the simple
YAML subset used by config/*.yaml so preflight checks can still run on a fresh
machine and report useful errors.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
from pathlib import Path, PurePosixPath
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = REPO_ROOT / "config"


def _coerce_scalar(value: str) -> Any:
    value = value.strip()
    if value == "":
        return ""
    if value in ("true", "True"):
        return True
    if value in ("false", "False"):
        return False
    if value in ("null", "None", "~"):
        return None
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_coerce_scalar(part.strip()) for part in inner.split(",")]
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()
        if ":" not in stripped:
            raise ValueError(f"Unsupported YAML line: {raw_line}")
        key, value = stripped.split(":", 1)
        key = key.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if value.strip() == "":
            child: dict[str, Any] = {}
            parent[key] = child
            stack.append((indent, child))
        else:
            parent[key] = _coerce_scalar(value)
    return root


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore

        loaded = yaml.safe_load(text)
        return loaded or {}
    except ModuleNotFoundError:
        return _parse_simple_yaml(text)


def dump_yaml(data: Any) -> str:
    try:
        import yaml  # type: ignore

        return yaml.safe_dump(data, sort_keys=False, allow_unicode=True)
    except ModuleNotFoundError:
        return json.dumps(data, indent=2, ensure_ascii=False)


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def to_windows_path(path_value: str | Path, root: str | Path | None = None) -> str:
    path_text = str(path_value).replace("\\", "/")
    if path_text.startswith("/"):
        # MSYS path, e.g. /e/VSCode -> E:/VSCode
        parts = PurePosixPath(path_text).parts
        if len(parts) > 1 and len(parts[1]) == 1:
            drive = parts[1].upper() + ":"
            return str(Path(drive, *parts[2:]))
    candidate = Path(path_text)
    if not candidate.is_absolute() and root is not None:
        candidate = Path(str(root)) / candidate
    return str(candidate)


def to_msys_path(path_value: str | Path, root: str | Path | None = None) -> str:
    win_path = Path(to_windows_path(path_value, root)).resolve()
    drive = win_path.drive.rstrip(":").lower()
    tail = win_path.as_posix().split(":", 1)[1]
    return f"/{drive}{tail}"


def _resolve_path_map(config: dict[str, Any], path_value: str) -> dict[str, str]:
    root = config["project"]["root"]
    return {
        "raw": path_value,
        "win": to_windows_path(path_value, root),
        "msys": to_msys_path(path_value, root),
    }


def apply_env_overrides(config: dict[str, Any]) -> dict[str, Any]:
    env_map = {
        "DS_SLAM_ROOT": ("project", "root"),
        "DS_SLAM_PROFILE": ("project", "profile"),
        "DS_SLAM_MSYS2_ROOT": ("toolchain", "msys2_root"),
        "DS_SLAM_MINGW64_SHELL": ("toolchain", "mingw64_shell"),
        "DS_SLAM_VIS_HOST": ("visualization", "host"),
        "DS_SLAM_VIS_PORT": ("visualization", "port"),
    }
    result = copy.deepcopy(config)
    for env_name, path_keys in env_map.items():
        if env_name not in os.environ:
            continue
        target = result
        for key in path_keys[:-1]:
            target = target.setdefault(key, {})
        value: Any = os.environ[env_name]
        if env_name.endswith("_PORT"):
            value = int(value)
        target[path_keys[-1]] = value
    return result


def load_config(profile: str = "dev", include_local: bool = True) -> dict[str, Any]:
    config = load_yaml(CONFIG_DIR / "default.yaml")
    profile_config = load_yaml(CONFIG_DIR / "profiles" / f"{profile}.yaml")
    config = deep_merge(config, profile_config)
    if include_local:
        config = deep_merge(config, load_yaml(CONFIG_DIR / "local.yaml"))
    config = apply_env_overrides(config)
    config.setdefault("project", {})["profile"] = profile
    config["project"]["root"] = to_windows_path(config["project"].get("root", "."), REPO_ROOT)
    add_resolved_paths(config)
    return config


def add_resolved_paths(config: dict[str, Any]) -> None:
    resolved: dict[str, Any] = {
        "project_root": _resolve_path_map(config, config["project"]["root"]),
        "toolchain": {
            "msys2_root": _resolve_path_map(config, config["toolchain"]["msys2_root"]),
            "mingw64_shell": _resolve_path_map(config, config["toolchain"]["mingw64_shell"]),
        },
        "orbslam3": {},
        "datasets": {},
        "segmentation": {},
        "output": {},
        "visualization": {},
    }
    for key in ("root", "build_dir", "vocabulary", "rgbd_exe"):
        resolved["orbslam3"][key] = _resolve_path_map(config, config["orbslam3"][key])
    resolved["orbslam3"]["camera_configs"] = {
        name: _resolve_path_map(config, path)
        for name, path in config["orbslam3"].get("camera_configs", {}).items()
    }
    for name, dataset in config.get("datasets", {}).items():
        camera_key = dataset.get("camera")
        camera_path = config["orbslam3"]["camera_configs"].get(camera_key, camera_key)
        resolved["datasets"][name] = {
            "root": _resolve_path_map(config, dataset["root"]),
            "association": _resolve_path_map(config, dataset["association"]),
            "camera": _resolve_path_map(config, camera_path),
        }
    resolved["segmentation"]["model_path"] = _resolve_path_map(
        config, config["segmentation"]["model_path"]
    )
    for key, path in config.get("output", {}).items():
        resolved["output"][key] = _resolve_path_map(config, path)
    static_dir = config.get("visualization", {}).get("static_dir", "visualization/frontend")
    resolved["visualization"]["static_dir"] = _resolve_path_map(config, static_dir)
    config["_resolved"] = resolved


def get_dataset(config: dict[str, Any], name: str) -> dict[str, Any]:
    if name not in config.get("datasets", {}):
        available = ", ".join(sorted(config.get("datasets", {}).keys()))
        raise KeyError(f"Unknown dataset '{name}'. Available: {available}")
    dataset = copy.deepcopy(config["datasets"][name])
    dataset["_resolved"] = config["_resolved"]["datasets"][name]
    return dataset


def runtime_config(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "project": config["project"],
        "orbslam3": config["_resolved"]["orbslam3"],
        "datasets": config["_resolved"]["datasets"],
        "segmentation": config["_resolved"]["segmentation"],
        "visualization": {
            "host": config["visualization"]["host"],
            "port": config["visualization"]["port"],
            "ws_path": config["visualization"]["ws_path"],
            "static_dir": config["_resolved"]["visualization"]["static_dir"],
        },
        "output": config["_resolved"]["output"],
    }


def write_runtime_config(config: dict[str, Any], output_path: str | Path) -> Path:
    path = Path(to_windows_path(output_path, config["project"]["root"]))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(runtime_config(config), indent=2), encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="dev")
    parser.add_argument("--format", choices=("json", "yaml"), default="json")
    parser.add_argument("--write-runtime")
    args = parser.parse_args()
    config = load_config(args.profile)
    if args.write_runtime:
        write_runtime_config(config, args.write_runtime)
    if args.format == "json":
        print(json.dumps(config, indent=2, ensure_ascii=False))
    else:
        print(dump_yaml(config))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
