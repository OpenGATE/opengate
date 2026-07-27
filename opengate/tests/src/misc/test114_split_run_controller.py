#!/usr/bin/env python3
"""Exercise the local high-level split-run API based on SplitRunController.

This test focuses on API consistency rather than physics depth. It checks that:

1. ``sim.run(number_of_jobs=1)`` stays on the normal simulation path and does
   not return a split-run controller.
2. ``sim.run(number_of_jobs>1, wait_for_result=False)`` returns a
   ``SplitRunController`` after split and submission, and the caller can take
   over manually via ``wait()``, ``merge()``, and ``clean()``.
3. ``sim.run(number_of_jobs>1, wait_for_result=True, merge_after_run=True)``
   drives the controller up to the merged stage and still returns that same
   controller to the user.

The simulation setup is intentionally simple: one water box, one low-energy
proton point source, a statistics actor, and a single-voxel dose actor. This
is enough to exercise split, local pool execution, and merge without making the
test about output physics details.
"""

import shutil

import itk
import numpy as np
import opengate as gate
from opengate.tests import utility


def build_simple_split_run_simulation(output_path, run_timing_intervals, source_n):
    """Build a small split-friendly simulation with standard mergeable output."""

    sim = gate.Simulation()
    sim.output_dir = output_path
    sim.g4_verbose = False
    sim.visu = False
    sim.number_of_threads = 1
    sim.random_seed = 123456789

    cm = gate.g4_units.cm
    m = gate.g4_units.m
    keV = gate.g4_units.keV

    world = sim.world
    world.size = [1.0 * m] * 3

    waterbox = sim.add_volume("Box", "waterbox")
    waterbox.size = [20.0 * cm] * 3
    waterbox.material = "G4_WATER"

    source = sim.add_source("GenericSource", "point_source")
    source.particle = "proton"
    source.energy.mono = 10 * keV
    source.n = source_n
    source.position.type = "point"
    source.position.translation = [0, 0, -9.0 * cm]
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]

    # Keep the statistics actor per-run so the split campaign must preserve the
    # original run structure. The dose actor adds a simple standard image output
    # that will be merged back into the live simulation.
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.output_filename = "stats.json"
    stats.keep_data_per_run = True

    dose = sim.add_actor("DoseActor", "dose")
    dose.attached_to = "waterbox"
    dose.size = [1, 1, 1]
    dose.spacing = [20.0 * cm, 20.0 * cm, 20.0 * cm]
    dose.output_filename = "dose.mhd"
    dose.keep_data_per_run = True

    sim.run_timing_intervals = run_timing_intervals
    return sim


