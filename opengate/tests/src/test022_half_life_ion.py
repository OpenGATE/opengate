#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import test022_half_life_helpers as test022
import opengate as gate
from opengate.tests import utility
import math
import sys
import matplotlib.pyplot as plt

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, output_folder="test022")

    # create the simulation
    sim = gate.Simulation()

    # multithread ?
    argv = sys.argv
    n = 1
    if len(argv) > 1:
        n = int(argv[1])

    # main options
    sim.g4_verbose = False
    # sim.visu = True
    sim.visu_type = "vrml"
    sim.number_of_threads = n
    sim.random_seed = 92344321
    sim.output_dir = paths.output
    print(sim)

    # units
    m = gate.g4_units.m
    cm = gate.g4_units.cm
    mm = gate.g4_units.mm
    nm = gate.g4_units.nm
    keV = gate.g4_units.keV
    Bq = gate.g4_units.Bq
    sec = gate.g4_units.s

    # set the world size like in the Gate macro
    sim.world.size = [10 * m, 10 * m, 10 * m]

    # waterbox
    waterbox1 = sim.add_volume("Box", "waterbox1")
    waterbox1.size = [50 * cm, 50 * cm, 50 * cm]
    waterbox1.translation = [50 * cm, 0 * cm, 0 * cm]
    waterbox1.material = "G4_WATER"

    # plane between the two waterbox to stop gamma
    gcm3 = gate.g4_units.g_cm3
    sim.volume_manager.material_database.add_material_nb_atoms(
        "Tung", ["W"], [1], 1000 * gcm3
    )
    tung_plane = sim.add_volume("Box", "tung_plane")
    tung_plane.size = [1 * cm, 300 * cm, 300 * cm]
    tung_plane.translation = [0 * cm, 0 * cm, 0 * cm]
    tung_plane.material = "Tung"

    # waterbox
    waterbox2 = sim.add_volume("Box", "waterbox2")
    waterbox2.size = [50 * cm, 50 * cm, 50 * cm]
    waterbox2.translation = [-50 * cm, 0 * cm, 0 * cm]
    waterbox2.material = "G4_WATER"

    # physics
    sim.physics_manager.physics_list_name = "QGSP_BERT_EMZ"
    sim.physics_manager.enable_decay = True
    sim.physics_manager.global_production_cuts.all = (
        1 * mm
    )  # all means: proton, electron, positron, gamma

    # activity
    activity_Bq = 8000 * Bq
    half_life = 5 * sec
    lifetime = half_life / math.log(2.0)

    # "hole" in the timeline to check if no particle are emitted at this moment
    sim.run_timing_intervals = [[0 * sec, 12 * sec], [13 * sec, 20 * sec]]

    # source #1
    source1 = sim.add_source("GenericSource", "source1")
    source1.mother = "waterbox1"
    source1.particle = "ion 49 111"  # In111 171 keV and 245 keV
    source1.position.type = "sphere"
    source1.position.radius = 1 * mm
    source1.direction.type = "iso"
    source1.activity = activity_Bq / sim.number_of_threads
    source1.half_life = half_life
    # this is needed, but automatically done in GenericSource.py
    source1.user_particle_life_time = 0
    print()
    print(f"Source1 ac = {source1.activity / Bq} Bq")
    print(f"Source1 HL = {half_life / sec} sec")

    # source #2
    source2 = sim.add_source("GenericSource", "source2")
    source2.mother = "waterbox2"
    source2.particle = "ion 49 111"  # In111 171 keV and 245 keV
    source2.position.type = "sphere"
    source2.position.radius = 1 * mm
    source2.position.translation = [0, 0, -3 * cm]
    source2.direction.type = "iso"
    source2.user_particle_life_time = lifetime
    source2.n = activity_Bq / Bq / sim.number_of_threads * lifetime / sec
    print()
    print("Source2 n = ", source2.n)
    print(f"Source2 HL = {half_life / sec} sec")
    print(f"Source2 LT = {lifetime / sec} sec")
    print()

    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.track_types_flag = True

    # hit actor w1
    ta1 = sim.add_actor("PhaseSpaceActor", "PhaseSpace1")
    ta1.attached_to = "waterbox1"
    ta1.attributes = ["KineticEnergy", "GlobalTime", "PreGlobalTime"]
    f = sim.add_filter("ParticleFilter", "f")
    f.particle = "gamma"
    f.policy = "accept"
    ta1.filters.append(f)
    ta1.output_filename = "test022_half_life_ion1.root"
    ta1.steps_to_store = "first"

    # hit actor w2
    ta2 = sim.add_actor("PhaseSpaceActor", "PhaseSpace2")
    ta2.attached_to = "waterbox2"
    ta2.attributes = ["KineticEnergy", "GlobalTime", "PreGlobalTime"]
    ta2.filters.append(f)
    ta2.output_filename = "test022_half_life_ion2.root"
    ta2.steps_to_store = "first"

    # start simulation
    sim.run()

    # get result
    stats = sim.get_actor("Stats")
    print(stats)

    # tests
    fig, ax = plt.subplots(ncols=2, nrows=1, figsize=(15, 5))
    b1, n1 = test022.test_half_life_fit(sim, ta1.get_output_path(), half_life, ax[0])
    b2, n2 = test022.test_half_life_fit(sim, ta2.get_output_path(), half_life, ax[1])
    fn = paths.output / "test022_half_life_ion_fit.png"
    print("Figure in ", fn)
    plt.savefig(fn)
    is_ok = b1 and b2

    # compare number of gammas
    diff = math.fabs(n1 - n2) / n2
    tol = 0.05
    b = diff < tol
    print()
    utility.print_test(
        b, f"Number of emitted gammas {n1} vs {n2} : {diff*100:.2f} % (tol is {tol})"
    )
    is_ok = is_ok and b

    utility.test_ok(is_ok)
