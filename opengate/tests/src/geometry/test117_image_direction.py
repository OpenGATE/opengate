#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import itk
import numpy as np
from opengate.tests import utility
import opengate as gate

# Images with a direction matrix that is not the identity (rotation or flip)
# are not supported by ImageVolume and VoxelSource: they must fail (see #421)


def write_image(path, value, direction):
    arr = np.full((10, 10, 10), value, dtype=np.float32)
    img = itk.image_from_array(arr)
    img.SetSpacing([2.0, 2.0, 2.0])
    img.SetDirection(direction)
    itk.imwrite(img, str(path))
    return path


def create_simulation(paths, ct_path, activity_path):
    mm = gate.g4_units.mm
    m = gate.g4_units.m
    keV = gate.g4_units.keV

    sim = gate.Simulation()
    sim.random_seed = 123456
    sim.output_dir = paths.output
    sim.world.size = [1 * m, 1 * m, 1 * m]
    sim.world.material = "G4_AIR"

    ct = sim.add_volume("ImageVolume", "ct")
    ct.image = ct_path
    ct.voxel_materials = [[-2000, 0, "G4_AIR"], [0, 3000, "G4_WATER"]]

    source = sim.add_source("VoxelSource", "activity")
    source.attached_to = "ct"
    source.image = activity_path
    source.particle = "gamma"
    source.energy.mono = 140 * keV
    source.direction.type = "iso"
    source.number_of_primaries = 100

    stats = sim.add_actor("SimulationStatisticsActor", "stats")
    return sim, ct, source, stats


def expect_failure(func, description):
    try:
        func()
    except Exception as e:
        b = "direction matrix that is not the identity" in str(e)
        utility.print_test(b, f"{description} fails with the expected error")
        return b
    utility.print_test(False, f"{description} does not fail")
    return False


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "", "test117")
    paths.output.mkdir(parents=True, exist_ok=True)

    identity = np.eye(3)
    flip_y = np.diag([1.0, -1.0, 1.0])
    rotation_z = np.array([[0.0, -1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]])

    ct_ok = write_image(paths.output / "ct_identity.mhd", 100, identity)
    act_ok = write_image(paths.output / "activity_identity.mhd", 1, identity)
    ct_flip = write_image(paths.output / "ct_flip.mhd", 100, flip_y)
    act_flip = write_image(paths.output / "activity_flip.mhd", 1, flip_y)
    act_rot = write_image(paths.output / "activity_rot.mhd", 1, rotation_z)

    is_ok = True

    # an image volume with a flipped image must fail
    _, ct, _, _ = create_simulation(paths, ct_flip, act_ok)
    b = expect_failure(ct.load_input_image, "ImageVolume with a flipped image")
    is_ok = is_ok and b

    # a voxel source with a flipped or rotated activity image must fail
    for path, description in ((act_flip, "flipped"), (act_rot, "rotated")):
        _, _, source, _ = create_simulation(paths, ct_ok, path)
        b = expect_failure(
            lambda: source.update_activity_image(path),
            f"VoxelSource with a {description} activity image",
        )
        is_ok = is_ok and b

    # a simulation with identity directions still runs normally
    sim, _, _, stats = create_simulation(paths, ct_ok, act_ok)
    sim.run()
    b = stats.counts.events == 100
    utility.print_test(
        b, f"Simulation with identity directions runs: {stats.counts.events} events"
    )
    is_ok = is_ok and b

    utility.test_ok(is_ok)
