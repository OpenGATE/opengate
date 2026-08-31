#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import opengate_core
from opengate.tests import utility


def collect_run_counts(simulation_engine):
    current_run = simulation_engine.g4_RunManager.GetCurrentRun()
    simulation_engine.user_hook_log.append(
        {
            "number_of_events": current_run.GetNumberOfEvent(),
            "number_of_events_to_be_processed": current_run.GetNumberOfEventToBeProcessed(),
        }
    )


def main():
    paths = utility.get_default_test_paths(__file__, output_folder="test098")

    sim = gate.Simulation()
    sim.g4_verbose = False
    sim.visu = False
    sim.number_of_threads = 1
    sim.random_seed = 123456
    sim.output_dir = paths.output
    sim.max_primaries_per_run = 1000
    sim.user_hook_after_run = collect_run_counts

    m = gate.g4_units.m
    Bq = gate.g4_units.Bq
    MeV = gate.g4_units.MeV
    sec = gate.g4_units.s

    sim.world.size = [1 * m, 1 * m, 1 * m]
    sim.world.material = "G4_Galactic"
    sim.physics_manager.physics_list_name = "QGSP_BERT_EMZ"

    source = sim.add_source("GenericSource", "too_many_primaries")
    source.particle = "gamma"
    source.activity = 1.0e6 * Bq
    source.energy.mono = 0.1 * MeV
    source.position.type = "point"
    source.direction.type = "iso"

    sim.run_timing_intervals = [(0, 1 * sec)]
    sim.run()

    run_info = sim.user_hook_log[0]
    produced_events = run_info["number_of_events"]
    requested_events = run_info["number_of_events_to_be_processed"]
    platform_limit = opengate_core.GateSourceManager.GetPlatformMaxPrimariesPerRun()
    is_ok = True

    utility.print_test(
        requested_events == platform_limit,
        f"Geant4 BeamOn requests the platform G4int maximum: {requested_events}",
    )
    is_ok = requested_events == platform_limit and is_ok

    utility.print_test(
        produced_events <= sim.max_primaries_per_run + 1,
        f"Run stopped at the configured ceiling: processed {produced_events} events for a "
        f"primary limit of {sim.max_primaries_per_run} "
        f"(the optional +1 is the dummy termination event)",
    )
    is_ok = produced_events <= sim.max_primaries_per_run + 1 and is_ok

    utility.print_test(
        produced_events < requested_events,
        f"Run terminated early before exhausting Geant4 BeamOn: produced {produced_events}, requested {requested_events}",
    )
    is_ok = produced_events < requested_events and is_ok

    utility.test_ok(is_ok)


if __name__ == "__main__":
    main()
