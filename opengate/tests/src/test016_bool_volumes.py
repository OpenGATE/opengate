#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.geometry.volumes import unite_volumes, subtract_volumes, intersect_volumes
import opengate_core as g4
from scipy.spatial.transform import Rotation

import opengate.tests.utility as tu


# the function called 'after_init' MUST be defined outside the main block
# It is used as "hook function" in the simulation and MUST take a simulation_engine object
# as input argument. No other arguments are accepted.
def after_init(simulation_engine):
    print("Checking solid ...")
    v = simulation_engine.volume_engine.get_volume("my_stuff").g4_logical_volume
    is_ok = v.GetName() == "my_stuff"
    tu.print_test(is_ok, f"Get volume {v.GetName()}")
    solid = v.GetSolid()
    pMin = g4.G4ThreeVector()
    pMax = g4.G4ThreeVector()
    solid.BoundingLimits(pMin, pMax)
    is_ok = list(pMin) == list([-50, -90, -100]) and is_ok
    tu.print_test(is_ok, f"pMin {pMin}")
    is_ok = list(pMax) == list([50, 60, 100]) and is_ok
    tu.print_test(is_ok, f"pMax {pMax}")
    if not is_ok:
        tu.test_ok(is_ok)


if __name__ == "__main__":
    paths = tu.get_default_test_paths(__file__)

    # global log level
    # create the simulation
    sim = gate.Simulation()
    print(f"Volumes types: {sim.volume_manager.dump_volume_types()}")

    # main options
    sim.g4_verbose = False
    sim.g4_verbose_level = 1
    sim.visu = False
    sim.check_volumes_overlap = True
    sim.random_seed = 1236789

    # add a material database
    sim.volume_manager.add_material_database(paths.data / "GateMaterials.db")

    # shortcuts for units
    m = gate.g4_units.m
    cm = gate.g4_units.cm
    mm = gate.g4_units.mm
    MeV = gate.g4_units.MeV
    Bq = gate.g4_units.Bq

    #  change world size
    sim.world.size = [1 * m, 1 * m, 1 * m]

    # first create the volumes to be used in the boolean operations
    b = gate.geometry.volumes.BoxVolume(name="box")
    b.size = [10 * cm, 10 * cm, 10 * cm]
    s = gate.geometry.volumes.SphereVolume(name="test_sph")
    s.rmax = 5 * cm
    t = gate.geometry.volumes.TubsVolume(name="t")
    t.rmin = 0
    t.rmax = 2 * cm
    t.dz = 15 * cm

    # boolean operations
    a1 = unite_volumes(b, s, translation=[0, 1 * cm, 5 * cm])
    a2 = subtract_volumes(a1, t, translation=[0, 1 * cm, 5 * cm])
    a3 = unite_volumes(a2, b, translation=[0, -1 * cm, -5 * cm])
    c = intersect_volumes(t, s, translation=[3 * cm, 0, 0])
    u = unite_volumes(a3, c, translation=[0, -7 * cm, -5 * cm], new_name="my_stuff")

    # Set user infos of this new volume
    u.translation = [5 * cm, 5 * cm, 5 * cm]
    u.rotation = Rotation.from_euler("x", 33, degrees=True).as_matrix()
    u.mother = "world"
    u.material = "G4_WATER"
    u.color = [0, 1, 0, 1]
    # add the new volume to the simulation
    sim.volume_manager.add_volume(u)

    # create a volume from a solid (not really useful)
    sim.volume_manager.add_volume(s)
    s.translation = [-5 * cm, -5 * cm, 1 - 5 * cm]
    s.mother = "world"
    s.material = "G4_WATER"
    s.color = [0, 1, 1, 1]

    # default source for tests
    source = sim.add_source("GenericSource", "Default")
    source.particle = "proton"
    source.energy.mono = 240 * MeV
    source.position.radius = 1 * cm
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    source.activity = 5 * Bq

    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")

    # function to run after init

    # create G4 objects
    print(sim)

    # start simulation
    sim.user_hook_after_init = after_init
    sim.run(True)

    # print results at the end
    print(stats)

    tu.test_ok(True)
