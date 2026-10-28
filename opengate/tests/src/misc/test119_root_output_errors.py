#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
1) When Geant4 cannot create a ROOT output file, the simulation must stop with a
   clear error instead of crashing (it used to crash with an access violation on
   Windows).
2) Windows extended-length path prefixes, which Path.resolve() may return
   on Windows, are removed before paths are given to other libraries: with this
   prefix, Windows does not accept the '/' that Geant4 adds to build file names.
"""

import os
import stat
import sys

import opengate as gate
from opengate.tests import utility
from opengate.utility import strip_windows_extended_path_prefix


def check_prefix_stripping():
    is_ok = True
    cases = [
        (r"\\?\C:\data\out\phsp.root", True, r"C:\data\out\phsp.root"),
        (r"\\?\UNC\server\share\phsp.root", True, r"\\server\share\phsp.root"),
        (r"C:\data\out\phsp.root", True, r"C:\data\out\phsp.root"),
        (r"\\?\C:\data\out\phsp.root", False, r"\\?\C:\data\out\phsp.root"),
        ("/home/user/out/phsp.root", False, "/home/user/out/phsp.root"),
    ]
    for path, is_windows, expected in cases:
        result = strip_windows_extended_path_prefix(path, is_windows=is_windows)
        b = result == expected
        utility.print_test(b, f"windows={is_windows}: {path} -> {result}")
        is_ok = is_ok and b
    return is_ok


def run_simulation_with_unwritable_output(output_dir):
    sim = gate.Simulation()
    sim.output_dir = output_dir
    sim.world.size = [1 * gate.g4_units.m] * 3
    source = sim.add_source("GenericSource", "source")
    source.particle = "gamma"
    source.energy.mono = 1 * gate.g4_units.MeV
    source.number_of_primaries = 10
    phsp = sim.add_actor("PhaseSpaceActor", "phsp")
    phsp.attached_to = "world"
    phsp.attributes = ["KineticEnergy"]
    phsp.output_filename = "phsp.root"
    sim.run(start_new_process=False)


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, output_folder="test119")
    is_ok = check_prefix_stripping()

    # Making a folder read-only is not reliable on Windows (and as root), so the
    # second part only runs on Linux and macOS.
    if os.name == "nt" or (hasattr(os, "geteuid") and os.geteuid() == 0):
        print("Skip the unwritable output folder check on this system.")
        utility.test_ok(is_ok)
        sys.exit()

    locked_dir = paths.output / "read_only"
    locked_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(locked_dir, stat.S_IRUSR | stat.S_IXUSR)
    try:
        run_simulation_with_unwritable_output(locked_dir)
        b = False
        message = "no error"
    except Exception as error:
        message = str(error)
        b = "Cannot create the ROOT output file" in message
    finally:
        os.chmod(locked_dir, stat.S_IRWXU)
    utility.print_test(b, f"Unwritable output folder gives a clear error: {message}")
    is_ok = is_ok and b

    utility.test_ok(is_ok)
