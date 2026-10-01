"""Small AMDM test cases; all synthetic inputs and outputs stay under tests/output."""

from pathlib import Path
import json

import itk
import numpy as np
import SimpleITK as sitk
from scipy.spatial.transform import Rotation

import opengate as gate
from opengate.tests import utility

GAMMA = np.array([2.0, 7.0, 13.0])
DELTA = np.array([0.25, 0.75, 0.0])


def output_dir(name):
    paths = utility.get_default_test_paths(__file__)
    path = paths.output / "test110_amdm" / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def constant_lut(directory, entries=None):
    if entries is None:
        entries = {6: (GAMMA, DELTA)}
    path = Path(directory) / "synthetic_lut.txt"
    with path.open("w") as stream:
        stream.write("  # charge energy[MeV/n] gamma[keV/um] delta\n\n")
        for charge, (gamma, delta) in sorted(entries.items()):
            for energy in [1.0, 10.0]:
                stream.write(
                    " ".join(map(str, [charge, energy, *gamma, *delta])) + "\n"
                )
    return path


def make_sim(
    directory,
    lut=None,
    threads=1,
    weight=1.0,
    hit_type="pre",
    coordinate="local",
    particle="ion 6 12",
    primaries=80,
    image_volume=False,
):
    directory = Path(directory)
    sim = gate.Simulation()
    sim.output_dir = directory
    sim.number_of_threads = threads
    sim.random_seed = 9123456
    sim.g4_verbose = False
    sim.visu = False
    sim.world.size = [200, 200, 200]
    sim.world.material = "G4_Galactic"
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option3"
    sim.physics_manager.global_production_cuts.all = 1.0
    phantom = sim.add_volume("Image" if image_volume else "Box", "phantom")
    if image_volume:
        from opengate.image import create_3d_image

        image = create_3d_image([5, 5, 5], [8, 8, 8], origin=[19, -11, 4])
        image.SetDirection(Rotation.from_euler("y", 15, degrees=True).as_matrix())
        image_path = directory / "volume.mhd"
        itk.imwrite(image, str(image_path))
        phantom.image = str(image_path)
        phantom.voxel_materials = [[-1, 1, "G4_WATER"]]
    else:
        phantom.size = [40, 40, 40]
    phantom.material = "G4_WATER"
    phantom.translation = [12.0, -8.0, 6.0]
    phantom.rotation = Rotation.from_euler("z", 30, degrees=True).as_matrix()
    actor = sim.add_actor("AMDMActor", "amdm")
    actor.attached_to = phantom
    actor.size = [5, 5, 5]
    actor.spacing = [8, 8, 8]
    actor.rotation = Rotation.from_euler("x", 20, degrees=True).as_matrix()
    actor.translation = [2, 1, -1]
    actor.hit_type = hit_type
    actor.output_coordinate_system = coordinate
    actor.LUTfilename = str(lut or constant_lut(directory))
    actor.AMDM_Bins = 3
    actor.storeMergingData = True
    actor.output_filename = "result.mhd"
    source = sim.add_source("GenericSource", "ions")
    source.particle = particle
    source.energy.mono = 60 * gate.g4_units.MeV
    source.number_of_primaries = primaries
    source.weight = weight
    source.position.type = "point"
    source.position.translation = (
        np.asarray(phantom.translation) + phantom.rotation @ actor.translation
    ).tolist()
    source.direction.type = "momentum"
    source.direction.momentum = (phantom.rotation @ actor.rotation @ [0, 0, 1]).tolist()
    return sim, actor


def arrays(actor, which="merged"):
    return tuple(
        itk.array_from_image(interface.get_data(which=which))
        for interface in (
            actor.restrictedEdep,
            actor.raw_delta,
            actor.raw_gamma,
            actor.delta,
            actor.gamma,
        )
    )


def expected_metadata(sim, actor):
    center = -(np.asarray(actor.size) - 1) * np.asarray(actor.spacing) / 2
    origin = actor.rotation @ center + actor.translation
    direction = actor.rotation
    if actor.output_coordinate_system == "global":
        volume = sim.volume_manager.get_volume("phantom")
        origin = volume.rotation @ origin + volume.translation
        direction = volume.rotation @ direction
    elif actor.output_coordinate_system == "attached_to_image":
        volume = actor.attached_to_volume
        origin = volume.native_rotation @ origin + volume.native_translation
        direction = volume.native_rotation @ direction
    elif actor.output_coordinate_system is None:
        origin = center
        direction = np.eye(3)
    return origin, direction


