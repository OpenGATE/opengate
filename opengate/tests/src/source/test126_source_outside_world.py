#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
A source that generates primary particles outside the world volume is
reported with a clear error, naming the source and the position. (Geant4
would stop with "Primary vertex outside of the world!", and since Geant4
11.4.3 it even crashes.) A source on the world surface is accepted.
Each simulation runs in a new Python process.
"""

import subprocess
import sys

from opengate.tests import utility

script = """
import opengate as gate

if __name__ == "__main__":
    sim = gate.Simulation()
    sim.output_dir = r"{output}"
    cm = gate.g4_units.cm
    sim.world.size = [20 * cm, 20 * cm, 20 * cm]
    sim.world.material = "G4_Galactic"
    src = sim.add_source("GenericSource", "my_source")
    src.particle = "gamma"
    src.energy.mono = 1 * gate.g4_units.MeV
    src.position.type = "point"
    src.position.translation = [0, 0, {z} * cm]
    src.direction.type = "momentum"
    src.direction.momentum = [0, 0, -1]
    src.number_of_primaries = 10
    sim.run()
    print("RUN ENDED")
"""


def run(paths, z):
    code = script.format(output=paths.output, z=z)
    r = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, timeout=600
    )
    return r.returncode, r.stdout + r.stderr


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, output_folder="test126")
    is_ok = True

    # outside the world (half size 10 cm)
    code, out = run(paths, 15)
    b = (
        code != 0
        and "RUN ENDED" not in out
        and "The source 'my_source' generated a primary particle" in out
        and "outside the world volume" in out
    )
    utility.print_test(b, f"Source outside the world: clear error (exit code {code})")
    if not b:
        print(out[-3000:])
    is_ok = is_ok and b

    # inside, and on the surface of the world: accepted
    for z, name in [(5, "inside"), (10, "on the world surface")]:
        code, out = run(paths, z)
        b = code == 0 and "RUN ENDED" in out
        utility.print_test(b, f"Source {name}: accepted (exit code {code})")
        if not b:
            print(out[-3000:])
        is_ok = is_ok and b

    utility.test_ok(is_ok)
