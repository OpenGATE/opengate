#!/usr/bin/env python3
"""
Put the bundled QtCore back into a framework bundle, in macOS wheels.

The macOS arm64 wheels are built with the Homebrew Qt, which is a *framework*
build. When delocate bundles it into the wheel, the QtCore binary is copied out
of its QtCore.framework folder (as opengate_core/.dylibs/QtCore). But at
start-up, QtCore asks macOS for its own bundle (org.qt-project.QtCore) to find
its paths; with no bundle it crashes (CFBundleCopyBundleURL called with a null
bundle, inside QLibraryInfoPrivate::paths). So the Qt visualisation crashed
with every pip installed wheel, while it works when compiled from source
(where the Homebrew frameworks are intact).

This script moves QtCore to .dylibs/QtCore.framework/Versions/A/QtCore, adds a
minimal Info.plist, rewrites the library paths that point to it (wheels
cannot contain symbolic links), re-signs the modified binaries, and
regenerates the RECORD file of the wheel.

Usage: fix_macos_qt_framework.py wheel1.whl [wheel2.whl ...]
Wheels without a bare '.dylibs/QtCore' are left unchanged.
"""

import base64
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

FRAMEWORK_REL = Path("QtCore.framework") / "Versions" / "A"

INFO_PLIST = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleIdentifier</key>
    <string>org.qt-project.QtCore</string>
    <key>CFBundleExecutable</key>
    <string>QtCore</string>
    <key>CFBundleName</key>
    <string>QtCore</string>
    <key>CFBundlePackageType</key>
    <string>FMWK</string>
</dict>
</plist>
"""


def run(cmd):
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def macho_dependencies(path):
    """Return the install names of the libraries a Mach-O file depends on,
    or None if the file is not a Mach-O binary."""
    r = subprocess.run(["otool", "-L", str(path)], capture_output=True, text=True)
    if r.returncode != 0 or "is not an object file" in r.stdout + r.stderr:
        return None
    lines = r.stdout.strip().splitlines()[1:]
    return [line.strip().split(" (compatibility")[0] for line in lines]


def fix_unpacked_wheel(root):
    dylibs = [p for p in root.glob("*/.dylibs") if (p / "QtCore").is_file()]
    if not dylibs:
        return False
    dylibs_dir = dylibs[0]
    old_qtcore = dylibs_dir / "QtCore"
    framework_dir = dylibs_dir / FRAMEWORK_REL
    new_qtcore = framework_dir / "QtCore"

    # move QtCore into the framework bundle, with its Info.plist
    (framework_dir / "Resources").mkdir(parents=True)
    shutil.move(old_qtcore, new_qtcore)
    (framework_dir / "Resources" / "Info.plist").write_text(INFO_PLIST)
    modified = {new_qtcore}

    # QtCore itself: its id, and its dependencies are now 3 folders up
    run(
        [
            "install_name_tool",
            "-id",
            f"@loader_path/{FRAMEWORK_REL}/QtCore",
            str(new_qtcore),
        ]
    )
    for dep in macho_dependencies(new_qtcore):
        if dep.startswith("@loader_path/"):
            new_dep = dep.replace("@loader_path/", "@loader_path/../../../", 1)
            run(["install_name_tool", "-change", dep, new_dep, str(new_qtcore)])

    # all the binaries linked to QtCore now point into the framework
    for path in root.rglob("*"):
        if not path.is_file() or path.is_symlink() or path == new_qtcore:
            continue
        deps = macho_dependencies(path)
        if not deps:
            continue
        for dep in deps:
            if dep.startswith("@loader_path") and dep.endswith("/QtCore"):
                new_dep = dep[: -len("QtCore")] + f"{FRAMEWORK_REL}/QtCore"
                run(["install_name_tool", "-change", dep, new_dep, str(path)])
                modified.add(path)

    # install_name_tool invalidates the signature: ad-hoc re-sign (arm64)
    for path in modified:
        run(["codesign", "--force", "--sign", "-", str(path)])
    return True


def write_record(root):
    dist_info = next(root.glob("*.dist-info"))
    record = dist_info / "RECORD"
    lines = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root).as_posix()
        if path == record:
            continue
        data = path.read_bytes()
        digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=")
        lines.append(f"{rel},sha256={digest.decode()},{len(data)}")
    lines.append(f"{record.relative_to(root).as_posix()},,")
    record.write_text("\n".join(lines) + "\n")


def fix_wheel(wheel_path):
    wheel_path = Path(wheel_path).resolve()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "wheel"
        with zipfile.ZipFile(wheel_path) as z:
            z.extractall(root)
            # keep the file permissions
            for info in z.infolist():
                mode = info.external_attr >> 16
                if mode:
                    os.chmod(root / info.filename, mode)
        if not fix_unpacked_wheel(root):
            print(f"{wheel_path.name}: no bare QtCore, unchanged")
            return
        write_record(root)
        new_wheel = wheel_path.with_suffix(".tmp")
        with zipfile.ZipFile(new_wheel, "w", zipfile.ZIP_DEFLATED) as z:
            for path in sorted(p for p in root.rglob("*") if p.is_file()):
                info = zipfile.ZipInfo.from_file(
                    path, path.relative_to(root).as_posix()
                )
                info.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(info, path.read_bytes())
        new_wheel.replace(wheel_path)
        print(f"{wheel_path.name}: QtCore moved into QtCore.framework")


if __name__ == "__main__":
    for w in sys.argv[1:]:
        fix_wheel(w)
