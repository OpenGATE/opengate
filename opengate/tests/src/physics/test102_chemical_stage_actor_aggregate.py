#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path

import matplotlib.pyplot as plt

import opengate as gate
from box import Box
from opengate.tests import utility


def print_results(label, results):
    print(label)
    print(f"  recorded_events: {results.recorded_events}")
    print(f"  chemistry_starts: {results.chemistry_starts}")
    print(f"  chemistry_stages: {results.chemistry_stages}")
    print(f"  pre_time_step_calls: {results.pre_time_step_calls}")
    print(f"  post_time_step_calls: {results.post_time_step_calls}")
    print(f"  reaction_count: {results.reaction_count}")
    print(f"  killed_particles: {results.killed_particles}")
    print(f"  aborted_events: {results.aborted_events}")
    print(
        f"  accumulated_primary_energy_loss: {results.accumulated_primary_energy_loss}"
    )
    print(f"  total_energy_deposit: {results.total_energy_deposit}")
    print(f"  mean_restricted_let: {results.mean_restricted_let}")
    print(f"  std_restricted_let: {results.std_restricted_let}")
    print(f"  chemistry_times: {len(results.times_to_record)}")
    print(f"  species_times: {len(results.species)}")


def create_simulation(use_actor_requested_dna_em, seed):
    sim = gate.Simulation()

    sim.g4_verbose = False
    sim.visu = False
    sim.random_engine = "MersenneTwister"
    sim.random_seed = seed
    sim.number_of_threads = 1

    km = gate.g4_units.km
    um = gate.g4_units.um
    keV = gate.g4_units.keV

    sim.world.size = [1 * km, 1 * km, 1 * km]
    sim.world.material = "G4_WATER"

    sim.physics_manager.physics_list_name = "G4EmStandardPhysics"
    sim.chemistry_manager.chemistry_list_name = "G4EmDNAChemistry_option3"
    sim.chemistry_manager.time_step_model = "IRT"

    target = sim.add_volume("Box", "chem_box")
    target.size = [10 * um, 10 * um, 10 * um]
    target.material = "G4_WATER"

    if not use_actor_requested_dna_em:
        target.set_track_structure_em_physics("DNA_Opt2")

    source = sim.add_source("GenericSource", "source")
    source.particle = "e-"
    source.energy.mono = 2 * keV
    source.position.type = "point"
    source.position.translation = [0, 0, 0]
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    source.n = 1

    stats = sim.add_actor("SimulationStatisticsActor", "stats")

    chem_actor = sim.add_actor("ChemicalStageActor", "chem_actor")
    chem_actor.attached_to = target
    chem_actor.number_of_time_bins = 50
    if use_actor_requested_dna_em:
        chem_actor.track_structure_em_physics = "DNA_Opt2"
    else:
        chem_actor.track_structure_em_physics = None

    return sim, stats, chem_actor


def check_single_run(stats, results):
    is_ok = True

    is_ok = is_ok and stats.counts.events == 1
    is_ok = is_ok and results.chemistry_starts == 1
    is_ok = is_ok and results.recorded_events == 1
    is_ok = is_ok and results.chemistry_stages >= 1
    is_ok = is_ok and results.pre_time_step_calls > 0
    is_ok = is_ok and results.post_time_step_calls > 0
    is_ok = is_ok and len(results.times_to_record) == 50
    is_ok = is_ok and len(results.species) > 0
    is_ok = is_ok and results.total_energy_deposit >= 0.0
    is_ok = is_ok and results.accumulated_primary_energy_loss >= 0.0
    is_ok = is_ok and results.reaction_count >= 0

    return is_ok


def _species_series(species_dict):
    sorted_items = sorted(species_dict.items(), key=lambda item: float(item[0]))
    times = [float(time) / gate.g4_units.ps for time, _ in sorted_items]
    species_names = sorted(
        {
            str(species_name)
            for _, species_at_time in sorted_items
            for species_name in species_at_time
        }
    )

    series = {species_name: [] for species_name in species_names}
    for _, species_at_time in sorted_items:
        for species_name in species_names:
            values = species_at_time.get(species_name)
            series[species_name].append(0 if values is None else int(values["number"]))

    return times, series


def plot_species_counts(results_list, label, output_filename):
    species_names = sorted(
        {
            str(species_name)
            for results in results_list
            for species_at_time in results["species"].values()
            for species_name in species_at_time
        }
    )

    plt.figure(figsize=(7, 4.5))
    color_cycle = plt.rcParams["axes.prop_cycle"].by_key().get("color", [])
    species_colors = {
        species_name: color_cycle[i % len(color_cycle)] if color_cycle else None
        for i, species_name in enumerate(species_names)
    }
    for species_name in species_names:
        for i, results in enumerate(results_list):
            times, series = _species_series(results["species"])
            counts = series.get(species_name, [0] * len(times))
            curve_label = species_name if i == 0 else None
            plt.plot(
                times,
                counts,
                marker="o",
                markersize=2,
                linewidth=1.0,
                alpha=0.7,
                color=species_colors[species_name],
                label=curve_label,
            )
    plt.xscale("log")
    plt.xlabel("Time [ps]")
    plt.ylabel("Number of chemical species")
    plt.title(f"Chemical species vs time: {label}")
    plt.grid(True, which="both", alpha=0.3)
    plt.legend()
    plt.tight_layout()

    output_path = Path(output_filename)
    plt.savefig(output_path, dpi=150)
    plt.close()
    print(f"Saved species-vs-time plot to: {output_path}")


def run_series(label, use_actor_requested_dna_em):
    results_list = []
    is_ok = True

    for i in range(10):
        sim, stats, chem_actor = create_simulation(
            use_actor_requested_dna_em=use_actor_requested_dna_em,
            seed=123456 + i,
        )
        sim.run(start_new_process=True)
        results = chem_actor.results.get_data()
        print_results(f"{label} run {i + 1}/10:", results)
        is_ok = check_single_run(stats, results) and is_ok
        results_list.append(results)

    return results_list, is_ok


if __name__ == "__main__":
    results_global, is_ok = run_series(
        "Explicit region DNA EM",
        use_actor_requested_dna_em=False,
    )
    plot_species_counts(
        results_global,
        "Explicit region DNA EM (10 x 1 primary)",
        "test102_species_explicit_region_dna_em.png",
    )

    results_actor, is_ok_actor = run_series(
        "Actor-requested DNA EM",
        use_actor_requested_dna_em=True,
    )
    plot_species_counts(
        results_actor,
        "Actor-requested DNA EM (10 x 1 primary)",
        "test102_species_actor_requested_dna_em.png",
    )

    utility.test_ok(is_ok and is_ok_actor)
