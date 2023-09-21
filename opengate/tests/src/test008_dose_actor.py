#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from scipy.spatial.transform import Rotation
import pathlib

if __name__ == "__main__":
    current_path = pathlib.Path(__file__).parent.resolve()
    data_path = current_path / ".." / "data"
    ref_path = (
        current_path / ".." / "data" / "gate" / "gate_test008_dose_actor" / "output"
    )
    output_path = current_path / ".." / "output"

    # create the simulation
    sim = gate.Simulation()

    # main options
    ui = sim.user_info
    ui.g4_verbose = False
    ui.g4_verbose_level = 1
    ui.visu = False
    ui.random_seed = 12345678

    #  change world size
    m = gate.g4_units("m")
    world = sim.world
    world.size = [1 * m, 1 * m, 1 * m]

    # add a simple fake volume to test hierarchy
    # translation and rotation like in the Gate macro
    fake = sim.add_volume("Box", "fake")
    cm = gate.g4_units("cm")
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
    um = gate.g4_units("um")
    global_cut = 700 * um
    sim.physics_manager.global_production_cuts.gamma = global_cut
    sim.physics_manager.global_production_cuts.electron = global_cut
    sim.physics_manager.global_production_cuts.positron = global_cut
    sim.physics_manager.global_production_cuts.proton = global_cut

    # default source for tests
    source = sim.add_source("GenericSource", "mysource")
    MeV = gate.g4_units("MeV")
    Bq = gate.g4_units("Bq")
    source.energy.mono = 150 * MeV
    nm = gate.g4_units("nm")
    source.particle = "proton"
    source.position.type = "disc"
    source.position.radius = 1 * nm
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    source.activity = 50000 * Bq

    # add dose actor
    dose = sim.add_actor("DoseActor", "dose")
    dose.output = output_path / "test008-edep.mhd"
    dose.mother = "waterbox"
    dose.size = [99, 99, 99]
    mm = gate.g4_units("mm")
    dose.spacing = [2 * mm, 2 * mm, 2 * mm]
    dose.translation = [2 * mm, 3 * mm, -2 * mm]
    dose.uncertainty = True
    dose.hit_type = "random"

    # add stat actor
    s = sim.add_actor("SimulationStatisticsActor", "Stats")
    s.track_types_flag = True

    # start simulation
    sim.run(start_new_process=True)

    # print results at the end
    stat = sim.output.get_actor("Stats")
    print(stat)

    dose = sim.output.get_actor("dose")
    print(dose)

    # tests
    stats_ref = gate.read_stat_file(ref_path / "stat.txt")
    is_ok = gate.assert_stats(stat, stats_ref, 0.11)

    print("\nDifference for EDEP")
    is_ok = (
        gate.assert_images(
            ref_path / "output-Edep.mhd",
            output_path / "test008-edep.mhd",
            stat,
            tolerance=13,
            ignore_value=0,
            sum_tolerance=1,
        )
        and is_ok
    )

    print("\nDifference for uncertainty")
    is_ok = (
        gate.assert_images(
            ref_path / "output-Edep-Uncertainty.mhd",
            output_path / "test008-edep_uncertainty.mhd",
            stat,
            tolerance=30,
            ignore_value=1,
            sum_tolerance=1,
        )
        and is_ok
    )

    gate.test_ok(is_ok)
