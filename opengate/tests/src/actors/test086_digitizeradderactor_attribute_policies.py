#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DigitizerAdderActor: option attribute_policies.

A gamma pencil beam crosses a water box, a collimator plate and a crystal.
The electrons and the X-rays are tracked in the crystal, so a single is made
of several hits. Some attributes of the hits (number of compt and Rayl in the
crystal and in the collimator, track ID, kinetic energy) differ among the hits
of a single.

For every policy (max, min, first, last, energy_winner), the attributes of the
singles are compared with the ones of the hit selected by the policy, computed
here from the hits.
"""

import numpy as np
import uproot

import opengate as gate
from opengate.tests import utility

policies = ("max", "min", "first", "last", "energy_winner")


def create_simulation(paths):
    cm = gate.g4_units.cm
    um = gate.g4_units.um
    m = gate.g4_units.m
    keV = gate.g4_units.keV

    sim = gate.Simulation()
    sim.output_dir = paths.output
    sim.random_seed = 123456
    sim.world.size = [1 * m, 1 * m, 1 * m]
    sim.world.material = "G4_Galactic"

    water = sim.add_volume("Box", "water")
    water.size = [20 * cm, 20 * cm, 20 * cm]
    water.material = "G4_WATER"

    collimator = sim.add_volume("Box", "collimator")
    collimator.size = [40 * cm, 40 * cm, 2 * cm]
    collimator.translation = [0, 0, 28.5 * cm]
    collimator.material = "G4_Al"

    crystal = sim.add_volume("Box", "crystal")
    crystal.size = [40 * cm, 40 * cm, 1 * cm]
    crystal.translation = [0, 0, 31 * cm]
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
    for process in ("compt", "Rayl"):
        for volume in (collimator, crystal):
            att = sim.activate_auxiliary_attribute(
                "ProcessDefinedStepInVolumeAttribute", f"n_{process}_{volume.name}"
            )
            att.process_name = process
            att.volume_name = volume.name
            att.propagate_from_parent_track = True
            names.append(att.name)
    # an int and a double attribute not related to the auxiliary attributes
    names += ["TrackID", "PreKineticEnergy"]

    hits = sim.add_actor("DigitizerHitsCollectionActor", "hits")
    hits.attached_to = crystal.name
    hits.attributes = [
        "EventID",
        "TotalEnergyDeposit",
        "PostPosition",
        "PreStepUniqueVolumeID",
        "GlobalTime",
    ] + names
    hits.output_filename = "test086_attribute_policies_hits.root"

    singles = {}
    for policy in policies:
        s = sim.add_actor("DigitizerAdderActor", f"singles_{policy}")
        s.attached_to = crystal.name
        s.input_digi_collection = hits.name
        s.policy = "EnergyWeightedCentroidPosition"
        s.attribute_policies = {name: policy for name in names}
        s.output_filename = f"test086_attribute_policies_singles_{policy}.root"
        singles[policy] = s

    # no policy: value of the last stored hit (EnergyWeightedCentroidPosition)
    s = sim.add_actor("DigitizerAdderActor", "singles_default")
    s.attached_to = crystal.name
    s.input_digi_collection = hits.name
    s.policy = "EnergyWeightedCentroidPosition"
    s.output_filename = "test086_attribute_policies_singles_default.root"
    singles["default"] = s

    return sim, hits, singles, names


def read_tree(actor):
    f = uproot.open(actor.get_output_path())
    return f[f.keys()[0]].arrays(library="pd")


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "", "test086")
    is_ok = True

    # an unknown policy must be detected
    sim, _, singles_actors, names = create_simulation(paths)
    singles_actors["max"].attribute_policies = {names[0]: "this_is_not_a_policy"}
    try:
        sim.run(start_new_process=True)
        b = False
    except Exception as e:
        b = True
    utility.print_test(b, "Unknown policy is an error")
    is_ok = is_ok and b

    sim, hits_actor, singles_actors, names = create_simulation(paths)
    sim.run(start_new_process=True)

    # one single per event here (one crystal, no weight)
    hits = read_tree(hits_actor)
    g = hits.groupby("EventID")
    expected = {
        "max": g[names].max(),
        "min": g[names].min(),
        "first": hits.loc[g.GlobalTime.idxmin()].set_index("EventID")[names],
        "last": hits.loc[g.GlobalTime.idxmax()].set_index("EventID")[names],
        "energy_winner": hits.loc[g.TotalEnergyDeposit.idxmax()].set_index("EventID")[
            names
        ],
        "default": g[names].last(),
    }
    print(f"{len(hits)} hits, {g.ngroups} events with hits")

    # the test is meaningful only if the hits of a single have different values
    for name in names:
        nb_mixed = int((expected["max"][name] != expected["min"][name]).sum())
        print(f"{name:20s} singles whose hits have different values: {nb_mixed}")
        # (the numbers for the auxiliary attributes depend on their semantics)
        if name in ("n_compt_crystal", "n_Rayl_crystal", "TrackID"):
            b = nb_mixed > (50 if name == "TrackID" else 10)
            utility.print_test(b, f"{name}: enough singles with different values")
            is_ok = is_ok and b

    for policy in expected:
        singles = read_tree(singles_actors[policy]).set_index("EventID")
        e = expected[policy].reindex(singles.index)
        nb_diff = int((singles[names] != e).any(axis=1).sum())
        b = nb_diff == 0 and len(singles) == g.ngroups
        utility.print_test(
            b,
            f"Policy {policy:14s} {len(singles)} singles, {nb_diff} differ from "
            f"the expected hit",
        )
        is_ok = is_ok and b

        # energy, position and time do not depend on the attribute policies
        ref = read_tree(singles_actors["default"]).set_index("EventID")
        keys = ["TotalEnergyDeposit", "PostPosition_X", "PostPosition_Z", "GlobalTime"]
        b = bool((singles[keys] == ref[keys].reindex(singles.index)).all().all())
        utility.print_test(b, f"Policy {policy:14s} same energy, position and time")
        is_ok = is_ok and b

    utility.test_ok(is_ok)
