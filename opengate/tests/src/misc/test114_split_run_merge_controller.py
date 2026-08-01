#!/usr/bin/env python3
"""Exercise the local high-level split-run-merge API based on SplitRunMergeController.

This test focuses on API consistency rather than physics depth. It checks that:

1. ``sim.run(number_of_jobs=1)`` stays on the normal simulation path and does
   not return a split-run controller.
2. ``sim.run(number_of_jobs>1, wait_for_result=False)`` returns a
   ``SplitRunMergeController`` after split and submission, and the caller can take
   over manually via ``wait()``, ``merge()``, and ``clean()``.
3. ``sim.run(number_of_jobs>1, wait_for_result=True, merge_after_run=True)``
   drives the controller up to the merged stage and still returns that same
   controller to the user.

The simulation setup is intentionally simple: one water box, one low-energy
isotropic gamma source at the center, a statistics actor, and a single-voxel
dose actor with edep uncertainty enabled. This is enough to exercise split,
local pool execution, and merge without making the test about output physics
details.

The test also checks the write-to-disk contract of the uncertainty-backed dose
output. In a normal local run, only the user-facing uncertainty image is meant
to appear on disk. In split runs, child jobs must additionally write the hidden
``edep_squared`` image so the merge stage can reconstruct uncertainty after
rehydration, while the merged master output should again expose only the
user-facing files.
"""

import shutil

import itk
import numpy as np
import opengate as gate
from opengate.tests import utility
from opengate.utility import insert_suffix_before_extension


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
    MeV = gate.g4_units.MeV

    world = sim.world
    world.size = [1.0 * m] * 3

    waterbox = sim.add_volume("Box", "waterbox")
    waterbox.size = [20.0 * cm] * 3
    waterbox.material = "G4_WATER"

    source = sim.add_source("GenericSource", "point_source")
    source.attached_to = waterbox
    source.particle = "proton"
    source.energy.mono = 70 * MeV
    source.number_of_primaries = source_n
    source.position.type = "point"
    source.position.translation = [0, 0, 0]
    source.direction.type = "iso"

    # Keep the statistics actor per-run so the split campaign must preserve the
    # original run structure. The dose actor adds a simple standard image output
    # plus a scalar uncertainty output that will be merged back into the live
    # simulation.
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.output_filename = "stats.json"
    stats.keep_data_per_run = True

    dose = sim.add_actor("DoseActor", "dose")
    dose.attached_to = waterbox
    dose.size = [1, 1, 1]
    dose.spacing = [20.0 * cm, 20.0 * cm, 20.0 * cm]
    dose.edep.output_filename = "edep.mhd"
    dose.edep.keep_data_per_run = False
    dose.edep_squared.write_to_disk = False
    dose.edep_uncertainty.active = True
    dose.edep_uncertainty.output_filename = "edep_uncertainty.mhd"
    dose.edep_uncertainty.keep_data_per_run = False

    sim.run_timing_intervals = run_timing_intervals
    return sim


def read_single_voxel_value_from_image_np(image):
    return sum(np.array(image))


def read_single_voxel_value_from_image(image):
    return float(np.asarray(itk.GetArrayViewFromImage(image)).ravel()[0])


def read_single_voxel_value(path):
    return read_single_voxel_value_from_image_np(itk.imread(str(path)))


def get_squared_output_path_from_dose_path(dose_output_path):
    return insert_suffix_before_extension(dose_output_path, "edep_squared")


