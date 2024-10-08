#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from opengate.tests.utility import *
from opengate.sources.phidsources import *
from opengate.utility import g4_units
import numpy as np
import math


def create_ion_gamma_simulation(sim, paths, z, a):
    # find ion name and direct daughter
    nuclide, direct_daughters = get_nuclide_and_direct_progeny(z, a)
    ion_name = nuclide.nuclide
    print(f"Ion : {ion_name} ({z} {a})  ->  direct daughters = {direct_daughters}")

    # units
    nm = g4_units.nm
    m = g4_units.m
    mm = g4_units.mm
    Bq = g4_units.Bq
    kBq = 1000 * Bq

    # main options
    ui = sim.user_info
    ui.g4_verbose = False
    ui.g4_verbose_level = 1
    ui.number_of_threads = 1
    ui.visu = False
    ui.random_seed = 123456

    # activity
    activity = 10 * kBq / ui.number_of_threads

    # world size
    world = sim.world
    world.size = [10 * m, 10 * m, 10 * m]
    world.material = "G4_WATER"

    # physics
    sim.physics_list_name = "G4EmStandardPhysics_option4"
    sim.physics_manager.enable_decay = True
    sim.physics_manager.global_production_cuts.all = 10 * mm
    sim.physics_manager.global_production_cuts.gamma = 0.001 * mm
    sim.g4_commands_after_init.append("/process/em/pixeXSmodel ECPSSR_ANSTO")
    sim.g4_commands_before_init.append("/process/em/fluoBearden true")

    # sources
    # ui.running_verbose_level = gate.EVENT
    source = sim.add_source("GenericSource", ion_name)
    source.particle = f"ion {z} {a}"
    source.position.type = "sphere"
    source.position.radius = 1 * nm
    source.position.translation = [0, 0, 0]
    source.direction.type = "iso"
    source.activity = activity

    # add stat actor
    s = sim.add_actor("SimulationStatisticsActor", "stats")
    s.track_types_flag = True
    s.output_filename = paths.output / f"test053_{ion_name}_stats.txt"

    # phsp actor
    phsp = sim.add_actor("PhaseSpaceActor", "phsp")
    phsp.attached_to = "world"
    phsp.attributes = [
        "KineticEnergy",
        "EventID",
        # "EventPosition",
        # "EventKineticEnergy",
        # "EventDirection",
        "TrackID",
        "ParentID",
        "TrackCreatorProcess",
        "TrackCreatorModelIndex",
        "ParticleName",
    ]
    phsp.output_filename = paths.output / f"test053_{ion_name}.root"
    phsp.steps_to_store = "exiting first"
    # phsp.store_absorbed_event = True
    # phsp.debug = True

    return ion_name, direct_daughters


def update_sim_for_tac(sim, ion_name, nuclide, activity, end):
    # change simulation parameters
    phsp = sim.get_actor("phsp")

    def rm_type(name, phsp):
        fg = sim.add_filter("ParticleFilter", f"fp_{name}")
        fg.particle = name
        fg.policy = "reject"
        phsp.filters.append(fg)

    phsp.attributes = ["ParticleName", "ParticleType", "GlobalTime"]
    rm_type("gamma", phsp)
    rm_type("anti_nu_e", phsp)
    rm_type("alpha", phsp)
    rm_type("e-", phsp)

    sec = g4_units.second
    Bq = g4_units.Bq

    source = sim.get_source_user_info(ion_name)

    half_life = nuclide.half_life("s") * sec
    lifetime = half_life / math.log(2.0)
    decay_constant = math.log(2.0) / half_life
    print("Ion half life (sec)", half_life / sec)
    print("Ion lifetime (sec)", lifetime / sec)
    print("Ion decay lambda (in s^-1)", decay_constant)

    source.activity = activity
    source.half_life = half_life

    """
    # should work but much too long !
    source.activity = 0
    source.user_particle_life_time = lifetime
    source.n = int((activity / Bq) * (lifetime / sec))"""

    print("Activity  = ", activity / Bq)
    print("Source n  = ", source.n)
    print("Source ac  = ", source.activity / Bq)
    print(f"Source HL = {half_life / sec} sec")
    print(f"Source HL = {half_life / sec / 3600 / 24} days")
    print(f"Source LT = {lifetime / sec} sec")

    # ui = sim.user_info
    # ui.g4_verbose = True
    # sim.g4_commands_after_init.append("/tracking/verbose 2")
    km = g4_units.km
    sim.physics_manager.global_production_cuts.all = 10 * km
    sim.run_timing_intervals = [[0, end]]


