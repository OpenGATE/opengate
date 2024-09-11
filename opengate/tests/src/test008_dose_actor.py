#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
from scipy.spatial.transform import Rotation
from pathlib import Path

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "gate_test008_dose_actor")
    ref_path = paths.gate_output

    # create the simulation
    sim = gate.Simulation()

    # main options
    sim.g4_verbose = False
    sim.g4_verbose_level = 1
    sim.visu = False
    sim.random_seed = 12345678
    sim.output_dir = paths.output / Path(__file__.rstrip(".py")).stem

    # shortcuts for units
    m = gate.g4_units.m
    cm = gate.g4_units.cm

    #  change world size
    world = sim.world
    world.size = [1 * m, 1 * m, 1 * m]

    # add a simple fake volume to test hierarchy
    # translation and rotation like in the Gate macro
    fake = sim.add_volume("Box", "fake")
    fake.size = [40 * cm, 40 * cm, 40 * cm]
    fake.translation = [1 * cm, 2 * cm, 3 * cm]
    fake.rotation = Rotation.from_euler("x", 10, degrees=True).as_matrix()
    fake.material = "G4_AIR"
    fake.color = [1, 0, 1, 1]

    # waterbox
    waterbox = sim.add_volume("Box", "waterbox")
    waterbox.mother = "fake"
    waterbox.size = [10 * cm, 10 * cm, 10 * cm]
    waterbox.translation = [-3 * cm, -2 * cm, -1 * cm]
    waterbox.rotation = Rotation.from_euler("y", 20, degrees=True).as_matrix()
    waterbox.material = "G4_WATER"
    waterbox.color = [0, 0, 1, 1]

    # physics
    sim.physics_manager.physics_list_name = "QGSP_BERT_EMV"
    sim.physics_manager.enable_decay = False
    sim.physics_manager.apply_cuts = True  # default
    um = gate.g4_units.um
    global_cut = 700 * um
    sim.physics_manager.global_production_cuts.gamma = global_cut
    sim.physics_manager.global_production_cuts.electron = global_cut
    sim.physics_manager.global_production_cuts.positron = global_cut
    sim.physics_manager.global_production_cuts.proton = global_cut

    # default source for tests
    source = sim.add_source("GenericSource", "mysource")
    MeV = gate.g4_units.MeV
    Bq = gate.g4_units.Bq
    source.energy.mono = 150 * MeV
    nm = gate.g4_units.nm
    source.particle = "proton"
    source.position.type = "disc"
    source.position.radius = 1 * nm
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    source.activity = 50000 * Bq

    # add dose actor
    dose = sim.add_actor("DoseActor", "dose")
    dose.attached_to = "waterbox"
    dose.size = [99, 99, 99]
    mm = gate.g4_units.mm
    dose.spacing = [2 * mm, 2 * mm, 2 * mm]
    dose.translation = [2 * mm, 3 * mm, -2 * mm]
    dose.edep_uncertainty.active = True
    dose.hit_type = "random"
    dose.output_coordinate_system = "local"
    dose.output_filename = "test.nii.gz"

    # add stat actor
    stat = sim.add_actor("SimulationStatisticsActor", "Stats")
    stat.track_types_flag = True

    # start simulation
    sim.run(start_new_process=True)

    # print results at the end
    print(stat)
    print(dose)

    # tests
    stats_ref = utility.read_stat_file(ref_path / "stat.txt")
    is_ok = utility.assert_stats(stat, stats_ref, 0.11)

    print("\nDifference for EDEP")
    is_ok = (
        utility.assert_images(
            ref_path / "output-Edep.mhd",
            dose.edep.get_output_path(),
            stat,
            tolerance=13,
            ignore_value=0,
            sum_tolerance=1,
        )
        and is_ok
    )

    print("\nDifference for uncertainty")
    is_ok = (
        utility.assert_images(
            ref_path / "output-Edep-Uncertainty.mhd",
            dose.edep_uncertainty.get_output_path(),
            stat,
            tolerance=30,
            ignore_value=1,
            sum_tolerance=1,
        )
        and is_ok
    )

    utility.test_ok(is_ok)
