#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Context: See test079_acollin_ions_geant4Material.py

Here, the material, Body is not known from Geant4 BUT it is defined in GateMaterials.db,
so one only need to set the mean energy per ion in the physics_manager via its
mean_energy_per_ion_pair property.
"""

from test079_acollin_helpers import *
import opengate.tests.utility as tu
import matplotlib.pyplot as plt


#########################################################################################
# Simulations configuration that may be relevant to change
#########################################################################################
# Mean energy of Ion Pair to use. 5.0 eV should produce the expected 0.5 deg FWHM in PET
# imaging
mean_energy = 5.0 * eV
# Key added to output to make sure that multi-threading the tests does not backfire
test_key = "p3"


#########################################################################################
# Main : We use this to launch the test
#########################################################################################
if __name__ == "__main__":
    paths = tu.get_default_test_paths(__file__, output_folder="test079")

    # Define core of the simulation, including physics
    sim = setup_simulation_engine(paths)

    # add a waterbox
    wb = sim.add_volume("Box", "waterbox")
    wb.size = [50 * cm, 50 * cm, 50 * cm]
    wb.material = "Body"

    # set the source
    source = sim.add_source("GenericSource", "f18")
    source.particle = "ion 9 18"
    source.energy.mono = 0
    source.activity = 10000 * Bq
    source.direction.type = "iso"

    # add phase actor
    phsp = setup_actor(sim, "phsp", wb.name)
    phsp.output_filename = paths.output / f"annihilation_photons_{test_key}.root"

    # go
    sim.run(start_new_process=True)

    # redo test changing the MeanEnergyPerIonPair
    root_filename = phsp.output_filename
    phsp.output_filename = (
        paths.output / f"annihilation_photons_with_mepip_{test_key}.root"
    )

    sim.physics_manager.mean_energy_per_ion_pair["Body"] = mean_energy

    # go
    sim.run()

    # test: no mean energy, should be mostly colinear
    gamma_pairs = read_gamma_pairs(root_filename)
    acollinearity_angles = compute_acollinearity_angles(gamma_pairs)

    colin_median = plot_colin_case(acollinearity_angles)

    # test: with mean energy, acolinearity amplitude should have a Rayleigh distribution
    gamma_pairs = read_gamma_pairs(phsp.output_filename)
    acollinearity_angles = compute_acollinearity_angles(gamma_pairs)

    acolin_scale = plot_acolin_case(mean_energy, acollinearity_angles)

    f = paths.output / f"acollinearity_angles_{test_key}.png"
    plt.savefig(f)
    print(f"Plot was saved in {f}")

    # final
    # No acolin
    is_ok_p1 = colin_median < 0.01
    # Basic acolin
    is_ok_p2 = np.isclose(acolin_scale * 2.355, 0.5, atol=0.2)

    tu.test_ok(is_ok_p1 and is_ok_p2)