def analyse_ion_gamma_from_root(filename, ion_names, events_nb):
    # open file and tree
    root = uproot.open(filename)
    tree = root[root.keys()[0]]
    print(f"Root tree {root.keys()} n={tree.num_entries}")
    print(f"Keys:{tree.keys()}")

    # loop on data to gather all gammas from RadioactiveDecay
    # and their corresponding parent
    i = 0
    event = -1
    g_by_ion = {}
    track = {}
    for batch in tree.iterate(step_size="50MB"):
        # (one single batch)
        print(f"batch len {len(batch)}")
        for e in batch:
            # update current list of track
            if event != e["EventID"]:
                # print(f'New EVENT {e}')
                track = {}
                event = e["EventID"]
            track[e["TrackID"]] = e
            # print(
            #    f'    current list of track {len(track)} -> {e["EventID"]} parent={e["ParentID"]} track={e["TrackID"]} '
            #    f'{e["ParticleName"]} ')

            # sometimes the parent is not in the root file, because this is the track
            # of the primary ion which decay without step
            if e["ParticleName"] == "gamma":
                # if e["TrackCreatorProcess"] == "RadioactiveDecay": # G4 11.1
                # if e["TrackCreatorProcess"] == "Radioactivation": # G4 11.2
                if e["TrackCreatorModelIndex"] == 130:
                    pid = e["ParentID"]
                    if pid not in track:
                        if pid == 1:
                            # it means, the parent is the initial ion (not in the phsp because no step)
                            continue
                        print()
                        print(e)
                        print("event id", e["EventID"])
                        print(f"track {len(track)}")
                        print(f"track {track}")
                        exit(0)
                    ion = track[e["ParentID"]]["ParticleName"]
                    # ene = e["KineticEnergy"]
                    # if ene < 100 * keV:
                    #    print(f"read {e} {ene/keV} keV {ion}")
                    if ion not in g_by_ion:
                        g_by_ion[ion] = []
                    g_by_ion[ion].append(e)
            i += 1

    print(f"Found {len(g_by_ion)} different gamma lines")

    # filter to keep only the one from the asked ion
    ion_names = [a.replace("-", "") for a in ion_names]
    print(ion_names)
    filtered_g_by_ion = {}
    for g in g_by_ion:
        print(f"{g} : n={len(g_by_ion[g])}")
        for ion_name in ion_names:
            if ion_name in g:
                filtered_g_by_ion[g] = g_by_ion[g]
    print(f"Keep {ion_names} only, found {len(filtered_g_by_ion)} lines")

    # extract all gammas and merge according
    # to a given energy precision
    gammas = []
    for g in filtered_g_by_ion:
        x = filtered_g_by_ion[g]
        for i in x:
            e = i["KineticEnergy"]
            e = round(e, 3)  # FIXME ?
            gammas.append(e)
    print(f"Found n={len(gammas)} different energy gammas, grouped by 1e-3 precision")

    # histogram
    gamma_peaks = {}
    for g in gammas:
        if g in gamma_peaks:
            gamma_peaks[g] += 1
        else:
            gamma_peaks[g] = 1

    # sort
    gamma_peaks = dict(sorted(gamma_peaks.items()))
    gp_ene = np.array([g for g in gamma_peaks])
    gp_w = np.array([g for g in gamma_peaks.values()])
    gp_w = gp_w / events_nb

    # print
    keV = g4_units.keV
    for e, w in zip(gp_ene, gp_w):
        print(f"{e / keV:.4f} keV \t -> {w * 100:.4f} %")

    return gp_ene, gp_w


