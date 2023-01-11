#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import opengate.contrib.phantom_nema_iec_body as gate_iec
import gatetools.phsp as phsp
import uproot
import numpy as np
import matplotlib.pyplot as plt
import os

paths = gate.get_default_test_paths(__file__, "")
paths.output_ref = paths.output_ref / "test040_ref"

# create the simulation
sim = gate.Simulation()

# units
m = gate.g4_units("m")
cm = gate.g4_units("cm")
cm3 = gate.g4_units("cm3")
keV = gate.g4_units("keV")
mm = gate.g4_units("mm")
Bq = gate.g4_units("Bq")
BqmL = Bq / cm3
sec = gate.g4_units("second")
deg = gate.g4_units("deg")
kBq = 1000 * Bq
MBq = 1000 * kBq

# main parameters
ui = sim.user_info
ui.check_volumes_overlap = True
ui.number_of_threads = 1
ui.random_seed = 123456
ac = 5e3 * BqmL / ui.number_of_threads
ui.visu = False
colli_flag = not ui.visu
if ui.visu:
    ac = 1 * BqmL
    ui.number_of_threads = 1

# world size
world = sim.world
world.size = [1.5 * m, 1.5 * m, 1.5 * m]
world.material = "G4_AIR"

# test phase space to check with reference
phsp_sphere_surface = sim.add_volume("Sphere", "phase_space_sphere")
phsp_sphere_surface.rmin = 215 * mm
phsp_sphere_surface.rmax = 216 * mm
phsp_sphere_surface.color = [1, 1, 1, 1]
phsp_sphere_surface.material = "G4_AIR"

# physic list
sim.set_cut("world", "all", 1 * mm)

# activity parameters
spheres_diam = [10, 13, 17, 22, 28, 37]
spheres_activity_concentration = [ac * 6, ac * 5, ac * 4, ac * 3, ac * 2, ac]

# initialisation for conditional
spheres_radius = [x / 2.0 for x in spheres_diam]
spheres_centers, spheres_volumes = gate_iec.get_default_sphere_centers_and_volumes()
spheres_activity_ratio = []
spheres_activity = []
for diam, ac, volume, center in zip(
    spheres_diam, spheres_activity_concentration, spheres_volumes, spheres_centers
):
    activity = ac * volume
    print(
        f"Sphere {diam}: {str(center):<30} {volume / cm3:7.3f} cm3 "
        f"{activity / Bq:7.0f} Bq  {ac / BqmL:7.1f} BqmL"
    )
    spheres_activity.append(activity)

total_activity = sum(spheres_activity)
print(f"Total activity {total_activity / Bq:.0f} Bq")
for activity in spheres_activity:
    spheres_activity_ratio.append(activity / total_activity)
print("Activity ratio ", spheres_activity_ratio, sum(spheres_activity_ratio))

# will store all conditional info (position, direction)
all_cond = None

# unique (reproducible) random generator
rs = gate.get_rnd_seed(123456)


def gen_cond(n):
    n_samples = gate_iec.get_n_samples_from_ratio(n, spheres_activity_ratio)
    # (it is very important to shuffle when several spheres to avoid time artifact)
    cond = gate_iec.generate_pos_spheres(
        spheres_centers, spheres_radius, n_samples, shuffle=True, rs=rs
    )

    # we keep all conditions for the test (not needed in normal simulation)
    global all_cond
    if all_cond is None:
        all_cond = cond
    else:
        all_cond = np.column_stack((all_cond, cond))

    return cond


