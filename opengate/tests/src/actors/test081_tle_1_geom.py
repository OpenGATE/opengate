#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import opengate as gate
from opengate.tests import utility
from opengate.tests.src.actors.test081_tle_helpers import (
    add_waterbox,
    add_source,
    plot_pdd,
    compare_pdd,
)
import sys


def main(argv):
    paths = utility.get_default_test_paths(__file__, output_folder="test081_tle")

    # create the simulation
    sim = gate.Simulation()

    # main options
    # sim.visu = True
    sim.visu_type = "qt"
    sim.random_seed = 12356654
    sim.output_dir = paths.output
    sim.progress_bar = True
    sim.number_of_threads = 1
    if len(argv) > 1:
        sim.number_of_threads = int(argv[1])

    # units
    m = gate.g4_units.m
    mm = gate.g4_units.mm
    MeV = gate.g4_units.MeV

    #  change world size
    world = sim.world
    world.size = [1 * m, 1 * m, 1 * m]

    # create voxelized waterbox
    waterbox = add_waterbox(sim)

    # save voxelized versions of the waterbox
    # voxelize_waterbox(sim, paths.data / "test081_tle")

    # physics
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option3"
    sim.physics_manager.global_production_cuts.all = 1 * mm
    sim.physics_manager.set_max_step_size("waterbox", 1 * mm)
    sim.physics_manager.set_user_limits_particles("gamma")

    s = f"/process/eLoss/CSDARange true"
    sim.g4_commands_before_init.append(s)

    # default source for tests
    source = add_source(sim, n=2e5)

    tle_dose_actor = sim.add_actor("TLEDoseActor", "tle_dose_actor")
    tle_dose_actor.output_filename = "test081_tle.mhd"
    tle_dose_actor.attached_to = waterbox
    tle_dose_actor.dose_uncertainty.active = True
    tle_dose_actor.dose.active = True
    tle_dose_actor.size = [200, 200, 200]
    tle_dose_actor.spacing = [x / y for x, y in zip(waterbox.size, tle_dose_actor.size)]
    print(f"TLE Dose actor pixels : {tle_dose_actor.size}")
    print(f"TLE Dose actor spacing : {tle_dose_actor.spacing} mm")
    print(f"TLE Dose actor size : {waterbox.size} mm")

    # add conventional dose actor
    dose_actor = sim.add_actor("DoseActor", "dose_actor")
    dose_actor.output_filename = "test081.mhd"
    dose_actor.attached_to = waterbox
    dose_actor.dose_uncertainty.active = True
    dose_actor.dose.active = True
    dose_actor.size = [200, 200, 200]
    dose_actor.spacing = [x / y for x, y in zip(waterbox.size, dose_actor.size)]
    print(f"Dose actor pixels : {dose_actor.size}")
    print(f"Dose actor spacing : {dose_actor.spacing} mm")
    print(f"Dose actor size : {waterbox.size} mm")

    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "stats")
    stats.track_types_flag = True

    # start simulation
    sim.run()

    # print results at the end
    print(stats)
    ax, plt = plot_pdd(dose_actor, tle_dose_actor)
    f1 = dose_actor.edep.get_output_path()
    f2 = tle_dose_actor.edep.get_output_path()
    is_ok = compare_pdd(f1, f2, dose_actor.spacing[2], ax[0], tol=0.25)

    print()
    f1 = dose_actor.dose.get_output_path()
    f2 = tle_dose_actor.dose.get_output_path()
    is_ok = compare_pdd(f1, f2, dose_actor.spacing[2], ax[1], tol=0.25) and is_ok

    # output
    f = paths.output / f"pdd_geom.png"
    plt.savefig(f)
    print(f"PDD image saved in {f}")

    utility.test_ok(is_ok)


if __name__ == "__main__":
    main(sys.argv)
