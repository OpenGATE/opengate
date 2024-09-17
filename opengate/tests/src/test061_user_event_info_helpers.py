#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import uproot
import opengate as gate
from opengate.tests import utility


def create_simulation(sim, paths, name):
    # units
    m = gate.g4_units.m
    mm = gate.g4_units.mm
    nm = gate.g4_units.nm

    sim.output_dir = paths.output

    # waterworld
    world = sim.world
    world.size = [100 * m, 100 * m, 100 * m]
    world.material = "G4_WATER"

    # physics
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option4"
    sim.physics_manager.enable_decay = True
    sim.physics_manager.set_production_cut("world", "all", 1e6 * mm)

    # radionuclide
    z = 89
    a = 225
    s1 = sim.add_source("GenericSource", "source")
    s1.particle = f"ion {z} {a}"
    s1.position.type = "sphere"
    s1.position.radius = 1 * nm
    s1.position.translation = [0, 0, 0]
    s1.direction.type = "iso"
    s1.n = 50

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
    phsp.output_filename = f"test061_{name}.root"
    phsp.steps_to_store = "first"


def analyse(simulation):
    # end
    stats = simulation.actor_manager.get_actor("stats")
    print(stats)

    # open root file
    phsp = simulation.actor_manager.get_actor("phsp")
    root = uproot.open(phsp.get_output_path())
    tree = root[root.keys()[0]]

    print(f"phsp.number_of_absorbed_events: {phsp.number_of_absorbed_events}")

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

    # we test if the stored ParentParticleName is the same as the one we can retrieve from
    # the TrackID and ParentID

    def set_parent_name(parent_by_track, starting_index):
        # print('set parent name', starting_index, len(parent_by_track))
        lindex = starting_index
        lis_ok = True
        while lindex < starting_index + len(parent_by_track):
            pid = parent_id_array[lindex]
            if pid in parent_by_track:
                parent_particle_array_ref[lindex] = parent_by_track[pid]
            else:
                # the events are not stored in the phsp because they do not do a single step,
                # for the test we force to Ac225 ? NO ! was ok in G4 11.1, but no more valid in G4 11.2
                # now we check if this is an ion with [] inside the name
                parent_particle_array_ref[lindex] = "Ac225"
            ok = (
                parent_particle_array_ref[lindex] == parent_particle_array[lindex]
                or "[" in parent_particle_array[lindex]
            )
            if not ok or lindex % 100 == 0:
                utility.print_test(
                    ok,
                    f"Parent particle i={lindex} track={track_id_array[lindex]} name={particle_array[lindex]}  ptrack={pid} "
                    f"       ref = {parent_particle_array_ref[lindex]} "
                    f"vs = {parent_particle_array[lindex]}",
                )
            if not ok:
                lis_ok = False
            lindex += 1
        return lis_ok

    index = 0
    parent_by_track = {}
    current_event_id = -1
    starting_index = 0
    is_ok = True
    while index < tree.num_entries:
        event_id = event_id_array[index]
        if current_event_id != event_id:
            is_ok = set_parent_name(parent_by_track, starting_index) and is_ok
            parent_by_track = {}
            starting_index = index
            current_event_id = event_id
        track_id = track_id_array[index]
        parent_by_track[track_id] = particle_array[index]
        index += 1

    print()
    utility.print_test(is_ok, f"Compared {len(kinetic_energy_array)} elements")
    return is_ok