# GAN source
gsource = sim.add_source("GAN", "gaga")
gsource.particle = "gamma"
# no phantom, we consider attached to the world at origin
gsource.activity = total_activity
gsource.pth_filename = paths.data / "pth120_test9221_GP_0GP_10.0_100000.pth"
gsource.position_keys = ["X1", "Y1", "Z1", "X2", "Y2", "Z2"]
gsource.direction_keys = ["dX1", "dY1", "dZ1", "dX2", "dY2", "dZ2"]
gsource.energy_key = ["E1", "E2"]
gsource.time_key = ["t1", "t2"]
# time is added to the simulation time
gsource.time_relative = True
gsource.weight_key = None
# particle are move backward with 10 cm
gsource.backward_distance = 10 * cm
# if the kinetic E is below this threshold, we set it to 0
gsource.energy_threshold = 0.1 * keV
gsource.skip_policy = "ZeroEnergy"
gsource.batch_size = 1e5
gsource.verbose_generator = True
# set the generator and the condition generator
gen = gate.GANSourceConditionalPairsGenerator(gsource, 210 * mm, gen_cond)
gsource.generator = gen

# add stat actor
stat = sim.add_actor("SimulationStatisticsActor", "Stats")
stat.output = paths.output / "test040_gan_stats.txt"

# phsp actor
phsp_actor = sim.add_actor("PhaseSpaceActor", "phsp")
phsp_actor.mother = phsp_sphere_surface.name
phsp_actor.attributes = [
    "KineticEnergy",
    "PrePosition",
    "PreDirection",
    "GlobalTime",
    "EventPosition",
    "EventDirection",
    "TimeFromBeginOfEvent",
    "EventKineticEnergy",
]
phsp_actor.output = paths.output / "test040_gan_phsp.root"
f = sim.add_filter("ParticleFilter", "f")
f.particle = "gamma"
phsp_actor.filters.append(f)
f = sim.add_filter("KineticEnergyFilter", "f")
f.energy_min = 100 * keV
phsp_actor.filters.append(f)

# ----------------------------------------------------------------------------------------------
# go (cannot be spawn in another process)
# ui.running_verbose_level = gate.EVENT
output = sim.start(False)

# ----------------------------------------------------------------------------------------------
# print stats
print()
gate.warning(f"Check stats")
if ui.number_of_threads == 1:
    s = output.get_source("gaga")
else:
    s = output.get_source_MT("gaga", 0)
print(f"Source, nb of skipped particles : {s.fTotalSkippedEvents}")
b = gate.get_source_skipped_events(output, gsource.name)
print(f"Source, nb of skipped particles (check) : {b}")

stats = output.get_actor("Stats")
print(stats)
stats_ref = gate.read_stat_file(paths.output / "test040_ref_stats.txt")
r = (
    stats_ref.counts.step_count - stats.counts.step_count
) / stats_ref.counts.step_count
print(f"!!! Steps cannot be compared => was {stats.counts.step_count}, {r:.2f}%")
stats.counts.step_count = stats_ref.counts.step_count
r = (
    stats_ref.counts.track_count - stats.counts.track_count
) / stats_ref.counts.track_count
print(f"!!! Tracks cannot be compared => was {stats.counts.track_count}, {r:.2f}%")
stats.counts.track_count = stats_ref.counts.track_count
is_ok = gate.assert_stats(stats, stats_ref, 0.10)

# save conditional for checking with reference cond
keys = ["EventPosition_X", "EventPosition_Y", "EventPosition_Z"]
phsp.save_npy(paths.output / "test040_gan_phsp_cond.npy", all_cond, keys)

# ----------------------------------------------------------------------------------------------
# compare conditional
# less particle in the ref because conditional data are stored
# when exit (not absorbed)
print()
gate.warning(f"Check conditions (position, direction)")
root_ref = (
    paths.output / "test040_ref_phsp.root"
)  # look root generated by previous 40_aref test
hits1 = uproot.open(root_ref)
branch = hits1.keys()[0]
print("Branch name:", branch)
hits1 = hits1[branch]
names = [k for k in hits1.keys()]
hits1_n = hits1.num_entries
hits1 = hits1.arrays(library="numpy")

# in the ref phsp, EventID is not unique (pairs of gamma), we set them unique
# to be compared to the generated cond
event_id = hits1["EventID"]
print("Nb of event (non unique)", event_id.shape)
u, indices = np.unique(event_id, return_index=True)
for k in hits1:
    hits1[k] = hits1[k][indices]
