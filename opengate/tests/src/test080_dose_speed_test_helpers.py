#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from scipy.spatial.transform import Rotation
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


scenarios = {}
s = {"storage_method": "local", "number_of_threads": 1, "name": "G4Cache<threadLocalT>"}
scenarios[create_dict_key(s)] = s
s = {"storage_method": "local", "number_of_threads": 4, "name": "G4Cache<threadLocalT>"}
scenarios[create_dict_key(s)] = s
s = {
    "storage_method": "standard",
    "number_of_threads": 1,
    "name": "std::vector<double>",
}
scenarios[create_dict_key(s)] = s
s = {
    "storage_method": "atomic",
    "number_of_threads": 1,
    "name": "std::deque<std::atomic<double>>",
}
scenarios[create_dict_key(s)] = s
s = {
    "storage_method": "atomic",
    "number_of_threads": 4,
    "name": "std::deque<std::atomic<double>>",
}
scenarios[create_dict_key(s)] = s
s = {
    "storage_method": "atomic_vec_pointer",
    "number_of_threads": 1,
    "name": "std::vector<std::atomic<double>>*",
}
scenarios[create_dict_key(s)] = s
s = {
    "storage_method": "atomic_vec_pointer",
    "number_of_threads": 4,
    "name": "std::vector<std::atomic<double>>*",
}
scenarios[create_dict_key(s)] = s


def run_simu(number_of_primaries, storage_method, number_of_threads, pixel_size):
    # create the simulation
    sim = gate.Simulation()

    # main options
    sim.g4_verbose = False
    sim.g4_verbose_level = 1
    sim.visu = False
    sim.random_seed = 12345678910
    sim.number_of_threads = number_of_threads

    # numPartSimTest = 2000
    numPartSimTest = number_of_primaries

    # units
    cm = gate.g4_units.cm
    mm = gate.g4_units.mm
    MeV = gate.g4_units.MeV

    #  change world size
    world = sim.world
    world.size = [600 * cm, 500 * cm, 500 * cm]

    # waterbox
    phantom = sim.add_volume("Box", "phantom")
    phantom.size = [10 * cm, 10 * cm, 10 * cm]
    phantom.translation = [-5 * cm, 0, 0]
    phantom.material = "G4_WATER"
    phantom.color = [0, 0, 1, 1]

    test_material_name = "G4_WATER"
    phantom_off = sim.add_volume("Box", "phantom_off")
    phantom_off.mother = phantom.name
    phantom_off.size = [100 * mm, 60 * mm, 60 * mm]
    phantom_off.translation = [0 * mm, 0 * mm, 0 * mm]
    phantom_off.material = test_material_name
    phantom_off.color = [0, 0, 1, 1]
    # phantom_off.set_max_step_size(1 * mm)
    # sim.physics_manager.user_limits_particles.all = True

    # default source for tests
    source = sim.add_source("GenericSource", "mysource")
    source.energy.mono = 80 * MeV
    source.particle = "proton"
    source.position.type = "disc"
    source.position.rotation = Rotation.from_euler("y", 90, degrees=True).as_matrix()
    source.position.radius = 30 * mm
    source.position.translation = [0, 0, 0]
    source.direction.type = "momentum"
    source.direction.momentum = [-1, 0, 0]
    source.n = numPartSimTest / sim.number_of_threads

    if pixel_size == "small":
        spacing = [2.0 * mm, 2.0 * mm, 2.0 * mm]
    elif pixel_size == "large":
        spacing = [10.0 * mm, phantom_off.size[1], phantom_off.size[2]]
    elif pixel_size == "single":
        spacing = phantom_off.size
    size = [int(length / s) for length, s in zip(phantom_off.size, spacing)]
    print(f"size: {size}")

    dose_speed_test_actor = sim.add_actor("DoseSpeedTestActor", "dose_speed_test_actor")
    dose_speed_test_actor.mother = phantom_off.name
    dose_speed_test_actor.size = size
    dose_speed_test_actor.spacing = spacing
    dose_speed_test_actor.storage_method = storage_method

    # start simulation
    sim.user_hook_after_run = hook_number_of_reattempts
    sim.run(start_new_process=True)

    return sim.output
