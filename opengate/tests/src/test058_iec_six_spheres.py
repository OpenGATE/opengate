#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import opengate.contrib.phantom_nema_iec_body as gate_iec
import uproot
import matplotlib.pyplot as plt

paths = gate.get_default_test_paths(__file__, "", output_folder="test058")

# create the simulation
sim = gate.Simulation()
simu_name = "main0_orientation"

# options
ui = sim.user_info
ui.number_of_threads = 1
ui.visu = False
ui.visu_type = "vrml"
ui.check_volumes_overlap = True

# units
m = gate.g4_units("m")
keV = gate.g4_units("keV")
cm = gate.g4_units("cm")
cm3 = gate.g4_units("cm3")
Bq = gate.g4_units("Bq")
BqmL = Bq / cm3

# world size
sim.world.size = [0.4 * m, 0.4 * m, 0.4 * m]

# add IEC phantom
iec1 = gate_iec.add_phantom(sim, name="iec", check_overlap=True)

# bg source
s = gate_iec.add_background_source(sim, "iec", "bg", 100 * BqmL, True)
s.particle = "gamma"
s.energy.type = "mono"
s.energy.mono = 10 * keV

# phys
sim.set_production_cut("world", "all", 100 * m)

# stats
sim.add_actor("SimulationStatisticsActor", "stats")

# phsp
phsp = sim.add_actor("PhaseSpaceActor", "phsp")
phsp.attributes = ["EventPosition"]
phsp.output = paths.output / "iec.root"

# run
sim.run()
output = sim.output

# end
stats = output.get_actor("stats")
print(stats)

# read root
root = uproot.open(phsp.output)
tree = root[root.keys()[0]]
posx = tree["EventPosition_X"].array()
posy = tree["EventPosition_Y"].array()
posz = tree["EventPosition_Z"].array()

nb = stats.counts.event_count
nb_root = len(posx)
is_ok = nb == nb_root
gate.print_test(is_ok, f"Number of events in stats {nb} and in root {nb_root}")

# consider only points around the sphere's centers
index = (posz > 3.5 * cm) & (posz < 3.9 * cm)
posx = posx[index]
posy = posy[index]

f, ax = plt.subplots(1, 1, figsize=(15, 5))
ax.scatter(posx, posy, s=1)
plt.gca().set_aspect("equal")

plt.tight_layout()
file = paths.output / "test058_bg.pdf"
plt.savefig(file, bbox_inches="tight", format="pdf")
print(f"Output plot is {file}")

# ref root
ref_root_file = paths.output_ref / "iec.root"
k = ["EventPosition_X", "EventPosition_Y", "EventPosition_Z"]
is_ok = is_ok and gate.compare_root3(
    ref_root_file,
    phsp.output,
    "phsp",
    "phsp",
    k,
    k,
    [0.4] * len(k),
    [1] * len(k),
    [1] * len(k),
    paths.output / "test058.png",
)

gate.test_ok(is_ok)
