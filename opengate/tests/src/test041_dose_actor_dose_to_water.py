#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from scipy.spatial.transform import Rotation
import matplotlib.pyplot as plt

paths = gate.get_default_test_paths(__file__, "gate_test041_dose_actor_dose_to_water")

# create the simulation
sim = gate.Simulation()

# main options
ui = sim.user_info
ui.g4_verbose = False
ui.g4_verbose_level = 1
ui.visu = False
ui.random_seed = 123456
ui.number_of_threads = 4
# units
m = gate.g4_units("m")
cm = gate.g4_units("cm")
mm = gate.g4_units("mm")
km = gate.g4_units("km")
MeV = gate.g4_units("MeV")
Bq = gate.g4_units("Bq")
kBq = 1000 * Bq

# add a material database
# sim.add_material_database(paths.gate_data / "HFMaterials2014.db")

#  change world size
world = sim.world
world.size = [600 * cm, 500 * cm, 500 * cm]
# world.material = "Vacuum"

# waterbox
phantom = sim.add_volume("Box", "phantom")
phantom.size = [10 * cm, 10 * cm, 10 * cm]
phantom.translation = [-5 * cm, 0, 0]
phantom.material = "G4_WATER"
phantom.color = [0, 0, 1, 1]


test_material_name = "G4_Si"
phantom_off = sim.add_volume("Box", "phantom_off")
phantom_off.mother = phantom.name
phantom_off.size = [100 * mm, 20 * mm, 20 * mm]
phantom_off.translation = [0 * mm, 0 * mm, 0 * mm]
phantom_off.material = test_material_name
phantom_off.color = [0, 0, 1, 1]


# water slab
water_slab_insert = sim.add_volume("Box", "water_slab_insert")
water_slab_insert.mother = phantom_off.name
water_slab_insert.size = [2 * mm, 20 * mm, 20 * mm]
water_slab_insert.translation = [43 * mm, 0, 0]
water_slab_insert.material = "G4_WATER"
water_slab_insert.color = [0, 0, 1, 1]
# si entrance
entranceRegion = sim.add_volume("Box", "entranceRegion")
entranceRegion.mother = phantom_off.name
entranceRegion.size = [5 * mm, 20 * mm, 20 * mm]
entranceRegion.translation = [47.5 * mm, 0, 0]
entranceRegion.material = "G4_Si"
entranceRegion.color = [0, 0, 1, 1]


# physics
p = sim.get_physics_user_info()
p.physics_list_name = "QGSP_BIC_EMY"
sim.set_cut("world", "all", 1000 * km)
# FIXME need SetMaxStepSizeInRegion ActivateStepLimiter

# default source for tests
source = sim.add_source("GenericSource", "mysource")
source.energy.mono = 40 * MeV
source.particle = "proton"
source.position.type = "disc"  # pos = Beam, shape = circle + sigma
# rotate the disc, equiv to : rot1 0 1 0 and rot2 0 0 1
source.position.rotation = Rotation.from_euler("y", 90, degrees=True).as_matrix()
# source.position.radius = 8 * mm
source.position.sigma_x = 2 * mm
source.position.sigma_y = 2 * mm
source.position.translation = [0, 0, 0]
source.direction.type = "momentum"
source.direction.momentum = [-1, 0, 0]
source.activity = 1000 * Bq
dir(source)

"""
doseActorName_IDD = "IDD"
dose = sim.add_actor("DoseActor", doseActorName_IDD)
dose.output = paths.output / ("test041-" + doseActorName_IDD + ".mhd")
dose.mother = phantom_off.name
# dose.size = [1, 250, 250]
# dose.spacing = [100, 0.4, 0.4]
dose.size = [100, 1, 1]
dose.spacing = [1.0, 20.0, 20.0]
dose.hit_type = "random"
"""

doseActorName_IDD_d = "IDD_d"
doseFour = sim.add_actor("DoseActor", doseActorName_IDD_d)
doseFour.output = paths.output / ("test041-" + doseActorName_IDD_d + ".mhd")
doseFour.mother = phantom_off.name
# dose.size = [1, 250, 250]
# dose.spacing = [100, 0.4, 0.4]
dose_size = [1000, 1, 1]
dose_spacing = [0.1, 20.0, 20.0]
doseFour.size = dose_size
doseFour.spacing = dose_spacing
doseFour.hit_type = "random"
doseFour.dose = True


doseActorName_IDD_d2w = "IDD_d2w"
doseFive = sim.add_actor("DoseActor", doseActorName_IDD_d2w)
doseFive.output = paths.output / ("test041-" + doseActorName_IDD_d2w + ".mhd")
doseFive.mother = phantom_off.name
# dose.size = [1, 250, 250]
# dose.spacing = [100, 0.4, 0.4]
doseFive.size = [1000, 1, 1]
doseFive.spacing = [0.1, 20.0, 20.0]
doseFive.hit_type = "random"
doseFive.dose_to_water = True


