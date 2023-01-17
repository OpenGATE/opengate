#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from scipy.spatial.transform import Rotation
import matplotlib.pyplot as plt

paths = gate.get_default_test_paths(__file__, "test050_let_actor_letd")

# create the simulation
sim = gate.Simulation()

# main options
ui = sim.user_info
ui.g4_verbose = False
ui.g4_verbose_level = 1
ui.visu = False
ui.random_seed = 123456

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
entranceRegion.material = "G4_WATER"
entranceRegion.color = [0, 0, 1, 1]


# physics
p = sim.get_physics_user_info()
p.physics_list_name = "QGSP_BIC_EMY"
sim.set_cut("world", "all", 1000 * km)
# FIXME need SetMaxStepSizeInRegion ActivateStepLimiter

# default source for tests
source = sim.add_source("Generic", "mysource")
source.energy.mono = 80 * MeV
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
source.activity = 100 * kBq


# filter : keep proton
f = sim.add_filter("ParticleFilter", "f")
f.particle = "proton"

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
doseFour.size = [100, 1, 1]
doseFour.spacing = [1.0, 20.0, 20.0]
doseFour.hit_type = "random"
doseFour.gray = True


LETActorName_IDD_d = "LETActorOG_d"
LETActor_IDD_d = sim.add_actor("LETActor", LETActorName_IDD_d)
LETActor_IDD_d.output = paths.output / ("test050-" + LETActorName_IDD_d + ".mhd")
LETActor_IDD_d.mother = phantom_off.name
# dose.size = [1, 250, 250]
# dose.spacing = [100, 0.4, 0.4]
LETActor_IDD_d.size = [100, 1, 1]
LETActor_IDD_d.spacing = [1.0, 20.0, 20.0]
LETActor_IDD_d.hit_type = "random"
LETActor_IDD_d.separate_output = True
setattr(LETActor_IDD_d, "dose_average", True)
# LETActor_IDD_d.track_average = True


LETActorName_IDD_t = "LETActorOG_t"
LETActor_IDD_t = sim.add_actor("LETActor", LETActorName_IDD_t)
LETActor_IDD_t.output = paths.output / ("test050-" + LETActorName_IDD_t + ".mhd")
LETActor_IDD_t.mother = phantom_off.name
# dose.size = [1, 250, 250]
# dose.spacing = [100, 0.4, 0.4]
LETActor_IDD_t.size = [100, 1, 1]
LETActor_IDD_t.spacing = [1.0, 20.0, 20.0]
LETActor_IDD_t.hit_type = "random"
LETActor_IDD_t.track_average = True


LETActorName_IDD_d2w = "LETActorOG_d2w"
LETActor_IDD_d2w = sim.add_actor("LETActor", LETActorName_IDD_d2w)
LETActor_IDD_d2w.output = paths.output / ("test050-" + LETActorName_IDD_d2w + ".mhd")
LETActor_IDD_d2w.mother = phantom_off.name
# dose.size = [1, 250, 250]
# dose.spacing = [100, 0.4, 0.4]
LETActor_IDD_d2w.size = [100, 1, 1]
LETActor_IDD_d2w.spacing = [1.0, 20.0, 20.0]
LETActor_IDD_d2w.hit_type = "random"
LETActor_IDD_d2w.other_material = "G4_WATER"
setattr(LETActor_IDD_d2w, "dose_average", True)

# self.dose_average = None
#        self.track_average = None
#        self.let_to_other_material  = None
#        self.other_material = None
#        self.let_to_water = None


# add stat actor
s = sim.add_actor("SimulationStatisticsActor", "stats")
s.track_types_flag = True
s.filters.append(f)

print("Filters: ", sim.filter_manager)
print(sim.filter_manager.dump())

# start simulation
sim.n = 10
output = sim.start()

# print results at the end
stat = output.get_actor("stats")
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

LETActorFPath_IDD_numerator = str(output.get_actor(LETActorName_IDD_d).user_info.output)

LETActorFPath_IDD_denominator = LETActorFPath_IDD_numerator.replace(
    "_numerator.mhd", "_denominator.mhd"
)

LETActorFPath_IDD_LETd = LETActorFPath_IDD_numerator.replace("_numerator.mhd", ".mhd")


is_ok = gate.assert_images(
    LETActorFPath_IDD_LETd,
    LETActorFPath_IDD_LETd,
    stat,
    tolerance=100,
    ignore_value=0,
    axis="x",
)


"""
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
"""

gate.test_ok(is_ok)
