#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import itk
from scipy.spatial.transform import Rotation

paths = gate.get_default_test_paths(__file__, "")

# create the simulation
sim = gate.Simulation()

# main options
ui = sim.user_info
ui.g4_verbose = False
ui.visu = False
ui.number_of_threads = 1
print(ui)

# add a material database
sim.add_material_database(paths.data / "GateMaterials.db")

# units
m = gate.g4_units("m")
mm = gate.g4_units("mm")
cm = gate.g4_units("cm")
keV = gate.g4_units("keV")
MeV = gate.g4_units("MeV")
Bq = gate.g4_units("Bq")
kBq = 1000 * Bq

#  change world size
world = sim.world
world.size = [1.5 * m, 1 * m, 1 * m]

# fake box #1
b = sim.add_volume("Box", "fake1")
b.size = [36 * cm, 36 * cm, 36 * cm]
b.translation = [25 * cm, 0, 0]
r = Rotation.from_euler("y", -25, degrees=True)
r = r * Rotation.from_euler("x", -35, degrees=True)
b.rotation = r.as_matrix()

# fake box #2
b = sim.add_volume("Box", "fake2")
b.mother = "fake1"
b.size = [35 * cm, 35 * cm, 35 * cm]

# CT image #1
ct_odd = sim.add_volume("Image", "ct_odd")
ct_odd.image = paths.data / "10x10x10.mhd"
ct_odd.mother = "fake2"
ct_odd.voxel_materials = [[0, 10, "G4_WATER"]]
ct_odd.translation = [-2 * cm, 0, 0]
r = Rotation.from_euler("y", 25, degrees=True)
r = r * Rotation.from_euler("x", 35, degrees=True)
ct_odd.rotation = r.as_matrix()

# CT image #2
ct_even = sim.add_volume("Image", "ct_even")
ct_even.image = paths.data / "11x11x11.mhd"
ct_even.voxel_materials = [[0, 10, "G4_WATER"]]
ct_even.voxel_materials = ct_odd.voxel_materials
ct_even.translation = [-25 * cm, 0, 0]

# source from image for CT #1
source1 = sim.add_source("Voxels", "vox1")
source1.mother = "ct_odd"
source1.particle = "alpha"
source1.activity = 10000 * Bq / ui.number_of_threads
source1.image = paths.data / "five_pixels.mha"
source1.direction.type = "iso"
source1.position.translation = gate.get_translation_between_images_center(
    str(ct_odd.image), str(source1.image)
)
source1.energy.mono = 1 * MeV

# source2 from image for CT #2
source2 = sim.add_source("Voxels", "vox2")
source2.mother = "ct_even"
source2.particle = "alpha"
source2.activity = 10000 * Bq / ui.number_of_threads
source2.image = paths.data / "five_pixels.mha"
source2.direction.type = "iso"
source2.position.translation = gate.get_translation_between_images_center(
    str(ct_even.image), str(source2.image)
)
source2.energy.mono = 1 * MeV

# cuts
p = sim.get_physics_user_info()
p.physics_list_name = "QGSP_BERT_EMZ"
p.enable_decay = False
sim.set_cut("world", "all", 1 * mm)

# add dose actor
dose1 = sim.add_actor("DoseActor", "dose1")
dose1.output = paths.output / "test021-odd-edep.mhd"
dose1.mother = "ct_odd"
img_info = gate.read_image_info(str(ct_odd.image))
dose1.size = img_info.size
dose1.spacing = img_info.spacing
dose1.translation = source1.position.translation
dose1.img_coord_system = True

# add dose actor
dose2 = sim.add_actor("DoseActor", "dose2")
dose2.output = paths.output / "test021-even-edep.mhd"
dose2.mother = "ct_even"
img_info = gate.read_image_info(str(ct_even.image))
dose2.size = img_info.size
dose2.spacing = img_info.spacing
dose2.translation = source2.position.translation
dose2.img_coord_system = True

# add stat actor
stats = sim.add_actor("SimulationStatisticsActor", "Stats")
stats.track_types_flag = True

# create G4 objects
sim.initialize()

# verbose
sim.apply_g4_command("/tracking/verbose 0")

# start simulation
sim.start()

# print results at the end
stat = sim.get_actor("Stats")
# stat.write(paths.output_ref / 'stat021_ref.txt')

# test pixels in dose #1
d_odd = itk.imread(str(dose1.output))
s = 1966
v = d_odd.GetPixel([4, 1, 5])
diff = (s - v) / s
tol = 0.2
is_ok = diff < tol
diff *= 100
gate.print_test(is_ok, f"Image #1 (odd): {v:.2f} {s:.2f} -> {diff:.2f}%")

# test pixels in dose #1
d_even = itk.imread(str(dose2.output))
s = itk.array_view_from_image(d_even).sum()
v0 = d_even.GetPixel([5, 5, 5])
v1 = d_even.GetPixel([1, 5, 5])
v2 = d_even.GetPixel([1, 2, 5])
v3 = d_even.GetPixel([5, 2, 5])
v4 = d_even.GetPixel([6, 2, 5])
tol = 0.15
ss = v0 + v1 + v2 + v3 + v4


def t(s, v):
    diff = abs(s - v) / s
    b = diff < tol
    p = diff * 100.0
    gate.print_test(b, f"Image #2 (even) {s:.2f} vs {v:.2f}  -> {p:.2f}%")
    return b


is_ok = t(s, ss) and is_ok
is_ok = t(2000, v0) and is_ok
is_ok = t(2000, v1) and is_ok
is_ok = t(2000, v2) and is_ok
is_ok = t(2000, v3) and is_ok
is_ok = t(2000, v4) and is_ok

stats_ref = gate.read_stat_file(paths.output_ref / "stat021_ref.txt")
stats_ref.counts.run_count = ui.number_of_threads
is_ok = gate.assert_stats(stat, stats_ref, 0.1) and is_ok

gate.test_ok(is_ok)
