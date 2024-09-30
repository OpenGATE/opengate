#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import opengate.contrib.spect.ge_discovery_nm670 as gate_spect
from opengate.tests import utility

if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, "gate_test028_ge_nm670_spect", output_folder="test028"
    )

    # create the simulation
    sim = gate.Simulation()

    # main options
    sim.g4_verbose = False
    sim.visu = False
    sim.number_of_threads = 1
    sim.check_volumes_overlap = False
    sim.output_dir = paths.output

    # units
    m = gate.g4_units.m
    cm = gate.g4_units.cm
    keV = gate.g4_units.keV
    mm = gate.g4_units.mm
    Bq = gate.g4_units.Bq
    kBq = 1000 * Bq

    # world size
    sim.world.size = [1 * m, 1 * m, 1 * m]
    sim.world.material = "G4_AIR"

    # spect head (debug mode = very small collimator)
    spect, colli, crystal = gate_spect.add_spect_head(sim, "spect", debug=False)
    psd = 6.11 * cm
    spect.translation = [0, 0, -(20 * cm + psd)]

    # waterbox
    waterbox = sim.add_volume("Box", "waterbox")
    waterbox.size = [15 * cm, 15 * cm, 15 * cm]
    waterbox.material = "G4_WATER"
    blue = [0, 1, 1, 1]
    waterbox.color = blue

    # physic list
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option4"
    sim.physics_manager.enable_decay = False

    sim.physics_manager.set_production_cut(
        volume_name="world", particle_name="all", value=10 * mm
    )  # all means proton, electron, positron, gamma

    sim.physics_manager.set_production_cut(
        volume_name="spect",
        particle_name="gamma",
        value=0.1 * mm,
    )
    sim.physics_manager.set_production_cut(
        volume_name="spect",
        particle_name="electron",
        value=0.1 * mm,
    )
    sim.physics_manager.set_production_cut(
        volume_name="spect",
        particle_name="positron",
        value=0.1 * mm,
    )

    # default source for tests
    activity = 100 * kBq
    beam1 = sim.add_source("GenericSource", "beam1")
    beam1.mother = waterbox.name
    beam1.particle = "gamma"
    beam1.energy.mono = 140.5 * keV
    beam1.position.type = "sphere"
    beam1.position.radius = 3 * cm
    beam1.position.translation = [0, 0, 0 * cm]
    beam1.direction.type = "momentum"
    beam1.direction.momentum = [0, 0, -1]
    beam1.activity = activity / sim.number_of_threads

    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.track_types_flag = True

    # start simulation
    sim.run()

    # stat
    gate.exception.warning("Compare stats")
    print(stats)
    print(f"Number of runs was {stats.counts.runs}. Set to 1 before comparison")
    stats.counts.runs = 1  # force to 1
    stats_ref = utility.read_stat_file(paths.gate_output / "stat1.txt")
    is_ok = utility.assert_stats(stats, stats_ref, tolerance=0.02)

    utility.test_ok(is_ok)
