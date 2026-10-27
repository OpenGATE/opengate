#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Test 134: overlaps of a parametrised volume (RepeatParametrisedVolume).

1. copies without overlap: checked, the simulation runs
2. copies that overlap each other: checked, the overlap is detected (fatal)
3. more copies than sim.check_volumes_overlap_max_copies: not checked
4. same, with a larger check_volumes_overlap_max_copies: the overlap is detected

Each case runs in a child process (option --child), because a fatal error
stops the simulation.
"""

import subprocess
import sys

import opengate as gate
from opengate.logger import INFO
from opengate.tests import utility

mm = gate.g4_units.mm
cm = gate.g4_units.cm


def run_child(spacing, nx, max_copies):
    sim = gate.Simulation()
    sim.verbose_level = INFO
    sim.world.material = "G4_AIR"
    sim.check_volumes_overlap = True
    sim.check_volumes_overlap_max_copies = max_copies

    box = sim.add_volume("Box", "box")
    box.size = [50 * cm, 50 * cm, 5 * cm]
    box.material = "G4_AIR"

    # small boxes of 1 cm, repeated nx times in x and y, with the given spacing
    pixel = sim.add_volume("Box", "pixel")
    pixel.mother = box.name
    pixel.size = [1 * cm, 1 * cm, 1 * cm]
    pixel.material = "G4_WATER"
    repeater = gate.geometry.volumes.RepeatParametrisedVolume(repeated_volume=pixel)
    repeater.translation = [spacing, spacing, 0]
    repeater.linear_repeat = [nx, nx, 1]
    sim.volume_manager.add_volume(repeater)

    source = sim.add_source("GenericSource", "source")
    source.particle = "gamma"
    source.energy.mono = 100 * gate.g4_units.keV
    source.number_of_primaries = 10

    sim.run()


def run_case(spacing, nx, max_copies=100):
    r = subprocess.run(
        [sys.executable, __file__, "--child", str(spacing), str(nx), str(max_copies)],
        capture_output=True,
        text=True,
    )
    return r.returncode, r.stdout + r.stderr


if __name__ == "__main__":
    if "--child" in sys.argv:
        run_child(float(sys.argv[-3]), int(sys.argv[-2]), int(sys.argv[-1]))
        sys.exit(0)

    is_ok = True
    overlap_msg = 'Some volumes overlap with the volume "pixel_param"'
    skip_msg = 'Overlaps of the volume "pixel_param" are not checked'

    # 1. no overlap: 3 x 3 copies, 12 mm apart
    code, out = run_case(12 * mm, 3)
    b = code == 0 and overlap_msg not in out and skip_msg not in out
    is_ok = utility.print_test(b, f"No overlap: no error (exit code {code})") and is_ok

    # 2. overlap: 3 x 3 copies, 5 mm apart
    code, out = run_case(5 * mm, 3)
    b = code != 0 and overlap_msg in out
    is_ok = utility.print_test(b, f"Overlap detected (exit code {code})") and is_ok

    # 3. overlap, but 20 x 20 = 400 copies, more than max_copies = 100: not checked
    code, out = run_case(5 * mm, 20)
    b = code == 0 and skip_msg in out
    is_ok = (
        utility.print_test(b, f"400 copies: not checked (exit code {code})") and is_ok
    )

    # 4. same, with max_copies = 400: checked, the overlap is detected
    code, out = run_case(5 * mm, 20, max_copies=400)
    b = code != 0 and overlap_msg in out
    is_ok = (
        utility.print_test(
            b, f"400 copies, max_copies = 400: overlap detected (exit code {code})"
        )
        and is_ok
    )

    utility.test_ok(is_ok)
