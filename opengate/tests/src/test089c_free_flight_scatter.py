#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from opengate.actors.biasingactors import distance_dependent_angle_tolerance
from opengate.tests import utility
from test089_helpers import *

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, None, output_folder="test089")

    # units
    cm = gate.g4_units.cm
    deg = gate.g4_units.deg

    # sim
    sim = gate.Simulation()
    sim.output_dir = paths.output
    stats, crystals, source = create_test089(sim, "test089_scatter", visu=False)

    if sim.visu is False:
        source.activity = 1e7 * gate.g4_units.Bq / sim.number_of_threads

    # free flight actor
    ff = sim.add_actor("ScatterSplittingFreeFlightActor", "ff")
    ff.attached_to = "world"
    ff.ignored_volumes = crystals
    ff.compton_splitting_factor = 100
    ff.rayleigh_splitting_factor = 100
    ff.max_compton_level = 3
    ff.acceptance_angle.intersection_flag = True
    ff.acceptance_angle.volumes = crystals

    # ??
    ff.acceptance_angle.normal_flag = True
    ff.acceptance_angle.distance_dependent_normal_tolerance = False
    ff.acceptance_angle.normal_vector = [1, 0, 0]
    ff.acceptance_angle.normal_tolerance = 20 * deg

    # go
    sim.run()
    print(stats)
    print(ff)
