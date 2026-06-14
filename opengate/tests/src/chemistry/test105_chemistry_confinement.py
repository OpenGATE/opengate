#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility


def create_simulation(confine_to_half_box, time_step_model):
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

    chem_box = sim.add_volume("Box", "chem_box")
    chem_box.size = [20 * um, 20 * um, 20 * um]
    chem_box.material = "G4_WATER"
    chem_box.set_track_structure_em_physics("G4EmDNAPhysics_option2")

    half_box_a = sim.add_volume("Box", "half_box_a")
    half_box_a.mother = chem_box.name
    half_box_a.size = [10 * um, 20 * um, 20 * um]
    half_box_a.translation = [-5 * um, 0, 0]
    half_box_a.material = "G4_WATER"

    half_box_b = sim.add_volume("Box", "half_box_b")
    half_box_b.mother = chem_box.name
    half_box_b.size = [10 * um, 20 * um, 20 * um]
    half_box_b.translation = [5 * um, 0, 0]
    half_box_b.material = "G4_WATER"

    if confine_to_half_box:
        sim.chemistry_manager.confine_chemistry_to_volume = half_box_a

    source = sim.add_source("GenericSource", "source")
    source.particle = "e-"
    # Keep the electron range comparable to the half-box size so an isotropic
    # source samples both halves in the unconstrained case.
    source.energy.mono = 1 * keV
    # Avoid placing the source exactly on the interface between the two half
    # boxes, which can make SBS chemistry tracking pathologically slow.
    source.position.type = "box"
    source.position.size = [18 * um, 18 * um, 18 * um]
    source.position.translation = [0, 0, 0]
    source.direction.type = "iso"
    source.n = 100

    stats = sim.add_actor("SimulationStatisticsActor", "stats")

    chem_actor = sim.add_actor("ChemicalStageActor", "chem_actor")
    chem_actor.attached_to = chem_box
    chem_actor.number_of_time_bins = 25
    # This test targets the global confinement controller. Use the actor-side
    # total reaction callback instead of the built-in Geant4 reaction counter,
    # which can still hit TIME_DONT_MATCH issues in IRT mode across events.
    chem_actor.counters.reaction_counter.active = False
    chem_actor.counters.molecule_counter.active = False

    return sim, stats, chem_actor


def run_case(time_step_model):
    sim_open, stats_open, actor_open = create_simulation(
        confine_to_half_box=False,
        time_step_model=time_step_model,
    )
    sim_open.run(start_new_process=True)

    sim_confined, stats_confined, actor_confined = create_simulation(
        confine_to_half_box=True,
        time_step_model=time_step_model,
    )
    sim_confined.run(start_new_process=True)

    results_open = actor_open.results.get_data()
    results_confined = actor_confined.results.get_data()
    total_reactions_open = int(results_open.reaction_count)
    total_reactions_confined = int(results_confined.reaction_count)
    reaction_ratio = total_reactions_confined / total_reactions_open

    print(f"Reference run without chemistry confinement ({time_step_model})")
    print(f"  events: {stats_open.counts.events}")
    print(f"  chemistry_starts: {results_open.chemistry_starts}")
    print(f"  total reactions: {total_reactions_open}")

    print(f"Run with chemistry confined to half_box_a ({time_step_model})")
    print(f"  events: {stats_confined.counts.events}")
    print(f"  chemistry_starts: {results_confined.chemistry_starts}")
    print(f"  total reactions: {total_reactions_confined}")
    print(f"  confined/open reaction ratio: {reaction_ratio:.3f}")

    is_ok = True
    is_ok = is_ok and results_open.chemistry_starts > 0
    is_ok = is_ok and results_confined.chemistry_starts > 0
    is_ok = is_ok and total_reactions_open > 0
    is_ok = is_ok and total_reactions_confined > 0
    is_ok = is_ok and total_reactions_confined < total_reactions_open
    is_ok = is_ok and 0.35 <= reaction_ratio <= 0.65
    return is_ok


if __name__ == "__main__":
    is_ok_irt = run_case("IRT")
    is_ok_sbs = run_case("SBS")
    utility.test_ok(is_ok_irt and is_ok_sbs)
