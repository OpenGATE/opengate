#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
import pathlib
import os

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, output_folder="test010_confine")

    # create the simulation
    sim = gate.Simulation()

    # main options
    sim.g4_verbose = False
    sim.g4_verbose_level = 1
    sim.visu = False
    sim.number_of_threads = 1
    sim.output_dir = paths.output

    # some units
    mm = gate.g4_units.mm
    cm = gate.g4_units.cm
    m = gate.g4_units.m
    deg = gate.g4_units.deg
    MeV = gate.g4_units.MeV
    keV = gate.g4_units.keV
    Bq = gate.g4_units.Bq

    # set the world size like in the Gate macro
    sim.world.size = [1 * m, 1 * m, 1 * m]

    # add a simple volume
    waterbox = sim.add_volume("Box", "waterbox")
    waterbox.size = [40 * cm, 40 * cm, 40 * cm]
    waterbox.translation = [0 * cm, 0 * cm, 0 * cm]
    waterbox.material = "G4_WATER"

    # volume where to confine
    stuff = sim.add_volume("Cons", "stuff")
    stuff.mother = "waterbox"
    stuff.rmin1 = 0
    stuff.rmax1 = 0.5 * cm
    stuff.rmin2 = 0
    stuff.rmax2 = 0.5 * cm
    stuff.dz = 2 * cm
    stuff.dphi = 360 * deg
    stuff.translation = [-5 * cm, 0 * cm, 0 * cm]
    stuff.material = "G4_WATER"

    # daughter volume
    stuffi = sim.add_volume("Cons", "stuff_inside")
    stuffi.mother = stuff.name
    stuffi.rmin1 = 0
    stuffi.rmax1 = 0.4 * cm
    stuffi.rmin2 = 0
    stuffi.rmax2 = 0.4 * cm
    stuffi.dz = 2 * cm
    stuffi.dphi = 360 * deg
    stuffi.translation = [-0.1 * cm, 0 * cm, 0 * cm]
    stuffi.material = "G4_AIR"

    # activity
    activity = 500000 * Bq
    # activity = 50 * Bq

    # test confined source
    source = sim.add_source("GenericSource", "non_confined_src")
    source.mother = "stuff"
    source.particle = "gamma"
    source.activity = activity / sim.number_of_threads
    source.position.type = "box"
    source.position.size = [5 * cm, 5 * cm, 5 * cm]
    source.direction.type = "momentum"
    source.direction.momentum = [-1, 0, 0]
    source.energy.type = "mono"
    source.energy.mono = 1 * MeV

    # test confined source
    """
       the source is confined in the given volume ('stuff'), it means that
       all particles will be emitted only in this volume.
       The 'box' type is required to define a larger volume than 'stuff'.
       It is done here by computing the bounding box
       Daughter volumes of 'stuff' do not count : no particle will be generated
       from 'stuff_inside'
    """
    source = sim.add_source("GenericSource", "confined_src")
    source.mother = "stuff"
    source.particle = "gamma"
    source.activity = activity / sim.number_of_threads
    source.position.type = "box"
    source.position.size = sim.volume_manager.volumes[source.mother].bounding_box_size
    print("Source size", source.position.size)
    pMin, pMax = sim.volume_manager.volumes[source.mother].bounding_limits
    source.position.confine = "stuff"
    source.direction.type = "momentum"
    source.direction.momentum = [1, 0, 0]
    source.energy.type = "mono"
    source.energy.mono = 1 * MeV

    # actors
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")

    dose_actor = sim.add_actor("DoseActor", "dose_actor")
    dose_actor.output_filename = "test010-2.mhd"
    # dose_actor.output_filename = paths.output_ref / 'test010-2-edep.mhd'
    dose_actor.attached_to = waterbox
    dose_actor.size = [100, 100, 100]
    dose_actor.spacing = [2 * mm, 1 * mm, 1 * mm]

    # start simulation
    sim.run()

    # print
    print("Simulation seed:", sim.current_random_seed)

    # get results
    print(stats)

    # tests
    stats_ref = utility.read_stat_file(paths.output_ref / "test010_confine_stats.txt")
    is_ok = utility.assert_stats(stats, stats_ref, 0.10)
    is_ok = is_ok and utility.assert_images(
        paths.output_ref / "test010-2-edep.mhd",
        dose_actor.edep.get_output_path(),
        stats,
        tolerance=59,
    )

    utility.test_ok(is_ok)
