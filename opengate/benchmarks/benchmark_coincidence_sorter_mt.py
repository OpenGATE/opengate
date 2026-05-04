#!/usr/bin/env python3
"""
Benchmark: CoincidenceSorterActor scalability with multiple threads.

Runs a fixed-activity, cylindrical back-to-back source inside a Siemens
Biograph PET scanner and measures wall-clock time for 1..N threads. Use the
results to identify the diminishing-returns knee caused by the shared-mutex
serialisation in the coincidence sorter.

Usage
-----
    python benchmark_coincidence_sorter_mt.py                  # defaults
    python benchmark_coincidence_sorter_mt.py --activity 5e5   # 500 kBq
    python benchmark_coincidence_sorter_mt.py --max-threads 6  # 1..6 threads
    python benchmark_coincidence_sorter_mt.py --repeats 3      # best-of-3 each
"""

import argparse
import time

import opengate as gate
import opengate.contrib.pet.siemensbiograph as pet_biograph


def _build_and_run(num_threads: int, activity_bq: float, duration_s: float) -> float:
    """Create a fresh Simulation with *num_threads* threads and return the
    wall-clock time (seconds) for sim.run()."""

    sim = gate.Simulation()
    sim.number_of_threads = num_threads
    sim.random_seed = 123456789
    sim.visu = False
    sim.running_verbose_level = 0

    mm = gate.g4_units.mm
    m = gate.g4_units.m
    sec = gate.g4_units.second
    Bq = gate.g4_units.Bq
    keV = gate.g4_units.keV

    # World
    sim.world.size = [2 * m, 2 * m, 2 * m]
    sim.world.material = "G4_AIR"

    # Empty output_filename suppresses ROOT file writing to avoid skewing timing.
    pet = pet_biograph.add_pet(sim, "pet")
    sc = pet_biograph.add_digitizer(sim, pet.name, "")

    # Coincidence sorter (the actor under test).
    cc = sim.add_actor("CoincidenceSorterActor", "coincidences")
    cc.input_digi_collection = sc.name
    cc.window = 3.0e-9 * sec
    cc.multiples_policy = "RemoveMultiples"
    cc.output_filename = ""  # suppress ROOT I/O

    source = sim.add_source("GenericSource", "b2b")
    source.particle = "back_to_back"
    source.activity = activity_bq * Bq / num_threads
    source.position.type = "cylinder"
    source.position.radius = 150 * mm
    source.position.dz = 150 * mm  # half-length along z
    source.direction.type = "iso"
    source.energy.mono = 511 * keV

    # Physics
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option4"
    sim.physics_manager.global_production_cuts.gamma = 1 * mm
    sim.physics_manager.global_production_cuts.electron = 1 * mm
    sim.physics_manager.global_production_cuts.positron = 1 * mm

    sim.run_timing_intervals = [[0, duration_s * sec]]

    t0 = time.perf_counter()
    sim.run(start_new_process=True)
    return time.perf_counter() - t0


def run_benchmark(
    max_threads: int, activity_bq: float, duration_s: float, repeats: int
) -> list[tuple[int, float]]:
    results = []
    for n in range(1, max_threads + 1):
        times = []
        for r in range(repeats):
            label = (
                f"[threads={n}"
                + (f", rep {r + 1}/{repeats}" if repeats > 1 else "")
                + "]"
            )
            print(f"  {label} running ...", flush=True)
            elapsed = _build_and_run(n, activity_bq, duration_s)
            times.append(elapsed)
            print(f"  {label} {elapsed:.2f} s", flush=True)
        best = min(times)
        results.append((n, best))
    return results


def print_results(results: list[tuple[int, float]]) -> None:
    t1 = results[0][1]
    col = 50
    print("\n" + "=" * col)
    print(
        f"  {'Threads':>7}  {'Wall time (s)':>14}  {'Speedup':>8}  {'Efficiency':>11}"
    )
    print("-" * col)
    for n, t in results:
        speedup = t1 / t
        efficiency = speedup / n * 100
        print(f"  {n:>7}  {t:>14.2f}  {speedup:>8.2f}x  {efficiency:>10.1f}%")
    print("=" * col)

    # Suggest optimal thread count: highest absolute speedup relative to
    # the per-thread cost (i.e. where marginal efficiency first drops below 70 %)
    optimal = 1
    for n, t in results:
        speedup = t1 / t
        if speedup / n >= 0.70:
            optimal = n
    print(
        f"\n  Suggested optimum: {optimal} thread(s)  "
        f"(last point where efficiency >= 70 %)\n"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Benchmark CoincidenceSorterActor MT scalability."
    )
    parser.add_argument(
        "--activity",
        type=float,
        default=1e6,
        help="Back-to-back source activity in Bq (default: 1 MBq).",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=10,
        help="Simulated time window in seconds (default: 10 s).",
    )
    parser.add_argument(
        "--max-threads",
        type=int,
        default=10,
        help="Highest thread count to test (default: 10).",
    )
    parser.add_argument(
        "--repeats",
        type=int,
        default=1,
        help="Repetitions per thread count; best time is reported (default: 1).",
    )
    args = parser.parse_args()

    print(
        f"\nBenchmark parameters:\n"
        f"  activity  = {args.activity:.0f} Bq\n"
        f"  duration  = {args.duration} s  "
        f"(~{args.activity * args.duration:.0f} primary events)\n"
        f"  threads   = 1 .. {args.max_threads}\n"
        f"  repeats   = {args.repeats}\n"
    )

    results = run_benchmark(
        max_threads=args.max_threads,
        activity_bq=args.activity,
        duration_s=args.duration,
        repeats=args.repeats,
    )
    print_results(results)
