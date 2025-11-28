#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
from opengate.tests.src.actors.test081_tle_helpers import (
    add_source,
    plot_pdd,
    compare_pdd,
)

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, output_folder="test081_tle")

    # create the simulation
    sim = gate.Simulation()

    # main options
    # sim.visu = True
    sim.visu_type = "qt"
    sim.random_seed = 321654
    sim.output_dir = paths.output
    sim.progress_bar = True
    sim.number_of_threads = 1

    # units
    m = gate.g4_units.m
    cm = gate.g4_units.cm
    mm = gate.g4_units.mm
    MeV = gate.g4_units.MeV
    Bq = gate.g4_units.Bq

    #  change world size
    world = sim.world
    world.size = [1 * m, 1 * m, 1 * m]

    # insert voxelized waterbox
    spacing = 8
    waterbox = sim.add_volume("Image", "waterbox")
    fn = paths.data / "test081_tle" / f"waterbox_with_inserts_{spacing}mm_"
    waterbox.image = f"{fn}image.mhd"
    waterbox.set_materials_from_voxelisation(f"{fn}labels.json")
    waterbox_size = [30 * cm, 30 * cm, 20 * cm]

    # physics
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option3"
    sim.physics_manager.global_production_cuts.all = 1 * mm
    sim.physics_manager.set_max_step_size("waterbox", 1 * mm)
    sim.physics_manager.set_user_limits_particles("gamma")

    s = f"/process/eLoss/CSDARange true"
    sim.g4_commands_before_init.append(s)

    # default source for tests
    source = add_source(sim, n=2e4, energy=1.2 * MeV, sigma=1 * MeV, radius=1 * mm)

    # add tle dose actor
    tle_dose_actor = sim.add_actor("TLEDoseActor", "tle_dose_actor")
    tle_dose_actor.output_filename = "test081_vox_he_tle.mhd"
    tle_dose_actor.attached_to = waterbox
    tle_dose_actor.dose_uncertainty.active = True
    tle_dose_actor.dose.active = True
    tle_dose_actor.size = [200, 200, 200]
    tle_dose_actor.spacing = [x / y for x, y in zip(waterbox_size, tle_dose_actor.size)]
    # the following option is important: if TLE is used for gammas with too high energy, the
    # resulting dose will be biased. The energy threshold depends on the voxels size of the
    # dose actor. Here the bias is clearly visible if TLE is used above 1.2 MeV.
    # With the threshold enabled, no acceleration for high enery gamma, but no bias.
    tle_dose_actor.tle_threshold_type = "energy"
    tle_dose_actor.tle_threshold = 0.8 * MeV
    tle_dose_actor.database = "EPDL"
    print(f"TLE Dose actor pixels : {tle_dose_actor.size}")
    print(f"TLE Dose actor spacing : {tle_dose_actor.spacing} mm")
    print(f"TLE Dose actor size : {waterbox_size} mm")

    # add conventional dose actor
    dose_actor = sim.add_actor("DoseActor", "dose_actor")
    dose_actor.output_filename = "test081_vox_he.mhd"
    dose_actor.attached_to = waterbox
    dose_actor.dose_uncertainty.active = True
    dose_actor.dose.active = True
    dose_actor.size = [200, 200, 200]
    dose_actor.spacing = [x / y for x, y in zip(waterbox_size, dose_actor.size)]
    print(f"Dose actor pixels : {dose_actor.size}")
    print(f"Dose actor spacing : {dose_actor.spacing} mm")
    print(f"Dose actor size : {waterbox_size} mm")

    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "stats")
    stats.track_types_flag = True

    # start simulation
    sim.run()

    # print results at the end
    print(stats)
    print()
    offset = 0
    ax, plt = plot_pdd(dose_actor, tle_dose_actor, offset=(0, offset))
    f1 = dose_actor.edep.get_output_path()
    f2 = tle_dose_actor.edep.get_output_path()
    is_ok = compare_pdd(f1, f2, dose_actor.spacing[2], ax[0], tol=0.12, offset=offset)

    print()
    f1 = dose_actor.dose.get_output_path()
    f2 = tle_dose_actor.dose.get_output_path()
    is_ok = (
        compare_pdd(f1, f2, dose_actor.spacing[2], ax[1], tol=0.15, offset=offset)
        and is_ok
    )

    # output
    f = paths.output / f"pdd_vox_he.png"
    plt.savefig(f)
    print(f"PDD image saved in {f}")

    utility.test_ok(is_ok)
