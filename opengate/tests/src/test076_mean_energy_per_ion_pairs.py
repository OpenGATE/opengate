#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from test076_mean_energy_per_ion_pairs_helpers import *
import opengate as gate
import opengate.tests.utility as tu
import matplotlib.pyplot as plt

if __name__ == "__main__":
    paths = tu.get_default_test_paths(__file__, "", "test076")

    # create simulation
    sim = gate.Simulation()

    # main options
    sim.g4_verbose = False
    sim.visu = False
    sim.visu_type = "vrml"
    # sim.random_seed = 1234

    # units
    m = gate.g4_units.m
    cm = gate.g4_units.cm
    mm = gate.g4_units.mm
    eV = gate.g4_units.eV
    MeV = gate.g4_units.MeV
    Bq = gate.g4_units.Bq

    # add a material database
    sim.volume_manager.add_material_database(paths.data / "GateMaterials.db")

    # set the world size
    sim.world.size = [3 * m, 3 * m, 3 * m]
    sim.world.material = "G4_AIR"

    # add a waterbox
    wb = sim.add_volume("Box", "waterbox")
    wb.size = [50 * cm, 50 * cm, 50 * cm]
    wb.material = "G4_WATER"

    # test mat properties
    mat = sim.volume_manager.find_or_build_material(wb.material)
    ionisation = mat.GetIonisation()
    print(
        f"material {wb.material} mean excitation energy is {ionisation.GetMeanExcitationEnergy() / eV} eV"
    )
    print(
        f"material {wb.material} mean energy per ion pair is {ionisation.GetMeanEnergyPerIonPair() / eV} eV"
    )

    # set the physics
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option4"
    sim.physics_manager.set_production_cut("waterbox", "gamma", 10 * mm)
    sim.physics_manager.enable_decay = True

    # set the source
    source = sim.add_source("GenericSource", "f18")
    source.particle = "ion 9 18"
    source.energy.mono = 0
    source.activity = 1000 * Bq
    source.direction.type = "iso"

    # add phase actor
    phsp = sim.add_actor("PhaseSpaceActor", "phsp")
    phsp.mother = wb.name
    phsp.attributes = [
        "EventID",
        "TrackID",
        "PrePosition",
        "PreDirection",
        "PostDirection",
        "ParticleName",
        "TrackCreatorProcess",
        "KineticEnergy",
    ]
    phsp.output = paths.output / "annihilation_photons.root"
    f = sim.add_filter("ParticleFilter", "f")
    f.particle = "gamma"
    phsp.filters.append(f)

    # go
    sim.run(start_new_process=True)

    # redo test changing the MeanEnergyPerIonPair
    root_filename = phsp.output
    phsp.output = paths.output / "annihilation_photons_with_mepip.root"
    ionisation.SetMeanEnergyPerIonPair(5 * eV)
    print(f"set MeanEnergyPerIonPair to {ionisation.GetMeanEnergyPerIonPair() / eV} eV")
    sim.run()

    # test
    print()
    gamma_pairs = read_gamma_pairs(root_filename)
    acollinearity_angles = compute_acollinearity_angles(gamma_pairs)
    median1 = np.median(acollinearity_angles)
    print(
        f"median angle: {median1}  min={np.min(acollinearity_angles)}   max={np.max(acollinearity_angles)}"
    )
    print(f"mean = {np.mean(acollinearity_angles)}")

    plt.hist(acollinearity_angles, bins=50, range=(0, 5), alpha=0.7, color="blue")
    plt.xlabel("Acollinearity Angle (Degrees)")
    plt.ylabel("Counts")
    plt.title("Acollinearity Distribution of Gamma Pairs")
    plt.grid(True)

    # test
    gamma_pairs = read_gamma_pairs(phsp.output)
    acollinearity_angles = compute_acollinearity_angles(gamma_pairs)
    median2 = np.median(acollinearity_angles)
    print(
        f"median angle: {median2} min={np.min(acollinearity_angles)}   max={np.max(acollinearity_angles)}"
    )
    print(f"mean = {np.mean(acollinearity_angles)}")

    plt.hist(acollinearity_angles, bins=50, range=(0, 5), alpha=0.7, color="red")
    f = paths.output / "acollinearity_angles.png"
    plt.savefig(f)
    print(f"Plot in {f}")
    # plt.show()

    # final
    is_ok = median1 < 0.01
    is_ok = median2 > 0.2 and is_ok
    tu.test_ok(is_ok)
