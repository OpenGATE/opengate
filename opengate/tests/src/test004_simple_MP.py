#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import pathlib
import os
from multiprocessing import Process, Queue

pathFile = pathlib.Path(__file__).parent.resolve()

m = gate.g4_units("m")
cm = gate.g4_units("cm")
keV = gate.g4_units("keV")
mm = gate.g4_units("mm")
Bq = gate.g4_units("Bq")


def start_sim(q):
    print("module name:", __name__)
    print("parent process:", os.getppid())
    print("process id:", os.getpid())

    sim = gate.Simulation()

    ui = sim.user_info
    ui.running_verbose_level = gate.RUN
    ui.g4_verbose = False
    ui.g4_verbose_level = 1
    ui.visu = False
    ui.random_engine = "MersenneTwister"
    ui.random_seed = 123654789
    ui.number_of_threads = 2
    print(ui)

    world = sim.world
    world.size = [3 * m, 3 * m, 3 * m]
    world.material = "G4_AIR"

    waterbox = sim.add_volume("Box", "Waterbox")
    waterbox.size = [40 * cm, 40 * cm, 40 * cm]
    waterbox.translation = [0 * cm, 0 * cm, 25 * cm]
    waterbox.material = "G4_WATER"

    p = sim.get_physics_user_info()
    # p.physics_list_name = "G4EmStandardPhysics_option4"
    p.physics_list_name = "QGSP_BERT_EMV"
    cuts = p.production_cuts
    um = gate.g4_units("um")
    cuts.world.gamma = 700 * um
    cuts.world.electron = 700 * um
    cuts.world.positron = 700 * um
    cuts.world.proton = 700 * um

    source = sim.add_source("Generic", "Default")
    source.particle = "gamma"
    source.energy.mono = 80 * keV
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    source.n = 200000 / ui.number_of_threads

    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.track_types_flag = True

    sim.initialize()
    output = sim.start()

    stats = output.get_actor("Stats")
    print(stats)
    stats_ref = gate.read_stat_file(
        pathFile
        / ".."
        / "data"
        / "gate"
        / "gate_test004_simulation_stats_actor"
        / "output"
        / "stat.txt"
    )
    stats_ref.counts.run_count = ui.number_of_threads
    is_ok = gate.assert_stats(stats, stats_ref, tolerance=0.01)
    q.put(is_ok)


if __name__ == "__main__":
    # create a FIFO queue to get results
    q = Queue()

    print("Start first simulation")
    p = Process(target=start_sim, args=(q,))
    p.start()
    p.join()
    is_ok = q.get()
    print("Simu1", is_ok)

    print()
    print("Start second simulation")
    p = Process(target=start_sim, args=(q,))
    p.start()
    p.join()
    is_ok = q.get() and is_ok

    gate.test_ok(is_ok)
