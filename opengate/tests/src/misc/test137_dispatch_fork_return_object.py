#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Test 137: dispatch_to_subprocess with the 'fork' start method, when the
function returns an opengate object (#1213).

The returned object (here a volume, which refers to its simulation and its
actors) is unpickled in the parent process. Before the fix, unpickling the
actors created their C++ part in the parent (e.g. a biasing operator, kept by
Geant4 in a global list), inherited by the next forked process, and the next
simulation failed ("Cannot find biased volume").

Two simulations are run one after the other, in a child process of this test
(option --child), because the start method can only be set once.
"""

import multiprocessing
import subprocess
import sys

import opengate as gate
from opengate.tests import utility
from opengate.utility import g4_units


def simulate(output_dir):
    sim = gate.Simulation()
    sim.output_dir = output_dir
    sim.verbose_level = "NONE"
    box = sim.add_volume("Box", "box")
    box.size = [10 * g4_units.cm] * 3
    box.material = "G4_WATER"
    source = sim.add_source("GenericSource", "source")
    source.particle = "gamma"
    source.energy.mono = 140 * g4_units.keV
    source.number_of_primaries = 100
    sim.g4_commands_before_init.append("/process/em/UseGeneralProcess false")
    ff = sim.add_actor("GammaFreeFlightActor", "ff")
    ff.attached_to = "box"
    sim.run()
    # an opengate object is returned
    return box


def run_child(output_dir):
    multiprocessing.set_start_method("fork")
    for i in range(2):
        r = gate.processing.dispatch_to_subprocess(simulate, output_dir)
        print(f"RESULT simulation {i}: {type(r).__name__}", flush=True)


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, None, "test137")
    if "--child" in sys.argv:
        run_child(sys.argv[-1])
        sys.exit(0)

    if "fork" not in multiprocessing.get_all_start_methods():
        print("No 'fork' start method on this platform: test skipped")
        utility.test_ok(True)
        sys.exit(0)

    r = subprocess.run(
        [sys.executable, __file__, "--child", str(paths.output)],
        capture_output=True,
        text=True,
        timeout=600,
    )
    results = [l for l in r.stdout.splitlines() if l.startswith("RESULT")]
    for l in results:
        print(l)
    is_ok = utility.print_test(
        r.returncode == 0
        and results == [f"RESULT simulation {i}: BoxVolume" for i in range(2)],
        f"Two simulations with fork, the first one returns a volume "
        f"(exit code {r.returncode})",
    )
    if not is_ok:
        print(r.stdout[-3000:])
        print(r.stderr[-3000:])

    utility.test_ok(is_ok)
