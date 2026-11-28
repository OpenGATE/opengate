#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TLEDoseActor.split_step_in_voxels: the TLE deposit of a photon step is split
among the dose voxels crossed by the step (length in each voxel / step
length), instead of going to one voxel.

A water image with a bone slab (2 mm voxels), an isotropic 140 keV point
source at the center, a dose grid of 3 mm, shifted (not aligned with the
image voxels). Checks:
- same seed, nested navigation, hit_type "middle" (no random number used
  by the actor, so the same tracks) vs split: the total edep in the dose
  grid is the same (the split moves the energy between voxels, it does not
  create or lose any);
- regular navigation + split vs nested + split (reference): same dose (z
  per voxel, mean and std, and the dose in the central voxels);
- regular navigation: split vs random hit, the voxel uncertainty is lower
  with split (the long regular steps put all their deposit in one voxel
  without split).
"""

import numpy as np
import itk
import opengate as gate
from opengate.tests import utility

mm = gate.g4_units.mm
keV = gate.g4_units.keV


def create_image(filename):
    # 50^3 voxels of 2 mm: water (label 0), a bone slab (label 1)
    labels = np.zeros((50, 50, 50), dtype=np.float32)
    labels[:, :, 30:36] = 1
    img = itk.image_from_array(labels)
    img.SetSpacing([2.0, 2.0, 2.0])
    img.SetOrigin([0.0, 0.0, 0.0])
    itk.imwrite(img, str(filename))


def run(paths, navigation, hit_type, split, n):
    sim = gate.Simulation()
    sim.output_dir = paths.output
    sim.random_seed = 123654
    sim.progress_bar = False
    sim.world.size = [500 * mm] * 3
    sim.world.material = "G4_AIR"

    image = sim.add_volume("Image", "image")
    image.image = paths.output / "test157_labels.mhd"
    image.material = "G4_AIR"
    image.voxel_materials = [
        [0, 1, "G4_WATER"],
        [1, 2, "G4_BONE_COMPACT_ICRU"],
    ]
    image.voxel_navigation = navigation

    source = sim.add_source("GenericSource", "src")
    source.particle = "gamma"
    source.energy.mono = 140 * keV
    source.position.type = "sphere"
    source.position.radius = 1 * mm
    source.attached_to = image.name
    source.direction.type = "iso"
    source.number_of_primaries = n

    dose = sim.add_actor("TLEDoseActor", "dose")
    dose.attached_to = image.name
    # 3 mm voxels, shifted by 1 mm: not aligned with the image voxels;
    # 34 x 3 mm = 102 mm covers the 100 mm image
    dose.size = [34, 34, 34]
    dose.spacing = [3 * mm, 3 * mm, 3 * mm]
    dose.translation = [1 * mm, 1 * mm, 1 * mm]
    dose.hit_type = hit_type
    dose.split_step_in_voxels = split
    dose.dose.active = True
    dose.dose_uncertainty.active = True
    dose.edep_uncertainty.active = True
    name = f"{navigation}_{hit_type}_{'split' if split else 'nosplit'}"
    dose.output_filename = f"test157_{name}.mhd"

    stats = sim.add_actor("SimulationStatisticsActor", "stats")
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option4"
    sim.physics_manager.set_production_cut("world", "all", 1 * mm)
    sim.run(start_new_process=True)
    print(f"{name}: {stats.counts.steps} steps")

    edep = itk.array_from_image(dose.edep.image)
    d = itk.array_from_image(dose.dose.image)
    u = itk.array_from_image(dose.dose_uncertainty.image)
    return {
        "edep": edep,
        "dose": d,
        "sigma": u * d,
        "u": u,
        "steps": stats.counts.steps,
    }


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, None, "test157")
    paths.output.mkdir(parents=True, exist_ok=True)
    create_image(paths.output / "test157_labels.mhd")

    is_ok = True
    n = 100000

    # same tracks: nested + middle vs nested + split
    a = run(paths, "nested", "middle", False, n)
    b = run(paths, "nested", "middle", True, n)
    ea, eb = a["edep"].sum(), b["edep"].sum()
    diff = abs(eb - ea) / ea
    ok = diff < 1e-9 and a["steps"] == b["steps"]
    utility.print_test(
        ok,
        f"same tracks (steps {a['steps']} {b['steps']}): total edep middle "
        f"{ea:.6e} split {eb:.6e} MeV, rel. diff {diff:.1e} (< 1e-9)",
    )
    is_ok = is_ok and ok

    # regular + split vs nested + split: same dose (nested + middle is biased
    # near the source: steep gradient, deposit at the middle of the step)
    r = run(paths, "regular", "random", True, n)
    m = (b["dose"] > 0.01 * b["dose"].max()) & (r["dose"] > 0)
    z = (r["dose"][m] - b["dose"][m]) / np.sqrt(r["sigma"][m] ** 2 + b["sigma"][m] ** 2)
    rel = np.max(np.abs(r["dose"][m] - b["dose"][m]) / b["dose"][m])
    ok = abs(z.mean()) < 0.1 and z.std() < 1.2
    utility.print_test(
        ok,
        f"regular + split vs nested + split: voxel z mean {z.mean():+.3f} std "
        f"{z.std():.3f}, max rel. diff {rel:.1e} ({m.sum()} voxels above 1 % of max), "
        f"steps {r['steps']} vs {b['steps']}",
    )
    is_ok = is_ok and ok
    # central 6^3 voxels
    c = slice(14, 20)
    dr, da = r["dose"][c, c, c].sum(), b["dose"][c, c, c].sum()
    sr = np.sqrt((r["sigma"][c, c, c] ** 2).sum())
    sa = np.sqrt((b["sigma"][c, c, c] ** 2).sum())
    zc = (dr - da) / np.hypot(sr, sa)
    ok = abs(zc) < 4
    utility.print_test(
        ok,
        f"central voxels: dose ratio regular + split / nested {dr / da:.4f} (z {zc:+.2f})",
    )
    is_ok = is_ok and ok

    # regular: split vs random, the uncertainty
    q = run(paths, "regular", "random", False, n)
    mm_ = m & (q["dose"] > 0)
    u_split = np.median(r["u"][mm_])
    u_random = np.median(q["u"][mm_])
    ok = u_split < 0.9 * u_random
    utility.print_test(
        ok,
        f"regular: median voxel uncertainty split {100 * u_split:.2f} % < random "
        f"{100 * u_random:.2f} % (x 0.9)",
    )
    is_ok = is_ok and ok

    utility.test_ok(is_ok)
