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


if __name__ == "__main__":

    paths = utility.get_default_test_paths(__file__, output_folder="gate_test091")

    # units
    cm = g4_units.cm
    mm = g4_units.mm
    nm = g4_units.nm
    MeV = gate.g4_units.MeV

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
    plane.rmax = 300 * mm
    plane.dz = 1 * nm  # half height
    plane.translation = [0, 0, 100 * mm]
    plane.color = [1, 0, 0, 1]  # red

    # tube plane for phase space
    tube = sim.add_volume("Tubs", "phase_space_tube")
    tube.mother = sim.world
    tube.material = "G4_Galactic"
    tube.rmin = 299 * mm
    tube.rmax = 300 * mm
    tube.dz = 10 * cm  # half height
    tube.translation = [0, 0, 0 * mm]
    tube.color = [1, 0, 1, 1]  # blue

    # physics
    sim.physics_manager.physics_list_name = "G4EmLivermorePolarizedPhysics"

    # default source for tests
    source = sim.add_source("GenericSource", "mysource")
    source.particle = "gamma"
    source.energy.type = "gauss"
    source.energy.mono = 1 * MeV
    source.energy.sigma_gauss = 0.5 * MeV
    source.position.type = "disc"
    source.position.radius = 20 * mm
    source.position.translation = [0, 0, 0 * mm]
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    source.n = 1

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
    px = root_file["Polarization_X"].array(library="np")[0]
    py = root_file["Polarization_Y"].array(library="np")[0]
    pz = root_file["Polarization_Z"].array(library="np")[0]
    is_ok = px == 0 and py == 0 and pz == 0
    utility.print_test(
        is_ok, "No Polarization: " + str(px) + ", " + str(py) + ", " + str(pz)
    )
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
    px = root_file["Polarization_X"].array(library="np")[0]
    py = root_file["Polarization_Y"].array(library="np")[0]
    pz = root_file["Polarization_Z"].array(library="np")[0]
    is_ok = is_ok and px == 1 and py == 0 and pz == 0
    utility.print_test(
        is_ok, "Horizontal Polarization: " + str(px) + ", " + str(py) + ", " + str(pz)
    )
    print()

    utility.test_ok(is_ok)
