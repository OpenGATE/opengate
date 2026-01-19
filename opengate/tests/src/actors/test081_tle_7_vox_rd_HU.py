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
    add_iso_source,
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
    gcm3 = gate.g4_units.g / gate.g4_units.cm3
    m = gate.g4_units.m
    cm = gate.g4_units.cm
    mm = gate.g4_units.mm
    keV = gate.g4_units.keV
    MeV = gate.g4_units.MeV
    Bq = gate.g4_units.Bq

    #  change world size
    world = sim.world
    world.size = [1 * m, 1 * m, 1 * m]

    # insert voxelized waterbox
    fn = paths.data / "test081_tle"
    box = sim.add_volume("Image", "box")
    box.image = f"{fn}/random_HU_img.mhd"
    box.mother = "world"
    box.material = "G4_AIR"  # material used by default
    f1 = paths.data / "Schneider2000MaterialsTable.txt"
    f2 = paths.data / "Schneider2000DensitiesTable.txt"
    tol = 0.05 * gcm3
    box.voxel_materials, materials = gate.geometry.materials.HounsfieldUnit_to_material(
        sim, tol, f1, f2
    )
    box.color = [1, 0, 1, 1]
    box_size = [180, 180, 180]
    # waterbox_size = [30 * cm, 30 * cm, 20 * cm]

    # physics
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option3"
    sim.physics_manager.global_production_cuts.all = 1 * mm
    s = f"/process/eLoss/CSDARange true"
    sim.g4_commands_before_init.append(s)

    # default source for tests
    source = add_iso_source(sim, n=4e5)

    # add tle dose actor
    tle_dose_actor = sim.add_actor("TLEDoseActor", "tle_dose_actor")
    tle_dose_actor.output_filename = "test081_vox_tle_rd_HU.mhd"
    tle_dose_actor.attached_to = box
    tle_dose_actor.dose_uncertainty.active = True
    tle_dose_actor.dose.active = True
    tle_dose_actor.size = [20, 20, 20]
    tle_dose_actor.spacing = [x / y for x, y in zip(box_size, tle_dose_actor.size)]
    tle_dose_actor.density.active = True
    tle_dose_actor.tle_threshold_type = "average range"
    tle_dose_actor.tle_threshold = 3 * mm
    # tle_dose_actor.tle_threshold_type = "energy"
    # tle_dose_actor.tle_threshold = 1*MeV
    tle_dose_actor.score_in = "material"  # only 'material' is allowed
    print(f"TLE Dose actor pixels : {tle_dose_actor.size}")
    print(f"TLE Dose actor spacing : {tle_dose_actor.spacing} mm")
    print(f"TLE Dose actor size : {box_size} mm")

    # add conventional dose actor
    dose_actor = sim.add_actor("DoseActor", "dose_actor")
    dose_actor.output_filename = "test081_vox_rd_HU.mhd"
    dose_actor.attached_to = box
    dose_actor.dose_uncertainty.active = True
    dose_actor.dose.active = True
    dose_actor.size = [20, 20, 20]
    dose_actor.spacing = [x / y for x, y in zip(box_size, dose_actor.size)]
    dose_actor.density.active = True
    print(f"Dose actor pixels : {dose_actor.size}")
    print(f"Dose actor spacing : {dose_actor.spacing} mm")
    print(f"Dose actor size : {box_size} mm")

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
    is_ok = compare_pdd(f1, f2, dose_actor.spacing[2], ax[0], tol=0.1)

    f1 = dose_actor.dose.get_output_path()
    f2 = tle_dose_actor.dose.get_output_path()
    is_ok = compare_pdd(f1, f2, dose_actor.spacing[2], ax[1], tol=0.1) and is_ok

    # output
    f = paths.output / f"pdd_vox_rd_HU.png"
    plt.savefig(f)
    print(f"PDD image saved in {f}")

    # check density
    utility.assert_images(
        dose_actor.density.get_output_path(),
        tle_dose_actor.density.get_output_path(),
        tolerance=0.001,
    )

    utility.test_ok(is_ok)
