"""Inert manifest-owned installation; no activation or enforcement."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

PROJECT = Path(__file__).resolve().parents[2]
MANIFEST = "/var/lib/usbgate/install-manifest.json"
FILES = {
    "bin/usbgate": "/usr/local/sbin/usbgate",
    "src/usbgate/__init__.py": "/usr/local/lib/usbgate/usbgate/__init__.py",
    "src/usbgate/cli.py": "/usr/local/lib/usbgate/usbgate/cli.py",
    "src/usbgate/observe.py": "/usr/local/lib/usbgate/usbgate/observe.py",
    "src/usbgate/policy.py": "/usr/local/lib/usbgate/usbgate/policy.py",
    "src/usbgate/demo.py": "/usr/local/lib/usbgate/usbgate/demo.py",
    "packaging/systemd/usbgate-reconcile.service": "/etc/systemd/system/usbgate-reconcile.service",
    "packaging/systemd/presence-demo.service": "/etc/systemd/system/presence-demo.service",
    "packaging/systemd/usbgate-reconcile.timer": "/etc/systemd/system/usbgate-reconcile.timer",
    "packaging/udev/70-usbgate.rules": "/usr/local/lib/usbgate/packaging/udev/70-usbgate.rules",
}


def destination(root, absolute):
    return root / absolute.lstrip("/")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ensure_safe_parents(root, target):
    """Refuse redirecting a managed installation path through a symlink."""
    parent = target.parent
    while True:
        if parent.is_symlink():
            raise RuntimeError(f"symlink parent refused: {parent}")
        if parent == root or parent == parent.parent:
            break
        parent = parent.parent


def install(root):
    manifest = destination(root, MANIFEST)
    if manifest.exists() or manifest.is_symlink():
        raise RuntimeError("installation already exists (manifest present)")
    for relative, path in FILES.items():
        source, target = PROJECT / relative, destination(root, path)
        ensure_safe_parents(root, target)
        if not source.is_file() or target.exists() or target.is_symlink():
            raise RuntimeError(f"missing source or occupied installation path: {path}")
    created = []
    try:
        entries = {}
        for relative, path in FILES.items():
            target = destination(root, path)
            target.parent.mkdir(parents=True, exist_ok=True)
            ensure_safe_parents(root, target)
            with (PROJECT / relative).open("rb") as input_stream:
                mode = 0o755 if relative == "bin/usbgate" else 0o644
                fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
                created.append(target)
                with os.fdopen(fd, "wb") as output_stream:
                    shutil.copyfileobj(input_stream, output_stream)
            entries[path] = digest(target)
        ensure_safe_parents(root, manifest)
        manifest.parent.mkdir(parents=True, exist_ok=True)
        ensure_safe_parents(root, manifest)
        fd = os.open(manifest, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        created.append(manifest)
        with os.fdopen(fd, "w") as stream:
            json.dump({"schema_version": 1, "files": entries}, stream, indent=2, sort_keys=True)
        print("Installed inert files; observation is not enabled.")
    except Exception:
        for target in reversed(created):
            target.unlink(missing_ok=True)
        raise


def uninstall(root):
    manifest = destination(root, MANIFEST)
    ensure_safe_parents(root, manifest)
    if manifest.is_symlink():
        raise RuntimeError("manifest symlink refused")
    data = json.loads(manifest.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1 or set(data.get("files", {})) != set(FILES.values()):
        raise RuntimeError("invalid manifest; refusing removal")
    if root == Path("/"):
        from .demo import POLICY, GRANT
        if POLICY.exists() or POLICY.is_symlink() or GRANT.exists() or GRANT.is_symlink():
            raise RuntimeError("disable and reset demo enrollment before uninstall")
        rule = Path("/etc/udev/rules.d/70-usbgate.rules")
        if rule.exists() or rule.is_symlink():
            raise RuntimeError("disable monitor before uninstall")
        for name in ("usbgate-reconcile.timer", "usbgate-reconcile.service", "presence-demo.service"):
            result = subprocess.run(["/usr/bin/systemctl", "is-active", name],
                                    capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                raise RuntimeError(f"{name} is active; refusing removal")
    for path, expected in data["files"].items():
        target = destination(root, path)
        ensure_safe_parents(root, target)
        if target.is_symlink() or not target.is_file() or digest(target) != expected:
            raise RuntimeError(f"file modified or missing; refusing removal: {path}")
    for path in data["files"]:
        destination(root, path).unlink()
    manifest.unlink()
    print("Removed manifest-owned files only; other data retained.")


def main():
    parser = argparse.ArgumentParser(description="Inert install/uninstall helper")
    parser.add_argument("action", choices=("install", "uninstall"))
    parser.add_argument("--root", type=Path, default=Path("/"))
    args = parser.parse_args()
    if args.root == Path("/") and os.geteuid() != 0:
        parser.error("live installation requires root")
    try:
        (install if args.action == "install" else uninstall)(args.root)
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"usbgate install: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
