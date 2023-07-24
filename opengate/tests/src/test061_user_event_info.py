#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import uproot
import matplotlib.pyplot as plt

paths = gate.get_default_test_paths(__file__, "", output_folder="test061")

# create the simulation
sim = gate.Simulation()

# options
ui = sim.user_info
ui.number_of_threads = 1  # FIXME check MT
ui.visu = False
ui.visu_type = "vrml"
ui.check_volumes_overlap = True

# units
m = gate.g4_units("m")
mm = gate.g4_units("mm")
keV = gate.g4_units("keV")
cm = gate.g4_units("cm")
cm3 = gate.g4_units("cm3")
Bq = gate.g4_units("Bq")
BqmL = Bq / cm3
nm = gate.g4_units("nm")
sec = gate.g4_units("second")

# waterworld
world = sim.world
world.size = [100 * m, 100 * m, 100 * m]
world.material = "G4_WATER"

# physics
p = sim.get_physics_user_info()
p.physics_list_name = "QGSP_BERT_EMZ"  # FIXME
p.enable_decay = True  # FIXME
sim.set_cut("world", "all", 1e6 * mm)

# radionuclide
z = 89
a = 225
activity_in_Bq = 100
activity = activity_in_Bq * Bq / sim.user_info.number_of_threads
s1 = sim.add_source("GenericSource", "source")
s1.particle = f"ion {z} {a}"
s1.position.type = "sphere"
s1.position.radius = 1 * nm
s1.position.translation = [0, 0, 0]
s1.direction.type = "iso"
s1.activity = activity

# add stat actor
s = sim.add_actor("SimulationStatisticsActor", "stats")
s.track_types_flag = True

# phsp actor
phsp = sim.add_actor("PhaseSpaceActor", "phsp")
phsp.attributes = [
    "KineticEnergy",
    "EventID",
    "TrackID",
    "ParentID",
    "GlobalTime",
    "ParticleName",
    "ParentParticleName",
    "TrackCreatorProcess",
    "ProcessDefinedStep",
]
phsp.debug = False
phsp.output = paths.output / "test061.root"

# run
sim.run()
output = sim.output

# end
stats = output.get_actor("stats")
print(stats)

# open root file
root_ref = phsp.output
root = uproot.open(root_ref)
tree = root[root.keys()[0]]

# Get the arrays from the tree
events = tree.arrays(
    [
        "GlobalTime",
        "KineticEnergy",
        "ParentParticleName",
        "ParticleName",
        "EventID",
        "TrackID",
        "ParentID",
    ]
)
global_time_array = events["GlobalTime"]
kinetic_energy_array = events["KineticEnergy"]
parent_particle_array = events["ParentParticleName"]
particle_array = events["ParticleName"]
event_id_array = events["EventID"]
track_id_array = events["TrackID"]
parent_id_array = events["ParentID"]
parent_particle_array_ref = ["unknown"] * len(kinetic_energy_array)

# we test if the stored ParentParticleName is exactly the same as the one we can retrieve from
# the TrackID and ParentID
is_ok = True


def set_parent_name(parent_by_track, starting_index):
    # print('set parent name', starting_index, len(parent_by_track))
    lindex = starting_index
    while lindex < starting_index + len(parent_by_track):
        pid = parent_id_array[lindex]
        if pid in parent_by_track:
            parent_particle_array_ref[lindex] = parent_by_track[pid]
        else:
            # the events are not store in the phsp because they do not do a single step,
            # for the test we force to Ac225
            parent_particle_array_ref[lindex] = "Ac225"
        if parent_particle_array_ref[lindex] != parent_particle_array[lindex]:
            is_ok = False
            gate.print_test(
                is_ok,
                f"Parent particle i={lindex} track={track_id_array[lindex]} name={particle_array[lindex]}  ptrack={pid} "
                f"       ref = {parent_particle_array_ref[lindex]} "
                f"vs = {parent_particle_array[lindex]}",
            )
        lindex += 1


index = 0
parent_by_track = {}
current_event_id = -1
starting_index = 0
while index < tree.num_entries:
    event_id = event_id_array[index]
    if current_event_id != event_id:
        set_parent_name(parent_by_track, starting_index)
        parent_by_track = {}
        starting_index = index
        current_event_id = event_id
    track_id = track_id_array[index]
    parent_by_track[track_id] = particle_array[index]
    index += 1

gate.test_ok(is_ok)
