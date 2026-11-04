#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test 142: the order of the biased processes does not depend on the Python
hash seed.

The biased processes are wrapped by Geant4 in the given order, and this is the
order in which they sample their interaction lengths (e.g. in the volumes
excluded from free flight). If this order changes, the simulation is not
reproducible, even with a fixed random seed.

The list of biased processes is computed in several Python processes with
different hash seeds (PYTHONHASHSEED): it must always be the order declared by
the actors. No simulation is run.
"""

import json
import os
import subprocess
import sys

import opengate as gate
from opengate.tests import utility


def get_biased_processes():
    sim = gate.Simulation()
    ff = sim.add_actor("GammaFreeFlightActor", "ff")
    ff.attached_to = "world"
    return sim.physics_manager.get_biasing_particles_and_processes()


if __name__ == "__main__":
    # child process: print the biased processes and exit
    if len(sys.argv) > 1 and sys.argv[1] == "--print":
        print(json.dumps(get_biased_processes()))
        sys.exit(0)

    expected = {
        "e-": [],
        "e+": [],
        "proton": [],
        "gamma": ["compt", "phot", "conv", "Rayl"],
    }
    is_ok = True
    for hash_seed in ["0", "1", "2", "3"]:
        env = dict(os.environ, PYTHONHASHSEED=hash_seed)
        output = subprocess.run(
            [sys.executable, __file__, "--print"],
            env=env,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        processes = json.loads(output.strip().splitlines()[-1])
        b = processes == expected
        is_ok = (
            utility.print_test(b, f"PYTHONHASHSEED={hash_seed}: {processes}") and is_ok
        )

    utility.test_ok(is_ok)
