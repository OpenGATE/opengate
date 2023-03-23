#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import uproot
import numpy as np
import opengate as gate
import matplotlib.pyplot as plt


def create_ion_gamma_simulation(sim, paths, z, a):
    # find ion name and direct daughter
    ion_name, daughters = gate.get_nuclide_name_and_direct_progeny(z, a)
    print(f"Ion : {ion_name} ({z} {a})  ->  direct daughters = {daughters}")

    # units
    nm = gate.g4_units("nm")
    m = gate.g4_units("m")
    mm = gate.g4_units("mm")
    Bq = gate.g4_units("Bq")
    kBq = 1000 * Bq
    keV = gate.g4_units("keV")

    # main options
    ui = sim.user_info
    ui.g4_verbose = False
    ui.g4_verbose_level = 1
    ui.number_of_threads = 1
    ui.visu = False
    ui.random_seed = "auto"

    # activity
    activity = 10 * kBq / ui.number_of_threads

    # world size
    world = sim.world
    world.size = [10 * m, 10 * m, 10 * m]
    world.material = "G4_WATER"

    # physics
    p = sim.get_physics_user_info()
    p.physics_list_name = "G4EmStandardPhysics_option4"
    p.enable_decay = True
    sim.set_cut("world", "all", 10 * mm)
    sim.set_cut("world", "gamma", 0.001 * mm)

    # sources
    # ui.running_verbose_level = gate.EVENT
    source = sim.add_source("GenericSource", ion_name)
    source.particle = f"ion {z} {a}"
    source.position.type = "sphere"
    source.position.radius = 1 * nm
    source.position.translation = [0, 0, 0]
    source.direction.type = "iso"
    # IMPORTANT : if energy is zero, there is no step for the ion,
    # and the phsp does not contain any initial ion
    source.energy.mono = 0.001 * keV
    source.activity = activity

    # add stat actor
    s = sim.add_actor("SimulationStatisticsActor", "stats")
    s.track_types_flag = True
    s.output = paths.output / f"test053_{ion_name}_stats.txt"

    # phsp actor
    phsp = sim.add_actor("PhaseSpaceActor", "phsp")
    phsp.mother = "world"
    phsp.attributes = [
        "KineticEnergy",
        "EventID",
        "TrackID",
        "ParentID",
        "TrackCreatorProcess",
        "ParticleName",
    ]
    phsp.output = paths.output / f"test053_{ion_name}.root"

    return ion_name, daughters


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
    for batch in tree.iterate():
        for e in batch:
            # update current list of track
            if event != e["EventID"]:
                # print(i, len(track))
                track = {}
                event = e["EventID"]
            track[e["TrackID"]] = e
            if e["ParticleName"] == "gamma":
                if e["TrackCreatorProcess"] == "RadioactiveDecay":
                    ion = track[e["ParentID"]]["ParticleName"]
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
    keV = gate.g4_units("keV")
    for e, w in zip(gp_ene, gp_w):
        print(f"{e/keV:.4f} keV \t -> {w*100:.4f} %")

    return gp_ene, gp_w


def analyse(paths, sim, output, ion_name, z, a, daughters):
    # print stats
    stats = output.get_actor("stats")
    print(stats)

    # Monte carlo data
    print("Data from MC, normalized by nb events")
    phsp = sim.get_actor_user_info("phsp")
    g2_ene, g2_w = analyse_ion_gamma_from_root(
        phsp.output, daughters, stats.counts.event_count
    )

    # direct computation of gammas
    print()
    print(f"Data extracted from the database")
    ge = gate.GammaFromIonDecayExtractor(z, a, verbose=False)
    ge.extract()
    g1_ene = []
    g1_w = []
    keV = gate.g4_units("keV")
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

    f_model = str(paths.output / f"test053_{ion_name}_model.txt")
    with open(f_model, "w") as f:
        f.write(f"# gamma intensity for {ion_name} -> {' '.join(daughters)}\n")
        f.write(f"# from model\n")
        for e, w in zip(g1_ene, g1_w):
            f.write(f"{e} {w}\n")

    f, ax = plt.subplots(1, 1, figsize=(15, 5))
    ax.bar(
        g2_ene - 2 * keV,
        g2_w,
        width=0.003,
        label=f"Monte Carlo {ion_name} -> {' '.join(daughters)}",
        color="red",
        log=1,
    )
    ax.bar(
        g1_ene + 2 * keV,
        g1_w,
        width=0.003,
        label=f"Model {ion_name} -> {' '.join(daughters)}",
        color="blue",
        log=1,
    )
    ax.set_ylabel("Intensity (log)")
    ax.set_xlabel("Energy in keV (slightly offset by +-2 keV for visualisation)")
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
                    tol = 0.15
                    if w < 0.02:
                        tol = 0.5
                    ok = d < tol
                    gate.print_test(
                        ok,
                        f"model={e/keV} keV    MC={e2/keV} keV"
                        f"   {w*100:.4f}%  {w2*100:.4f}%   => {d*100:.4f}% (tol={tol})",
                    )
                    is_ok = ok and is_ok

    print()
    print(f"Figure in {f}")
    return is_ok
