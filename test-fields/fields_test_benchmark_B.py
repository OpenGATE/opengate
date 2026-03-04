#!/usr/bin/env python3
"""
Benchmark custom magnetic field vs Geant4 uniform magnetic field.

Runs the same simple simulation for increasing number of histories
and compare run times.
"""

from pathlib import Path
import argparse
import csv
import json
import matplotlib.pyplot as plt
import subprocess
import sys
import time

import opengate as gate
from opengate.geometry import fields

HISTORIES = [1, 10, 100, 1000, 10000, 100000]


def _build_simulation(
    field_impl: str,
    n_histories: int,
) -> tuple[gate.Simulation, object]:
    sim = gate.Simulation()

    sim.g4_verbose = False
    sim.visu = False
    sim.number_of_threads = 1
    sim.random_seed = 42
    sim.output_dir = "."

    g4_m = gate.g4_units.m
    g4_cm = gate.g4_units.cm
    g4_MeV = gate.g4_units.MeV
    g4_tesla = gate.g4_units.tesla

    world = sim.world
    world.size = [1 * g4_m, 1 * g4_m, 1 * g4_m]
    world.material = "G4_Galactic"

    box = sim.add_volume("BoxVolume", "field_box")
    box.size = [50 * g4_cm, 50 * g4_cm, 50 * g4_cm]
    box.material = "G4_Galactic"

    by = 5 * g4_tesla
    if field_impl == "uniform":
        field = fields.UniformMagneticField(name="B_uniform")
        field.field_vector = [0, by, 0]

    elif field_impl == "custom":

        def custom_uniform_b_field(x, y, z, t):
            return [0, by, 0]

        field = fields.CustomMagneticField(
            name="B_uniform_custom",
            field_function=custom_uniform_b_field,
        )

    else:
        raise ValueError(f"Unknown field implementation: {field_impl}")

    box.add_field(field)

    source = sim.add_source("GenericSource", "proton_source")
    source.particle = "proton"
    source.n = int(n_histories)
    source.energy.type = "mono"
    source.energy.mono = 10 * g4_MeV
    source.position.type = "point"
    source.position.translation = [0 * g4_cm, 0 * g4_cm, -100 * g4_cm]
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]

    stats = sim.add_actor("SimulationStatisticsActor", "stats")
    return sim, stats


def _run_once(field_impl: str, n_histories: int) -> dict:
    sim, stats = _build_simulation(field_impl=field_impl, n_histories=n_histories)
    start = time.perf_counter()
    sim.run()
    elapsed_s = time.perf_counter() - start

    duration_s = float(stats.counts["duration"] / gate.g4_units.s)
    events = int(stats.counts["events"])
    return {
        "field_impl": field_impl,
        "n_histories": int(n_histories),
        "wall_time_s": elapsed_s,
        "geant4_duration_s": duration_s,
        "events": events,
    }


def _run_once_subprocess(
    field_impl: str,
    n_histories: int,
    out_dir: Path,
) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    result_path = out_dir / f"benchmark_B_{field_impl}_{n_histories}.json"

    cmd = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--child-run",
        "--field-impl",
        str(field_impl),
        "--histories",
        str(int(n_histories)),
        "--result-json",
        str(result_path),
    ]

    completed = subprocess.run(cmd, capture_output=True, text=True)
    if completed.returncode != 0:
        raise RuntimeError(
            "Child benchmark process failed.\n"
            f"Command: {' '.join(cmd)}\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )

    with open(result_path, "r") as fp:
        return json.load(fp)


def _write_csv(path: Path, rows: list[dict]) -> None:
    with Path.open(path, "w", newline="") as fp:
        writer = csv.DictWriter(
            fp,
            fieldnames=[
                "field_impl",
                "n_histories",
                "wall_time_s",
                "geant4_duration_s",
                "events",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def _child_main(
    field_impl: str,
    n_histories: int,
    result_json: Path,
) -> None:
    row = _run_once(field_impl=field_impl, n_histories=n_histories)
    result_json.parent.mkdir(parents=True, exist_ok=True)

    with Path.open(result_json, "w") as fp:
        json.dump(row, fp)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--child-run", action="store_true", default=False)
    parser.add_argument(
        "--field-impl", choices=["uniform", "custom"], default="uniform"
    )
    parser.add_argument("--histories", type=int, default=1)
    parser.add_argument("--result-json", type=Path, default=None)
    args = parser.parse_args()

    if args.child_run:
        if args.result_json is None:
            raise ValueError("--result-json is required with --child-run")
        _child_main(args.field_impl, args.histories, args.result_json)
        raise SystemExit(0)

    out_dir = Path(__file__).resolve().parent / "out"
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    print("\nBenchmark: custom B field vs uniform B field")
    print(f"Histories: {HISTORIES}")

    for n in HISTORIES:
        res_uniform = _run_once_subprocess("uniform", n, out_dir)
        res_custom = _run_once_subprocess("custom", n, out_dir)
        rows.extend([res_uniform, res_custom])

        ratio = res_custom["wall_time_s"] / res_uniform["wall_time_s"]
        print(
            f"n={n:>6d} | uniform={res_uniform['wall_time_s']:.6f}s | "
            f"custom={res_custom['wall_time_s']:.6f}s | custom/uniform={ratio:.3f}"
        )

    fig, ax = plt.subplots()
    for field_impl in ["uniform", "custom"]:
        impl_rows = [row for row in rows if row["field_impl"] == field_impl]
        n_histories = [row["n_histories"] for row in impl_rows]
        wall_times = [row["wall_time_s"] for row in impl_rows]
        ax.plot(n_histories, wall_times, marker="o", label=field_impl)
    ax.set_xscale("log")
    ax.set_yscale("linear")
    ax.set_xlabel("Number of Histories")
    ax.set_ylabel("Wall Time (s)")
    ax.set_title("Benchmark: Custom B Field vs Uniform B Field")
    ax.legend()
    plt.grid()
    plt.tight_layout()
    plt.savefig(out_dir / "benchmark_B.png")

    csv_path = out_dir / "benchmark_fields_B.csv"
    _write_csv(csv_path, rows)
    print(f"\nSaved results to: {csv_path}")
