#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import opengate_core as g4
from scipy.spatial.transform import Rotation
import pathlib

pathFile = pathlib.Path(__file__).parent.resolve()

# global log level
# create the simulation
sim = gate.Simulation()
print(f"Volumes types: {sim.dump_volume_types()}")

# main options
ui = sim.user_info
ui.g4_verbose = False
ui.g4_verbose_level = 1
ui.visu = False
ui.check_volumes_overlap = True

# add a material database
sim.add_material_database(pathFile / ".." / "data" / "GateMaterials.db")

#  change world size
m = gate.g4_units("m")
cm = gate.g4_units("cm")
mm = gate.g4_units("mm")
world = sim.world
world.size = [1 * m, 1 * m, 1 * m]

# create a union of several volumes

# first create the boolean volumes
# use the create_volume() method, *not* the create_and_add_volume() method
b = sim.volume_manager.create_volume("Box", "box")
b.size = [10 * cm, 10 * cm, 10 * cm]
s = sim.volume_manager.create_volume("Sphere", "test_sph")
s.rmax = 5 * cm
t = sim.volume_manager.create_volume("Tubs", "t")
t.rmin = 0
t.rmax = 2 * cm
t.dz = 15 * cm

# bool operations
a = s.add_to(b, translation=[0, 1 * cm, 5 * cm])
a = t.subtract_from(a, translation=[0, 1 * cm, 5 * cm])
a = b.add_to(a, translation=[0, -1 * cm, -5 * cm])
b = s.intersect_with(t, translation=[3 * cm, 0, 0])
u = b.add_to(a, translation=[0, -7 * cm, -5 * cm], new_name="my_stuff")

# a = gate.solid_union(b, s, [0, 1 * cm, 5 * cm])
# a = gate.solid_subtraction(a, t, [0, 1 * cm, 5 * cm])
# a = gate.solid_union(a, b, [0, -1 * cm, -5 * cm])  # strange but ok
# b = gate.solid_intersection(t, s, [3 * cm, 0, 0])
# a = gate.solid_union(a, b, [0, -7 * cm, -5 * cm])

# then add them to a Union, with translation/rotation
# u = sim.add_volume_from_solid(a, "my_stuff")
sim.volume_manager.add_volume(u)
u.translation = [5 * cm, 5 * cm, 5 * cm]
u.rotation = Rotation.from_euler("x", 33, degrees=True).as_matrix()
u.mother = "world"
u.material = "G4_WATER"
u.color = [0, 1, 0, 1]

# create a volume from a solid (not really useful)
sim.volume_manager.add_volume(s)
s.translation = [-5 * cm, -5 * cm, 1 - 5 * cm]
s.mother = "world"
s.material = "G4_WATER"
s.color = [0, 1, 1, 1]

# default source for tests
source = sim.add_source("GenericSource", "Default")
MeV = gate.g4_units("MeV")
Bq = gate.g4_units("Bq")
source.particle = "proton"
source.energy.mono = 240 * MeV
source.position.radius = 1 * cm
source.direction.type = "momentum"
source.direction.momentum = [0, 0, 1]
source.activity = 5 * Bq

# add stat actor
sim.add_actor("SimulationStatisticsActor", "Stats")


# function to run after init
def after_init(se):
    print("Checking solid ...")
    ve = se.volume_engine
    v = ve.get_volume("my_stuff")
    v = v.g4_logical_volume
    is_ok = v.GetName() == "my_stuff"
    gate.print_test(is_ok, f"Get volume {v.GetName()}")
    solid = v.GetSolid()
    pMin = g4.G4ThreeVector()
    pMax = g4.G4ThreeVector()
    solid.BoundingLimits(pMin, pMax)
    is_ok = list(pMin) == list([-50, -90, -100]) and is_ok
    gate.print_test(is_ok, f"pMin {pMin}")
    is_ok = list(pMax) == list([50, 60, 100]) and is_ok
    gate.print_test(is_ok, f"pMax {pMax}")
    if not is_ok:
        gate.test_ok(is_ok)


# create G4 objects
print(sim)

# start simulation

sim.user_fct_after_init = after_init
sim.run()

# print results at the end
stats = sim.output.get_actor("Stats")
print(stats)

gate.test_ok(True)
