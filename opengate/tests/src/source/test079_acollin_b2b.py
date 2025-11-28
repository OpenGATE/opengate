#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Context: By default, simulation of BTB source does not result in the expected acolin. of
PET imaging. To enable this, one need to activate it. The test is in three parts:
1) If nothing is done, more annihilations should be colinear
2) If acolinearity is activated, the amplitude of acolinearity should follow a Rayleight
distribution with a scale of 0.21 deg., which corresponds to the acolin deviation
following a 2D Gaussian with a FWHM of 0.5 deg.
3) Same as previous, except that the acolinearity FWHM is setted as 0.55 deg FWHM.
"""

from test079_acollin_helpers import *
import opengate.tests.utility as tu
import matplotlib.pyplot as plt


#########################################################################################
# Simulations configuration that may be relevant to change
#######################################################################################
# Key added to output to make sure that multi-threading the tests does not backfire
test_key = "p7"
# The number of events simulated to validate the distribution of acolineaity in each
# cases.
number_Events = 10000
default_accolinearity = 0.5 * deg
# Default acolin. FWHM is 0.5 deg, so here we also test with another value.
custom_acolin_FWHM = 0.55 * deg


def create_sim(output_filename, accolinearity_flag=None, accolinearity_fwhm=None):
    paths = tu.get_default_test_paths(__file__, output_folder="test079")

    # Define core of the simulation, including physics
    sim = gate.Simulation()
    # main options
    sim.g4_verbose = False
    sim.visu = False
    sim.random_seed = 12345654
    sim.progress_bar = True
    # set the world size
    sim.world.size = [3 * m, 3 * m, 3 * m]
    sim.world.material = "G4_AIR"

    # set the source
    source = sim.add_source("GenericSource", "b2b")
    source.particle = "back_to_back"
    source.n = number_Events
    source.position.type = "sphere"
    source.position.radius = 5 * mm
    source.direction.type = "iso"
    if accolinearity_flag:
        source.direction.accolinearity_flag = accolinearity_flag
    if accolinearity_fwhm:
        source.direction.accolinearity_fwhm = accolinearity_fwhm

    print("accolinearity")
    print(f"accolinearity_flag = {source.direction.accolinearity_flag}")
    print(
        f"accolinearity_fwhm = {source.direction.accolinearity_fwhm/gate.g4_units.deg} deg"
    )

    # add a waterbox
    wb = sim.add_volume("Box", "waterbox")
    wb.size = [5 * cm, 5 * cm, 5 * cm]
    wb.material = "G4_WATER"

    # add phase actor
    phsp = setup_actor(sim, "phsp", wb.name)
    phsp.output_filename = output_filename

    return sim


#########################################################################################
# Main : We use this to launch the test
#########################################################################################
if __name__ == "__main__":
    paths = tu.get_default_test_paths(__file__, output_folder="test079")

    root_filename_no_acolin = paths.output / f"annihilation_photons_{test_key}.root"
    sim = create_sim(root_filename_no_acolin)
    sim.run(start_new_process=True)

    # # Now, activate acolin.
    root_filename_default_acolin = (
        paths.output / f"annihilation_photons_with_acolin_{test_key}.root"
    )
    sim = create_sim(root_filename_default_acolin, True)
    sim.run(start_new_process=True)

    # # Now, custom acolin case
    root_filename_custom_acolin = (
        paths.output / f"annihilation_photons_with_acolin_55_{test_key}.root"
    )
    sim = create_sim(root_filename_custom_acolin, True, custom_acolin_FWHM)
    sim.run(start_new_process=True)

    # test: without acolinearity, should be mostly colinear
    gamma_pairs = read_gamma_pairs(root_filename_no_acolin, is_btb=True)
    # print(gamma_pairs)
    acollinearity_angles = compute_acollinearity_angles(gamma_pairs)
    colin_median = plot_colin_case(acollinearity_angles)

    # test: with acolinearity, its amplitude should have a Rayleigh distribution
    gamma_pairs = read_gamma_pairs(root_filename_default_acolin, is_btb=True)
    acollinearity_angles = compute_acollinearity_angles(gamma_pairs)
    acolin_scale_default = plot_acolin_case_angle(
        default_accolinearity, acollinearity_angles
    )

    # test: with acolinearity, its amplitude should have a Rayleigh distribution
    gamma_pairs = read_gamma_pairs(root_filename_custom_acolin, is_btb=True)
    acollinearity_angles = compute_acollinearity_angles(gamma_pairs)
    acolin_scale_custom = plot_acolin_case_angle(
        custom_acolin_FWHM, acollinearity_angles, is_second=True
    )

    f = paths.output / f"acollinearity_angles_{test_key}.png"
    plt.savefig(f)
    print(f"Plot was saved in {f}")

    # final
    # No acolin
    is_ok_p1 = colin_median < 0.01
    # Basic acolin
    is_ok_p2 = np.isclose(
        acolin_scale_default * 2.355, default_accolinearity / deg, atol=0.02
    )
    print(acolin_scale_default, is_ok_p2)
    # Custom acolin
    is_ok_p3 = np.isclose(
        acolin_scale_custom * 2.355, custom_acolin_FWHM / deg, atol=0.02
    )

    tu.test_ok(is_ok_p1 and is_ok_p2 and is_ok_p3)
