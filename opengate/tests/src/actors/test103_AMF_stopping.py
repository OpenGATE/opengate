#!/usr/bin/env python3
"""Synthetic regression for stopping power on an absorbed energetic proton.

The arbitrary Fermi-only coefficients deliberately distinguish positive
stopping power from the zero-stopping fallback. No physical reference data
are loaded or copied into this test.
"""

import itk
import numpy as np
import opengate as gate
from opengate.actors.filters import GateFilterBuilder
from opengate.tests import utility
from test103_AMF_helpers import make_simulation


def main():
    """Guard mean-energy stopping lookup for energetic ions absorbed in one step."""
    paths = utility.get_default_test_paths(
        __file__, output_folder="test103_AMF_stopping"
    )
    sim, actor, reference = make_simulation(paths.output, energy=200)
    # Arbitrary simple binary fractions; this is a mathematical fixture.
    coefficients = paths.output / "fermi_stopping.dat"
    np.savetxt(coefficients, np.tile([0.5, 0.5, 0.0625, 0, 1, 2, 0, 2, 32], (576, 1)))
    actor.tsed_file_name = str(coefficients)
    sim.world.size = [1200, 1200, 1200]
    water = sim.volume_manager.get_volume("water")
    water.size = [80, 80, 400]
    actor.size = [1, 1, 1]
    actor.spacing = [80, 80, 400]
    reference.size = actor.size
    reference.spacing = actor.spacing
    beam = sim.source_manager.get_source("beam")
    beam.position.translation = [0, 0, -199.999]
    beam.number_of_primaries = 256
    sim.physics_manager.physics_list_name = "QGSP_BIC_EMZ"
    sim.physics_manager.set_max_step_size("water", 2)
    sim.physics_manager.user_limits_particles = "all"
    F = GateFilterBuilder()
    actor.filter = (
        (F.ParticleName == "proton")
        & (F.PostKineticEnergy == 0.0)
        & (F.PreKineticEnergy > 100 * gate.g4_units.MeV)
    )
    actor.write_to_disk = False
    sim.run()
    dose = itk.array_from_image(actor.dose.get_data())
    spectrum = itk.array_from_image(actor.microdosimetric_spectra.get_data()).reshape(
        400
    )
    yd = itk.array_from_image(actor.DoseAveragedLinealEnergy.get_data())
    labels = np.asarray(actor.GetHistogramLabels())
    assert dose.sum() > 0, "Must select energetic proton absorption steps"
    np.testing.assert_allclose(spectrum.sum() * np.log(10) / 50, 1, rtol=1e-12)
    # A positive proton stopping power produces the short Fermi distribution.
    # Evaluating it at zero post-step energy incorrectly selects a broad fallback.
    assert 0 < yd.item() < 10, f"Unphysical zero-stopping fallback: yD={yd.item()}"
    assert spectrum[labels > 100].sum() * np.log(10) / 50 < 1e-12
    print(f"Synthetic absorption-step yD: {yd.item():.12g} keV/um")
    utility.test_ok(True)


if __name__ == "__main__":
    main()