event_id = hits1["EventID"]
print("Nb of event (unique)", event_id.shape)

root_gan = paths.output / "test040_gan_phsp_cond.npy"
hits2, hits2_keys, hits2_n = phsp.load(root_gan)
tols = [10.0] * len(keys)
tols[keys.index("EventPosition_X")] = 0.15
tols[keys.index("EventPosition_Y")] = 0.15
tols[keys.index("EventPosition_Z")] = 0.15
scalings = [1] * len(keys)
is_ok = (
    gate.compare_trees(
        hits1,
        list(hits1.keys()),
        hits2,
        list(hits2_keys),
        keys,
        keys,
        tols,
        scalings,
        scalings,
        True,
    )
    and is_ok
)
# figure
img_filename = paths.output / "test040_cond.png"
plt.suptitle(
    f"Values: ref {os.path.basename(root_ref)} {os.path.basename(root_gan)} "
    f"-> {hits1_n} vs {hits2_n}"
)
plt.savefig(img_filename)
print(f"Figure in {img_filename}")

# ----------------------------------------------------------------------------------------------
# compare output phsp
# absorbed events are when E == 0
print()
gate.warning(
    f"Check output phsp (the pth is not perfect, but it should be sufficient for tests"
)
print("Warning: in the ref phsp, we remove when E==0 (absorbed events)")

ref_file = paths.output / "test040_ref_phsp.root"
hits1 = uproot.open(root_ref)
branch = hits1.keys()[0]
print("Branch name:", branch)
hits1 = hits1[branch]
names = [k for k in hits1.keys()]
hits1_n = hits1.num_entries
hits1 = hits1.arrays(library="numpy")

# in the ref, remove when E == 0
ke = hits1["KineticEnergy"]
print("Nb of event (all E)", ke.shape)
mask = ke > 0
for k in hits1:
    hits1[k] = hits1[k][mask]
ke = hits1["KineticEnergy"]
print("Nb of event (non E==0)", ke.shape)

hc_file = phsp_actor.output
hits2, hits2_keys, hits2_n = phsp.load(hc_file)

checked_keys = [
    "GlobalTime",
    "KineticEnergy",
    "PrePosition_X",
    "PrePosition_Y",
    "PrePosition_Z",
    "PreDirection_X",
    "PreDirection_Y",
    "PreDirection_Z",
]
scalings = [1.0] * len(checked_keys)
scalings[checked_keys.index("GlobalTime")] = 1e-9  # time in ns
tols = [10.0] * len(checked_keys)
tols[checked_keys.index("GlobalTime")] = 0.003
tols[checked_keys.index("KineticEnergy")] = 0.01
tols[checked_keys.index("PrePosition_X")] = 2
tols[checked_keys.index("PrePosition_Y")] = 1
tols[checked_keys.index("PrePosition_Z")] = 1
tols[checked_keys.index("PreDirection_X")] = 0.02
tols[checked_keys.index("PreDirection_Y")] = 0.02
tols[checked_keys.index("PreDirection_Z")] = 0.02
is_ok = (
    gate.compare_trees(
        hits1,
        list(hits1.keys()),
        hits2,
        list(hits2_keys),
        checked_keys,
        checked_keys,
        tols,
        scalings,
        scalings,
        True,
    )
    and is_ok
)
# figure
img_filename = paths.output / "test040_phsp.png"
plt.suptitle(
    f"Values: ref {os.path.basename(root_ref)} {os.path.basename(root_gan)} "
    f"-> {hits1_n} vs {hits2_n}"
)
plt.savefig(img_filename)
print(f"Figure in {img_filename}")

# is_ok = gate.compare_root3(ref_file, hc_file, "phsp", "phsp",
#                          checked_keys, checked_keys, tols, scalings, scalings,
#                          paths.output / 'test040_phsp.png') and is_ok

# ----------------------------------------------------------------------------------------------

# this is the end, my friend
gate.delete_run_manager_if_needed(sim)
gate.test_ok(is_ok)
