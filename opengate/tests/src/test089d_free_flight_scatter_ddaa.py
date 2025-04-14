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
    stats, crystals, source = create_test089(sim, "test089_scatter_ddaa", visu=False)

    if sim.visu is False:
        source.activity = 1e7 * gate.g4_units.Bq / sim.number_of_threads

    # free flight actor
    ff = sim.add_actor("ScatterSplittingFreeFlightActor", "ff")
    ff.attached_to = "world"
    ff.ignored_volumes = crystals
    ff.compton_splitting_factor = 50
    ff.rayleigh_splitting_factor = 50
    ff.max_compton_level = 3
    ff.acceptance_angle.intersection_flag = True
    ff.acceptance_angle.volumes = crystals

    # DDAA
    ff.acceptance_angle.normal_flag = True
    ff.acceptance_angle.distance_dependent_normal_tolerance = True
    ff.acceptance_angle.normal_vector = [1, 0, 0]
    ff.acceptance_angle.distance1 = 10 * cm
    ff.acceptance_angle.angle1 = 90 * deg
    ff.acceptance_angle.distance2 = 30 * cm
    ff.acceptance_angle.angle2 = 15 * deg

    # plot dd
    a1 = ff.acceptance_angle.angle1
    a2 = ff.acceptance_angle.angle2
    d1 = ff.acceptance_angle.distance1
    d2 = ff.acceptance_angle.distance2
    distances = np.linspace(d1 / 2, d2 * 2, 200)
    angles = [distance_dependent_angle_tolerance(a1, a2, d1, d2, d) for d in distances]

    import matplotlib.pyplot as plt

    plt.figure(figsize=(8, 6))
    plt.plot(distances / cm, np.degrees(angles), label="Distance vs Angle")
    plt.xlabel("Distance (cm)")
    plt.ylabel("Angle (degrees)")
    plt.title("Distance vs Angle Tolerance")
    plt.grid()
    plt.legend()
    # plt.show()
    f = paths.output / "ddaa.png"
    plt.savefig(f)
    print(f)

    # go
    sim.run()
    print(stats)
    print(ff)
