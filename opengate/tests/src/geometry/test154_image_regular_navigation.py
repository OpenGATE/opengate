#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ImageVolume.voxel_navigation = "regular" (G4PhantomParameterisation, the
regular navigation of Geant4, the consecutive voxels of the same material
crossed in one step) vs "nested" (default).

An image of random blocks of four materials; a parallel beam of 140 keV
photons through it; a phase space behind the image. Two cases:
- free flight (GammaFreeFlightActor): the beam is parallel to the columns
  of blocks, so the weight behind the image depends only on the column
  (x, y) of the photon: it must be the same with both navigations (to the
  floating point precision), and so the mean weight (the transmission);
- analog: the number of photons behind the image without interaction must
  be the same (statistically).
The regular navigation must need fewer steps.
"""

import numpy as np
import itk
import uproot
import opengate as gate
from opengate.tests import utility

mm = gate.g4_units.mm
cm = gate.g4_units.cm
keV = gate.g4_units.keV


def create_image(filename):
    rng = np.random.default_rng(42)
    # 40^3 voxels of 3 mm, blocks of 4 voxels with one of the 4 labels
    blocks = rng.integers(0, 4, size=(10, 10, 10))
    labels = np.kron(blocks, np.ones((4, 4, 4))).astype(np.float32)
    img = itk.image_from_array(labels)
    img.SetSpacing([3.0, 3.0, 3.0])
    img.SetOrigin([0.0, 0.0, 0.0])
    itk.imwrite(img, str(filename))


def run(paths, navigation, free_flight, n):
    sim = gate.Simulation()
    sim.output_dir = paths.output
    sim.random_seed = 321
    sim.progress_bar = False
    sim.world.size = [1 * 1000 * mm] * 3
    sim.world.material = "G4_Galactic"

    image = sim.add_volume("Image", "image")
    image.image = paths.output / "test154_labels.mhd"
    image.material = "G4_AIR"
    image.voxel_materials = [
        [0, 1, "G4_WATER"],
        [1, 2, "G4_BONE_COMPACT_ICRU"],
        [2, 3, "G4_LUNG_ICRP"],
        [3, 4, "G4_AIR"],
    ]
    image.voxel_navigation = navigation

    plane = sim.add_volume("Box", "plane")
    plane.size = [20 * cm, 20 * cm, 1 * mm]
    plane.translation = [0, 0, 10 * cm]
    plane.material = "G4_Galactic"

    source = sim.add_source("GenericSource", "beam")
    source.particle = "gamma"
    source.energy.mono = 140 * keV
    source.position.type = "box"
    source.position.size = [10 * cm, 10 * cm, 0]
    source.position.translation = [0, 0, -10 * cm]
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    source.number_of_primaries = n

    if free_flight:
        ff = sim.add_actor("GammaFreeFlightActor", "ff")
        ff.attached_to = "world"

    phsp = sim.add_actor("PhaseSpaceActor", "phsp")
    phsp.attached_to = plane.name
    phsp.attributes = ["Weight", "KineticEnergy", "PrePosition"]
    name = f"{navigation}_{'ff' if free_flight else 'analog'}"
    phsp.output_filename = f"test154_{name}.root"

    stats = sim.add_actor("SimulationStatisticsActor", "stats")
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option4"
    sim.g4_commands_before_init.append("/process/em/UseGeneralProcess false")
    sim.run(start_new_process=True)
    print(stats)

    df = uproot.open(phsp.get_output_path())["phsp"].arrays(library="np")
    w = df["Weight"]
    e = df["KineticEnergy"]
    # the column of blocks (12 mm) of the image (120 mm, centered)
    ix = np.floor((df["PrePosition_X"] + 60 * mm) / (12 * mm)).astype(int)
    iy = np.floor((df["PrePosition_Y"] + 60 * mm) / (12 * mm)).astype(int)
    return {
        "w": w,
        "column": ix * 100 + iy,
        "unscattered": np.sum(np.isclose(e, 140 * keV)),
        "steps": stats.counts.steps,
    }


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, None, "test154")
    paths.output.mkdir(parents=True, exist_ok=True)
    create_image(paths.output / "test154_labels.mhd")

    is_ok = True
    n = 20000

    # free flight: mean weight (transmission)
    r = {nav: run(paths, nav, True, n) for nav in ("nested", "regular")}
    mean = {k: np.mean(v["w"]) for k, v in r.items()}
    sig = {k: np.std(v["w"]) / np.sqrt(len(v["w"])) for k, v in r.items()}
    z = (mean["regular"] - mean["nested"]) / np.hypot(sig["regular"], sig["nested"])
    b = len(r["nested"]["w"]) == n and len(r["regular"]["w"]) == n and abs(z) < 4
    utility.print_test(
        b,
        f"FF: mean weight behind the image, nested {mean['nested']:.5f} "
        f"regular {mean['regular']:.5f} (z {z:+.2f}), {len(r['regular']['w'])} "
        f"photons",
    )
    is_ok = is_ok and b
    # the weight per column: the median per column, max relative difference
    col_w = {}
    for nav, v in r.items():
        col_w[nav] = {
            c: np.median(v["w"][v["column"] == c]) for c in np.unique(v["column"])
        }
    common = set(col_w["nested"]) & set(col_w["regular"])
    diff = max(
        abs(col_w["regular"][c] - col_w["nested"][c]) / col_w["nested"][c]
        for c in common
    )
    b = len(common) >= 64 and diff < 1e-9
    utility.print_test(
        b,
        f"FF: weight per column of blocks, {len(common)} columns, max relative "
        f"difference regular / nested {diff:.2e} (< 1e-9)",
    )
    is_ok = is_ok and b
    b = r["regular"]["steps"] < 0.6 * r["nested"]["steps"]
    utility.print_test(
        b,
        f"FF: steps nested {r['nested']['steps']} regular {r['regular']['steps']} "
        f"(regular < 0.6 x nested)",
    )
    is_ok = is_ok and b

    # analog: photons without interaction behind the image
    a = {nav: run(paths, nav, False, n) for nav in ("nested", "regular")}
    un, ur = a["nested"]["unscattered"], a["regular"]["unscattered"]
    z = (ur - un) / np.sqrt(un + ur)
    b = abs(z) < 4
    utility.print_test(
        b,
        f"analog: unscattered photons behind the image, nested {un} regular {ur} "
        f"(z {z:+.2f}); FF expectation {mean['nested'] * n:.0f}",
    )
    is_ok = is_ok and b

    utility.test_ok(is_ok)