def read_single_voxel_value(path):
    return float(np.asarray(itk.GetArrayViewFromImage(itk.imread(str(path)))).ravel()[0])


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, output_folder="test114")
    shutil.rmtree(paths.output, ignore_errors=True)
    is_ok = True

    sec = gate.g4_units.s
    run_timing_intervals = [(0.0 * sec, 1.0 * sec), (1.0 * sec, 3.0 * sec)]
    source_n = [100, 300]

    # ------------------------------------------------------------------
    # 1) Degenerate managed case: number_of_jobs=1 should map to the normal
    # subprocess path, not to SplitRunController.
    # ------------------------------------------------------------------
    single_job_sim = build_simple_split_run_simulation(
        paths.output / "single_job_output",
        run_timing_intervals,
        source_n,
    )
    single_job_result = single_job_sim.run(number_of_jobs=1)
    single_job_stats_path = single_job_sim.get_actor("Stats").get_output_path()
    single_job_dose_path = single_job_sim.get_actor("dose").edep.get_output_path()
    is_ok = (
        utility.print_test(
            single_job_result is None,
            "sim.run(number_of_jobs=1) stays on the normal run path and returns no controller",
        )
        and is_ok
    )
    is_ok = (
        utility.print_test(
            single_job_stats_path.exists() and single_job_dose_path.exists(),
            "number_of_jobs=1 still produces ordinary simulation output at the actor-resolved output paths",
        )
        and is_ok
    )

    # ------------------------------------------------------------------
    # 2) Asynchronous split run: sim.run(...) returns a SplitRunController
    # after split and submission, then the caller explicitly continues with
    # wait(), merge(), and clean().
    # ------------------------------------------------------------------
    async_sim = build_simple_split_run_simulation(
        paths.output / "async_master_output",
        run_timing_intervals,
        source_n,
    )
    async_controller = async_sim.run(
        number_of_jobs=3,
        wait_for_result=False,
        jobs_root_dir=paths.output / "async_campaign",
        split_policy="split_in_time_total",
        backend_options={
            "n_workers": 2,
            "start_method": "spawn",
            "maxtasksperchild": 1,
        },
        merge_after_run=False,
    )
    is_ok = (
        utility.print_test(
            isinstance(async_controller, gate.SplitRunController),
            "sim.run(number_of_jobs>1) returns a SplitRunController",
        )
        and is_ok
    )
    is_ok = (
        utility.print_test(
            async_controller.stage in ("submitted", "running"),
            f"Asynchronous controller is returned after submission: stage={async_controller.stage}",
        )
        and is_ok
    )
    is_ok = (
        utility.print_test(
            async_controller.jobs_root_dir == (paths.output / "async_campaign").resolve(),
            f"Controller keeps track of the jobs root directory: {async_controller.jobs_root_dir}",
        )
        and is_ok
    )

    # The caller explicitly takes over from here: first wait for the detached
    # local-pool campaign to finish, then merge the output into the live
    # simulation object, then remove temporary split artifacts.
    async_controller.wait(poll_interval=0.2, timeout=120)
    is_ok = (
        utility.print_test(
            async_controller.stage == "completed",
            f"Controller.wait() advances the controller to the completed stage: {async_controller.stage}",
        )
        and is_ok
    )

    async_controller.merge()
    async_stats_path = async_sim.get_actor("Stats").get_output_path()
    async_dose_path = async_sim.get_actor("dose").edep.get_output_path()
    is_ok = (
        utility.print_test(
            async_controller.stage == "merged",
            f"Controller.merge() advances the controller to the merged stage: {async_controller.stage}",
        )
        and is_ok
    )
    is_ok = (
        utility.print_test(
            async_stats_path.exists() and async_dose_path.exists(),
            "Manual controller.merge() writes merged output at the live actor-resolved output paths",
        )
        and is_ok
    )

    async_controller.clean()
    is_ok = (
        utility.print_test(
            async_controller.stage == "cleaned",
            f"Controller.clean() advances the controller to the cleaned stage: {async_controller.stage}",
        )
        and is_ok
    )
    is_ok = (
        utility.print_test(
            not (paths.output / "async_campaign" / "job0001").exists()
            and (paths.output / "async_campaign" / "simulation.json").exists(),
            "Controller.clean() removes job folders but keeps the packaged campaign root",
        )
        and is_ok
    )

    # ------------------------------------------------------------------
    # 3) Synchronous split run with automatic merge: sim.run(...) should
    # return the same SplitRunController, already advanced to the merged
    # stage, so the user can continue inspection or cleanup manually.
    # ------------------------------------------------------------------
    merged_sim = build_simple_split_run_simulation(
        paths.output / "merged_master_output",
        run_timing_intervals,
        source_n,
    )
    merged_controller = merged_sim.run(
        number_of_jobs=3,
        wait_for_result=True,
        jobs_root_dir=paths.output / "merged_campaign",
        split_policy="split_in_time_total",
        backend_options={
            "n_workers": 2,
            "start_method": "spawn",
            "maxtasksperchild": 1,
        },
        merge_after_run=True,
        cleanup_after_run=False,
        poll_interval=0.2,
        timeout=120,
    )
    is_ok = (
        utility.print_test(
            isinstance(merged_controller, gate.SplitRunController)
            and merged_controller.stage == "merged",
            f"Synchronous split run returns a merged controller: stage={merged_controller.stage}",
        )
        and is_ok
    )
    is_ok = (
        utility.print_test(
            merged_controller.merge_manager is not None
            and merged_controller.status["merge_result"] is not None,
            "Merged controller exposes merge_manager and merge_result for further inspection",
        )
        and is_ok
    )

    # The merged dose value itself is not the purpose of this test, but
    # checking that it is positive confirms that the live simulation received
    # real merged data rather than only bookkeeping state.
    merged_dose_value = read_single_voxel_value(
        merged_sim.get_actor("dose").edep.get_output_path()
    )
    is_ok = (
        utility.print_test(
            merged_dose_value > 0.0,
            f"Merged split-run dose output contains data: voxel value={merged_dose_value}",
        )
        and is_ok
    )

    utility.test_ok(is_ok)
