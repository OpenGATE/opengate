#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate

paths = gate.get_default_test_paths(__file__, "gate_test034_gan_phsp_linac")

# create the simulation
sim = gate.Simulation()

# main options
ui = sim.user_info
ui.g4_verbose = False
ui.visu = False
ui.check_volumes_overlap = False
ui.number_of_threads = 1
# ui.running_verbose_level = gate.EVENT

# units
m = gate.g4_units("m")
mm = gate.g4_units("mm")
cm = gate.g4_units("cm")
nm = gate.g4_units("nm")
Bq = gate.g4_units("Bq")
kBq = 1000 * Bq
MBq = 1000 * kBq
MeV = gate.g4_units("MeV")

#  adapt world size
world = sim.world
world.size = [2 * m, 2 * m, 2 * m]
world.material = "G4_AIR"

# FIXME to compare to current GATE benchmark gaga
# FIXME or the dqprm exercises write/read

# add a waterbox
waterbox = sim.add_volume("Box", "waterbox")
waterbox.size = [30 * cm, 30 * cm, 30 * cm]
waterbox.translation = [0 * cm, 0 * cm, 52.2 * cm]
waterbox.material = "G4_WATER"
waterbox.color = [0, 0, 1, 1]  # blue

# virtual plane for phase space
# It is not really used, only for visualisation purpose
# and as origin of the coordinate system of the GAN source
plane = sim.add_volume("Box", "phase_space_plane")
plane.mother = world.name
plane.material = "G4_AIR"
plane.size = [3 * cm, 4 * cm, 5 * cm]
# plane.rotation = Rotation.from_euler('x', 15, degrees=True).as_matrix()
plane.color = [1, 0, 0, 1]  # red

# GAN source
# in the GAN : position, direction, E, weights
gsource = sim.add_source("GAN", "gaga")
gsource.particle = "gamma"
gsource.mother = plane.name
# gsource.activity = 10 * MBq / ui.number_of_threads
gsource.n = 1e6 / ui.number_of_threads
gsource.pth_filename = (
    paths.data / "003_v3_40k.pth"
)  # FIXME also allow .pt (include the NN)
gsource.position_keys = ["X", "Y", 271.1 * mm]
gsource.direction_keys = ["dX", "dY", "dZ"]
gsource.energy_key = "Ekine"
gsource.weight_key = None
gsource.time_key = None
gsource.batch_size = 1e5
gsource.verbose_generator = True
# it is possible to define another generator
# gsource.generator = generator

# add stat actor
s = sim.add_actor("SimulationStatisticsActor", "Stats")
s.track_types_flag = True

# PhaseSpace Actor
dose = sim.add_actor("DoseActor", "dose")
dose.mother = waterbox.name
dose.spacing = [4 * mm, 4 * mm, 4 * mm]
dose.size = [75, 75, 75]
dose.output = paths.output / "test034_edep.mhd"
dose.uncertainty = True

"""
Dont know why similar to hit_type == post while in Gate
this is hit_type = random ?
"""
dose.hit_type = "post"

# phys
p = sim.get_physics_user_info()
p.physics_list_name = "G4EmStandardPhysics_option4"
sim.set_cut("world", "all", 1000 * m)
sim.set_cut("waterbox", "all", 1 * mm)

# start simulation
output = sim.start()

s = output.get_source("gaga")
print(f"Source, nb of E<=0: {s.fTotalSkippedEvents}")

# print results
gate.warning(f"Check stats")
stats = output.get_actor("Stats")
print(stats)
stats_ref = gate.read_stat_file(paths.gate / "stats.txt")
is_ok = gate.assert_stats(stats, stats_ref, 0.10)

gate.warning(f"Check dose")
h = output.get_actor("dose")
print(h)
is_ok = (
    gate.assert_images(
        paths.gate / "dose-Edep.mhd", dose.output, stats, tolerance=58, ignore_value=0
    )
    and is_ok
)

gate.test_ok(is_ok)
