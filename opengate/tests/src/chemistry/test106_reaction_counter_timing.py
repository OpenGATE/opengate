#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility


def create_simulation(number_of_events, time_step_model, confine_to_half_box):
    sim = gate.Simulation()

    sim.g4_verbose = False
    sim.visu = False
    sim.random_engine = "MersenneTwister"
    sim.random_seed = 123456
    sim.number_of_threads = 1

    km = gate.g4_units.km
    um = gate.g4_units.um
    keV = gate.g4_units.keV

    sim.world.size = [1 * km, 1 * km, 1 * km]
    sim.world.material = "G4_WATER"

    sim.physics_manager.physics_list_name = "G4EmStandardPhysics"
    sim.chemistry_manager.chemistry_list_name = "G4EmDNAChemistry_option3"
    sim.chemistry_manager.time_step_model = time_step_model

    target = sim.add_volume("Box", "chem_box")
    target.size = [20 * um, 20 * um, 20 * um]
    target.material = "G4_WATER"
    target.set_track_structure_em_physics("G4EmDNAPhysics_option2")

    half_box_a = sim.add_volume("Box", "half_box_a")
    half_box_a.mother = target.name
    half_box_a.size = [10 * um, 20 * um, 20 * um]
    half_box_a.translation = [-5 * um, 0, 0]
    half_box_a.material = "G4_WATER"

    half_box_b = sim.add_volume("Box", "half_box_b")
    half_box_b.mother = target.name
    half_box_b.size = [10 * um, 20 * um, 20 * um]
    half_box_b.translation = [5 * um, 0, 0]
    half_box_b.material = "G4_WATER"

    if confine_to_half_box:
        sim.chemistry_manager.confine_chemistry_to_volume = half_box_a

    source = sim.add_source("GenericSource", "source")
    source.particle = "e-"
    source.energy.mono = 1 * keV
    source.position.type = "box"
    source.position.size = [18 * um, 18 * um, 18 * um]
    source.position.translation = [0, 0, 0]
    source.direction.type = "iso"
    source.n = number_of_events

    stats = sim.add_actor("SimulationStatisticsActor", "stats")

    chem_actor = sim.add_actor("ChemicalStageActor", "chem_actor")
    chem_actor.attached_to = target
    chem_actor.number_of_time_bins = 10
    chem_actor.counters.molecule_counter.active = False
    chem_actor.counters.reaction_counter.active = True

    return sim, stats, chem_actor


def run_case(number_of_events, time_step_model, confine_to_half_box):
    confinement_label = "half-box confinement" if confine_to_half_box else "no confinement"
    print(
        f"Run case: model={time_step_model}, source.n={number_of_events}, "
        f"{confinement_label}"
    )
    sim, stats, chem_actor = create_simulation(
        number_of_events,
        time_step_model,
        confine_to_half_box,
    )
    try:
        sim.run(start_new_process=True)
    except Exception as exc:
        print("  status: exception")
        print(f"  type: {type(exc).__name__}")
        print(f"  message: {exc}")
        return {
            "ok": False,
            "exception": str(exc),
        }

    results = chem_actor.results.get_data()
    reaction_data = chem_actor.reaction_counter.get_data()
    print("  status: ok")
    print(f"  events: {stats.counts.events}")
    print(f"  chemistry_starts: {results.chemistry_starts}")
    print(f"  total_reactions_callback: {results.reaction_count}")
    print(f"  recorded_reaction_series: {len(reaction_data)}")
    return {
        "ok": True,
        "exception": None,
    }


if __name__ == "__main__":
    is_ok = True

    # Single-event chemistry should work as a baseline.
    result_single_irt = run_case(1, "IRT", False)
    result_single_sbs = run_case(1, "SBS", False)
    is_ok = is_ok and result_single_irt["ok"]
    is_ok = is_ok and result_single_sbs["ok"]

    # Multi-event chemistry is the configuration that previously exposed the
    # TIME_DONT_MATCH issue in the built-in Geant4 reaction counter.
    result_multi_irt = run_case(2, "IRT", False)
    result_multi_sbs = run_case(2, "SBS", False)

    # Probe the same counter path with chemistry confinement enabled, so we can
    # tell whether killing chemistry tracks during the stage destabilizes the
    # Geant4 built-in reaction counter bookkeeping.
    result_confined_single_irt = run_case(1, "IRT", True)
    result_confined_single_sbs = run_case(1, "SBS", True)
    result_confined_multi_irt = run_case(2, "IRT", True)
    result_confined_multi_sbs = run_case(2, "SBS", True)

    print("Summary")
    print(f"  IRT single-event ok: {result_single_irt['ok']}")
    print(f"  SBS single-event ok: {result_single_sbs['ok']}")
    print(f"  IRT multi-event ok: {result_multi_irt['ok']}")
    print(f"  SBS multi-event ok: {result_multi_sbs['ok']}")
    print(f"  IRT confined single-event ok: {result_confined_single_irt['ok']}")
    print(f"  SBS confined single-event ok: {result_confined_single_sbs['ok']}")
    print(f"  IRT confined multi-event ok: {result_confined_multi_irt['ok']}")
    print(f"  SBS confined multi-event ok: {result_confined_multi_sbs['ok']}")

    # This file is meant as an active regression/debug probe. It only passes
    # when all baseline and confined cases succeed.
    is_ok = is_ok and result_multi_irt["ok"] and result_multi_sbs["ok"]
    is_ok = is_ok and result_confined_single_irt["ok"]
    is_ok = is_ok and result_confined_single_sbs["ok"]
    is_ok = is_ok and result_confined_multi_irt["ok"]
    is_ok = is_ok and result_confined_multi_sbs["ok"]
    utility.test_ok(is_ok)
