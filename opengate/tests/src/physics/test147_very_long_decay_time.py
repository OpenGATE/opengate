#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Radioactive decay of ions with a very long half-life (#358).
Since Geant4 11.2, the decay of the ions whose lifetime is above the threshold
"thresholdForVeryLongDecayTime" is ignored (e.g. Cs137, 30 years). It can be
changed with a G4 command after the initialization.
"""

import opengate as gate
from opengate.tests import utility

m = gate.g4_units.m
n = 200


def run(threshold_command):
    sim = gate.Simulation()
    sim.output_dir = paths.output
    sim.verbose_level = gate.logger.NONE
    sim.random_seed = 123456
    sim.world.size = [1 * m, 1 * m, 1 * m]
    sim.world.material = "G4_WATER"
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option4"
    sim.physics_manager.enable_decay = True

    source = sim.add_source("GenericSource", "cs137")
    source.particle = "ion 55 137"
    source.energy.mono = 0
    source.number_of_primaries = n

    if threshold_command:
        sim.g4_commands_after_init.append(
            "/process/had/rdm/thresholdForVeryLongDecayTime 1.0e+60 year"
        )

    stats = sim.add_actor("SimulationStatisticsActor", "stats")
    stats.track_types_flag = True
    sim.run(start_new_process=True)
    return stats.counts.track_types


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "", output_folder="test147")

    # default threshold: with Geant4 11.4, Cs137 does not decay (only printed, the
    # default value may change with the Geant4 version)
    tt = run(False)
    print(f"Default threshold: {tt.get('Ba137', 0)} Ba137 for {n} Cs137")

    # larger threshold: all Cs137 decay into Ba137 (+ e- and anti_nu_e)
    tt = run(True)
    nba = tt.get("Ba137", 0)
    nnu = tt.get("anti_nu_e", 0)
    is_ok = nba == n and nnu == n
    utility.print_test(
        is_ok, f"Larger threshold: {nba} Ba137 and {nnu} anti_nu_e for {n} Cs137"
    )

    utility.test_ok(is_ok)
