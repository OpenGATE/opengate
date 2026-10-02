#!/usr/bin/env python3
"""Small-exponent limits and finite initialization, independently evaluated."""

import itk
import numpy as np
import opengate as gate
from opengate_core import opengate_core as g4

from opengate.tests import utility
from test103_AMF_helpers import make_simulation, labels, analytical_power_spectrum


def main():
    """Check finite kernel results and stable small-exponent biological corrections."""
    paths = utility.get_default_test_paths(__file__, output_folder="test103_AMF_numerics")
    sim, actor, _ = make_simulation(paths.output)
    actor.NucleusRadius = 1e9 * gate.g4_units.um
    actor.write_to_disk = False
    calc = g4._AMFCalculator(400, .6, .3, 1e9, .0615, 2, 9)
    calc.load(actor.tsed_file_name)
    _, yd, ys = calc.calculate(6, 12, 100, 10, 1)
    np.testing.assert_allclose(ys, yd, rtol=2e-4)
    # Finite individual inputs must not silently initialize a NaN y0.
    try:
        g4._AMFCalculator(400, .6, .3, 1e200, .0615, 2, 9)
    except RuntimeError as error:
        assert "saturation" in str(error)
    else:
        raise AssertionError("Expected nonfinite saturation parameter rejection")
    sim.run()
    dose = itk.array_from_image(actor.dose.get_data())
    nonzero = dose > 0
    y = labels()
    lam, _ = analytical_power_spectrum()
    weights = y**2 * np.exp(-lam * y)
    weights[np.exp(-lam * y) <= 1e-10] = 0
    # As nucleus radius tends to infinity, the biological correction tends to
    # one, alpha tends to alpha0+beta*zD, and beta tends to betaRef.
    expected_alpha = np.average(.117 + .0615 * .16022 * y / (np.pi * .3**2), weights=weights)
    np.testing.assert_allclose(itk.array_from_image(actor.Alpha_MCFMKM.get_data())[nonzero], expected_alpha, rtol=1e-12)
    np.testing.assert_allclose(itk.array_from_image(actor.Beta_MCFMKM.get_data())[nonzero], .0615, rtol=1e-12)
    np.testing.assert_allclose(itk.array_from_image(actor.DoseAveragedLinealEnergySaturationCorrected.get_data())[nonzero], yd, rtol=2e-4)
    utility.test_ok(True)


if __name__ == "__main__":
    main()
