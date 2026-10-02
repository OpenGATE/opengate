#!/usr/bin/env python3
"""Public AMF scoring, synthetic analytical expectations and file contracts."""

import itk
import numpy as np
import SimpleITK as sitk

from opengate.tests import utility
from test103_AMF_helpers import make_simulation, analytical_power_spectrum, labels


def main():
    """Verify public scoring, analytical expectations and scalar/vector files."""
    paths = utility.get_default_test_paths(__file__, output_folder="test103_AMF")
    sim, actor, reference_dose = make_simulation(paths.output)
    sim.run(start_new_process=True)
    dose = np.asarray(actor.dose.get_data())
    reference = np.asarray(reference_dose.dose.get_data())
    assert dose.sum() > 0
    np.testing.assert_allclose(dose, reference, rtol=1e-12, atol=1e-25)
    scored = dose > 0
    empty = ~scored
    assert empty.any(), "The off-axis voxels must remain empty"
    lam, expected_yd = analytical_power_spectrum()
    yd = np.asarray(actor.DoseAveragedLinealEnergy.get_data())
    # Midpoint integration on 50 logarithmic bins/decade and tail truncation.
    np.testing.assert_allclose(yd[scored], expected_yd, rtol=2e-3)
    ys = np.asarray(actor.DoseAveragedLinealEnergySaturationCorrected.get_data())
    assert np.all((ys[scored] > 0) & (ys[scored] <= yd[scored]))
    spectrum = itk.array_from_image(actor.microdosimetric_spectra.get_data())
    assert spectrum.shape == (3, 1, 3, 400)
    assert spectrum.dtype == np.float64
    # Dose density integrated in ln(y) must equal one, with the legacy bins.
    np.testing.assert_allclose(
        spectrum[scored].sum(axis=-1) * np.log(10) / 50, 1, rtol=1e-12
    )
    # An independent closed form gives the spectral shape and peak at 2/lambda.
    y = labels()
    closed_shape = y**2 * np.exp(-lam * y)
    peak = np.argmax(closed_shape)
    assert np.all(np.argmax(spectrum[scored], axis=-1) == peak)
    # The source truncates component values below 1e-10.
    closed_shape[np.exp(-lam * y) <= 1e-10] = 0
    closed_shape *= (50 / np.log(10)) / closed_shape.sum()
    np.testing.assert_allclose(
        spectrum[scored],
        np.tile(closed_shape, (scored.sum(), 1)),
        rtol=1e-10,
        atol=1e-12,
    )
    # Source-defined MCFMKM coefficients use discrete logarithmic-bin weights.
    # Evaluate their relationships independently from the closed spectrum.
    z_domain = 0.16022 * y / (np.pi * 0.3**2)
    z_nucleus = 0.16022 * y / (np.pi * 4.5**2)
    alpha_y = 0.117 + 0.0615 * z_domain
    exponent = alpha_y * z_nucleus + 0.0615 * z_nucleus**2
    correction = -np.expm1(-exponent) / exponent
    expected_alpha = np.average(alpha_y * correction, weights=closed_shape)
    expected_beta = 0.0615 * np.average(correction, weights=closed_shape) ** 2
    np.testing.assert_allclose(
        np.asarray(actor.Alpha_MCFMKM.get_data())[scored], expected_alpha, rtol=1e-12
    )
    np.testing.assert_allclose(
        np.asarray(actor.Beta_MCFMKM.get_data())[scored], expected_beta, rtol=1e-12
    )
    assert sim.get_actor("stats").counts.events == 8
    assert (
        actor.user_output.dose.merged_data.get_data_item_object(0).number_of_samples
        == 8
    )

    for name in actor.user_output:
        output = actor.interfaces_to_user_output[name]
        image = sitk.ReadImage(str(output.get_output_path()))
        assert image.GetDimension() == 3
        assert image.GetSize() == (3, 1, 3)
        assert image.GetSpacing() == (2, 6, 2)
        np.testing.assert_allclose(image.GetOrigin(), [-2, 0, -2])
        np.testing.assert_allclose(image.GetDirection(), np.eye(3).ravel())
        components = 400 if name == "microdosimetric_spectra" else 1
        assert image.GetNumberOfComponentsPerPixel() == components
        assert "64-bit float" in image.GetPixelIDTypeAsString()
        array = sitk.GetArrayFromImage(image)
        assert np.isfinite(array).all()
        assert np.all(array[empty] == 0)
        np.testing.assert_array_equal(array, itk.array_from_image(output.get_data()))
        header = output.get_output_path().read_text()
        assert "ElementType = MET_DOUBLE" in header
        payload_name = next(
            line.split("=", 1)[1].strip()
            for line in header.splitlines()
            if line.startswith("ElementDataFile")
        )
        payload = output.get_output_path().with_name(payload_name)
        assert payload.stat().st_size == 3 * 1 * 3 * components * 8
    label_file = paths.output / "spectrum_histo_x_labels.txt"
    assert (
        label_file.read_text().splitlines()[0]
        == "#Histogram x-axis labels (lineal energy in keV/um)"
    )
    np.testing.assert_allclose(np.loadtxt(label_file), y, rtol=5e-6)
    assert not (paths.output / "microdosimetric_spectra.dat").exists()
    utility.test_ok(True)


if __name__ == "__main__":
    main()
