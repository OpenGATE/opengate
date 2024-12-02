#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import click
from opengate.data.PhotonAttenuationMixture import *
from opengate import g4_units

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option("--mixture", "-m", default="Water", help="Material mixture name")
@click.option("--energy", "-e", default=0.1405, help="Energy in MeV")
@click.option("--verbose", "-v", is_flag=True, default=False, help="Verbose output")
@click.option(
    "--option",
    default=1,
    help="Computation option 1=mass attenuation coefficient of the mixture, μ/ρ in cm²/g"
    "2=mass energy absorption coefficient of the mixture in cm²/g"
    "3=linear attenuation coefficient of the mixture µ = (μ/ρ)×ρ in cm⁻¹",
)
def go(mixture, energy, option, verbose):
    """
    1. Mass Attenuation Coefficient of the Mixture (μ/ρ):
        Definition: Represents the attenuation of a material per unit mass density, typically expressed in cm²/g.
        Usage: It describes the probability of interaction (via processes like photoelectric absorption, Compton scattering, etc.) as radiation passes through a material.
        Dependence: Depends on the photon energy and the composition of the material but is normalized to the material's density.
        Application in Imaging: Useful for understanding how photons interact with a material, independent of its physical density.

    2. Mass Energy Absorption Coefficient of the Mixture:
        Definition: Indicates the fraction of energy transferred from the photon beam to the medium (and ultimately absorbed) per unit mass density, expressed in cm²/g.
        Usage: Relevant to dosimetry, as it reflects energy deposition in tissues or detectors.
        Dependence: Depends on the energy transfer and absorption mechanisms specific to the material's composition.
        Application in Imaging: Not directly used in attenuation correction but is critical in dose calculations.

    3. Linear Attenuation Coefficient of the Mixture (µ):
        Definition: Represents the attenuation of a photon beam per unit path length through a material, typically expressed in cm⁻¹.
        Usage: Combines the material's density and its mass attenuation coefficient: μ=(μ/ρ)×ρ.
        Dependence: Depends on the photon energy and both the density and composition of the material.
        Application in Imaging: Directly used in attenuation correction since it accounts for both the material composition and its physical density.

    """

    [w, El] = ChComposition(mixture)
    if len(w) == 0:
        print(f"Cannot find the mixture {mixture}. ")
        print(f"Known mixtures are: {PropsMix}")
    result = PhotonAttenuationMixture(mixture, energy, option)
    if verbose:
        op = {
            1: "mass attenuation coefficient",
            2: "mass energy absorption coefficient",
            3: "linear attenuation coefficient",
        }
        un = {1: "cm²/g", 2: "cm²/g", 3: "cm⁻¹"}
        print(
            f"{mixture} energy = {energy/g4_units.keV} keV {op[option]} = {result} {un[option]}"
        )
    else:
        print(result)


if __name__ == "__main__":
    go()
