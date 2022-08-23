#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import opengate.contrib.spect_ge_nm670 as gate_spect

paths = gate.get_default_test_paths(__file__, "")

# create the simulation
sim = gate.Simulation()

# main options
ui = sim.user_info
ui.g4_verbose = False
ui.check_volumes_overlap = False
ui.random_seed = 123456

# units
m = gate.g4_units("m")
cm = gate.g4_units("cm")
keV = gate.g4_units("keV")
mm = gate.g4_units("mm")
Bq = gate.g4_units("Bq")
sec = gate.g4_units("second")
deg = gate.g4_units("deg")
kBq = 1000 * Bq
MBq = 1000 * kBq

""" ================================================== """
# main parameters
ui.visu = False
ui.g4_verbose = False
ui.visu_verbose = False
ui.number_of_threads = 1
ac = 10 * MBq
ac = 1 * MBq
distance = 15 * cm
psd = 6.11 * cm
p = [0, 0, -(distance + psd)]
""" ================================================== """

# world size
world = sim.world
world.size = [1.5 * m, 1.5 * m, 1.5 * m]
world.material = "G4_AIR"

# spect head (debug mode = very small collimator)
spect1 = gate_spect.add_ge_nm67_spect_head(
    sim, "spect1", collimator_type="lehr", debug=ui.visu
)
spect1.translation, spect1.rotation = gate.get_transform_orbiting(p, "x", 180)

# spect head (debug mode = very small collimator)
spect2 = gate_spect.add_ge_nm67_spect_head(
    sim, "spect2", collimator_type="lehr", debug=ui.visu
)
spect2.translation, spect2.rotation = gate.get_transform_orbiting(p, "x", 0)

# physic list
sim.set_cut("world", "all", 10 * mm)
# sim.set_cut('spect1_crystal', 'all', 1 * mm)
# sim.set_cut('spect2_crystal', 'all', 1 * mm)

# source #1
sources = []
source = sim.add_source("Generic", "source1")
source.particle = "gamma"
source.energy.type = "mono"
source.energy.mono = 140.5 * keV
source.position.type = "sphere"
source.position.radius = 2 * mm
source.position.translation = [0, 0, 20 * mm]
source.direction.type = "iso"
source.direction.acceptance_angle.volumes = ["spect2", "spect1"]
source.direction.acceptance_angle.intersection_flag = True
source.direction.acceptance_angle.normal_flag = True
source.direction.acceptance_angle.normal_vector = [0, 0, -1]
source.direction.acceptance_angle.normal_tolerance = 10 * deg
source.activity = ac / ui.number_of_threads
sources.append(source)

# source #1
source2 = sim.add_source("Generic", "source2")
gate.copy_user_info(source, source2)
source2.position.radius = 1 * mm
source2.position.translation = [20 * mm, 0, -20 * mm]
sources.append(source2)

# add stat actor
stat = sim.add_actor("SimulationStatisticsActor", "Stats")
stat.output = paths.output / "test033_stats.txt"

# add default digitizer (it is easy to change parameters if needed)
gate_spect.add_simplified_digitizer_Tc99m(
    sim, "spect1_crystal", paths.output / "test033_proj_1.mhd"
)
gate_spect.add_simplified_digitizer_Tc99m(
    sim, "spect2_crystal", paths.output / "test033_proj_2.mhd"
)

# motion of the spect, create also the run time interval
heads = [spect1, spect2]

# create a list of run (total = 1 second)
n = 10
sim.run_timing_intervals = gate.range_timing(0, 1 * sec, n)

for head in heads:
    motion = sim.add_actor("MotionVolumeActor", f"Move_{head.name}")
    motion.mother = head.name
    motion.translations, motion.rotations = gate.volume_orbiting_transform(
        "x", 0, 180, n, head.translation, head.rotation
    )
    motion.priority = 5

# go
sim.initialize()
sim.start()

stats = sim.get_actor("Stats")
print(stats)

s = 0
for source in sources:
    s += gate.get_source_skipped_particles(sim, source.name)
print(f"Skipped particles {s}")

########################
gate.warning(f"Check skipped")
# ref_skipped = 19695798
ref_skipped = 1968330
tol = 0.01
d = abs(ref_skipped - s) / ref_skipped
is_ok = d < tol
gate.print_test(
    is_ok,
    f"Skipped particles ref={ref_skipped}, get {s} -> {d * 100}% vs tol={tol * 100}%",
)

########################
gate.warning(f"Check stats")
stats_ref = gate.read_stat_file(paths.output_ref / "test033_stats.txt")
is_ok = gate.assert_stats(stats, stats_ref, 0.01) and is_ok

# compare edep map
gate.warning(f"Check images")
is_ok = (
    gate.assert_images(
        paths.output_ref / "test033_proj_1.mhd",
        paths.output / "test033_proj_1.mhd",
        stats,
        tolerance=1,
        axis="x",
    )
    and is_ok
)
is_ok = (
    gate.assert_images(
        paths.output_ref / "test033_proj_2.mhd",
        paths.output / "test033_proj_2.mhd",
        stats,
        tolerance=1,
        axis="x",
    )
    and is_ok
)

gate.test_ok(is_ok)