def check_image(path, dimension, actor, origin, direction, samples=None):
    """Parse the header/payload independently with SimpleITK and compare to ITK."""
    path = Path(path)
    assert path.is_file(), path
    header = dict(
        line.split(" = ", 1) for line in path.read_text().splitlines() if " = " in line
    )
    assert int(header["NDims"]) == dimension
    assert header["ElementType"] == "MET_DOUBLE"
    assert int(header.get("ElementNumberOfChannels", "1")) == 1
    payload = path.parent / header["ElementDataFile"]
    assert payload.is_file() and payload.stat().st_size > 0, payload
    image = sitk.ReadImage(str(path))
    assert image.GetDimension() == dimension
    assert image.GetNumberOfComponentsPerPixel() == 1
    assert image.GetPixelID() == sitk.sitkFloat64
    size = list(actor.size)
    spacing = list(actor.spacing)
    expected_origin = list(origin)
    expected_direction = direction
    if dimension == 4:
        size += [actor.AMDM_Bins]
        spacing += [1.0]
        expected_origin += [0.0]
        expected_direction = np.eye(4)
        expected_direction[:3, :3] = direction
    assert image.GetSize() == tuple(size)
    np.testing.assert_allclose(image.GetSpacing(), spacing, rtol=0, atol=1e-12)
    np.testing.assert_allclose(image.GetOrigin(), expected_origin, rtol=0, atol=1e-10)
    np.testing.assert_allclose(
        np.array(image.GetDirection()).reshape(dimension, dimension),
        expected_direction,
        rtol=0,
        atol=1e-12,
    )
    data = sitk.GetArrayFromImage(image)
    assert data.dtype == np.float64
    assert data.shape == tuple(reversed(size)), (path, data.shape)
    assert np.isfinite(data).all(), path
    np.testing.assert_array_equal(data, itk.array_from_image(itk.imread(str(path))))
    if header.get("CompressedData", "False").lower() == "false":
        assert payload.stat().st_size == data.size * 8
    if samples is not None:
        # Current actor outputs record sample counts beside the image.
        metadata = json.loads(
            path.with_name(path.stem + "-samples.mhd.json").read_text()
        )
        assert metadata["number_of_samples"] == samples
    return data


def check_outputs(sim, actor, which="merged", samples=None):
    origin, direction = expected_metadata(sim, actor)
    result = []
    for interface, dimension, suffix in [
        (actor.restrictedEdep, 3, "restrictedEdep"),
        (actor.raw_delta, 4, "unprocessedForMergingOnly-delta"),
        (actor.raw_gamma, 4, "unprocessedForMergingOnly-gamma"),
        (actor.delta, 4, "delta"),
        (actor.gamma, 4, "gamma"),
    ]:
        path = interface.get_output_path(which=which)
        expected_name = f"result-{suffix}"
        if which != "merged":
            expected_name += f"-run{which}"
        assert path.name == expected_name + ".mhd", path
        assert path.parent.resolve() == Path(sim.output_dir).resolve()
        if interface.active and interface.write_to_disk:
            data = check_image(path, dimension, actor, origin, direction, samples)
            np.testing.assert_array_equal(
                data, itk.array_from_image(interface.get_data(which))
            )
            result.append(data)
        else:
            assert not path.exists(), path
    return result


def assert_constant_scoring(actor, gamma=GAMMA, delta=DELTA):
    energy, raw_delta, raw_gamma, normalized_delta, normalized_gamma = arrays(actor)
    assert energy.sum() > 0, "simulation must score nonzero restricted energy"
    assert np.any(energy == 0), "test must include empty voxels"
    for b in range(actor.AMDM_Bins):
        # Accumulation error only: constants make these exact scientific identities.
        np.testing.assert_allclose(
            raw_delta[b], delta[b] * energy, rtol=1e-12, atol=1e-12
        )
        np.testing.assert_allclose(
            raw_gamma[b], gamma[b] * raw_delta[b], rtol=1e-12, atol=1e-12
        )
        np.testing.assert_allclose(
            normalized_delta[b][energy > 0], delta[b], rtol=1e-12, atol=1e-12
        )
        expected_gamma = gamma[b] if delta[b] != 0 else 0
        np.testing.assert_allclose(
            normalized_gamma[b][energy > 0], expected_gamma, rtol=1e-12, atol=1e-12
        )
        assert np.all(normalized_delta[b][energy == 0] == 0)
        assert np.all(normalized_gamma[b][energy == 0] == 0)
    return energy.sum()
