#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pickle

import opengate as gate
import opengate.tests.utility as tu

if __name__ == "__main__":
    # create the simulation
    sim = gate.Simulation()
    sim.verbose_getstate = True

    # waterbox
    waterbox = sim.add_volume("Box", "waterbox")

    # add actor1
    actor1 = sim.add_actor("DoseActor", "actor1")
    actor1.attached_to = "waterbox"
    actor1.output_filename = "original.mhd"
    actor1.edep_uncertainty.active = True
    actor1.edep.keep_data_per_run = True

    # add stat actor
    stat = sim.add_actor("SimulationStatisticsActor", "Stats")
    stat.track_types_flag = True

    kill = sim.add_actor("KillActor", "kill")

    print("****************  PICKLE SIM  ****************")
    sim_pickled = pickle.dumps(sim)
    print("***************  UNPICKLE SIM ***************")
    sim_reloaded = pickle.loads(sim_pickled)

    stat_reloaded = sim_reloaded.get_actor("Stats")
    actor1_reloaded = sim_reloaded.get_actor("actor1")
    actor1_reloaded.edep.output_filename = "reloaded.mhd"
    actor1_reloaded.edep_uncertainty.active = False

    sim_pickled_twice = pickle.loads(pickle.dumps(sim_reloaded))

    actor1_reloaded_twice = sim_pickled_twice.get_actor("actor1")

    is_ok = True
    print("**** TEST ****")

    b = actor1_reloaded_twice.edep.output_filename != actor1.edep.output_filename
    is_ok &= b
    print(
        f"Test: Is the input parameter 'output_filename' equal in original and "
        f"re-re-loaded actor output to which interface edep belongs? \n"
        f"Expected: not equal. Passed: {b}"
    )

    b = (
        actor1_reloaded_twice.edep_uncertainty.active
        is not actor1.edep_uncertainty.active
    )
    is_ok &= b
    print(
        f"Test: Is the input parameter 'active' equal in original and "
        f"re-re-loaded actor output to which interface edep_uncertainty belongs? \n"
        f"Expected: not equal. Passed: {b}"
    )

    b = stat.stats.belongs_to_actor is stat
    is_ok &= b
    print(f"interface in original actor belongs to original actor? Passed: {b}")

    b = stat_reloaded.stats.belongs_to_actor is stat_reloaded
    is_ok &= b
    print(f"interface in reloaded belongs to reloaded actor? Passed: {b}")

    tu.test_ok(is_ok)
