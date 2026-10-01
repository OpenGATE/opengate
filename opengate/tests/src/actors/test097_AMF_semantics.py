#!/usr/bin/env python3
"""Particle applicability, weighting, hit position, coordinates and write controls."""

import itk
import numpy as np
import SimpleITK as sitk
from scipy.spatial.transform import Rotation

from opengate.tests import utility
from test097_AMF_helpers import make_simulation


def values(output):
    return itk.array_from_image(output.get_data())


def main():
    paths = utility.get_default_test_paths(__file__, output_folder="test097_AMF_semantics")
    baseline = None
    for weight in (1, 3.7):
        sim, actor, dose = make_simulation(paths.output / f"weight{weight}", weight=weight)
        actor.MicrodosimetricSpectra = False
        actor.Alpha_MCFMKM.active = False
        actor.Beta_MCFMKM.active = False
        actor.write_to_disk = False
        sim.run(start_new_process=True)
        scored = values(actor.dose)
        np.testing.assert_allclose(scored, values(dose.dose), rtol=1e-12, atol=1e-25)
        assert scored.sum() > 0
        yd = values(actor.DoseAveragedLinealEnergy)
        assert np.all(yd[scored > 0] > 0), "Scalar means must finalize when spectra are disabled"
        if baseline is None:
            baseline = (scored, yd)
        else:
            np.testing.assert_allclose(scored, baseline[0] * weight, rtol=1e-12, atol=1e-25)
            np.testing.assert_allclose(yd, baseline[1], rtol=1e-12)
        assert not list(sim.output_dir.glob("*.mhd"))
        assert not list(sim.output_dir.glob("*_histo_x_labels.txt"))

    for label, particle, energy in (("electron", "e-", 1),
                                     ("low_energy", "proton", .01),
                                     ("high_charge", "ion 19 39", 3900)):
        sim, actor, dose = make_simulation(paths.output / label, particle=particle, energy=energy)
        sim.source_manager.get_source("beam").position.translation = [0, 0, 0]
        actor.write_to_disk = False
        sim.run(start_new_process=True)
        assert values(dose.dose).sum() > 0, "The excluded-particle test must actually deposit energy"
        for output in actor.interfaces_to_user_output.values():
            assert np.all(values(output) == 0)

    sim, actor, dose = make_simulation(paths.output / "coordinates")
    water = sim.volume_manager.get_volume("water")
    rotation = Rotation.from_euler("y", 35, degrees=True).as_matrix()
    translation = np.array([5, -3, 2])
    water.rotation = rotation
    water.translation = translation
    beam = sim.source_manager.get_source("beam")
    beam.position.translation = rotation @ np.array([0, 0, -4]) + translation
    beam.direction.momentum = rotation @ np.array([0, 0, 1])
    actor.output_coordinate_system = "global"
    actor.hit_type = "post"
    dose.hit_type = "post"
    sim.physics_manager.set_max_step_size("water", 0.5)
    sim.physics_manager.user_limits_particles = "proton"
    # Both standard and AMF scorers must use the same post-step voxel.
    sim.run(start_new_process=True)
    assert values(actor.dose).sum() > 0
    np.testing.assert_allclose(values(actor.dose), values(dose.dose), rtol=1e-12, atol=1e-25)
    for output in actor.interfaces_to_user_output.values():
        image = sitk.ReadImage(str(output.get_output_path()))
        np.testing.assert_allclose(image.GetOrigin(), rotation @ [-2, 0, -2] + translation, atol=1e-12)
        np.testing.assert_allclose(image.GetDirection(), rotation.ravel(), atol=1e-12)

    hits = {}
    for hit in ("pre", "post", "random"):
        sim, actor, dose = make_simulation(paths.output / hit)
        actor.size = dose.size = [1, 1, 20]
        actor.spacing = dose.spacing = [10, 10, .5]
        actor.hit_type = hit
        dose.hit_type = "middle" if hit == "random" else hit
        actor.write_to_disk = False
        if hit == "random":
            actor.microdosimetric_spectra.active = False
        else:
            actor.microdosimetric_spectra_file_name = "microdosimetric_spectra.dat"
            suffix = ".mha" if hit == "pre" else ".nrrd"
            actor.microdosimetric_spectra.output_filename = "spectrum" + suffix
            actor.microdosimetric_spectra.write_to_disk = True
        sim.physics_manager.set_max_step_size("water", 2)
        sim.physics_manager.user_limits_particles = "proton"
        sim.run(start_new_process=True)
        scored = values(actor.dose)
        assert scored.sum() > 0
        reference = values(dose.dose)
        if hit == "random":
            # All random/middle points remain in this full-volume grid;
            # random positions differ, but their total energy must agree.
            np.testing.assert_allclose(scored.sum(), reference.sum(), rtol=1e-12)
        else:
            np.testing.assert_allclose(scored, reference, rtol=1e-12, atol=1e-25)
        hits[hit] = scored
        if hit != "random":
            image = sitk.ReadImage(str(actor.microdosimetric_spectra.get_output_path()))
            assert image.GetSize() == (1, 1, 20)
            assert image.GetNumberOfComponentsPerPixel() == 400
            assert "64-bit float" in image.GetPixelIDTypeAsString()
            np.testing.assert_array_equal(
                sitk.GetArrayFromImage(image), values(actor.microdosimetric_spectra)
            )
    assert not np.allclose(hits["pre"], hits["post"], rtol=1e-3, atol=0)
    assert not np.allclose(hits["random"], hits["pre"], rtol=1e-3, atol=0)
    utility.test_ok(True)


if __name__ == "__main__":
    main()
