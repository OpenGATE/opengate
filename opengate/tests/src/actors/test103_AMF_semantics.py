#!/usr/bin/env python3
"""Particle, weight, hit-position and coordinate checks in one small transport."""

import itk
import numpy as np
import SimpleITK as sitk
from scipy.spatial.transform import Rotation
from opengate.tests import utility
from test103_AMF_helpers import make_simulation


def values(output):
    """Copy the retained output image into a NumPy array."""
    return itk.array_from_image(output.get_data())


def add_actor(sim, template, name, volume="water"):
    """Add an AMF scorer using the shared synthetic fit and a full-volume grid."""
    actor = sim.add_actor("AMFActor", name)
    actor.attached_to = volume
    actor.tsed_file_name = template.tsed_file_name
    actor.size = [1, 1, 20]
    actor.spacing = [10, 10, 0.5]
    actor.hit_type = "middle"
    actor.DoseAveragedLinealEnergy.active = True
    actor.DoseAveragedLinealEnergySaturationCorrected.active = True
    actor.output_filename = name + ".mhd"
    actor.microdosimetric_spectra.output_filename = name + "-spectrum.mhd"
    actor.write_to_disk = False
    return actor


def add_reference(sim, actor, name):
    """Add an independent all-particle dose scorer with matching hit geometry."""
    reference = sim.add_actor("DoseActor", name)
    reference.attached_to = actor.attached_to
    reference.size = actor.size
    reference.spacing = actor.spacing
    reference.hit_type = actor.hit_type
    reference.dose.active = True
    reference.write_to_disk = False
    return reference


def main():
    """Check scalar-only scoring, exclusions, all hit modes and vector formats."""
    paths = utility.get_default_test_paths(
        __file__, output_folder="test103_AMF_semantics"
    )
    sim, base, reference = make_simulation(paths.output, weight=3.7)
    sim.world.size = [250, 250, 250]
    base.size = reference.size = [1, 1, 20]
    base.spacing = reference.spacing = [10, 10, 0.5]
    base.write_to_disk = False
    scalar = add_actor(sim, base, "scalar_only")
    scalar.MicrodosimetricSpectra = False
    scalar.Alpha_MCFMKM.active = scalar.Beta_MCFMKM.active = False

    rotation = Rotation.from_euler("y", 35, degrees=True).as_matrix()
    translation = np.array([5, -3, 2])
    water = sim.volume_manager.get_volume("water")
    water.rotation, water.translation = rotation, translation
    beam = sim.source_manager.get_source("beam")
    beam.position.translation = rotation @ np.array([0, 0, -4]) + translation
    beam.direction.momentum = rotation @ np.array([0, 0, 1])
    sim.physics_manager.set_max_step_size("water", 2)
    sim.physics_manager.user_limits_particles = "proton"

    hits = {}
    for hit in ("pre", "post", "random"):
        actor = add_actor(sim, base, hit)
        actor.hit_type = hit
        actor.output_coordinate_system = "global"
        ref = add_reference(sim, actor, hit + "_dose")
        if hit == "random":
            ref.hit_type = "middle"
            actor.microdosimetric_spectra.active = False
        else:
            actor.microdosimetric_spectra.output_filename = hit + (
                ".mha" if hit == "pre" else ".nrrd"
            )
            actor.microdosimetric_spectra.write_to_disk = True
        hits[hit] = (actor, ref)

    exclusions = []
    for x, label, particle, energy in (
        (30, "electron", "e-", 1),
        (60, "low_energy", "proton", 0.01),
        (90, "high_charge", "ion 19 39", 3900),
    ):
        box = sim.add_volume("Box", label + "_water")
        box.size = [10, 10, 10]
        box.translation = [x, 0, 0]
        box.material = "G4_WATER"
        source = sim.add_source("GenericSource", label + "_beam")
        source.particle = particle
        source.energy.mono = energy
        source.number_of_primaries = 8
        source.position.translation = [x, 0, 0]
        source.direction.type = "momentum"
        source.direction.momentum = [0, 0, 1]
        actor = add_actor(sim, base, label, box.name)
        ref = add_reference(sim, actor, label + "_dose")
        exclusions.append((actor, ref))

    # Each scorer sees the same histories, avoiding repeated Geant4 startups.
    sim.run()
    assert values(base.dose).sum() > 0
    np.testing.assert_allclose(
        values(base.dose), values(reference.dose), rtol=1e-12, atol=1e-25
    )
    np.testing.assert_allclose(values(scalar.dose), values(base.dose), rtol=1e-12)
    np.testing.assert_allclose(
        values(scalar.DoseAveragedLinealEnergy),
        values(base.DoseAveragedLinealEnergy),
        rtol=1e-12,
    )
    assert not scalar.microdosimetric_spectra.active
    assert not list(paths.output.glob("scalar_only*.mhd"))
    for actor, ref in exclusions:
        assert (
            values(ref.dose).sum() > 0
        ), "Excluded particles must actually deposit energy"
        for output in actor.interfaces_to_user_output.values():
            assert np.all(values(output) == 0)

    arrays = {}
    for hit, (actor, ref) in hits.items():
        scored = values(actor.dose)
        assert scored.sum() > 0
        if hit == "random":
            np.testing.assert_allclose(scored.sum(), values(ref.dose).sum(), rtol=1e-12)
        else:
            np.testing.assert_allclose(scored, values(ref.dose), rtol=1e-12, atol=1e-25)
            image = sitk.ReadImage(str(actor.microdosimetric_spectra.get_output_path()))
            assert image.GetSize() == (1, 1, 20)
            assert image.GetNumberOfComponentsPerPixel() == 400
            assert "64-bit float" in image.GetPixelIDTypeAsString()
            np.testing.assert_allclose(
                image.GetOrigin(), rotation @ [0, 0, -4.75] + translation, atol=1e-12
            )
            np.testing.assert_allclose(
                image.GetDirection(), rotation.ravel(), atol=1e-12
            )
            np.testing.assert_array_equal(
                sitk.GetArrayFromImage(image), values(actor.microdosimetric_spectra)
            )
        arrays[hit] = scored
    assert not np.allclose(arrays["pre"], arrays["post"], rtol=1e-3, atol=0)
    assert not np.allclose(arrays["random"], arrays["pre"], rtol=1e-3, atol=0)
    utility.test_ok(True)


if __name__ == "__main__":
    main()
