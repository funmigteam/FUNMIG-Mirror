#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fcntl
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT / "sync" / "mirror-sync.json"
APPROVAL_TOKEN = "START-FUNMIG-MIRROR-DOWNLOADS-V1"
GIB = 1024 ** 3


def load_config() -> dict:
    with CONFIG_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def resolve_project_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT / path


def enabled_registries(config: dict) -> dict:
    return {name: item for name, item in config["registries"].items() if item.get("enabled")}


def validate(config: dict, *, require_tools: bool = False) -> list[str]:
    errors: list[str] = []
    data_root = Path(config["data_root"])
    state_root = Path(config["state_root"])
    if not data_root.is_absolute() or not state_root.is_absolute():
        errors.append("data_root and state_root must be absolute")
    volume_root = Path("/media/arshia/New Volume1")
    for path, label in ((data_root, "data_root"), (state_root, "state_root")):
        if volume_root not in path.parents:
            errors.append(f"{label} must be located on Volume 1")
    registries = enabled_registries(config)
    total = sum(int(item["budget_gib"]) for item in registries.values())
    if total != int(config["hard_limit_gib"]):
        errors.append(f"registry budgets total {total} GiB, expected {config['hard_limit_gib']} GiB")
    for name, item in registries.items():
        if int(item.get("budget_gib", 0)) <= 0:
            errors.append(f"{name}: invalid budget")
        list_name = item.get("package_list")
        if list_name and not resolve_project_path(list_name).is_file():
            errors.append(f"{name}: package list not found: {list_name}")
        if require_tools and item["tool"] == "debmirror" and not shutil.which("debmirror"):
            errors.append(f"{name}: debmirror is not installed")
    return errors


def usage_bytes(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def registry_path(config: dict, name: str, item: dict) -> Path:
    if item.get("storage_root"):
        return Path(item["storage_root"])
    return Path(config["data_root"]) / name


def total_content_bytes(config: dict) -> int:
    return sum(usage_bytes(registry_path(config, name, item)) for name, item in enabled_registries(config).items())


def print_plan(config: dict) -> None:
    print("Funmig Mirror synchronization plan (no transfer)")
    print(f"Data root: {config['data_root']}")
    for name, item in enabled_registries(config).items():
        details = ""
        if name in {"debian", "ubuntu"}:
            details = f" suites={','.join(item['suites'])} arch={','.join(item['architectures'])}"
        else:
            package_file = resolve_project_path(item["package_list"])
            count = sum(1 for line in package_file.read_text().splitlines() if line.strip() and not line.startswith("#"))
            details = f" seed_packages={count} versions={item['versions_per_package']}"
        print(f"- {name}: {item['budget_gib']} GiB;{details}")
    print(f"Hard content limit: {config['hard_limit_gib']} GiB; reserve: {config['reserve_gib']} GiB")
    print(f"Approval token (not installed): {APPROVAL_TOKEN}")


def status(config: dict) -> None:
    data_root = Path(config["data_root"])
    for name, item in enabled_registries(config).items():
        used = usage_bytes(registry_path(config, name, item))
        print(f"{name}: {used / GIB:.3f} GiB / {item['budget_gib']} GiB")
    approval = Path(config["approval_file"])
    print("downloads: APPROVED" if approval.is_file() and approval.read_text().strip() == APPROVAL_TOKEN else "downloads: LOCKED")


def debmirror_command(name: str, item: dict, destination: Path) -> list[str]:
    command = [
        "debmirror", str(destination), "--method", item["method"], "--host", item["host"],
        "--root", item["root"], "--dist", ",".join(item["suites"]),
        "--section", ",".join(item["components"]), "--arch", ",".join(item["architectures"]),
        "--nosource", "--progress", "--postcleanup", "--ignore-release-gpg"
    ]
    return command


def adapter_command(name: str, item: dict) -> list[str]:
    return [
        str(Path("/media/arshia/New Volume1/funmig-mirror/.venv/bin/python")),
        str(PROJECT / "manage.py"), "prefetch_registry", "--registry", name,
        "--package-list", str(resolve_project_path(item["package_list"])),
        "--versions", str(item["versions_per_package"]),
        "--budget-gib", str(item["budget_gib"]),
    ]


def run(config: dict, requested: str) -> None:
    approval = Path(config["approval_file"])
    if not approval.is_file() or approval.read_text().strip() != APPROVAL_TOKEN:
        raise SystemExit("DOWNLOAD LOCKED: explicit approval file is absent")
    errors = validate(config, require_tools=True)
    if errors:
        raise SystemExit("\n".join(errors))
    registries = enabled_registries(config)
    names = list(registries) if requested == "all" else [requested]
    if any(name not in registries for name in names):
        raise SystemExit(f"Unknown or disabled registry: {requested}")
    data_root, state_root = Path(config["data_root"]), Path(config["state_root"])
    data_root.mkdir(parents=True, exist_ok=True)
    state_root.mkdir(parents=True, exist_ok=True)
    lock_path = state_root / "sync.lock"
    with lock_path.open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise SystemExit("another synchronization is already running") from exc
        for name in names:
            item = registries[name]
            destination = registry_path(config, name, item)
            destination.mkdir(parents=True, exist_ok=True)
            if usage_bytes(destination) >= int(item["budget_gib"]) * GIB:
                raise SystemExit(f"{name}: quota already reached")
            command = debmirror_command(name, item, destination) if item["tool"] == "debmirror" else adapter_command(name, item)
            started = datetime.now(timezone.utc).isoformat()
            result = subprocess.run(command, cwd=PROJECT, check=False)
            record = {"registry": name, "started": started, "finished": datetime.now(timezone.utc).isoformat(), "exit_code": result.returncode}
            (state_root / f"{name}.json").write_text(json.dumps(record, indent=2) + "\n")
            if result.returncode:
                raise SystemExit(result.returncode)
            used = usage_bytes(destination)
            if used > int(item["budget_gib"]) * GIB or total_content_bytes(config) > int(config["hard_limit_gib"]) * GIB:
                raise SystemExit("hard quota exceeded; synchronization stopped")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("validate", "plan", "status", "run"))
    parser.add_argument("--registry", default="all")
    args = parser.parse_args()
    config = load_config()
    errors = validate(config)
    if args.command == "validate":
        print("configuration valid" if not errors else "\n".join(errors))
        raise SystemExit(bool(errors))
    if errors:
        raise SystemExit("\n".join(errors))
    if args.command == "plan":
        print_plan(config)
    elif args.command == "status":
        status(config)
    else:
        run(config, args.registry)


if __name__ == "__main__":
    main()
