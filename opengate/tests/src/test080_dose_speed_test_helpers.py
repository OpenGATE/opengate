#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from scipy.spatial.transform import Rotation
import numpy as np
import json
import matplotlib.pyplot as plt

import opengate as gate
from opengate.tests import utility

test_paths = utility.get_default_test_paths(__file__, "gate_test080_dose_speed_test")


def hook_number_of_reattempts(se):
    a = se.actor_engine.get_actor("dose_speed_test_actor")
    nb_reattempts = a.GetTotalReattemptsAtomicAdd()
    nb_deposit_writes = a.GetTotalDepositWrites()
    print(
        f"Nb. reattempts / total writes: {nb_reattempts}/{nb_deposit_writes} = {float(nb_reattempts) / float(nb_deposit_writes) * 100.} %"
    )
    se.hook_log.append(nb_reattempts)
    se.hook_log.append(nb_deposit_writes)


def create_dict_key(s):
    return f"{s['storage_method']}_{s['number_of_threads']}"


def create_label(s):
    return f"{s['name']}, {s['number_of_threads']} threads"


test_scenarios = {}
s = {"storage_method": "local", "number_of_threads": 1, "name": "G4Cache<threadLocalT>"}
test_scenarios[create_dict_key(s)] = s
s = {"storage_method": "local", "number_of_threads": 4, "name": "G4Cache<threadLocalT>"}
test_scenarios[create_dict_key(s)] = s
s = {
    "storage_method": "standard",
    "number_of_threads": 1,
    "name": "std::vector<double>",
}
test_scenarios[create_dict_key(s)] = s
s = {
    "storage_method": "atomic",
    "number_of_threads": 1,
    "name": "std::deque<std::atomic<double>>",
}
test_scenarios[create_dict_key(s)] = s
s = {
    "storage_method": "atomic",
    "number_of_threads": 4,
    "name": "std::deque<std::atomic<double>>",
}
test_scenarios[create_dict_key(s)] = s
s = {
    "storage_method": "atomic_vec_pointer",
    "number_of_threads": 1,
    "name": "std::vector<std::atomic<double>>*",
}
test_scenarios[create_dict_key(s)] = s
s = {
    "storage_method": "atomic_vec_pointer",
    "number_of_threads": 4,
    "name": "std::vector<std::atomic<double>>*",
}
test_scenarios[create_dict_key(s)] = s


def run_simu(
    number_of_primaries,
    storage_method,
    number_of_threads,
    pixel_size,
    count_write_attempts=False,
):
    # create the simulation
    sim = gate.Simulation()

    # main options
    sim.g4_verbose = False
    sim.g4_verbose_level = 1
    sim.visu = False
    sim.random_seed = 12345678910
    sim.number_of_threads = number_of_threads

    # units
    cm = gate.g4_units.cm
    mm = gate.g4_units.mm
    MeV = gate.g4_units.MeV

    #  change world size
    world = sim.world
    world.size = [600 * cm, 500 * cm, 500 * cm]

    # waterbox
    phantom = sim.add_volume("Box", "phantom")
    phantom.size = [20 * cm, 10 * cm, 10 * cm]
    phantom.translation = [15 * cm, 0, 0]
    phantom.material = "G4_WATER"
    phantom.color = [0, 0, 1, 1]
    phantom.set_max_step_size(2 * mm)
    sim.physics_manager.user_limits_particles.all = True

    # default source for tests
    source = sim.add_source("GenericSource", "mysource")
    source.energy.mono = 150 * MeV
    source.particle = "proton"
    source.position.type = "disc"
    source.position.rotation = Rotation.from_euler("y", 90, degrees=True).as_matrix()
    source.position.radius = 10 * mm
    source.position.translation = [0, 0, 0]
    source.direction.type = "momentum"
    source.direction.momentum = [1, 0, 0]
    source.n = number_of_primaries / sim.number_of_threads

    if pixel_size == "small":
        spacing = [2.0 * mm, 2.0 * mm, 2.0 * mm]
    elif pixel_size == "large":
        spacing = [10.0 * mm, phantom.size[1], phantom.size[2]]
    elif pixel_size == "single":
        spacing = phantom.size
    else:
        raise ValueError(
            "Unknown pixelation. Known values are 'small', 'large', 'single'."
        )
    size = [int(length / s) for length, s in zip(phantom.size, spacing)]
    print(f"size: {size}")

    dose_speed_test_actor = sim.add_actor("DoseSpeedTestActor", "dose_speed_test_actor")
    dose_speed_test_actor.mother = phantom.name
    dose_speed_test_actor.size = size
    dose_speed_test_actor.spacing = spacing
    dose_speed_test_actor.storage_method = storage_method
    dose_speed_test_actor.count_write_attempts = count_write_attempts

    # start simulation
    sim.user_hook_after_run = hook_number_of_reattempts
    sim.run(start_new_process=True)

    return sim.output


def run_experiment(scenarios, pixelation):
    """
    scenarios: A dictionary of dictionary, e.g. as defined above.
        Each dictionary contains the parameters of a test case.
    pixelation: A string specifying how the dose actor should be pixelated.
        'small' means 2 mm voxels,
        'large' means 10 mm depth slices, no transverse slicing
        'single' means one single voxel covering the entire volume
    """
    n_primaries_list = np.logspace(3, 7, num=9)

    for k, scenario in scenarios.items():
        sim_times = []
        for n_primaries in n_primaries_list:
            print(30 * "*")
            print(f"Running {k} with {n_primaries} primaries.")
            print(30 * "*")
            output = run_simu(
                n_primaries,
                scenario["storage_method"],
                scenario["number_of_threads"],
                pixel_size=pixelation,
            )
            sim_times.append(output.simulation_time)

        scenario["sim_times"] = sim_times
        scenario["n_primaries_list"] = n_primaries_list.tolist()

    with open(
        test_paths.output / f"results_doseactor_speed_comparison_{pixelation}.json", "w"
    ) as fp:
        json.dump(scenarios, fp, indent=4)


def plot_profile_comparison(scenarios, n_primaries=1e5):
    """
    scenarios: A dictionary of dictionary, e.g. as defined above.
        Each dictionary contains the parameters of a test case.
    pixelation: A string specifying how the dose actor should be pixelated.
        'small' means 2 mm voxels,
        'large' means 10 mm depth slices, no transverse slicing
        'single' means one single voxel covering the entire volume
    """
    plt.figure()
    for s in scenarios.values():
        print(30 * "*")
        print(f"Running {create_label(s)} with {n_primaries} primaries.")
        print(30 * "*")
        output = run_simu(
            n_primaries, s["storage_method"], s["number_of_threads"], "large"
        )
        dose = output.get_actor("dose_speed_test_actor").dose_array
        dose_profile = dose.squeeze()
        plt.plot(dose_profile, label=create_label(s))

    plt.legend()
    plt.tight_layout()
    plt.savefig(test_paths.output / "dose_speed_test_profile_comparison.pdf")