def get_child_squared_output_paths(job_folders):
    child_squared_paths = []
    for job_folder in job_folders:
        child_simulation = gate.create_sim_from_json(job_folder / "simulation.json")
        child_squared_paths.append(
            child_simulation.get_actor("dose").edep_squared.get_output_path()
        )
    return child_squared_paths


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, output_folder="test114")
    shutil.rmtree(paths.output, ignore_errors=True)
    is_ok = True

    sec = gate.g4_units.s
    run_timing_intervals = [(0.0 * sec, 1.0 * sec), (1.0 * sec, 3.0 * sec)]
    source_n = [1000, 3000]

    # ------------------------------------------------------------------
    # 1) Degenerate managed case: number_of_jobs=1 should map to the normal
    # subprocess path, not to SplitRunMergeController.
    # ------------------------------------------------------------------
    single_job_sim = build_simple_split_run_simulation(
        paths.output / "single_job_output",
        run_timing_intervals,
        source_n,
    )
    single_job_result = single_job_sim.run(number_of_jobs=1)
    single_job_stats_actor = single_job_sim.get_actor("Stats")
    print("Stats results single job: ")
    print(single_job_stats_actor.stats)
    single_job_stats_path = single_job_stats_actor.get_output_path()
    single_job_dose_actor = single_job_sim.get_actor("dose")
    single_job_dose_path = single_job_dose_actor.edep.get_output_path()
    single_job_uncertainty_path = (
        single_job_dose_actor.edep_uncertainty.get_output_path()
    )
    single_job_squared_path = get_squared_output_path_from_dose_path(
        single_job_dose_path
    )

    is_ok = (
        utility.print_test(
            single_job_result is None,
            "sim.run(number_of_jobs=1) stays on the normal run path and returns no controller",
        )
        and is_ok
    )
    is_ok = (
        utility.print_test(
            single_job_stats_path.exists()
            and single_job_dose_path.exists()
            and single_job_uncertainty_path.exists(),
            "number_of_jobs=1 still produces ordinary simulation output at the actor-resolved output paths: "
            f"{single_job_stats_path}, {single_job_dose_path}, and {single_job_uncertainty_path}",
        )
        and is_ok
    )
    # In a normal local run, the hidden squared image stays internal and should
    # not be written to the user-facing output folder.
    is_ok = (
        utility.print_test(
            not single_job_squared_path.exists(),
            "number_of_jobs=1 keeps the hidden edep_squared image off disk in the normal output folder",
        )
        and is_ok
    )

    single_job_dose_value_live_actor = read_single_voxel_value_from_image_np(
        single_job_dose_actor.edep.image
    )
    single_job_uncertainty_value_live_actor = read_single_voxel_value_from_image_np(
        single_job_dose_actor.edep_uncertainty.image
    )
    print(f"Single job dose value from live actor: {single_job_dose_value_live_actor}")

    single_job_dose_value = read_single_voxel_value(single_job_dose_path)
    single_job_uncertainty_value = read_single_voxel_value(single_job_uncertainty_path)
    is_ok = (
        utility.print_test(
            True,
            f"number_of_jobs=1 dose voxel value: {single_job_dose_value}",
        )
        and is_ok
    )
    is_ok = (
        utility.print_test(
            True,
            f"number_of_jobs=1 edep uncertainty voxel value: {single_job_uncertainty_value}",
        )
        and is_ok
    )

    # ------------------------------------------------------------------
    # 2) Asynchronous split run: sim.run(...) returns a SplitRunMergeController
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
        campaign_dir=paths.output / "async_campaign",
        split_policy="split_in_time_total",
        merge_after_run=False,
    )
    is_ok = (
        utility.print_test(
            isinstance(async_controller, gate.SplitRunMergeController),
            "sim.run(number_of_jobs>1) returns a SplitRunMergeController",
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
            async_controller.campaign_dir
            == (paths.output / "async_campaign").resolve(),
            f"Controller keeps track of the campaign directory: {async_controller.campaign_dir}",
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
    async_uncertainty_path = async_sim.get_actor(
        "dose"
    ).edep_uncertainty.get_output_path()
    async_squared_path = get_squared_output_path_from_dose_path(async_dose_path)
    is_ok = (
        utility.print_test(
            async_controller.stage == "merged",
            f"Controller.merge() advances the controller to the merged stage: {async_controller.stage}",
        )
        and is_ok
    )
    is_ok = (
        utility.print_test(
            async_stats_path.exists()
            and async_dose_path.exists()
            and async_uncertainty_path.exists(),
            "Manual controller.merge() writes merged output at the live actor-resolved output paths",
        )
        and is_ok
    )
    # Child jobs must persist the hidden squared image so the merge stage can
    # reconstruct uncertainty from rehydrated output.
    async_child_squared_paths = get_child_squared_output_paths(
        async_controller.jobs_split_manager.job_folders
    )
    is_ok = (
        utility.print_test(
            all(path.exists() for path in async_child_squared_paths),
            "Async split child jobs write the hidden edep_squared image to support uncertainty merge after rehydration",
        )
        and is_ok
    )
    # The merged master output should again expose only the user-facing files.
    is_ok = (
        utility.print_test(
            not async_squared_path.exists(),
            "Async merged master output keeps the hidden edep_squared image off disk",
        )
        and is_ok
    )
    async_merged_dose_value = read_single_voxel_value(async_dose_path)
    async_merged_uncertainty_value = read_single_voxel_value(async_uncertainty_path)
    is_ok = (
        utility.print_test(
            async_merged_dose_value > 0,
            f"Async split-run merged dose voxel value: {async_merged_dose_value}",
        )
        and is_ok
    )
    is_ok = (
        utility.print_test(
            async_merged_uncertainty_value > 0,
            "Async split-run merged edep uncertainty voxel value: "
            f"{async_merged_uncertainty_value}",
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
    # return the same SplitRunMergeController, already advanced to the merged
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
        campaign_dir=paths.output / "merged_campaign",
        split_policy="split_in_time_total",
        merge_after_run=True,
        cleanup_after_run=False,
        poll_interval=0.2,
        timeout=120,
    )
    is_ok = (
        utility.print_test(
            isinstance(merged_controller, gate.SplitRunMergeController)
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

    # Compare the actual merged dose values across all three execution paths.
    # This makes the test robust against setup changes: if one path gives zero
    # while the others do not, we see it immediately in the printed values.
    sync_dose_path = merged_sim.get_actor("dose").edep.get_output_path()
    sync_uncertainty_path = merged_sim.get_actor(
        "dose"
    ).edep_uncertainty.get_output_path()
    sync_squared_path = get_squared_output_path_from_dose_path(sync_dose_path)
    sync_merged_dose_value = read_single_voxel_value(sync_dose_path)
    sync_merged_uncertainty_value = read_single_voxel_value(sync_uncertainty_path)
    is_ok = (
        utility.print_test(
            sync_merged_dose_value > 0,
            f"Synchronous split-run merged dose voxel value: {sync_merged_dose_value}",
        )
        and is_ok
    )
    is_ok = (
        utility.print_test(
            sync_merged_uncertainty_value > 0,
            "Synchronous split-run merged edep uncertainty voxel value: "
            f"{sync_merged_uncertainty_value}",
        )
        and is_ok
    )
    # The same split-only persistence rule should hold when sim.run() waits
    # and merges automatically before returning the controller.
    sync_child_squared_paths = get_child_squared_output_paths(
        merged_controller.jobs_split_manager.job_folders
    )
    is_ok = (
        utility.print_test(
            all(path.exists() for path in sync_child_squared_paths),
            "Synchronous split child jobs write the hidden edep_squared image to support uncertainty merge after rehydration",
        )
        and is_ok
    )
    is_ok = (
        utility.print_test(
            not sync_squared_path.exists(),
            "Synchronous merged master output keeps the hidden edep_squared image off disk",
        )
        and is_ok
    )
    is_ok = (
        utility.print_test(
            np.isclose(
                single_job_dose_value,
                single_job_dose_value_live_actor,
                rtol=0.05,
                atol=0.0,
            ),
            "Normal single job merged dose form disk is close to the normal single-job dose from live actor: "
            f"{single_job_dose_value} vs {single_job_dose_value_live_actor}",
        )
        and is_ok
    )
    is_ok = (
        utility.print_test(
            np.isclose(
                single_job_uncertainty_value,
                single_job_uncertainty_value_live_actor,
                rtol=0.05,
                atol=0.0,
            ),
            "Normal single job edep uncertainty from disk is close to the normal single-job uncertainty from live actor: "
            f"{single_job_uncertainty_value} vs {single_job_uncertainty_value_live_actor}",
        )
        and is_ok
    )
    is_ok = (
        utility.print_test(
            np.isclose(
                single_job_dose_value,
                async_merged_dose_value,
                rtol=0.05,
                atol=0.0,
            ),
            "Async split-run merged dose is close to the normal single-job dose: "
            f"{single_job_dose_value} vs {async_merged_dose_value}",
        )
        and is_ok
    )
    is_ok = (
        utility.print_test(
            np.isclose(
                single_job_uncertainty_value,
                async_merged_uncertainty_value,
                rtol=0.15,
                atol=0.0,
            ),
            "Async split-run merged edep uncertainty is close to the normal single-job uncertainty: "
            f"{single_job_uncertainty_value} vs {async_merged_uncertainty_value}",
        )
        and is_ok
    )
    is_ok = (
        utility.print_test(
            np.isclose(
                single_job_dose_value,
                sync_merged_dose_value,
                rtol=0.05,
                atol=0.0,
            ),
            "Synchronous split-run merged dose is close to the normal single-job dose:"
            f"{single_job_dose_value} vs {sync_merged_dose_value}",
        )
        and is_ok
    )
    is_ok = (
        utility.print_test(
            np.isclose(
                single_job_uncertainty_value,
                sync_merged_uncertainty_value,
                rtol=0.15,
                atol=0.0,
            ),
            "Synchronous split-run merged edep uncertainty is close to the normal single-job uncertainty: "
            f"{single_job_uncertainty_value} vs {sync_merged_uncertainty_value}",
        )
        and is_ok
    )
    is_ok = (
        utility.print_test(
            np.isclose(
                async_merged_dose_value,
                sync_merged_dose_value,
                rtol=0.05,
                atol=0.0,
            ),
            "Asynchronous and synchronous split-run merged doses are mutually consistent: "
            f"{async_merged_dose_value} vs {sync_merged_dose_value}",
        )
        and is_ok
    )

    utility.test_ok(is_ok)
