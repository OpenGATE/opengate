#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ProcessDefinedStepInVolumeAttribute: value stored in the hits.

A gamma pencil beam crosses a water box, then a detector head (air) made of a
collimator plate and a crystal. The attributes count compt and Rayl in the
water, the head, the collimator, the crystal and in [collimator, crystal].

All the steps of all the tracks are stored with a phase space attached to the
world: the expected value of the attributes is rebuilt from them, for every
hit, as the number of interactions of the track up to the hit (included), plus
the ones of its ancestors up to the step that created each of them (included).

Checks:
- hits: attribute == expected value, for the gamma, the electrons, the X-rays
- volume: daughters are counted, a list of volumes is the sum of its volumes
- an unknown volume name is an error
"""

import numpy as np
import pandas as pd
import uproot

import opengate as gate
from opengate.tests import utility

cm = gate.g4_units.cm
mm = gate.g4_units.mm
um = gate.g4_units.um
m = gate.g4_units.m
keV = gate.g4_units.keV

# z extent of the volumes (the interactions are strictly inside)
z_ranges = {
    "water": (-10 * cm, 10 * cm),
    "head": (27 * cm, 33 * cm),
    "collimator": (27.5 * cm, 29.5 * cm),
    "crystal": (30.5 * cm, 31.5 * cm),
}
processes = ("compt", "Rayl")


def att_name(process, volume):
    return f"n_{process}_{volume}"


def create_simulation(paths, unknown_volume=False):
    sim = gate.Simulation()
    sim.output_dir = paths.output
    sim.random_seed = 123456
    sim.world.size = [1 * m, 1 * m, 1 * m]
    sim.world.material = "G4_Galactic"

    water = sim.add_volume("Box", "water")
    water.size = [20 * cm, 20 * cm, 20 * cm]
    water.material = "G4_WATER"

    head = sim.add_volume("Box", "head")
    head.size = [40 * cm, 40 * cm, 6 * cm]
    head.translation = [0, 0, 30 * cm]
    head.material = "G4_AIR"

    collimator = sim.add_volume("Box", "collimator")
    collimator.mother = head.name
    collimator.size = [40 * cm, 40 * cm, 2 * cm]
    collimator.translation = [0, 0, -1.5 * cm]
    collimator.material = "G4_Al"

    crystal = sim.add_volume("Box", "crystal")
    crystal.mother = head.name
    crystal.size = [40 * cm, 40 * cm, 1 * cm]
    crystal.translation = [0, 0, 1 * cm]
    crystal.material = "G4_CADMIUM_TELLURIDE"

    source = sim.add_source("GenericSource", "source")
    source.particle = "gamma"
    source.energy.mono = 140 * keV
    source.position.type = "point"
    source.position.translation = [0, 0, -30 * cm]
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    source.number_of_primaries = 30000

    # track the electrons and the X-rays in the crystal: several hits per single
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option4"
    sim.physics_manager.set_production_cut("crystal", "electron", 1 * um)
    sim.physics_manager.set_production_cut("crystal", "gamma", 1 * um)

    names = []
    volumes = list(z_ranges.keys()) + [["collimator", "crystal"]]
    if unknown_volume:
        volumes = ["this_volume_does_not_exist"]
    for process in processes:
        for volume in volumes:
            v = volume if isinstance(volume, str) else "list"
            att = sim.activate_auxiliary_attribute(
                "ProcessDefinedStepInVolumeAttribute", att_name(process, v)
            )
            att.process_name = process
            att.volume_name = volume
            att.propagate_from_parent_track = True
            names.append(att.name)

    steps = sim.add_actor("PhaseSpaceActor", "steps")
    steps.attached_to = "world"
    steps.steps_to_store = "all"
    steps.attributes = [
        "EventID",
        "TrackID",
        "ParentID",
        "CurrentStepNumber",
        "ProcessDefinedStep",
        "PostPosition",
        "TrackVertexPosition",
    ] + names
    steps.output_filename = "test023_process_in_volume_steps.root"

    hits = sim.add_actor("DigitizerHitsCollectionActor", "hits")
    hits.attached_to = crystal.name
    hits.attributes = [
        "EventID",
        "TrackID",
        "CurrentStepNumber",
        "TotalEnergyDeposit",
        "PostPosition",
        "PreStepUniqueVolumeID",
        "GlobalTime",
    ] + names
    hits.output_filename = "test023_process_in_volume_hits.root"

    return sim, steps, hits, names


def read_tree(actor):
    f = uproot.open(actor.get_output_path())
    df = f[f.keys()[0]].arrays(library="pd")
    for k in df.columns:
        if df[k].dtype == object or str(df[k].dtype).startswith("awkward"):
            df[k] = np.asarray(df[k].to_numpy()).astype(str)
    return df


def add_expected_values(steps):
    """
    For every step, expected attribute value = interactions of the track up to
    this step (included) + the ones of the ancestors up to the creating step
    (included).
    """
    steps = steps.sort_values(["EventID", "TrackID", "CurrentStepNumber"])
    steps = steps.reset_index(drop=True)
    keys = [steps.EventID, steps.TrackID]
    flag_names = []
    for process in processes:
        for volume, (z0, z1) in z_ranges.items():
            z = steps.PostPosition_Z
            flag = (steps.ProcessDefinedStep == process) & (z > z0) & (z < z1)
            n = f"own_{process}_{volume}"
            steps[n] = flag.astype(int).groupby(keys).cumsum()
            flag_names.append(n)

    # the step that created a secondary is the step of its parent that ends at
    # the vertex of the secondary
    pos = ["PostPosition_X", "PostPosition_Y", "PostPosition_Z"]
    vertex = [f"TrackVertexPosition_{a}" for a in "XYZ"]
    first = steps[steps.ParentID > 0].groupby(["EventID", "TrackID"]).head(1)
    first = first[["EventID", "TrackID", "ParentID"] + vertex]
    parents = steps[["EventID", "TrackID"] + pos + flag_names].drop_duplicates(
        ["EventID", "TrackID"] + pos, keep="last"
    )
    created = first.merge(
        parents,
        left_on=["EventID", "ParentID"] + vertex,
        right_on=["EventID", "TrackID"] + pos,
        how="left",
        suffixes=("", "_parent"),
    )
    nb_not_found = int(created[flag_names[0]].isna().sum())

    # inherited values, generation after generation (ParentID < TrackID)
    inherited = {}
    values = created[flag_names].to_numpy()
    created = created.assign(order=np.arange(len(created)))
    created = created.sort_values(["EventID", "TrackID"])
    for event_id, track_id, parent_id, i in zip(
        created.EventID, created.TrackID, created.ParentID, created.order
    ):
        v = values[i]
        p = inherited.get((event_id, parent_id))
        inherited[(event_id, track_id)] = v if p is None else v + p
    zero = np.zeros(len(flag_names))
    inh = np.array([inherited.get(k, zero) for k in zip(steps.EventID, steps.TrackID)])
    for j, n in enumerate(flag_names):
        steps["expected_" + n[4:]] = (steps[n].to_numpy() + inh[:, j]).astype(int)
    return steps, nb_not_found


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "", "test023")
    is_ok = True

    # an unknown volume name must be detected
    sim, _, _, _ = create_simulation(paths, unknown_volume=True)
    try:
        sim.run(start_new_process=True)
        b = False
    except Exception as e:
        b = True
    utility.print_test(b, "Unknown volume name is an error")
    is_ok = is_ok and b

    sim, steps_actor, hits_actor, names = create_simulation(paths)
    sim.run(start_new_process=True)

    steps, nb_not_found = add_expected_values(read_tree(steps_actor))
    hits = read_tree(hits_actor)
    print(f"{len(steps)} steps, {len(hits)} hits")
    b = nb_not_found == 0
    utility.print_test(b, f"Creating step found for all secondaries ({nb_not_found})")
    is_ok = is_ok and b

    expected_names = [n for n in steps.columns if n.startswith("expected_")]
    hits = hits.merge(
        steps[["EventID", "TrackID", "CurrentStepNumber"] + expected_names],
        on=["EventID", "TrackID", "CurrentStepNumber"],
        how="left",
    )
    b = not hits[expected_names[0]].isna().any()
    utility.print_test(b, "All hits are found in the steps")
    is_ok = is_ok and b

    # 1) hits
    for process in processes:
        for volume in z_ranges:
            a = att_name(process, volume)
            nb_diff = int((hits[a] != hits[f"expected_{process}_{volume}"]).sum())
            nb_non_zero = int((hits[a] > 0).sum())
            b = nb_diff == 0 and nb_non_zero > 0
            utility.print_test(
                b,
                f"Hits: {a:20s} {nb_non_zero:6d} non-zero values, max {hits[a].max()}, "
                f"{nb_diff} differ from the expected value",
            )
            is_ok = is_ok and b

    # 2) volumes
    for process in processes:
        a = hits[att_name(process, "list")]
        b = (
            a
            == hits[att_name(process, "collimator")]
            + hits[att_name(process, "crystal")]
        ).all() and a.sum() > 0
        utility.print_test(b, f"Hits: {process} in [collimator, crystal] is the sum")
        is_ok = is_ok and b
        b = (hits[att_name(process, "head")] >= a).all()
        utility.print_test(b, f"Hits: {process} in head >= in its daughters")
        is_ok = is_ok and b

    utility.test_ok(is_ok)
