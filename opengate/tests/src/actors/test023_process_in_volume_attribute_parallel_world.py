#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ProcessDefinedStepInVolumeAttribute with volumes in a parallel world.

A gamma pencil beam crosses a water box (mass world). A parallel world
contains a "table" slab located inside the water box, and a "plate" slab
(with a daughter "insert") located in the vacuum behind the water box.
Both have a material (layered mass geometry).

All the steps of the primary gamma are stored with a phase space attached to
the world. The expected value of every attribute, at every step, is the number
of interactions up to this step (included), with the volume given by the
position of the interaction:
- in the table or in the plate: counted there (parallel world)
- in the water outside the table: counted in the water
- the interactions in the table are NOT counted in the water, nor in the world
"""

import os
import numpy as np
import uproot

import opengate as gate
from opengate.tests import utility

cm = gate.g4_units.cm
m = gate.g4_units.m
keV = gate.g4_units.keV

processes = ("compt", "Rayl")


def create_simulation(paths, number_of_threads=1):
    sim = gate.Simulation()
    sim.output_dir = paths.output
    sim.random_seed = 987654
    sim.number_of_threads = number_of_threads
    sim.world.size = [1 * m, 1 * m, 1 * m]
    sim.world.material = "G4_Galactic"

    water = sim.add_volume("Box", "water")
    water.size = [20 * cm, 20 * cm, 20 * cm]
    water.material = "G4_WATER"

    sim.add_parallel_world("parallel_world")

    table = sim.add_volume("Box", "table")
    table.mother = "parallel_world"
    table.size = [30 * cm, 30 * cm, 2 * cm]
    table.material = "G4_Al"

    plate = sim.add_volume("Box", "plate")
    plate.mother = "parallel_world"
    plate.size = [30 * cm, 30 * cm, 2 * cm]
    plate.translation = [0, 0, 20 * cm]
    plate.material = "G4_WATER"

    insert = sim.add_volume("Box", "insert")
    insert.mother = plate.name
    insert.size = [30 * cm, 30 * cm, 1 * cm]
    insert.material = "G4_Al"

    source = sim.add_source("GenericSource", "source")
    source.particle = "gamma"
    source.energy.mono = 140 * keV
    source.position.type = "point"
    source.position.translation = [0, 0, -30 * cm]
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    source.number_of_primaries = 20000

    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option4"

    names = []
    volumes = ["world", "water", "table", "plate", "insert", ["table", "plate"]]
    for process in processes:
        for volume in volumes:
            v = volume if isinstance(volume, str) else "list"
            att = sim.activate_auxiliary_attribute(
                "ProcessDefinedStepInVolumeAttribute", f"n_{process}_{v}"
            )
            att.process_name = process
            att.volume_name = volume
            names.append(att.name)

    steps = sim.add_actor("PhaseSpaceActor", "steps")
    steps.attached_to = "world"
    steps.steps_to_store = "all"
    steps.attributes = [
        "EventID",
        "TrackID",
        "CurrentStepNumber",
        "ProcessDefinedStep",
        "PostPosition",
    ] + names
    steps.output_filename = f"test023_process_in_volume_pw_{number_of_threads}.root"

    return sim, steps, names


def check(steps_actor, names):
    f = uproot.open(steps_actor.get_output_path())
    steps = f[f.keys()[0]].arrays(library="pd")
    process = np.asarray(steps.ProcessDefinedStep.to_numpy()).astype(str)
    steps = steps.drop(columns="ProcessDefinedStep").assign(process=process)
    steps = steps[steps.TrackID == 1]
    steps = steps.sort_values(["EventID", "CurrentStepNumber"]).reset_index(drop=True)

    # volume of the interaction, from its position
    x, y, z = steps.PostPosition_X, steps.PostPosition_Y, steps.PostPosition_Z
    in_water_box = (x.abs() < 10 * cm) & (y.abs() < 10 * cm) & (z.abs() < 10 * cm)
    in_slab = (x.abs() < 15 * cm) & (y.abs() < 15 * cm)
    in_table = in_slab & (z.abs() < 1 * cm)
    in_plate = in_slab & (z > 19 * cm) & (z < 21 * cm)
    in_insert = in_slab & (z > 19.5 * cm) & (z < 20.5 * cm)
    in_water = in_water_box & ~in_table
    where = {
        "world": in_water,
        "water": in_water,
        "table": in_table,
        "plate": in_plate,
        "insert": in_insert,
        "list": in_table | in_plate,
    }

    is_ok = True
    print(f"{len(steps)} steps of the primary gamma")
    for p in processes:
        for v, selection in where.items():
            name = f"n_{p}_{v}"
            flag = ((steps.process == p) & selection).astype(int)
            expected = flag.groupby(steps.EventID).cumsum()
            nb_diff = int((steps[name] != expected).sum())
            nb = int(flag.sum())
            b = nb_diff == 0 and nb > 0
            utility.print_test(
                b,
                f"{name:16s} {nb:6d} interactions, {nb_diff} steps differ from "
                f"the expected value",
            )
            is_ok = is_ok and b
    return is_ok


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "", "test023")

    sim, steps_actor, names = create_simulation(paths)
    sim.run(start_new_process=True)
    is_ok = check(steps_actor, names)

    # one navigator per thread (no multithreading on Windows)
    if os.name != "nt":
        print()
        print("Multithread")
        sim, steps_actor, names = create_simulation(paths, number_of_threads=3)
        sim.run(start_new_process=True)
        is_ok = check(steps_actor, names) and is_ok

    utility.test_ok(is_ok)
