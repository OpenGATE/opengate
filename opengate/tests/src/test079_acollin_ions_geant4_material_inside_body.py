#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Context: In Shibuya et al. 2007 [1], it was shown that acollinearity of annihilation
photons in a human subject follows a double Gaussian distribution with a combined FWHM
of 0.55 deg.
While the double Gaussian distribution currently cannot be reproduced in GATE, setting the MeanEnergyPerIonPair of the material to 6.0 eV results in a 2D Gaussian with a FWHM of 0.55 deg.

Note: Changing the material to "Body" does not change the value of acollinearity
compared to water. Unknown if it is a limitation in the simulation or if it is due to
0.5 deg being obtained in older setup with water at 20 deg vs human that are a little
more warm?

[1] https://iopscience.iop.org/article/10.1088/0031-9155/52/17/010
"""

from test079_acollin_helpers import *
import opengate.tests.utility as tu
import matplotlib.pyplot as plt


#########################################################################################
# Simulations configuration that may be relevant to change
#########################################################################################
# Mean energy of Ion Pair to use. 6.0 eV seems to results in 0.55 deg FWHM
mean_energy = 6.0 * eV
# Key added to output to make sure that multi-threading the tests does not backfire
test_key = "p5"


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

    # set the source
    source = sim.add_source("GenericSource", "f18")
    source.particle = "ion 9 18"
    source.energy.mono = 0
    source.activity = 10000 * Bq
    source.direction.type = "iso"

    # add phase actor
    phsp = setup_actor(sim, "phsp", wb.name)
    phsp.output_filename = (
        paths.output / f"annihilation_photons_with_mepip_{test_key}.root"
    )
    ionisation.SetMeanEnergyPerIonPair(mean_energy)
    print(f"set MeanEnergyPerIonPair to {ionisation.GetMeanEnergyPerIonPair() / eV} eV")

    # go
    sim.run()

    # test: with mean energy, acolinearity amplitude should have a Rayleigh distribution
    gamma_pairs = read_gamma_pairs(phsp.output_filename)
    acollinearity_angles = compute_acollinearity_angles(gamma_pairs)

    acolin_scale = plot_acolin_case_mepip(mean_energy, acollinearity_angles)

    f = paths.output / f"acollinearity_angles_{test_key}.png"
    plt.savefig(f)
    print(f"Plot was saved in {f}")

    # final
    # Basic acolin
    is_ok_p2 = np.isclose(acolin_scale * 2.355, 0.55, atol=0.2)

    tu.test_ok(is_ok_p2)
