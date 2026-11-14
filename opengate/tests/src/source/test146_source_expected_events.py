#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Expected number of events of a source (used by the progress bar), #1024.
It is compared to the analytical integral of the activity and to the number
of generated events:
- constant activity, source start_time/end_time inside the run;
- decaying activity (half_life), source starting after the run start;
- TAC (time activity curve), with a hole between two runs, mono and multi-thread,
  and with a spectrum (the activity is scaled by the total yield);
- number_of_primaries.
"""

import numpy as np
import opengate as gate
from opengate.tests import utility

m = gate.g4_units.m
sec = gate.g4_units.s
Bq = gate.g4_units.Bq
MeV = gate.g4_units.MeV
keV = gate.g4_units.keV


def run(name, set_source, intervals, threads=1):
    sim = gate.Simulation()
    sim.output_dir = paths.output
    sim.verbose_level = gate.logger.NONE
    sim.random_seed = 32145
    sim.number_of_threads = threads
    sim.world.size = [1 * m, 1 * m, 1 * m]
    sim.world.material = "G4_Galactic"
    sim.run_timing_intervals = intervals

    source = sim.add_source("GenericSource", name)
    source.particle = "geantino"
    source.energy.mono = 1 * MeV
    source.direction.type = "iso"
    set_source(source)

    stats = sim.add_actor("SimulationStatisticsActor", "stats")
    sim.run(start_new_process=True)
    return sim.expected_number_of_events, stats.counts.events


def check(name, set_source, intervals, analytic, threads=1):
    expected, generated = run(name, set_source, intervals, threads)
    # rounding: one event per thread and per run
    b1 = abs(expected - analytic) <= threads * len(intervals)
    # generated: Poisson, 4 sigma (exact when the number of primaries is set)
    b2 = abs(generated - expected) <= 4 * np.sqrt(expected)
    utility.print_test(
        b1 and b2,
        f"{name:20}: expected {expected:6} (analytic {analytic:9.1f}), "
        f"generated {generated:6}",
    )
    return b1 and b2


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "", output_folder="test146")
    is_ok = True

    # constant activity, the source is active between 1 and 3 sec only
    def constant(s):
        s.activity = 2000 * Bq
        s.start_time = 1 * sec
        s.end_time = 3 * sec

    is_ok = check("constant", constant, [[0, 5 * sec]], 2000 * 2) and is_ok

    # decaying activity, starting at 2 sec
    hl = 2 * sec
    lbd = np.log(2) / (hl / sec)

    def decay(s):
        s.activity = 3000 * Bq
        s.half_life = hl
        s.start_time = 2 * sec

    analytic = 3000 / lbd * (1 - np.exp(-lbd * 8))
    is_ok = check("half_life", decay, [[0, 10 * sec]], analytic) and is_ok

    # TAC between 1 and 6 sec, two runs with a hole between 2.9 and 3 sec
    times = np.linspace(1, 6, num=50) * sec
    activities = 4000 * np.exp(-lbd * times / sec) * Bq

    def tac(s):
        s.tac_times = times
        s.tac_activities = activities

    intervals = [[0, 2.9 * sec], [3 * sec, 7 * sec]]
    t = np.linspace(0, 7, 70001)
    a = np.interp(t, times / sec, activities / Bq, left=0, right=0)
    a[(t > 2.9) & (t < 3)] = 0
    analytic = np.sum((a[1:] + a[:-1]) / 2 * np.diff(t))
    is_ok = check("tac", tac, intervals, analytic) and is_ok
    is_ok = check("tac_mt", tac, intervals, analytic, threads=2) and is_ok

    # TAC with a spectrum: the activity is scaled by the sum of the weights
    # (total yield 0.4), like without TAC
    def tac_yield(s):
        tac(s)
        s.particle = "gamma"
        s.energy.type = "spectrum_discrete"
        s.energy.spectrum_energies = [100 * keV, 200 * keV]
        s.energy.spectrum_weights = [0.3, 0.1]

    is_ok = check("tac_yield", tac_yield, intervals, analytic * 0.4) and is_ok

    # number of primaries
    def primaries(s):
        s.number_of_primaries = 1234

    is_ok = check("number_of_primaries", primaries, [[0, 1 * sec]], 1234) and is_ok

    utility.test_ok(is_ok)
