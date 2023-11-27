#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import uproot
import matplotlib.pyplot as plt
import opengate as gate
import opengate.contrib.phantoms.nemaiec as gate_iec
from opengate.tests import utility


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "", output_folder="test058")

    # create the simulation
    sim = gate.Simulation()
    simu_name = "main0_orientation"

    # options
    ui = sim.user_info
    ui.number_of_threads = 1
    ui.visu = False
    ui.visu_type = "vrml"
    ui.check_volumes_overlap = True
    ui.random_seed = 321654

    # units
    m = gate.g4_units.m
    keV = gate.g4_units.keV
    cm = gate.g4_units.cm
    cm3 = gate.g4_units.cm3
    Bq = gate.g4_units.Bq
    BqmL = Bq / cm3

    # world size
    sim.world.size = [0.4 * m, 0.4 * m, 0.4 * m]

    # add IEC phantom
    iec1 = gate_iec.add_iec_phantom(sim, name="iec", check_overlap=True)

    # bg source
    s = gate_iec.add_background_source(sim, "iec", "bg", 100 * BqmL, True)
    s.particle = "gamma"
    s.energy.type = "mono"
    s.energy.mono = 10 * keV

    # spheres source
    sources = gate_iec.add_spheres_sources(
        sim, "iec", "spheres", "all", [100 * BqmL] * 6, True
    )
    for s in sources:
        s.particle = "e-"
        s.energy.type = "mono"
        s.energy.mono = 1 * keV

    # phys
    sim.set_production_cut("world", "all", 100 * m)

    # stats
    sim.add_actor("SimulationStatisticsActor", "stats")

    # phsp
    phsp_bg = sim.add_actor("PhaseSpaceActor", "phsp_bg")
    phsp_bg.attributes = ["EventPosition"]
    phsp_bg.output = paths.output / "iec_bg.root"
    f = sim.add_filter("ParticleFilter", "g")
    f.particle = "gamma"
    phsp_bg.filters.append(f)

    phsp_sph = sim.add_actor("PhaseSpaceActor", "phsp_sph")
    phsp_sph.attributes = ["EventPosition"]
    phsp_sph.output = paths.output / "iec_spheres.root"
    f = sim.add_filter("ParticleFilter", "electron")
    f.particle = "e-"
    phsp_sph.filters.append(f)

    # run
    sim.run()
    output = sim.output

    # end
    stats = output.get_actor("stats")
    print(stats)

    # read root bg
    root = uproot.open(phsp_bg.output)
    tree = root[root.keys()[0]]
    posx = tree["EventPosition_X"].array()
    posy = tree["EventPosition_Y"].array()
    posz = tree["EventPosition_Z"].array()

    # consider only points around the sphere's centers
    # index = (posz > 3.5 * cm) & (posz < 3.9 * cm)
    index = (posz > 2 * cm) & (posz < 3.5 * cm)
    posx = posx[index]
    posy = posy[index]

    f, ax = plt.subplots(1, 1, figsize=(15, 5))
    ax.scatter(posx, posy, s=1)
    plt.gca().set_aspect("equal")

    plt.tight_layout()
    file = paths.output / "test058_bg.pdf"
    plt.savefig(file, bbox_inches="tight", format="pdf")
    print(f"Output plot is {file}")

    # read root sph
    root = uproot.open(phsp_sph.output)
    tree = root[root.keys()[0]]
    posx = tree["EventPosition_X"].array()
    posy = tree["EventPosition_Y"].array()
    posz = tree["EventPosition_Z"].array()

    # consider only points around the sphere's centers
    # index = (posz > 3.5 * cm) & (posz < 3.9 * cm)
    index = (posz > 2 * cm) & (posz < 3.5 * cm)
    posx = posx[index]
    posy = posy[index]

    f, ax = plt.subplots(1, 1, figsize=(15, 5))
    ax.scatter(posx, posy, s=1)
    plt.gca().set_aspect("equal")

    plt.tight_layout()
    file = paths.output / "test058_spheres.pdf"
    plt.savefig(file, bbox_inches="tight", format="pdf")
    print(f"Output plot is {file}")

    # ref root
    ref_root_file = paths.output_ref / "iec_bg.root"
    k = ["EventPosition_X", "EventPosition_Y", "EventPosition_Z"]
    is_ok = utility.compare_root3(
        ref_root_file,
        phsp_bg.output,
        "phsp_bg",
        "phsp_bg",
        k,
        k,
        [0.2] * len(k),
        [1] * len(k),
        [1] * len(k),
        paths.output / "test058_bg.png",
    )

    # ref root
    ref_root_file = paths.output_ref / "iec_spheres.root"
    k = ["EventPosition_X", "EventPosition_Y", "EventPosition_Z"]
    is_ok = (
        utility.compare_root3(
            ref_root_file,
            phsp_sph.output,
            "phsp_sph",
            "phsp_sph",
            k,
            k,
            [1.5] * len(k),
            [1] * len(k),
            [1] * len(k),
            paths.output / "test058_spheres.png",
        )
        and is_ok
    )

    utility.test_ok(is_ok)
