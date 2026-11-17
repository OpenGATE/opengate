#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
InteractionCounterAttribute, LastProcessDefinedStepInVolumeAttribute and
LastInteractionPositionInVolumeAttribute: the value read by an actor for a step
includes this step (#1270).

A 140 keV gamma pencil beam crosses a water box. All the steps of the primary
gamma are stored by a phase space attached to the world (the actor reads the
attributes before the stepping action). The expected values are rebuilt from
the steps (ProcessDefinedStep = process that limited the step, PostPosition):
- counter: number of compt steps up to the current step (included);
- last process in the water: process of the last non-Transportation step in
  the water up to the current step (included), "Transportation" if none;
- last interaction position in the water: PostPosition of this step, NaN if none.
"""

import numpy as np
import uproot

import opengate as gate
from opengate.tests import utility

cm = gate.g4_units.cm
m = gate.g4_units.m
keV = gate.g4_units.keV


def create_simulation(paths):
    sim = gate.Simulation()
    sim.output_dir = paths.output
    sim.random_seed = 87654
    sim.world.size = [1 * m, 1 * m, 1 * m]
    sim.world.material = "G4_Galactic"

    water = sim.add_volume("Box", "water")
    water.size = [20 * cm, 20 * cm, 20 * cm]
    water.material = "G4_WATER"

    source = sim.add_source("GenericSource", "source")
    source.particle = "gamma"
    source.energy.mono = 140 * keV
    source.position.type = "point"
    source.position.translation = [0, 0, -30 * cm]
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    source.number_of_primaries = 5000

    att = sim.activate_auxiliary_attribute("InteractionCounterAttribute", "n_compt")
    att.process_name = "compt"
    att = sim.activate_auxiliary_attribute(
        "LastProcessDefinedStepInVolumeAttribute", "last_process"
    )
    att.volume_name = water.name
    att = sim.activate_auxiliary_attribute(
        "LastInteractionPositionInVolumeAttribute", "last_position"
    )
    att.volume_name = water.name

    steps = sim.add_actor("PhaseSpaceActor", "steps")
    steps.attached_to = "world"
    steps.steps_to_store = "all"
    steps.attributes = [
        "EventID",
        "TrackID",
        "ParentID",
        "CurrentStepNumber",
        "ProcessDefinedStep",
        "PrePosition",
        "PostPosition",
        "n_compt",
        "last_process",
        "last_position",
    ]
    steps.output_filename = "test023_interaction_attributes_same_step.root"
    return sim, steps


def expected_values(df):
    """Rebuild the expected values, step by step, for each track"""
    df = df.sort_values(["EventID", "TrackID", "CurrentStepNumber"])
    df = df.reset_index(drop=True)
    keys = [df.EventID, df.TrackID]
    process = df.ProcessDefinedStep
    n_compt = (process == "compt").astype(int).groupby(keys).cumsum()

    # interaction in the water: not Transportation, pre-step point in the water
    # (the step entering the water starts on its boundary; the world is
    # vacuum, so no interaction occurs in a step starting on the boundary
    # outside the water)
    pre = df[["PrePosition_X", "PrePosition_Y", "PrePosition_Z"]].to_numpy()
    in_water = np.all(np.abs(pre) <= 10 * cm + 1e-6, axis=1)
    interaction = in_water & (process != "Transportation")
    last_process = np.full(len(df), "Transportation", dtype=object)
    nan = np.nan
    last_position = np.full((len(df), 3), nan)
    post = df[["PostPosition_X", "PostPosition_Y", "PostPosition_Z"]].to_numpy()
    prev_key = None
    current_p = "Transportation"
    current_x = np.array([nan, nan, nan])
    for i, k in enumerate(zip(df.EventID, df.TrackID)):
        if k != prev_key:
            current_p = "Transportation"
            current_x = np.array([nan, nan, nan])
            prev_key = k
        if interaction[i]:
            current_p = process[i]
            current_x = post[i]
        last_process[i] = current_p
        last_position[i] = current_x
    return df, n_compt.to_numpy(), last_process, last_position


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "", "test023")
    is_ok = True

    sim, steps_actor = create_simulation(paths)
    sim.run(start_new_process=True)

    f = uproot.open(steps_actor.get_output_path())
    df = f[f.keys()[0]].arrays(library="pd")
    for k in ["ProcessDefinedStep", "last_process"]:
        df[k] = np.asarray(df[k].to_numpy()).astype(str)
    # the primary gamma only (no inheritance from a parent track)
    df = df[df.ParentID == 0]
    df, n_compt, last_process, last_position = expected_values(df)
    n = len(df)
    print(f"{n} steps of the primary gamma")

    nb = int((df.n_compt.to_numpy() == n_compt).sum())
    b = nb == n and n_compt.max() > 1
    utility.print_test(
        b, f"InteractionCounter (compt): {nb}/{n} as expected (max {n_compt.max()})"
    )
    is_ok = is_ok and b

    nb = int((df.last_process.to_numpy() == last_process).sum())
    nb_int = int((last_process != "Transportation").sum())
    b = nb == n and nb_int > 0
    utility.print_test(
        b, f"LastProcessDefinedStepInVolume: {nb}/{n} as expected ({nb_int} set)"
    )
    is_ok = is_ok and b

    pos = df[["last_position_X", "last_position_Y", "last_position_Z"]].to_numpy()
    both_nan = np.all(np.isnan(pos), axis=1) & np.all(np.isnan(last_position), axis=1)
    close = np.all(np.abs(pos - last_position) < 1e-6, axis=1)
    nb = int((both_nan | close).sum())
    b = nb == n and (~both_nan).sum() > 0
    utility.print_test(
        b,
        f"LastInteractionPositionInVolume: {nb}/{n} as expected "
        f"({int((~both_nan).sum())} set)",
    )
    is_ok = is_ok and b

    utility.test_ok(is_ok)
