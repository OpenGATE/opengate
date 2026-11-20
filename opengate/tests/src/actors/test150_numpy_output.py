#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Same simulation written as ROOT and as numpy (.npy), compared column by column.
Hits and Singles share one filename, the energy windows actor writes two
collections: each collection gets its own .npy file.
"""

import json

import numpy as np
import uproot

import opengate as gate
from opengate.tests import utility

paths = utility.get_default_test_paths(__file__, output_folder="test150")


def create_simulation(fmt, number_of_threads):
    sim = gate.Simulation()
    sim.number_of_threads = number_of_threads
    sim.random_seed = 654321
    sim.check_volumes_overlap = False
    sim.output_dir = paths.output / f"{fmt}_{number_of_threads}"

    m = gate.g4_units.m
    cm = gate.g4_units.cm
    keV = gate.g4_units.keV
    Bq = gate.g4_units.Bq
    sec = gate.g4_units.s

    sim.world.size = [2 * m, 2 * m, 2 * m]
    head = sim.add_volume("Box", "head")
    head.size = [30 * cm, 30 * cm, 18 * cm]
    head.material = "G4_AIR"
    crystal = sim.add_volume("Box", "crystal")
    crystal.mother = head
    crystal.size = [0.5 * cm, 0.5 * cm, 2 * cm]
    crystal.material = "G4_SODIUM_IODIDE"
    crystal.translation = gate.geometry.utility.get_grid_repetition(
        size=[40, 40, 1],
        spacing=[0.5 * cm, 0.5 * cm, 0],
        start=[-10 * cm, -10 * cm, 4 * cm],
    )

    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option4"
    source = sim.add_source("GenericSource", "source")
    source.particle = "gamma"
    source.energy.mono = 140.5 * keV
    source.position.type = "sphere"
    source.position.radius = 4 * cm
    source.position.translation = [0, 0, -15 * cm]
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    source.activity = 20000 * Bq

    hits = sim.add_actor("DigitizerHitsCollectionActor", "Hits")
    hits.attached_to = crystal
    hits.output_filename = f"test150.{fmt}"
    hits.attributes = [
        "TotalEnergyDeposit",
        "PostPosition",
        "GlobalTime",
        "TrackVolumeName",
        "PreStepUniqueVolumeID",
        "RunID",
        "EventID",
        "ThreadID",
    ]

    singles = sim.add_actor("DigitizerAdderActor", "Singles")
    singles.attached_to = crystal
    singles.input_digi_collection = "Hits"
    singles.policy = "EnergyWinnerPosition"
    singles.output_filename = f"test150.{fmt}"

    ew = sim.add_actor("DigitizerEnergyWindowsActor", "EnergyWindows")
    ew.attached_to = crystal
    ew.input_digi_collection = "Singles"
    ew.channels = [
        {"name": "scatter", "min": 114 * keV, "max": 126 * keV},
        {"name": "peak140", "min": 126 * keV, "max": 154.55 * keV},
    ]
    ew.output_filename = f"test150_ew.{fmt}"

    sim.run_timing_intervals = [[0, 0.3 * sec], [0.3 * sec, 1 * sec]]
    return sim


def sorted_columns(columns, keys):
    order = np.lexsort([columns[k] for k in reversed(keys)])
    return {k: np.asarray(v)[order] for k, v in columns.items()}


def compare_tree(npy_file, root_file, tree_name, ignored):
    a = np.load(npy_file)
    npy = {name: a[name] for name in a.dtype.names}
    with uproot.open(root_file) as f:
        root = f[tree_name].arrays(library="np")

    is_ok = utility.print_test(
        set(npy) == set(root),
        f"{tree_name}: same columns in {npy_file.name} and {root_file.name}",
    )
    is_ok = (
        utility.print_test(
            len(a) == len(root["EventID"]) and len(a) > 0,
            f"{tree_name}: {len(a)} rows in numpy, {len(root['EventID'])} in ROOT",
        )
        and is_ok
    )
    if not is_ok:
        return False

    # thread order differs between two MT runs, so compare sorted rows
    keys = ["RunID", "EventID", "GlobalTime", "TotalEnergyDeposit"]
    npy = sorted_columns(npy, keys)
    root = sorted_columns(root, keys)
    different = []
    for name in npy:
        if name in ignored:
            continue
        x, y = npy[name], root[name]
        if x.dtype.kind == "S":
            x = x.astype(str)
            y = y.astype(str)
        if not np.array_equal(x, y):
            different.append(name)
    return (
        utility.print_test(
            len(different) == 0, f"{tree_name}: different columns {different}"
        )
        and is_ok
    )


def check_output_file_path(sims):
    root_hits = sims["root"].get_actor("Hits")
    npy_hits = sims["npy"].get_actor("Hits")
    npy_ew = sims["npy"].get_actor("EnergyWindows")
    is_ok = utility.print_test(
        root_hits.get_output_file_path() == root_hits.get_output_path(),
        f"ROOT: get_output_file_path() is {root_hits.get_output_file_path().name}",
    )
    path = npy_hits.get_output_file_path()
    is_ok = (
        utility.print_test(
            path.name == "test150.Hits.npy" and path.exists(),
            f"numpy: get_output_file_path() is {path.name}",
        )
        and is_ok
    )
    path = npy_ew.get_output_file_path("peak140")
    is_ok = (
        utility.print_test(
            path.name == "test150_ew.peak140.npy" and path.exists(),
            f"numpy: get_output_file_path('peak140') is {path.name}",
        )
        and is_ok
    )
    # two collections: the name is required
    try:
        npy_ew.get_output_file_path()
        raised = False
    except Exception:
        raised = True
    return (
        utility.print_test(
            raised, "numpy: get_output_file_path() without collection fails"
        )
        and is_ok
    )


def check(number_of_threads):
    print(f"\nThreads: {number_of_threads}")
    sims = {}
    for fmt in ("root", "npy"):
        sims[fmt] = create_simulation(fmt, number_of_threads)
        sims[fmt].run(start_new_process=True)

    root_dir = paths.output / f"root_{number_of_threads}"
    npy_dir = paths.output / f"npy_{number_of_threads}"
    ignored = ["ThreadID"] if number_of_threads > 1 else []

    is_ok = check_output_file_path(sims)
    for tree_name, stem in [
        ("Hits", "test150"),
        ("Singles", "test150"),
        ("scatter", "test150_ew"),
        ("peak140", "test150_ew"),
    ]:
        npy_file = npy_dir / f"{stem}.{tree_name}.npy"
        is_ok = (
            utility.print_test(npy_file.exists(), f"{npy_file.name} exists") and is_ok
        )
        if npy_file.exists():
            is_ok = (
                compare_tree(npy_file, root_dir / f"{stem}.root", tree_name, ignored)
                and is_ok
            )

    with open(npy_dir / "test150-Hits-metadata.json") as f:
        metadata = json.load(f)
    is_ok = (
        utility.print_test(
            metadata["file_format"] == "npy", "metadata: file_format is npy"
        )
        and is_ok
    )
    return is_ok


if __name__ == "__main__":
    is_ok = check(1)
    is_ok = check(2) and is_ok
    utility.test_ok(is_ok)
