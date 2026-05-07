#!/usr/bin/env python3
"""Print the merged DS-SLAM configuration."""

from __future__ import annotations

import argparse
import json

from config_loader import dump_yaml, load_config, write_runtime_config


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
