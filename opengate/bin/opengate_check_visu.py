#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Check which visualisation types work on this machine (vrml, gdml, qt),
without opening any window by default.

Each check runs in its own Python process, so that a crash (for example a Qt
or OpenGL crash) is reported as a failure instead of stopping this tool.
"""

import os
import platform
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

import click

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])

# printed (by a Geant4 shell command) once the Qt viewer is created and the
# geometry drawn, just before the events are simulated and the Qt session starts
QT_READY_MARKER = "OPENGATE_CHECK_VISU_QT_READY"

# printed by Qt when the platform cannot create OpenGL widgets (for example the
# offscreen platform on Linux): the viewer is then not created, the check
# cannot tell anything
QT_NO_OPENGL_MESSAGE = "QOpenGLWidget is not supported on this platform"

# printed by Qt when the OpenGL context of the viewer cannot be created: the
# window opens but stays empty (e.g. the xcbglintegrations plugins are missing)
QT_OPENGL_CONTEXT_FAILED_MESSAGES = (
    "QOpenGLWidget: Failed to create context",
    "neither GLX nor EGL are enabled",
)


def build_simulation(visu_type, visu_filename=None):
    import opengate as gate

    sim = gate.Simulation()
    sim.verbose_level = gate.logger.NONE
    sim.output_dir = Path(tempfile.gettempdir())
    sim.number_of_threads = 1
    sim.visu = True
    sim.visu_type = visu_type
    if visu_filename is not None:
        sim.visu_filename = visu_filename

    cm = gate.g4_units.cm
    sim.world.size = [50 * cm, 50 * cm, 50 * cm]
    box = sim.add_volume("Box", "box")
    box.size = [10 * cm, 10 * cm, 10 * cm]
    box.material = "G4_WATER"

    source = sim.add_source("GenericSource", "source")
    source.particle = "gamma"
    source.energy.mono = 1 * gate.g4_units.MeV
    source.position.type = "point"
    source.direction.type = "iso"
    source.number_of_primaries = 5
    return sim


# ---------------------------------------------------------------------------
# the checks themselves, run in a child process (see run_check_in_process)
# each one prints a short message and exits with 0 if ok


def check_file_output(visu_type, extension, tmp_dir):
    filename = Path(tmp_dir) / f"check_visu.{extension}"
    sim = build_simulation(visu_type, filename)
    sim.run()
    if not filename.is_file() or filename.stat().st_size == 0:
        print(f"no {extension} file written")
        sys.exit(1)
    print(f"{filename.stat().st_size} bytes written")


def check_qt_init(tmp_dir):
    import opengate_core as g4

    ui = g4.G4UIExecutive()
    if not ui.IsGUI():
        print("G4UIExecutive started, but not as a Qt session")
        sys.exit(1)
    print("Qt session created")


def check_qt_viewer(tmp_dir):
    sim = build_simulation("qt")
    # the visu commands create the OpenGL viewer and draw the geometry;
    # the echo is done by the shell, so it is not hidden by the Geant4 output
    sim.visu_commands = list(sim.visu_commands) + [
        f"/control/shell echo {QT_READY_MARKER}"
    ]
    sim.run()


def check_import(module):
    try:
        __import__(module)
    except ModuleNotFoundError:
        print(f"not installed (pip install {module})")
        sys.exit(2)
    print(f"{module} imported")


# optional python modules, only needed to display the vrml or gdml files
OPTIONAL_CHECKS = ("pyvista", "pyg4ometry")

CHECKS = {
    "vrml": lambda d: check_file_output("vrml_file_only", "wrl", d),
    "gdml": lambda d: check_file_output("gdml_file_only", "gdml", d),
    "qt_init": check_qt_init,
    "qt_viewer": check_qt_viewer,
    "pyvista": lambda d: check_import("pyvista"),
    "pyg4ometry": lambda d: check_import("pyg4ometry"),
}


# ---------------------------------------------------------------------------
# the parent process


def child_env(display):
    env = dict(os.environ)
    env["PYTHONFAULTHANDLER"] = "1"
    env["PYTHONUNBUFFERED"] = "1"
    # Qt sends its messages to the system journal when the output is not a
    # terminal: keep them in the output of the check
    env["QT_FORCE_STDERR_LOGGING"] = "1"
    if not display:
        # Qt draws in memory, no window is opened
        env["QT_QPA_PLATFORM"] = "offscreen"
    return env


def run_check_in_process(name, tmp_dir, display, timeout):
    # the child runs in tmp_dir: 'python -m' puts the current folder first in
    # sys.path, so a folder named like a package (e.g. a stale opengate_core
    # in the source folder) would otherwise be imported instead of the package
    cmd = [sys.executable, "-m", "opengate.bin.opengate_check_visu"]
    cmd += ["--run-check", name, "--tmp-dir", str(tmp_dir)]
    if name == "qt_viewer":
        return run_qt_viewer_check(cmd, tmp_dir, display, timeout)
    try:
        r = subprocess.run(
            cmd,
            env=child_env(display),
            cwd=tmp_dir,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return False, f"no answer after {timeout} s", ""
    output = r.stdout + r.stderr
    if r.returncode == 2 and name in OPTIONAL_CHECKS:
        # optional module not installed
        return None, r.stdout.strip(), ""
    return r.returncode == 0, describe_exit(r.returncode, r.stdout), output


def run_qt_viewer_check(cmd, tmp_dir, display, timeout):
    """The Qt session never ends by itself: the check is ok if the process is
    still alive a few seconds after the viewer has been created and the
    geometry drawn (it is in the Qt event loop), and is then stopped."""
    p = subprocess.Popen(
        cmd,
        env=child_env(display),
        cwd=tmp_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    lines = []
    ready_time = None
    start = time.time()

    def read_output():
        for line in p.stdout:
            lines.append(line)

    reader = threading.Thread(target=read_output, daemon=True)
    reader.start()
    while True:
        if ready_time is None and any(QT_READY_MARKER in l for l in lines):
            ready_time = time.time()
        if p.poll() is not None:
            break
        if ready_time is not None and time.time() - ready_time > 5:
            break
        if time.time() - start > timeout:
            break
        time.sleep(0.2)

    alive = p.poll() is None
    if alive:
        p.kill()
        p.wait()
    reader.join(timeout=2)
    output = "".join(lines)
    if not display and QT_NO_OPENGL_MESSAGE in output:
        return None, "no OpenGL with the offscreen Qt, use --display", output
    for message in QT_OPENGL_CONTEXT_FAILED_MESSAGES:
        if message in output:
            return False, f"no OpenGL context ({message})", output
    if ready_time is None:
        if alive:
            return False, f"viewer not created after {timeout} s", output
        return False, describe_exit(p.returncode, output), output
    if alive or p.returncode == 0:
        return True, "OpenGL viewer created, geometry drawn", output
    return (
        False,
        "crash after the viewer creation: " + describe_exit(p.returncode, output),
        output,
    )


def describe_exit(returncode, stdout):
    last = [l for l in stdout.strip().splitlines() if l.strip()]
    if returncode == 0:
        return last[-1] if last else "ok"
    if returncode < 0:
        return f"crashed (signal {-returncode})"
    if returncode > 255 or returncode < -255:
        return f"crashed (code {returncode:#x})"
    return f"failed (code {returncode})"


def is_low_level_trace(line):
    """Lines of the faulthandler crash report that only list binaries."""
    line = line.strip()
    return line.startswith(
        ("Binary file", "Extension modules:", "<truncated", "Current thread")
    )


def print_build_info():
    import opengate_core as g4

    info = g4.GateInfo
    qt = info.get_G4VIS_USE_OPENGLQT()
    print(f"Platform        : {platform.platform()}")
    print(f"Python          : {sys.version.split()[0]}  ({sys.executable})")
    print(f"opengate_core   : {Path(g4.__file__).parent}")
    print(f"Geant4          : {info.get_G4Version()}")
    print(f"Qt in build     : {qt}  {info.get_QT_VERSION() if qt else ''}")
    print(f"GDML in build   : {info.get_G4GDML()}")
    for v in ["DISPLAY", "WAYLAND_DISPLAY", "QT_QPA_PLATFORM"]:
        if v in os.environ:
            print(f"{v:<16}: {os.environ[v]}")
    return qt, info.get_G4GDML()


DESCRIPTIONS = {
    "vrml": "write a VRML file (visu_type='vrml_file_only')",
    "gdml": "write a GDML file (visu_type='gdml_file_only')",
    "qt_init": "start a Geant4 Qt session",
    "qt_viewer": "create the Qt OpenGL viewer, draw the geometry",
    "pyvista": "pyvista, viewer for visu_type='vrml'",
    "pyg4ometry": "pyg4ometry, viewer for visu_type='gdml'",
}


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option(
    "--display",
    "-d",
    is_flag=True,
    help="Run the Qt checks on the real display: a Qt window opens for a few "
    "seconds and is closed automatically. By default, Qt runs offscreen and no "
    "window is opened.",
)
@click.option("--timeout", "-t", default=120, help="Maximum duration of each check (s)")
@click.option("--verbose", "-v", is_flag=True, help="Print the output of every check")
@click.option("--run-check", default=None, hidden=True)
@click.option("--tmp-dir", default=None, hidden=True)
def go(display, timeout, verbose, run_check, tmp_dir):
    """
    Check the visualisation types (vrml, gdml, qt) on this machine.
    No window is opened, unless --display is used.
    """

    # child process: run one check
    if run_check is not None:
        CHECKS[run_check](tmp_dir)
        return

    qt, gdml = print_build_info()
    print()
    skipped = {}
    if not gdml:
        skipped["gdml"] = "Geant4 compiled without GDML"
    if not qt:
        skipped["qt_init"] = "opengate_core compiled without Qt (novis?)"
        skipped["qt_viewer"] = skipped["qt_init"]

    results = {}
    with tempfile.TemporaryDirectory() as tmp:
        for name in CHECKS:
            if name == "qt_viewer" and results.get("qt_init", (True,))[0] is False:
                skipped[name] = "the Qt session cannot be started"
            if name in skipped:
                results[name] = (None, skipped[name], "")
            else:
                results[name] = run_check_in_process(name, tmp, display, timeout)
            ok, message, output = results[name]
            status = {True: "OK", False: "FAIL", None: "SKIP"}[ok]
            print(f"[{status:>4}] {name:<11} {DESCRIPTIONS[name]}")
            print(f"       {'':<11} -> {message}")
            if output and (verbose or ok is False):
                tail = output.strip().splitlines()
                if not verbose:
                    tail = [l for l in tail if not is_low_level_trace(l)][-15:]
                for line in tail:
                    print(f"       | {line}")

    if not display and "qt_viewer" not in skipped:
        print()
        print(
            "Note: the Qt checks ran offscreen. Use --display to check them "
            "with the real display (a window opens for a few seconds)."
        )

    # the optional viewers are not counted as failures
    failed = [
        n for n, r in results.items() if r[0] is False and n not in OPTIONAL_CHECKS
    ]
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    go()
