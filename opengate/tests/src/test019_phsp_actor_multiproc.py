#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
import uproot
import numpy as np


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "", output_folder="test019_multiproc")

    # create the simulation
    sim = gate.Simulation()

    # main options
    sim.output_dir = paths.output
    sim.g4_verbose = False
    sim.visu = False
    sim.visu_type = "vrml"
    sim.check_volumes_overlap = False
    sim.number_of_threads = 1
    sim.random_seed = 321654

    # units
    m = gate.g4_units.m
    mm = gate.g4_units.mm
    nm = gate.g4_units.nm
    Bq = gate.g4_units.Bq
    MeV = gate.g4_units.MeV

    #  adapt world size
    sim.world.size = [1 * m, 1 * m, 1 * m]
    sim.world.material = "G4_AIR"

    # virtual plane for phase space
    plane = sim.add_volume("Tubs", "phase_space_plane")
    plane.mother = sim.world
    plane.material = "G4_AIR"
    plane.rmin = 0
    plane.rmax = 700 * mm
    plane.dz = 1 * nm  # half height
    plane.translation = [0, 0, -100 * mm]
    plane.color = [1, 0, 0, 1]  # red

    # e- source
    source = sim.add_source("GenericSource", "Default")
    source.particle = "gamma"
    source.energy.type = "gauss"
    source.energy.mono = 1 * MeV
    source.energy.sigma_gauss = 0.5 * MeV
    source.position.type = "disc"
    source.position.radius = 20 * mm
    source.position.translation = [0, 0, 0 * mm]
    source.direction.type = "momentum"
    source.n = 66

    # add stat actor
    stats_actor = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats_actor.track_types_flag = True

    # PhaseSpace Actor
    phsp_actor = sim.add_actor("PhaseSpaceActor", "PhaseSpace")
    phsp_actor.attached_to = plane.name
    phsp_actor.attributes = [
        "KineticEnergy",
        "PostPosition",
        "PrePosition",
        "PrePositionLocal",
        "ParticleName",
        "PreDirection",
        "PreDirectionLocal",
        "PostDirection",
        "TimeFromBeginOfEvent",
        "GlobalTime",
        "LocalTime",
        "EventPosition",
        "PDGCode",
        "EventID",
        "RunID"
    ]
    phsp_actor.debug = False

    # run the simulation once with no particle in the phsp
    source.direction.momentum = [0, 0, -1]
    phsp_actor.output_filename = "test019_phsp_actor.root"

    sim.run_timing_intervals = [(i, i+1) for i in range(3)]

    # run
    nb_proc = 3
    sim.output_dir = paths.output / "multiproc"
    sim.run(number_of_sub_processes=nb_proc,
            avoid_write_to_disk_in_subprocess=False,
            clear_output_dir_before_run=True)
    path_phsp_output_single = phsp_actor.get_output_path()

    sim.output_dir = paths.output / "singleproc"
    sim.run(number_of_sub_processes=nb_proc,
            avoid_write_to_disk_in_subprocess=False,
            clear_output_dir_before_run=True)
    path_phsp_output_multi = phsp_actor.get_output_path()


    f_multi = uproot.open(path_phsp_output_multi)
    eventid_multi = np.asarray(f_multi['PhaseSpace;1']['EventID'])
    runid_multi = np.asarray(f_multi['PhaseSpace;1']['RunID'])

    f_single = uproot.open(path_phsp_output_single)
    eventid_single = np.asarray(f_single['PhaseSpace;1']['EventID'])
    runid_single = np.asarray(f_single['PhaseSpace;1']['RunID'])

    assert len(set(eventid_multi)) == len(eventid_multi)
    assert set(runid_multi) == set([i for i in range(len(sim.run_timing_intervals))])
    assert set(eventid_single) == set(eventid_multi)
    assert set(runid_single) == set(runid_multi)
