#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from opengate.tests import utility
import opengate as gate
from opengate.contrib.beamlines.ionbeamline import BeamlineModel


def run_simulation(
    paths, n, intervals, sorted_spot_generation, number_of_threads, seed=123654789
):
    sim = gate.Simulation()
    sim.g4_verbose = False
    sim.visu = False
    sim.random_seed = seed
    sim.number_of_threads = number_of_threads
    sim.output_dir = paths.output
    sim.progress_bar = False

    cm = gate.g4_units.cm
    km = gate.g4_units.km
    sec = gate.g4_units.s

    sim.world.size = [600 * cm, 500 * cm, 500 * cm]
    sim.world.material = "G4_Galactic"

    beamline = BeamlineModel()
    beamline.name = None
    beamline.radiation_types = "proton"
    beamline.energy_mean_coeffs = [1, 0]
    beamline.energy_spread_coeffs = [0.4417036946562556]
    beamline.sigma_x_coeffs = [2.3335754]
    beamline.theta_x_coeffs = [2.3335754e-3]
    beamline.epsilon_x_coeffs = [0.00078728e-3]
    beamline.sigma_y_coeffs = [1.96433431]
    beamline.theta_y_coeffs = [0.00079118e-3]
    beamline.epsilon_y_coeffs = [0.00249161e-3]

    tps = sim.add_source("TreatmentPlanPBSource", "TPSource")
    tps.number_of_primaries = n
    tps.beam_model = beamline
    tps.plan_path = paths.output_ref / "TreatmentPlan2Spots.txt"
    tps.beam_nr = 1
    tps.gantry_rot_axis = "x"
    tps.sorted_spot_generation = sorted_spot_generation
    tps.particle = "proton"

    stats = sim.add_actor("SimulationStatisticsActor", "Stats")

    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option4"
    sim.physics_manager.set_production_cut("world", "all", 1000 * km)

    sim.run_timing_intervals = [[a * sec, b * sec] for a, b in intervals]
    sim.run(start_new_process=True)

    return stats.counts.events, tps.get_generated_primaries()


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "gate_test044_pbs", "test059")

    # The number of generated primaries must be the requested one, whatever the
    # duration of the run(s), the spot generation mode and the number of threads.
    # (n, run intervals in sec, sorted_spot_generation, number_of_threads)
    cases = [
        (1000, [[0, 1]], False, 1),
        (1000, [[0, 0.5]], False, 1),
        (1000, [[0, 2]], False, 1),
        (1000, [[0, 0.5]], True, 1),
        (1000, [[0, 2]], True, 1),
        (1001, [[0, 2]], True, 3),
        (1001, [[0, 0.5]], False, 3),
        ([600, 400], [[0, 1], [1, 3]], True, 1),
        ([600, 400], [[0, 1], [1, 3]], False, 2),
    ]

    is_ok = True
    for n, intervals, sorted_spot_generation, number_of_threads in cases:
        events, per_spot = run_simulation(
            paths, n, intervals, sorted_spot_generation, number_of_threads
        )
        expected = sum(n) if isinstance(n, list) else n
        b = events == expected and len(per_spot) == 2 and sum(per_spot) == expected
        utility.print_test(
            b,
            f"n={n} intervals={intervals} sorted={sorted_spot_generation} "
            f"threads={number_of_threads}: events={events} per spot={per_spot} "
            f"(expected {expected})",
        )
        is_ok = b and is_ok

    utility.test_ok(is_ok)
