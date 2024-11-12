#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import test037_pet_hits_singles_helpers as t37
from opengate.tests import utility

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "gate_test037_pet", "test037")

    # test version
    v = "2_2"

    # create the simulation
    sim = gate.Simulation()
    crystal = t37.create_pet_simulation(sim, paths, create_mat=True)
    module = sim.volume_manager.volumes["pet_module"]
    die = sim.volume_manager.volumes["pet_die"]
    stack = sim.volume_manager.volumes["pet_stack"]

    # digitizer hits
    hc = sim.add_actor("DigitizerHitsCollectionActor", "Hits")
    hc.attached_to = crystal.name
    hc.authorize_repeated_volumes = True
    hc.output_filename = f"test037_test{v}.root"
    hc.attributes = [
        "PostPosition",
        "TotalEnergyDeposit",
        "PreStepUniqueVolumeID",
        "GlobalTime",
    ]

    # Readout (not need for adder)
    sc = sim.add_actor("DigitizerReadoutActor", "Singles2_1")
    sc.authorize_repeated_volumes = True
    sc.output_filename = f"test037_test{v}.root"
    sc.input_digi_collection = "Hits"
    sc.group_volume = stack.name  # should be depth=1 in Gate
    sc.discretize_volume = crystal.name
    sc.policy = "EnergyWeightedCentroidPosition"

    # Readout: another one, with different option (in the same output file)
    sc = sim.add_actor("DigitizerReadoutActor", "Singles2_2")
    sc.output_filename = f"test037_test{v}.root"
    sc.input_digi_collection = "Hits"
    sc.group_volume = crystal.name  # should be depth=4 in Gate
    sc.discretize_volume = crystal.name
    sc.policy = "EnergyWeightedCentroidPosition"

    # timing
    sec = gate.g4_units.second
    sim.run_timing_intervals = [[0, 0.00005 * sec]]

    # start simulation
    sim.run()

    # print results
    stats = sim.get_actor("Stats")
    print(stats)

    # ----------------------------------------------------------------------------------------------------------

    # check stats
    print()
    gate.exception.warning(f"Check stats")
    # p = paths.gate / "output_test1"
    p = paths.gate / "output"
    stats_ref = utility.read_stat_file(p / f"stats{v}.txt")
    is_ok = utility.assert_stats(stats, stats_ref, 0.03)

    # check root hits
    hc = sim.get_actor("Hits")
    f = p / f"output{v}.root"
    is_ok = t37.check_root_hits(paths, v, f, hc.get_output_path()) and is_ok

    # check root singles
    sc = sim.get_actor("Singles2_1")
    f = p / f"output2_1.root"
    is_ok = (
        t37.check_root_singles(paths, "2_1", f, sc.get_output_path(), sc.name) and is_ok
    )

    # check root singles
    sc = sim.get_actor("Singles2_2")
    f = p / f"output2_2.root"
    is_ok = (
        t37.check_root_singles(paths, "2_2", f, sc.get_output_path(), sc.name) and is_ok
    )

    utility.test_ok(is_ok)