doseActorName_water_slab_insert_d = "IDD_waterSlab_d"
doseFive = sim.add_actor("DoseActor", doseActorName_water_slab_insert_d)
doseFive.output = paths.output / (
    "test041-" + doseActorName_water_slab_insert_d + ".mhd"
)
doseFive.mother = water_slab_insert.name
# dose.size = [1, 250, 250]
# dose.spacing = [100, 0.4, 0.4]
doseFive.size = doseFour.size
doseFive.spacing = doseFour.spacing
doseFive.hit_type = "random"
doseFive.dose = True

doseActorName_water_slab_insert_d2w = "IDD_waterSlab_d2w"
doseFive = sim.add_actor("DoseActor", doseActorName_water_slab_insert_d2w)
doseFive.output = paths.output / (
    "test041-" + doseActorName_water_slab_insert_d2w + ".mhd"
)
doseFive.mother = water_slab_insert.name
# dose.size = [1, 250, 250]
# dose.spacing = [100, 0.4, 0.4]
doseFive.size = [1000, 1, 1]
doseFive.spacing = [0.1, 20.0, 20.0]
doseFive.hit_type = "random"
doseFive.dose_to_water = True


doseActorName_entranceRegiont_d = "IDD_entranceRegion_d"
doseFive = sim.add_actor("DoseActor", doseActorName_entranceRegiont_d)
doseFive.output = paths.output / ("test041-" + doseActorName_entranceRegiont_d + ".mhd")
doseFive.mother = entranceRegion.name
# dose.size = [1, 250, 250]
# dose.spacing = [100, 0.4, 0.4]
doseFive.size = [1000, 1, 1]
doseFive.spacing = [10.1, 20.0, 20.0]
doseFive.hit_type = "random"
doseFive.dose = True

doseActorName_entranceRegiont_d2w = "IDD_entranceRegion_d2w"
doseFive = sim.add_actor("DoseActor", doseActorName_entranceRegiont_d2w)
doseFive.output = paths.output / (
    "test041-" + doseActorName_entranceRegiont_d2w + ".mhd"
)
doseFive.mother = entranceRegion.name
# dose.size = [1, 250, 250]
# dose.spacing = [100, 0.4, 0.4]
doseFive.size = [1000, 1, 1]
doseFive.spacing = [0.1, 20.0, 20.0]
doseFive.hit_type = "random"
doseFive.dose_to_water = True


# add stat actor
s = sim.add_actor("SimulationStatisticsActor", "stats")
s.track_types_flag = True

# start simulation
sim.n = 10
output = sim.run()
# output = sim.run(start_new_process=True)

# print results at the end
stat = sim.output.get_actor("stats")
print(stat)

# dose = output.get_actor("doseInXZ")
# print(dose)
# plt.plot(dose)
# plt.show()

# ----------------------------------------------------------------------------------------------------------------
# tests
print()
# gate.warning("Tests stats file")
# stats_ref = gate.read_stat_file(paths.gate_output / "stats.txt")
# is_ok = gate.assert_stats(stat, stats_ref, 0.14)


doseFpath_IDD_d = str(
    sim.output.get_actor(doseActorName_IDD_d).user_info.output
).replace(".mhd", "_dose.mhd")
doseFpath_IDD_d2w = str(
    sim.output.get_actor(doseActorName_IDD_d2w).user_info.output
).replace(".mhd", "_doseToWater.mhd")
doseFpath_geoWater_d = str(
    sim.output.get_actor(doseActorName_water_slab_insert_d).user_info.output
).replace(".mhd", "_dose.mhd")
doseFpath_geoWater_d2w = str(
    sim.output.get_actor(doseActorName_water_slab_insert_d2w).user_info.output
).replace(".mhd", "_doseToWater.mhd")

doseFpath_geoSi_d = str(
    sim.output.get_actor(doseActorName_entranceRegiont_d).user_info.output
).replace(".mhd", "_dose.mhd")
doseFpath_geoSi_d2w = str(
    sim.output.get_actor(doseActorName_entranceRegiont_d2w).user_info.output
).replace(".mhd", "_doseToWater.mhd")
unused = gate.assert_images(
    doseFpath_IDD_d,
    doseFpath_IDD_d2w,
    stat,
    tolerance=100,
    ignore_value=0,
    axis="x",
)

mSPR_40MeV = 1.268771331
mSPR_80MeV = 1.253197674
gate.warning("Test ratio: dose / dose_to_water in geometry with material: G4_WATER")
is_ok = gate.assert_images_ratio(
    1.00, doseFpath_geoWater_d, doseFpath_geoWater_d2w, abs_tolerance=0.05
)

gate.warning("Test ratio: dose / dose_to_water in geometry with material: G4_Si")
is_ok = (
    gate.assert_images_ratio(
        mSPR_40MeV, doseFpath_geoSi_d, doseFpath_geoSi_d2w, abs_tolerance=0.05
    )
    and is_ok
)


gate.test_ok(is_ok)
