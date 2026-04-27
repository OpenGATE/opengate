#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Apr  2 09:48:30 2025

@author: fava
"""

import opengate as gate
from opengate.utility import g4_units
import opengate.tests.utility as utility
import uproot
import numpy as np
from scipy.spatial.transform import Rotation

if __name__ == "__main__":

    paths = utility.get_default_test_paths(__file__, output_folder="gate_test090")

    # units
    cm = g4_units.cm
    mm = g4_units.mm
    nm = g4_units.nm
    keV = gate.g4_units.keV

    # create simulation object
    sim = gate.Simulation()
    sim.output_dir = paths.output
    sim.g4_verbose = False
    sim.visu = False
    sim.visu_type = "vrml"
    sim.check_volumes_overlap = False
    sim.number_of_threads = 1
    sim.random_seed = 321654
    sim.output_dir = paths.output

    # world
    sim.world.size = [100 * cm, 100 * cm, 100 * cm]
    sim.world.material = "G4_Galactic"

    # virtual plane for phase space
    plane = sim.add_volume("Tubs", "phase_space_plane")
    plane.mother = sim.world
    plane.material = "G4_Galactic"
    plane.rmin = 0
    plane.rmax = 7 * cm
    plane.dz = 1 * nm  # half height
    rot = Rotation.from_rotvec(np.pi / 2 * np.array([0, 1, 0]))
    plane.rotation = rot.as_matrix()
    plane.translation = [
        30 * cm,
        0,
        0,
    ]
    plane.color = [1, 0, 0, 1]  # red

    # waterbox
    waterbox = sim.add_volume("Box", "waterbox")
    waterbox.mother = sim.world
    waterbox.material = "G4_WATER"
    waterbox.size = [2 * cm, 2 * cm, 2 * cm]
    waterbox.translation = [0, 0, 0 * mm]
    waterbox.color = [0, 0, 1, 1]  # blue

    # physics
    sim.physics_manager.physics_list_name = "G4EmLivermorePolarizedPhysics"

    # default source for tests
    source = sim.add_source("GenericSource", "mysource")
    source.particle = "gamma"
    source.energy.type = "gauss"
    source.energy.mono = 100 * keV
    source.position.type = "disc"
    source.position.radius = 1 * mm
    source.position.translation = [0, 0, -30 * cm]
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    source.n = 1e6

    # PhaseSpace Actor to save polarization
    phspa = sim.add_actor("PhaseSpaceActor", "PhaseSpace")
    phspa.attached_to = plane.name
    phspa.attributes = [
        "Polarization",
    ]
    phspa.output_filename = "test091_phsp_actor_no_defined_polarization.root"

    # Run the simulation without user defined polarization
    print("Run the simulation without user defined polarization")
    sim.run(start_new_process=True)

    # The polarization outputs should be random
    root_filename = paths.output / "test091_phsp_actor_no_defined_polarization.root"
    root_file = uproot.open(root_filename)["PhaseSpace"]
    px = root_file["Polarization_X"].array(library="np")
    nb_compton_no_polarization = px.size
    print()

    # Set the polarization to a specific value
    source.polarization = [1, 0, 0]  # linear polarization (horizontal)
    # source.polarization = [-1, 0, 0]  # linear polarization (vertical)
    # source.polarization = [0, 1, 0]  # linear polarization (45°)
    # source.polarization = [0, -1, 0]  # linear polarization (-45°)
    # source.polarization = [0, 0, 1]  # circular polarization (right)
    # source.polarization = [0, 0, -1]  # circular polarization (left)
    # source.polarization = [0, 0, 0]  # unpolarized
    phspa.output_filename = "test091_phsp_actor_with_polarization.root"
    print("Run the simulation with user defined linear polarization")
    sim.run(start_new_process=True)

    # The polarization outputs should be 1, 0, 0
    root_filename = paths.output / "test091_phsp_actor_with_polarization.root"
    root_file = uproot.open(root_filename)["PhaseSpace"]
    px = root_file["Polarization_X"].array(library="np")
    nb_compton_with_polarization = px.size

    # Compute std (poisson distribution)
    std = np.sqrt(nb_compton_no_polarization)
    is_ok = nb_compton_with_polarization < (nb_compton_no_polarization - 5 * std)
    utility.print_test(
        is_ok,
        "Compton detected without polarization: "
        + str(nb_compton_no_polarization)
        + " > "
        + "Compton detected with polarization: "
        + str(nb_compton_with_polarization),
    )
    utility.test_ok(is_ok)
