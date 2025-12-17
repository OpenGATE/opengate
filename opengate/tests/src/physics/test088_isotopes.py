#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import uproot
import numpy as np
import opengate.tests.utility as utility


g_cm3 = gate.g4_units.g_cm3
mm = gate.g4_units.mm
cm = gate.g4_units.cm
m = gate.g4_units.m
Bq = gate.g4_units.Bq
MeV = gate.g4_units.MeV
sec = gate.g4_units.second
ns = gate.g4_units.nanosecond
deg = gate.g4_units.degree


def create_simu(material):

    paths = utility.get_default_test_paths(__file__, output_folder="test088")

    sim = gate.Simulation()
    sim.g4_verbose = False
    sim.visu = False
    sim.visu_type = "vrml"
    sim.random_engine = "MersenneTwister"
    sim.random_seed = 1234
    sim.output_dir = paths.output
    sim.number_of_threads = 1

    sim.world.size = [3 * m, 3 * m, 3 * m]
    sim.world.material = "G4_AIR"
    file = paths.data / "GateMaterials_Isotopes.db"
    sim.volume_manager.add_material_database(str(file))

    # waterbox
    waterbox = sim.add_volume("Box", "waterbox")
    waterbox.size = [40 * cm, 40 * cm, 40 * cm]
    waterbox.translation = [0 * cm, 0 * cm, 0 * cm]
    waterbox.material = material
    waterbox.color = [0, 1, 1, 1]

    # physics
    # sim.physics_manager.physics_list_name = "QGSP_BIC"
    sim.physics_manager.physics_list_name = "QGSP_BIC_HP"
    sim.physics_manager.set_production_cut("world", "all", 10 * mm)
    sim.physics_manager.set_production_cut("waterbox", "all", 0.01 * mm)

    # source
    source = sim.add_source("GenericSource", "mysource")
    source.particle = "gamma"
    source.energy.type = "gauss"
    source.energy.mono = 50 * MeV
    source.energy.sigma_gauss = 0.1 * MeV
    source.position.type = "disc"
    source.position.radius = 5 * cm
    source.position.translation = [0, 0, -100 * cm]
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    # source.n = 100000
    source.n = 10000

    # stats
    stats = sim.add_actor("SimulationStatisticsActor", "stats")
    stats.track_types_flag = True
    stats.output_filename = "stats.txt"

    # phase space actor
    phsp = sim.add_actor("PhaseSpaceActor", "PhaseSpace")
    phsp.attached_to = waterbox.name
    phsp.attributes = [
        "KineticEnergy",
    ]
    phsp.output_filename = "ps.root"
    phsp.steps_to_store = "exiting"
    f = sim.add_filter("ParticleFilter", "f")
    f.particle = "neutron"
    phsp.filters.append(f)

    # run
    sim.run(start_new_process=True)

    events = uproot.open(phsp.get_output_path_string())["PhaseSpace;1"]
    ekin = events["KineticEnergy"].array(library="np")

    return np.shape(ekin)[0]


if __name__ == "__main__":
    # Run a simulation without and with isotope
    # The simulation with isotope should output much more detected neutrons
    print("Run the simulation with normal water")
    neutron_water = create_simu("G4_WATER")
    print("Number of detected neutrons: " + str(neutron_water))
    print()
    print("Run the simulation with heavy water")
    neutron_water_h2 = create_simu("Water_H2")
    print("Number of detected neutrons: " + str(neutron_water_h2))
    print()
    print("Run the simulation with Deuterium")
    neutron_deuterium = create_simu("Deuterium")
    print("Number of detected neutrons: " + str(neutron_deuterium))
    print()
    # Run a simulation with a material with frequency < 1
    print("Run the simulation with BrainBNCTB1025mMB")
    neutron_brainBNCTB1025mMB = create_simu("BrainBNCTB1025mMB")
    print("Number of detected neutrons: " + str(neutron_brainBNCTB1025mMB))

    # Compute std (poisson distribution)
    std = np.sqrt(neutron_water)
    is_ok = neutron_water_h2 > (neutron_water + 2 * std)
    utility.print_test(
        is_ok,
        f"neutron_water_h2 {neutron_water_h2} > neutron_water + 2 * std {neutron_water + 2 * std}",
    )
    b = neutron_deuterium > (neutron_water + 2 * std)
    utility.print_test(
        b,
        f"neutron_deuterium {neutron_deuterium} > neutron_water + 2 * std {neutron_water + 2 * std}",
    )
    is_ok = is_ok and b

    utility.test_ok(is_ok)
