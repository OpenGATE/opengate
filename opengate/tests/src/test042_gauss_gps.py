#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from scipy.spatial.transform import Rotation
import opengate as gate
from opengate.tests import utility

if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, "gate_test042_gauss_gps", "test042"
    )

    # create the simulation
    sim = gate.Simulation()

    # main options
    sim.g4_verbose = False
    sim.g4_verbose_level = 1
    sim.visu = False
    sim.random_seed = 123456
    sim.output_dir = paths.output

    # units
    m = gate.g4_units.m
    cm = gate.g4_units.cm
    mm = gate.g4_units.mm
    km = gate.g4_units.km
    MeV = gate.g4_units.MeV
    Bq = gate.g4_units.Bq
    kBq = 1000 * Bq

    # add a material database
    sim.volume_manager.add_material_database(paths.gate_data / "HFMaterials2014.db")

    #  change world size
    world = sim.world
    world.size = [600 * cm, 500 * cm, 500 * cm]
    world.material = "Vacuum"

    # waterbox
    phantom = sim.add_volume("Box", "phantom")
    phantom.size = [10 * cm, 10 * cm, 10 * cm]
    phantom.translation = [-5 * cm, 0, 0]
    phantom.material = "G4_WATER"
    phantom.color = [0, 0, 1, 1]

    # daughter
    phantom_y = sim.add_volume("Box", "phantom_y")
    phantom_y.mother = phantom.name
    phantom_y.size = [2 * mm, 10 * cm, 2 * mm]
    phantom_y.translation = [49 * mm, 0, 0]
    phantom_y.material = "G4_WATER"
    phantom_y.color = [0, 0, 1, 1]

    # physics
    sim.physics_manager.physics_list_name = "QGSP_INCLXX_EMZ"
    sim.physics_manager.global_production_cuts.all = 1000 * km
    # FIXME need SetMaxStepSizeInRegion ActivateStepLimiter
    # e.g., like so:
    # sim.physics_manager.set_max_step_size(
    #     volume_name="phantom", max_step_size=1 * mm
    # )
    # or:
    # reg = sim.physics_manager.add_region('reg')
    # reg.max_step_size = 1 * mm
    # reg.associate_volume(phantom)

    # default source for tests
    source = sim.add_source("GenericSource", "mysource")
    source.energy.mono = 40 * MeV
    source.particle = "proton"
    source.position.type = "disc"  # pos = Beam, shape = circle + sigma
    # rotate the disc, equiv to : rot1 0 1 0 and rot2 0 0 1
    source.position.rotation = Rotation.from_euler("y", 90, degrees=True).as_matrix()
    # source.position.radius = 8 * mm
    source.position.sigma_x = 8 * mm
    source.position.sigma_y = 8 * mm
    source.direction.type = "momentum"
    source.direction.momentum = [-1, 0, 0]
    source.activity = 100 * kBq

    # add dose actor
    dose = sim.add_actor("DoseActor", "doseInXZ")
    dose.output_filename = paths.output / "test042-lateral_xz.mhd"
    dose.attached_to = phantom.name
    dose.size = [250, 1, 250]
    dose.spacing = [0.4, 100, 0.4]
    dose.hit_type = "random"

    dose = sim.add_actor("DoseActor", "doseInXY")
    dose.output_filename = paths.output / "test042-lateral_xy.mhd"
    dose.attached_to = phantom.name
    dose.size = [250, 250, 1]
    dose.spacing = [0.4, 0.4, 100]
    dose.hit_type = "random"

    dose = sim.add_actor("DoseActor", "doseInYZ")
    dose.output_filename = paths.output / "test042-lateral_yz.mhd"
    dose.attached_to = phantom.name
    dose.size = [1, 250, 250]
    dose.spacing = [100, 0.4, 0.4]
    dose.hit_type = "random"

    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "stats")
    stats.track_types_flag = True

    # start simulation
    sim.run()

    # print results at the end
    print(stats)

    dose = sim.get_actor("doseInXZ")
    print(dose)

    # ----------------------------------------------------------------------------------------------------------------
    # tests
    print()
    gate.exception.warning("Tests stats file")
    stats_ref = utility.read_stat_file(paths.gate_output / "stats.txt")
    is_ok = utility.assert_stats(stats, stats_ref, 0.14)

    print()
    gate.exception.warning("Difference for EDEP XZ")
    is_ok = (
        utility.assert_images(
            paths.gate_output / "lateral_xz_Protons_40MeV_sourceShapeGaussian-Edep.mhd",
            paths.output / sim.get_actor("doseInXZ").get_output_path("edep"),
            stats,
            tolerance=10,
            ignore_value=0,
        )
        and is_ok
    )

    print()
    gate.exception.warning("Difference for EDEP XY")
    is_ok = (
        utility.assert_images(
            paths.gate_output / "lateral_xy_Protons_40MeV_sourceShapeGaussian-Edep.mhd",
            paths.output / sim.get_actor("doseInXY").get_output_path("edep"),
            stats,
            tolerance=10,
            ignore_value=0,
            axis="y",
        )
        and is_ok
    )

    print()
    gate.exception.warning("Difference for EDEP YZ")
    is_ok = (
        utility.assert_images(
            paths.gate_output / "lateral_yz_Protons_40MeV_sourceShapeGaussian-Edep.mhd",
            paths.output / sim.get_actor("doseInYZ").get_output_path("edep"),
            stats,
            tolerance=30,
            ignore_value=0,
            axis="y",
        )
        and is_ok
    )

    utility.test_ok(is_ok)
