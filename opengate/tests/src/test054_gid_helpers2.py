#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from test053_gid_helpers1 import *

paths = gate.get_default_test_paths(__file__, "", output="test054")

sim = gate.Simulation()


def create_sim_test054(sim, sim_name, output=paths.output):
    # units
    m = gate.g4_units("m")
    mm = gate.g4_units("mm")

    # main options
    ui = sim.user_info
    ui.g4_verbose = False
    ui.g4_verbose_level = 1
    ui.number_of_threads = 1
    ui.visu = False
    ui.random_seed = "auto"

    # world size
    world = sim.world
    world.size = [1 * m, 1 * m, 1 * m]
    world.material = "G4_WATER"

    # physics
    p = sim.get_physics_user_info()
    p.physics_list_name = "G4EmStandardPhysics_option4"
    p.enable_decay = True
    sim.set_cut("world", "all", 1e6 * mm)

    # add stat actor
    s = sim.add_actor("SimulationStatisticsActor", "stats")
    s.track_types_flag = True
    s.output = output / f"test054_{sim_name}.txt"

    # phsp actor
    phsp = sim.add_actor("PhaseSpaceActor", "phsp")
    phsp.attributes = [
        "KineticEnergy",
        "GlobalTime",
        "TrackCreatorModelIndex",
        "TrackCreatorModelName",
        "TrackCreatorProcess",
        "ProcessDefinedStep",
    ]
    phsp.output = output / f"test054_{sim_name}.root"
    phsp.debug = False

    f = sim.add_filter("ParticleFilter", "f1")
    f.particle = "gamma"
    phsp.filters.append(f)

    if "ref" in sim_name:
        f = sim.add_filter("TrackCreatorProcessFilter", "f2")
        f.process_name = "RadioactiveDecay"
        # phsp.debug = True
        phsp.filters.append(f)


def add_source_generic(sim, z, a, activity_in_Bq=1000):
    Bq = gate.g4_units("Bq")
    nm = gate.g4_units("nm")
    sec = gate.g4_units("second")
    nuclide, _ = gate.get_nuclide_and_direct_progeny(z, a)

    activity = activity_in_Bq * Bq / sim.user_info.number_of_threads
    s1 = sim.add_source("GenericSource", nuclide.nuclide)
    s1.particle = f"ion {z} {a}"
    s1.position.type = "sphere"
    s1.position.radius = 1 * nm
    s1.position.translation = [0, 0, 0]
    s1.direction.type = "iso"
    s1.activity = activity
    s1.half_life = nuclide.half_life("s") * sec
    print(f"Half Life is {s1.half_life/sec:.2f} sec")

    return s1


def add_source_model(sim, z, a, activity_in_Bq=1000):
    Bq = gate.g4_units("Bq")
    nm = gate.g4_units("nm")
    nuclide, _ = gate.get_nuclide_and_direct_progeny(z, a)

    # sources
    activity = activity_in_Bq * Bq / sim.user_info.number_of_threads
    s1 = sim.add_source("GammaFromIonDecaySource", nuclide.nuclide)
    s1.particle = f"ion {z} {a}"
    s1.position.type = "sphere"
    s1.position.radius = 1 * nm
    s1.position.translation = [0, 0, 0]
    s1.direction.type = "iso"
    s1.activity = activity
    s1.write_to_file = paths.output / f"test054_{nuclide.nuclide}_gamma.json"
    s1.tac_bins = 200
    s1.dump_log = paths.output / f"test054_{nuclide.nuclide}_gamma_log.txt"
    s1.verbose = True

    return s1


def compare_root(sim_name_ref, sim_name, start_time, end_time, model_index=130):
    # read root ref
    f1 = paths.output / f"test054_{sim_name_ref}.root"
    print(f1)
    root_ref = uproot.open(f1)
    tree_ref = root_ref[root_ref.keys()[0]]

    f2 = paths.output / f"test054_{sim_name}.root"
    print(f2)
    root = uproot.open(f2)
    tree = root[root.keys()[0]]

    # get gammas with correct timing
    print("Nb entries", tree_ref.num_entries)
    ref_g = tree_ref.arrays(
        ["KineticEnergy"],
        f"(GlobalTime >= {start_time}) & (GlobalTime <= {end_time}) "
        f"& (TrackCreatorModelIndex == {model_index})",
    )
    """
        TrackCreatorModelIndex
        index=130  model_RDM_IT  RadioactiveDecay
        index=148  model_RDM_AtomicRelaxation  RadioactiveDecay
    """
    print("Nb entries with correct range time", len(ref_g))

    k = "KineticEnergy"
    is_ok = gate.compare_branches_values(ref_g[k], tree[k], k, k, tol=0.015)

    # plot histo
    ref_g = ref_g[k]
    print(f"Nb de gamma", len(ref_g))
    f, ax = plt.subplots(1, 1, figsize=(15, 5))
    ax.hist(ref_g, label=f"Reference root", bins=200, alpha=0.7)

    g = tree.arrays(["KineticEnergy"])["KineticEnergy"]
    ax.hist(g, label=f"Model source", bins=200, alpha=0.5)

    ax.legend()
    # plt.show()
    f = paths.output / f"test054_{sim_name}.png"
    print("Save figure in ", f)
    plt.savefig(f)
    # plt.show()

    return is_ok