def analyse(paths, sim, output, ion_name, z, a, daughters, log_flag=True, tol=0.03):
    # print stats
    stats = output.get_actor("stats")
    print(stats)

    # Monte carlo data
    print("Data from MC, normalized by nb events")
    phsp = sim.get_actor("phsp")
    g2_ene, g2_w = analyse_ion_gamma_from_root(
        phsp.get_output_path(), daughters, stats.counts.events
    )

    # direct computation of gammas
    print()
    print(f"Data extracted from the database")
    ge = PhotonIonDecayIsomericTransitionExtractor(
        z, a, verbose=True
    )  ## FIXME change verbose
    ge.extract()
    g1_ene = []
    g1_w = []
    keV = g4_units.keV
    for g in ge.gammas:
        print(
            f"{g.transition_energy / keV:.4f} keV \t-> {g.final_intensity * 100:.4f} % "
        )
        g1_ene.append(g.transition_energy)
        g1_w.append(g.final_intensity)
    g1_ene = np.array(g1_ene)
    g1_w = np.array(g1_w)
    print()

    # save to files
    f_mc = str(paths.output / f"test053_{ion_name}_mc.txt")
    with open(f_mc, "w") as f:
        f.write(f"# gamma intensity for {ion_name} -> {' '.join(daughters)}\n")
        f.write(f"# from Monte Carlo\n")
        for e, w in zip(g2_ene, g2_w):
            f.write(f"{e} {w}\n")

    # save to files
    f_model = str(paths.output / f"test053_{ion_name}_model.txt")
    with open(f_model, "w") as f:
        f.write(f"# gamma intensity for {ion_name} -> {' '.join(daughters)}\n")
        f.write(f"# from model\n")
        for e, w in zip(g1_ene, g1_w):
            f.write(f"{e} {w}\n")

    # plot reference
    f, ax = plt.subplots(1, 1, figsize=(15, 5))
    ax.bar(
        g2_ene,  # "- 2 * keV,
        g2_w,
        width=0.003,
        label=f"Monte Carlo {ion_name} -> {' '.join(daughters)}",
        color="red",
        alpha=0.7,
        log=log_flag,
    )
    # plot model
    ax.bar(
        g1_ene,  # + 2 * keV,
        g1_w,
        width=0.003,
        label=f"Model {ion_name} -> {' '.join(daughters)}",
        color="blue",
        alpha=0.5,
        log=log_flag,
    )
    ax.set_ylabel("Intensity (log)")
    ax.set_xlabel("Energy in keV")  # (slightly offset by +-2 keV for visualisation)")
    if log_flag:
        ax.set_yscale("log")
    ax.legend()

    f = str(paths.output / f"test053_{ion_name}.pdf")
    plt.savefig(f)

    # compare for tests
    is_ok = True
    for e, w in zip(g1_ene, g1_w):
        # only consider weight larger than 0.2%
        if w > 0.002:
            for e2, w2 in zip(g2_ene, g2_w):
                # match energy ?
                if np.fabs(e2 - e) / e < 0.01:
                    d = np.fabs(w2 - w) / w
                    # tol = 0.03
                    if w < 0.02:
                        tol = 0.5
                    ok = d < tol
                    print_test(
                        ok,
                        f"model={e / keV} keV    MC={e2 / keV} keV"
                        f"   {w * 100:.4f}%  {w2 * 100:.4f}%   => {d * 100:.4f}% (tol={tol})",
                    )
                    is_ok = ok and is_ok

    print()
    print(f"Figure in {f}")
    return is_ok


def analyse_time_per_ion_root(sim, end):
    phsp = sim.get_actor("phsp")
    filename = phsp.get_output_path()
    root = uproot.open(filename)
    print(f"Open root file {filename}")
    tree = root[root.keys()[0]]
    print(f"Root tree {root.keys()} n={tree.num_entries}")
    print(f"Keys:{tree.keys()}")

    # group by ion
    sec = g4_units.s
    time_by_ion = {}
    for batch in tree.iterate():
        for e in batch:
            if e["ParticleType"] != "nucleus":
                continue
            n = e["ParticleName"]
            if "[" in n:
                continue
            if n not in time_by_ion:
                time_by_ion[n] = []
            t = e["GlobalTime"] / sec
            if t < end:
                time_by_ion[n].append(t)

    return time_by_ion
