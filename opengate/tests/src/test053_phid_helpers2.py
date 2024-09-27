#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from test053_phid_helpers1 import *

paths = get_default_test_paths(__file__, "", output_folder="test053")


def create_sim_test053(sim, sim_name, output=paths.output):
    # units
    m = g4_units.m
    mm = g4_units.mm

    # main options
    ui = sim.user_info
    ui.g4_verbose = False
    ui.g4_verbose_level = 1
    ui.number_of_threads = 1
    ui.visu = False
    ui.random_seed = 123654

    # world size
    world = sim.world
    world.size = [10 * m, 10 * m, 10 * m]
    world.material = "G4_WATER"

    # physics
    sim.physics_list_name = "QGSP_BERT_EMZ"
    sim.physics_manager.enable_decay = True
    sim.physics_manager.global_production_cuts.all = 1e6 * mm
    sim.g4_commands_after_init.append("/process/em/pixeXSmodel ECPSSR_ANSTO")
    sim.g4_commands_before_init.append("/process/em/fluoBearden true")

    # add stat actor
    s = sim.add_actor("SimulationStatisticsActor", "stats")
    s.track_types_flag = True
    s.output_filename = output / f"test053_{sim_name}.txt"

    # phsp actor
    phsp = sim.add_actor("PhaseSpaceActor", "phsp")
    phsp.attributes = [
        "KineticEnergy",
        "TrackVertexKineticEnergy",
        "GlobalTime",
        "TrackCreatorModelIndex",
        "TrackCreatorModelName",
        "TrackCreatorProcess",
        "ProcessDefinedStep",
    ]
    phsp.output_filename = output / f"test053_{sim_name}.root"
    phsp.debug = False
    phsp.steps_to_store = "exiting first"

    f = sim.add_filter("ParticleFilter", "f1")
    f.particle = "gamma"
    phsp.filters.append(f)

    if "ref" in sim_name:
        f = sim.add_filter("TrackCreatorProcessFilter", "f2")
        # f.process_name = "RadioactiveDecay" # G4 11.1
        f.process_name = "Radioactivation"  # G4 11.2
        # phsp.debug = True
        phsp.filters.append(f)


def add_source_generic(sim, z, a, activity_in_Bq=1000):
    Bq = g4_units.Bq
    nm = g4_units.nm
    sec = g4_units.second
    nuclide, _ = get_nuclide_and_direct_progeny(z, a)

    activity = activity_in_Bq * Bq / sim.user_info.number_of_threads
    s1 = sim.add_source("GenericSource", nuclide.nuclide)
    s1.particle = f"ion {z} {a}"
    s1.position.type = "sphere"
    s1.position.radius = 1 * nm
    s1.position.translation = [0, 0, 0]
    s1.direction.type = "iso"
    s1.activity = activity
    s1.half_life = nuclide.half_life("s") * sec
    print(f"Half Life is {s1.half_life / sec:.2f} sec")

    return s1


def add_source_model(sim, z, a, activity_in_Bq=1000):
    Bq = g4_units.Bq
    nm = g4_units.nm
    nuclide, _ = get_nuclide_and_direct_progeny(z, a)

    # sources
    activity = activity_in_Bq * Bq / sim.user_info.number_of_threads
    s1 = sim.add_source("PhotonFromIonDecaySource", nuclide.nuclide)
    s1.particle = f"ion {z} {a}"
    s1.position.type = "sphere"
    s1.position.radius = 1 * nm
    s1.position.translation = [0, 0, 0]
    s1.direction.type = "iso"
    s1.activity = activity
    s1.tac_bins = 200
    s1.dump_log = paths.output / f"test053_{nuclide.nuclide}_gamma_log.txt"
    s1.verbose = True

    return s1


def compare_root_energy(
    root_ref, root_model, start_time, end_time, model_index=130, tol=0.008, erange=None
):
    # read root ref
    print(root_ref)
    root_ref = uproot.open(root_ref)
    tree_ref = root_ref[root_ref.keys()[0]]

    print(root_model)
    root = uproot.open(root_model)
    tree = root[root.keys()[0]]

    # get gammas with correct timing
    print("Nb entries", tree_ref.num_entries)
    keV = g4_units.keV
    s = ""
    if erange is not None:
        s = f"(KineticEnergy >= {erange[0] * keV}) & (KineticEnergy <= {erange[1] * keV}) & "
    if model_index != -1:
        ref_g = tree_ref.arrays(
            ["KineticEnergy"],
            f"{s}(GlobalTime >= {start_time}) & (GlobalTime <= {end_time}) "
            f"& (TrackCreatorModelIndex == {model_index})",
        )
    else:
        ref_g = tree_ref.arrays(
            ["KineticEnergy"],
            f"{s}(GlobalTime >= {start_time}) & (GlobalTime <= {end_time}) ",
        )
    """
        TrackCreatorModelIndex
        index=130  model_RDM_IT                RadioactiveDecay
        index=148  model_RDM_AtomicRelaxation  RadioactiveDecay
    """
    print("Nb entries with correct range time", len(ref_g))

    k = "KineticEnergy"
    is_ok = compare_branches_values(ref_g[k], tree[k], k, k, tol=tol)

    # plot histo
    keV = g4_units.keV
    ref_g = ref_g[k] / keV
    print(f"Nb de gamma", len(ref_g))
    f, ax = plt.subplots(1, 1, figsize=(15, 5))
    ax.hist(ref_g, label=f"Reference root", bins=200, alpha=0.7, range=erange)

    g = tree.arrays(["KineticEnergy"])["KineticEnergy"] / keV
    ax.hist(g, label=f"Model source", bins=200, alpha=0.5, range=erange)

    ax.set_xlabel("Energy in keV")
    ax.set_ylabel("Counts")

    ax.legend()
    f = str(root_model).replace(".root", ".png")
    print("Save figure in ", f)
    plt.savefig(f)

    return is_ok
