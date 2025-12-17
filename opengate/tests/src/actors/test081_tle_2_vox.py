#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from matplotlib import pyplot as plt
import opengate as gate
from opengate import g4_units
from opengate.tests import utility
from opengate.tests.src.actors.test081_tle_helpers import (
    add_waterbox,
    voxelize_waterbox,
    add_source,
    plot_pdd,
    compare_pdd,
)
from opengate.tests.utility import get_image_1d_profile

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
    keV = gate.g4_units.keV
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

    # default source for tests
    source = add_source(sim, n=2e5)

    # add tle dose actor
    tle_dose_actor = sim.add_actor("TLEDoseActor", "tle_dose_actor")
    tle_dose_actor.output_filename = "test081_vox_tle.mhd"
    tle_dose_actor.attached_to = waterbox
    tle_dose_actor.dose_uncertainty.active = True
    tle_dose_actor.dose.active = True
    tle_dose_actor.size = [100, 100, 100]
    tle_dose_actor.spacing = [x / y for x, y in zip(waterbox_size, tle_dose_actor.size)]
    tle_dose_actor.density.active = True
    tle_dose_actor.score_in = "material"  # only 'material' is allowed
    print(f"TLE Dose actor pixels : {tle_dose_actor.size}")
    print(f"TLE Dose actor spacing : {tle_dose_actor.spacing} mm")
    print(f"TLE Dose actor size : {waterbox_size} mm")

    # add conventional dose actor
    dose_actor = sim.add_actor("DoseActor", "dose_actor")
    dose_actor.output_filename = "test081_vox.mhd"
    dose_actor.attached_to = waterbox
    dose_actor.dose_uncertainty.active = True
    dose_actor.dose.active = True
    dose_actor.size = [100, 100, 100]
    dose_actor.spacing = [x / y for x, y in zip(waterbox_size, dose_actor.size)]
    dose_actor.density.active = True
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
    ax, plt = plot_pdd(dose_actor, tle_dose_actor)
    f1 = dose_actor.edep.get_output_path()
    f2 = tle_dose_actor.edep.get_output_path()
    is_ok = compare_pdd(f1, f2, dose_actor.spacing[2], ax[0], tol=0.17)

    print()
    f1 = dose_actor.dose.get_output_path()
    f2 = tle_dose_actor.dose.get_output_path()
    is_ok = compare_pdd(f1, f2, dose_actor.spacing[2], ax[1], tol=0.17) and is_ok

    # output
    f = paths.output / f"pdd_vox.png"
    plt.savefig(f)
    print(f"PDD image saved in {f}")

    # check density
    utility.assert_images(
        dose_actor.density.get_output_path(),
        tle_dose_actor.density.get_output_path(),
        tolerance=0.001,
    )

    utility.test_ok(is_ok)
