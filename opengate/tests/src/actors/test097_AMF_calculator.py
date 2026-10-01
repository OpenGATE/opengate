#!/usr/bin/env python3
"""Independent analytical expectations and coefficient/parser boundaries."""

import math

import numpy as np
from opengate_core import opengate_core as g4
from scipy.integrate import quad
from scipy.special import expit
from scipy.stats import truncnorm

from opengate.tests import utility
from test097_AMF_helpers import write_coefficients, analytical_power_spectrum


def expect_error(call, message):
    try:
        call()
    except (RuntimeError, ValueError, TypeError) as error:
        assert message in str(error), str(error)
    else:
        raise AssertionError(f"Expected failure containing {message}")


def calculator(path, radius=.3):
    result = g4._AMFCalculator(400, 2 * radius, radius, 4.5, .0615, 2, 9)
    result.load(str(path))
    return result


def main():
    paths = utility.get_default_test_paths(__file__, output_folder="test097_AMF_calculator")
    paths.output.mkdir(parents=True, exist_ok=True)
    path = write_coefficients(paths.output / "power.dat")
    calc = calculator(path)
    _, expected = analytical_power_spectrum()
    first, yd, ys = calc.calculate(6, 12, 120, 15, 1)
    np.testing.assert_allclose(yd, expected, rtol=2e-4)
    assert 0 < ys <= yd
    # Weight is applied to every raw accumulator, including zero-weight steps.
    for weight in (0, .25, 3.7):
        spectrum, d, s = calc.calculate(6, 12, 120, 15, weight)
        np.testing.assert_allclose(spectrum, first * weight, rtol=1e-14, atol=0)
        np.testing.assert_allclose([d, s], np.array([yd, ys]) * weight, rtol=1e-14)
    for radius in (.0015, .003, .005, .015, .05, .1, .15, .25, .5):
        current = calculator(path, radius)
        for z, energy in ((1, .025), (2, 1), (6, 10), (18, 999), (18, 10000)):
            spectrum, d, s = current.calculate(z, 40, energy, 5, 1)
            assert np.isfinite(spectrum).all() and math.isfinite(d) and math.isfinite(s)
            np.testing.assert_allclose(d, analytical_power_spectrum(radius)[1], rtol=2e-4)
            np.testing.assert_allclose(spectrum.sum() * np.log(10) / 50, 1, rtol=1e-12)

    # All eight corners differ. The integral of a mixture of exponentials has
    # closed moments k!/lambda**(k+1), independent of the code's bin quadrature.
    rows = []
    for charge in range(6):
        for energy in range(12):
            for diameter in range(8):
                rows.append([0, 0, 0, 0, 0, 0, 1, 2 + .6 * charge + .15 * energy + .3 * diameter, 1000])
    mixture = write_coefficients(paths.output / "mixture.dat", rows)
    radius = np.sqrt(.5) / 2
    mixture_calc = calculator(mixture, radius)
    spectrum, d, s = mixture_calc.calculate(5, 10, np.sqrt(100 * 300), 10, 1)
    terms = []
    for charge, wz in ((1, .25), (2, .75)):
        for energy, we in ((9, .5), (10, .5)):
            for diameter, wc in ((6, .5), (7, .5)):
                a7 = 2 + .6 * charge + .15 * energy + .3 * diameter
                rate = -np.log((a7 - 1) / a7) * (4 * radius / 3)
                terms.append((wz * we * wc / (a7 - 1), rate))
    moment1 = sum(amplitude / rate**2 for amplitude, rate in terms)
    moment2 = sum(2 * amplitude / rate**3 for amplitude, rate in terms)
    np.testing.assert_allclose(d, moment2 / moment1, rtol=2e-4)
    # Independent continuous saturation integral, with water density assumed.
    moment0 = sum(amplitude / rate for amplitude, rate in terms)
    y0 = np.pi * radius * 4.5**2 / (np.sqrt(.0615 * (radius**2 + 4.5**2)) * .16022)
    numerator = sum(amplitude * quad(lambda y: -np.expm1(-(y / y0)**2) * np.exp(-rate * y), 0, np.inf)[0]
                    for amplitude, rate in terms)
    np.testing.assert_allclose(s, y0**2 * numerator / moment1, rtol=2e-3)
    assert moment0 > 0

    # Distorted-normal components reduce to a truncated Gaussian for exponent
    # two. Its continuous first/second moments are available independently.
    mu, sigma = 20 / .4, np.sqrt(20) / .4
    normal = truncnorm(-mu / sigma, np.inf, loc=mu, scale=sigma)
    expected_normal = normal.moment(2) / normal.moment(1)
    for name, row in (("first_zero_dedx", [1, 20, 2, 0, 0, 0, 0, 0, 1000]),
                      ("second", [0, 0, 0, 1, 20, 2, 0, 0, 1000])):
        model = calculator(write_coefficients(paths.output / (name + ".dat"), np.tile(row, (576, 1))))
        _, d, _ = model.calculate(1, 1, 10, 0, 1)
        np.testing.assert_allclose(d, expected_normal, rtol=2e-4)

    # Sato (2023) distorted Fermi term: its moments are independent continuous
    # integrals. Deliberately vary stopping power, kinetic cap and mass.
    fermi = calculator(write_coefficients(paths.output / "fermi.dat",
                                          np.tile([1, 1, 1, 0, 0, 0, 0, 0, 1000], (576, 1))))
    for mass, energy, dedx in ((1, 10, 1), (2, 10, 100), (1, .025, 100), (2, .025, 300)):
        nc = min(dedx * .6, energy * mass * 1000)
        first_moment = quad(lambda x: x**2 * expit(nc - x), 0, nc + 50, points=[nc])[0]
        second_moment = quad(lambda x: x**3 * expit(nc - x), 0, nc + 50, points=[nc])[0]
        _, d, _ = fermi.calculate(1, mass, energy, dedx, 1)
        np.testing.assert_allclose(d, second_moment / first_moment / .4, rtol=2e-3)
    capped_a = fermi.calculate(1, 1, .025, 100, 1)
    capped_b = fermi.calculate(1, 1, .025, 300, 1)
    for a, b in zip(capped_a, capped_b):
        np.testing.assert_allclose(a, b, rtol=1e-14)

    invalid = paths.output / "invalid.dat"
    for text, message in (("", "576"), (path.read_text().splitlines()[0] + "\n", "576"),
                          (path.read_text() + path.read_text().splitlines()[0] + "\n", "576"),
                          ("0 0 0\n", "nine finite"),
                          ("0 0 0 0 0 0 1 2 1000 extra\n", "extra coefficient"),
                          ("0 0 0 0 0 0 nan 2 1000\n", "finite"),
                          ("0 0 0 0 0 0 1 1 1000\n", "invalid distribution"),
                          ("0 0 0 0 0 0 0 2 1000\n", "invalid distribution"),
                          ("0 0 0 0 0 0 1 2 0\n", "invalid distribution")):
        invalid.write_text(text)
        expect_error(lambda: calculator(invalid), message)
    expect_error(lambda: calculator(paths.output / "missing.dat"), "cannot open")
    unloaded = g4._AMFCalculator(400, .6, .3, 4.5, .0615, 2, 9)
    expect_error(lambda: unloaded.calculate(6, 12, 120, 15, 1), "not been loaded")
    for z, mass, energy, dedx, weight in ((0, 12, 10, 2, 1), (19, 12, 10, 2, 1),
                                          (6, 0, 10, 2, 1), (6, 12, .01, 2, 1),
                                          (6, 12, 10, -2, 1), (6, 12, 10, 2, -1)):
        expect_error(lambda: calc.calculate(z, mass, energy, dedx, weight), "invalid particle")
    for radius in (0, .0001, .51, np.nan):
        expect_error(lambda: g4._AMFCalculator(400, 2 * radius, radius, 4.5, .0615, 2, 9), "invalid calculator")
    utility.test_ok(True)


if __name__ == "__main__":
    main()
