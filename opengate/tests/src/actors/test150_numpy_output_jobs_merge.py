#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Split jobs with numpy output: the merged .npy must match the merged ROOT file
of the same campaign, including the remapped RunID and EventID.
"""

import json
import shutil

import numpy as np
import uproot

import opengate as gate
from opengate.tests import utility

paths = utility.get_default_test_paths(__file__, output_folder="test150_jobs")


def create_simulation(fmt, output_dir):
    sim = gate.Simulation()
    sim.output_dir = output_dir
    sim.number_of_threads = 1
    sim.random_seed = 123456

    m = gate.g4_units.m
    cm = gate.g4_units.cm
    keV = gate.g4_units.keV
    Bq = gate.g4_units.Bq
    sec = gate.g4_units.s

    sim.world.size = [1 * m, 1 * m, 1 * m]
    sim.world.material = "G4_AIR"
    sphere = sim.add_volume("Sphere", "sphere")
    sphere.material = "G4_AIR"
    sphere.rmax = 20 * cm

    source = sim.add_source("GenericSource", "source")
    source.particle = "gamma"
    source.energy.type = "gauss"
    source.energy.mono = 10 * keV
    source.energy.sigma_gauss = 0.1 * keV
    source.position.type = "point"
    source.direction.type = "iso"
    source.activity = 1000 * Bq

    phsp = sim.add_actor("PhaseSpaceActor", "PhaseSpace")
    phsp.attached_to = sphere
    phsp.steps_to_store = "first"
    phsp.output_filename = f"test150_phsp.{fmt}"
    phsp.attributes = ["GlobalTime", "KineticEnergy", "EventID", "ParticleName"]
    phsp.keep_data_per_run = True

    sim.run_timing_intervals = [(0, 1 * sec), (2 * sec, 5 * sec)]
    return sim


def run_campaign(fmt):
    folder = paths.output / fmt
    shutil.rmtree(folder, ignore_errors=True)
    sim = create_simulation(fmt, folder / "input")
    controller = gate.SplitRunMergeController(
        simulation=sim,
        campaign_dir=folder / "split",
        split_policy="split_in_time_total",
        backend="local_pool",
    )
    controller.split(number_of_jobs=3)
    controller.run(number_of_workers=3)
    controller.wait(poll_interval=0.2, timeout=300)
    controller.merge(to_path=folder / "merged")
    return controller.merge_manager.master_simulation.get_actor("PhaseSpace")


if __name__ == "__main__":
    root_path = run_campaign("root").get_output_file_path()
    npy_phsp = run_campaign("npy")
    npy_path = npy_phsp.get_output_path()

    merged = npy_phsp.get_output_file_path()
    is_ok = utility.print_test(
        merged.name == "test150_phsp.PhaseSpace.npy" and merged.exists(),
        f"merged file from get_output_file_path(): {merged.name}",
    )

    a = np.load(merged)
    with uproot.open(root_path) as f:
        root = f["PhaseSpace"].arrays(library="np")

    is_ok = (
        utility.print_test(
            set(a.dtype.names) == set(root),
            f"same columns: {sorted(a.dtype.names)}",
        )
        and is_ok
    )
    is_ok = (
        utility.print_test(
            len(a) == len(root["EventID"]) and len(a) > 0,
            f"rows: {len(a)} in numpy, {len(root['EventID'])} in ROOT",
        )
        and is_ok
    )
    different = []
    for name in a.dtype.names:
        x, y = a[name], root[name]
        if x.dtype.kind == "S":
            x = x.astype(str)
            y = y.astype(str)
        if len(x) != len(y) or not np.array_equal(x, y):
            different.append(name)
    is_ok = (
        utility.print_test(
            len(different) == 0, f"different columns after merge: {different}"
        )
        and is_ok
    )
    is_ok = (
        utility.print_test(
            np.array_equal(np.unique(a["RunID"]), [0, 1]),
            f"RunID values: {np.unique(a['RunID'])}",
        )
        and is_ok
    )

    metadata_path = npy_path.with_name("test150_phsp-PhaseSpace-metadata.json")
    with open(metadata_path) as f:
        metadata = json.load(f)
    is_ok = (
        utility.print_test(
            metadata["file_format"] == "npy", "merged metadata: file_format is npy"
        )
        and is_ok
    )

    utility.test_ok(is_ok)
