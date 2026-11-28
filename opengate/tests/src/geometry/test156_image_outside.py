#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ImageVolume.outside_threshold: an image volume with an outside (its solid
is the union of the inside voxels, GateImageMaskSolid). Other volumes can
then be in the same world, inside the box of the image, without overlap.

A CT-like image (40 x 40 x 20 cm, 4 mm voxels): a water cylinder (r 10 cm)
in air; six NaI boxes ("heads") around it, inside the box of the image but
in its air. A 140 keV gamma source in the water. Two geometries:
- "parallel": the image is a box, the heads in a parallel world (the usual
  way when volumes overlap the box of an image);
- "outside": outside_threshold = -500, the heads in the mass world.
The energy deposited in the heads must be the same (statistically), the
outside voxels are only air. Also checked: the number of outside voxels
(the air connected to the border), a closed pocket of air in the water
stays inside, and the overlap check of Geant4 (heads vs the mask solid).
The time of each run is printed (information).
"""

import time
import numpy as np
import itk
import uproot
from scipy.spatial.transform import Rotation
import opengate as gate
from opengate.tests import utility

mm = gate.g4_units.mm
cm = gate.g4_units.cm
keV = gate.g4_units.keV


def create_image(filename):
    # (z, y, x) = 50 x 100 x 100 voxels of 4 mm
    n_xy, n_z, s = 100, 50, 4.0
    c = (np.arange(n_xy) - (n_xy - 1) / 2) * s
    x, y = np.meshgrid(c, c, indexing="xy")
    disk = x**2 + y**2 < 100**2
    arr = np.full((n_z, n_xy, n_xy), -1000, dtype=np.int16)
    arr[:, disk] = 0
    # a closed pocket of air in the water (must stay inside)
    arr[20:30, 45:55, 45:55] = -1000
    img = itk.image_from_array(arr)
    img.SetSpacing([s, s, s])
    img.SetOrigin([0.0, 0.0, 0.0])
    itk.imwrite(img, str(filename))
    expected_outside = int((~disk).sum()) * n_z
    return expected_outside


def head_positions():
    for i in range(6):
        a = i * np.pi / 3
        r = 150 * mm  # the heads: r 130 to 170 mm (the water: r < 100 mm)
        rot = Rotation.from_euler("z", a).as_matrix()
        yield i, [r * np.cos(a), r * np.sin(a), 0], rot


def run(paths, mode, n, threads=1):
    sim = gate.Simulation()
    sim.output_dir = paths.output
    sim.random_seed = 654321
    sim.progress_bar = False
    sim.number_of_threads = threads
    sim.world.size = [1 * 1000 * mm] * 3
    sim.world.material = "G4_AIR"
    sim.check_volumes_overlap = True

    image = sim.add_volume("Image", "ct")
    image.image = paths.output / "test156_ct.mhd"
    image.material = "G4_AIR"
    image.voxel_materials = [[-2000, -500, "G4_AIR"], [-500, 2000, "G4_WATER"]]
    image.voxel_navigation = "regular"
    if mode == "outside":
        image.outside_threshold = -500
        mother = "world"
    else:
        sim.add_parallel_world("world2")
        mother = "world2"

    heads = []
    for i, tr, rot in head_positions():
        h = sim.add_volume("Box", f"head{i}")
        h.mother = mother
        h.size = [40 * mm, 80 * mm, 160 * mm]
        h.translation = tr
        h.rotation = rot
        h.material = "G4_SODIUM_IODIDE"
        heads.append(h.name)

    source = sim.add_source("GenericSource", "src")
    source.particle = "gamma"
    source.energy.mono = 140 * keV
    source.position.type = "sphere"
    source.position.radius = 50 * mm
    source.direction.type = "iso"
    source.number_of_primaries = n // threads

    hc = sim.add_actor("DigitizerHitsCollectionActor", "hits")
    hc.attached_to = heads
    hc.attributes = ["TotalEnergyDeposit", "EventID"]
    hc.output_filename = f"test156_{mode}.root"

    stats = sim.add_actor("SimulationStatisticsActor", "stats")
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option4"
    sim.g4_commands_before_init.append("/process/em/UseGeneralProcess false")
    t = time.time()
    sim.run(start_new_process=True)
    t = time.time() - t
    print(stats)

    df = uproot.open(hc.get_output_path())["hits"].arrays(library="np")
    edep = df["TotalEnergyDeposit"]
    events = df["EventID"]
    # per event energy (for the statistical uncertainty)
    _, inv = np.unique(events, return_inverse=True)
    per_event = np.bincount(inv, weights=edep)
    n_events = stats.counts.events
    mean = per_event.sum() / n_events
    var = (np.sum(per_event**2) / n_events - mean**2) / n_events
    return {
        "mean": mean,
        "sigma": np.sqrt(var),
        "events_with_edep": len(per_event),
        "steps": stats.counts.steps,
        "time": t,
    }


def check_outside_voxels(paths, expected):
    sim = gate.Simulation()
    image = sim.add_volume("Image", "ct")
    image.image = paths.output / "test156_ct.mhd"
    image.outside_threshold = -500
    mask = image.compute_outside_mask()
    b = int(mask.sum()) == expected and not mask[20:30, 45:55, 45:55].any()
    utility.print_test(
        b,
        f"outside voxels {int(mask.sum())} (expected {expected}, the air around "
        f"the cylinder); the closed pocket of air stays inside",
    )
    return b


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, None, "test156")
    paths.output.mkdir(parents=True, exist_ok=True)
    expected = create_image(paths.output / "test156_ct.mhd")

    is_ok = check_outside_voxels(paths, expected)

    n = 200000
    r = {mode: run(paths, mode, n) for mode in ("parallel", "outside")}
    for mode, v in r.items():
        print(
            f"{mode:9s}: edep per event {v['mean'] / keV:.5f} +- "
            f"{v['sigma'] / keV:.5f} keV, events with edep {v['events_with_edep']}, "
            f"steps {v['steps']}, time {v['time']:.1f} s"
        )
    a, b_ = r["parallel"], r["outside"]
    z = (b_["mean"] - a["mean"]) / np.hypot(a["sigma"], b_["sigma"])
    na, nb = a["events_with_edep"], b_["events_with_edep"]
    zn = (nb - na) / np.sqrt(na + nb)
    b = abs(z) < 4 and abs(zn) < 4
    utility.print_test(
        b,
        f"energy in the heads, outside vs parallel world: z {z:+.2f}; events with "
        f"energy: z {zn:+.2f}",
    )
    is_ok = is_ok and b
    utility.print_test(
        True,
        f"time: parallel world {a['time']:.1f} s, outside {b_['time']:.1f} s "
        f"(ratio {a['time'] / b_['time']:.2f}, information only)",
    )

    utility.test_ok(is_ok)
