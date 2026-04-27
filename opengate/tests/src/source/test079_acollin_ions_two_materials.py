#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Context: See test079_acollin_ions_geant4_material.py

Here, the source is between two materials.
In the first simulation, only one of them has the correct energy per ion for acollin.
Thus, the test expect a dirac and a Rayleigh distributions.
In the second simulation, both materials have the correct energy per ion for acollin.
Thus. the test expect a Rayleigh distribution.
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
test_key = "p6"


#########################################################################################
# Main : We use this to launch the test
#########################################################################################
if __name__ == "__main__":
    paths = tu.get_default_test_paths(__file__, output_folder="test079")

    # Define core of the simulation, including physics
    sim = setup_simulation_engine(paths)

    # add a volume that englobe the two objets for the actor
    wb0 = sim.add_volume("Box", "both_obj")
    e = 0.01 * cm
    wb0.size = [e + 50 * cm, e + 100 * cm, e + 50 * cm]
    wb0.material = "G4_AIR"

    # add a bodybox
    wb1 = sim.add_volume("Box", "bodybox")
    wb1.mother = wb0
    wb1.size = [50 * cm, 50 * cm, 50 * cm]
    wb1.translation = [0 * cm, -25.0001 * cm, 0 * cm]
    wb1.material = "Body"

    # add a waterbox
    wb2 = sim.add_volume("Box", "waterbox")
    wb2.mother = wb0
    wb2.size = [50 * cm, 50 * cm, 50 * cm]
    wb2.translation = [0 * cm, 25.0001 * cm, 0 * cm]
    wb2.material = "Water"

    # set the source
    source = sim.add_source("GenericSource", "f18")
    source.particle = "ion 9 18"
    source.energy.mono = 0
    source.activity = 10000 * Bq
    source.direction.type = "iso"

    # add phase actor
    phsp = setup_actor(sim, "phsp", wb0.name)
    phsp.output_filename = paths.output / f"annihilation_photons_{test_key}.root"

    sim.physics_manager.mean_energy_per_ion_pair["Water"] = mean_energy

    # go
    sim.run(start_new_process=True)

    # redo test changing the MeanEnergyPerIonPair
    root_filename1 = phsp.output_filename
    phsp.output_filename = (
        paths.output / f"annihilation_photons_with_mepip_{test_key}.root"
    )

    sim.physics_manager.mean_energy_per_ion_pair["Body"] = mean_energy

    # go
    sim.run()

    # test: no mean energy, should be mostly collinear
    gamma_pairs = read_gamma_pairs(root_filename1, "phsp")
    acollinearity_angles = compute_acollinearity_angles(gamma_pairs)

    plt.hist(
        acollinearity_angles,
        bins=71,
        range=(0, 1.0),
        alpha=0.7,
        color="blue",
        label=f"Only one material with mean energy per Ion par of {mean_energy / eV:.1f} eV ",
    )
    # Significant, like 30%, have angle bigger than 0.8 deg... seems
    # to be due to curr_actor.steps_to_store = "first". Not sure how
    # to make the test more clean...
    ratio_colin = np.sum(np.array(acollinearity_angles) < 0.01) / np.sum(
        np.array(acollinearity_angles) < 0.8
    )
    print(f"Ratio of collinear annihilation pairs: {ratio_colin}")

    # test: with mean energy, acolinearity amplitude should have a Rayleigh distribution
    gamma_pairs = read_gamma_pairs(phsp.output_filename, "phsp")
    acollinearity_angles = compute_acollinearity_angles(gamma_pairs)

    acolin_scale = plot_acolin_case_mepip(mean_energy, acollinearity_angles)

    f = paths.output / f"acollinearity_angles_{test_key}.png"
    plt.savefig(f)
    print(f"Plot was saved in {f}")

    # final
    # No acolin
    is_ok_p1 = np.isclose(ratio_colin, 0.5, atol=0.1)
    # Basic acolin
    is_ok_p2 = np.isclose(acolin_scale * 2.355, 0.5, atol=0.2)

    tu.test_ok(is_ok_p1 and is_ok_p2)
