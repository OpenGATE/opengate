#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
import uproot
import numpy as np
from scipy.spatial.transform import Rotation

def validation_test(arr_data,nb_part):
    nb_detected_gamma = len(arr_data)
    err_nb_detected_gamma = np.sqrt(len(arr_data))
    theoretical_number_of_gamma = nb_part * (2*np.pi * (1 - np.cos(np.pi/4)))/(4*np.pi)
    print("Number of detected particles: {} +/- {} ".format(nb_detected_gamma,np.round(err_nb_detected_gamma)))
    print("Theoretical number of detected particles: {}".format(np.round(theoretical_number_of_gamma)))
    if nb_detected_gamma - 4 * err_nb_detected_gamma < theoretical_number_of_gamma < nb_detected_gamma + 4 * err_nb_detected_gamma:
        return True
    return False

if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, "gate_test095_kill_according_crossed_material", output_folder="kill_according_crossed_material"
    )

    # create the simulation
    sim = gate.Simulation()

    # main options
    sim.g4_verbose = False
    sim.g4_verbose_level = 1
    # sim.visu = True
    sim.number_of_threads = 1
    sim.output_dir = paths.output

    # useful units
    MeV = gate.g4_units.MeV
    keV = gate.g4_units.keV
    Bq = gate.g4_units.Bq
    deg = gate.g4_units.deg
    mm = gate.g4_units.mm
    nm = gate.g4_units.nm
    m = gate.g4_units.m
    cm = gate.g4_units.cm

    # set the world size like in the Gate macro
    world = sim.world
    world.size = [2 * m, 2 * m, 2 * m]
    world.material = "G4_Galactic"
    # add a simple volume
    #Volume 1


    cyl = sim.add_volume("Tubs", "cyl")
    cyl.rmin = 0
    cyl.rmax = 40*cm
    cyl.dz = 1 * nm
    cyl.material = "G4_AIR"

    d_cyl = sim.add_volume("Tubs", "d_cyl")
    d_cyl.rmin = 10*cm
    d_cyl.rmax = 40*cm
    d_cyl.dz = 1 * nm
    d_cyl.material = "G4_Galactic"
    d_cyl.mother = cyl.name



    # test sources
    source = sim.add_source("GenericSource", "source1")
    source.particle = "gamma"
    source.n= 100000
    source.position.type = "sphere"
    source.position.radius = 1 * nm
    source.position.translation = [0,0,10*cm]
    source.direction.type = "iso"
    source.energy.type = "mono"
    source.energy.mono = 1 * MeV


    # actors

    kill_if_no_galactic = sim.add_actor("KillParticlesNotCrossingMaterialsActor","kill_by_mat_actor")
    kill_if_no_galactic.material_sparing_particles = ["G4_AIR"]
    kill_if_no_galactic.attached_to = cyl.name

    phsp_plan = sim.add_volume("Box","plan")
    phsp_plan.size = [40*cm,40*cm,1*nm]
    phsp_plan.translation = [0,0,-10 *cm]
    phsp_actor = sim.add_actor("PhaseSpaceActor","phsp")
    phsp_actor.attached_to = phsp_plan.name
    phsp_actor.attributes = [
        "EventID",
    ]

    phsp_actor.output_filename = "test095_output.root"
    print(phsp_actor.output_filename)
    stats_actor = sim.add_actor("SimulationStatisticsActor", "Stats")




    # start simulation
    sim.run()

    f_data = uproot.open(paths.output / "test095_output.root")
    arr_data = f_data["phsp"].arrays()
    # #
    is_ok = validation_test(arr_data,source.n)
    utility.test_ok(is_ok)
