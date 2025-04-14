#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from opengate.tests import utility
from test089_helpers import *

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, None, output_folder="test089")

    # create the simulation
    sim = gate.Simulation()
    sim.output_dir = paths.output
    stats, crystals, source = create_test089(sim, "test089_primary", visu=False)

    if sim.visu is False:
        source.activity = 1e8 * gate.g4_units.Bq / sim.number_of_threads

    # Source with AA
    source.direction.acceptance_angle.skip_policy = "SkipEvents"
    source.direction.acceptance_angle.intersection_flag = True
    source.direction.acceptance_angle.normal_flag = True
    source.direction.acceptance_angle.volumes = ["spect0", "spect1"]
    source.direction.acceptance_angle.normal_vector = [1, 0, 0]
    source.direction.acceptance_angle.normal_tolerance = 20 * gate.g4_units.deg

    # free flight actor
    ff = sim.add_actor("GammaFreeFlightActor", "ff")
    ff.attached_to = "world"
    ff.ignored_volumes = crystals

    # go
    sim.run()
    print(stats)
    print(f"Nb of skipped events {source.total_skipped_events}")
