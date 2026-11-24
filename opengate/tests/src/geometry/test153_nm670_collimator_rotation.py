#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Test 153: rotation of the GE NM670 collimator holes (#791).

With rotation_deg, the hexagonal holes and their lattice are rotated together.

1. Positions (LEHR, MEGP, HEGP, full size):
   - no rotation: the lattice is unchanged (no explicit translations), and
     rotate_collimator_holes with 0 deg gives the same holes;
   - 15 deg: the holes are turned by 15 deg (the rotation given to Geant4 is
     the frame rotation, the inverse); every hole has its 6 nearest neighbours at the lattice distance,
     in the directions of the unrotated lattice turned by 15 deg (the septa
     keep their thickness); all holes are inside the area of the unrotated
     lattice, and their number is within 2 % of the unrotated one.
2. Geant4 overlap check of the rotated holes (LEHR, 6 x 6 x 2 holes, in a child
   process): no overlap at 15 deg. Control: when the lattice is rotated but
   the holes are turned the other way (the rotation matrix not inverted, as
   before the fix), the holes overlap and this is detected.
"""

import subprocess
import sys

import numpy as np
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation

import opengate as gate
import opengate.contrib.spect.ge_discovery_nm670 as nm670
from opengate.tests import utility

mm = gate.g4_units.mm


def get_holep(colli_type, rotation_deg, debug=False):
    sim = gate.Simulation()
    nm670.add_spect_head(
        sim, "spect", collimator_type=colli_type, rotation_deg=rotation_deg, debug=debug
    )
    return sim, sim.volume_manager.get_volume("spect_collimator_hole_param")


def neighbour_directions(tr, n=6):
    """Distances and directions (deg, modulo 60) of the n nearest neighbours."""
    xy = tr[:, :2]
    d, i = cKDTree(xy).query(xy, k=n + 1)
    v = xy[i[:, 1:]] - xy[:, None, :]
    a = np.degrees(np.arctan2(v[..., 1], v[..., 0])) % 60
    return d[:, 1:], a


def check_positions(colli_type):
    is_ok = True
    _, holep0 = get_holep(colli_type, 0)
    ref = holep0.copy_translations()
    b = holep0.translations is None
    is_ok = utility.print_test(b, f"{colli_type} 0 deg: lattice unchanged") and is_ok

    nm670.rotate_collimator_holes(holep0, 0)
    tr0 = holep0.translations
    same = len(tr0) == len(ref) and np.allclose(
        np.array(sorted(map(tuple, np.round(tr0, 6)))),
        np.array(sorted(map(tuple, np.round(ref, 6)))),
    )
    is_ok = (
        utility.print_test(
            same, f"{colli_type} rotate_collimator_holes(0): same {len(tr0)} holes"
        )
        and is_ok
    )

    # hexagonal lattice: neighbour distance and directions, unrotated
    d_ref, a_ref = neighbour_directions(ref)
    # keep the holes with 6 neighbours at the same distance (not on the border)
    dist = np.median(d_ref[:, 0])

    _, holep = get_holep(colli_type, 15)
    tr = holep.copy_translations()
    rot = holep.rotation
    b = np.allclose(rot, Rotation.from_euler("Z", -15, degrees=True).as_matrix())
    is_ok = (
        utility.print_test(b, f"{colli_type} 15 deg: holes rotated by 15 deg") and is_ok
    )

    d, a = neighbour_directions(tr)
    # (the lattice steps are given with 5 or 6 decimals: distances within 1e-4 mm)
    inner = np.all(np.abs(d - dist) < 1e-4 * mm, axis=1)
    inner_ref = np.all(np.abs(d_ref - dist) < 1e-4 * mm, axis=1)
    dir_ref = np.unique(np.round(a_ref[inner_ref], 1) % 60)
    dir_rot = np.unique(np.round(a[inner], 1) % 60)
    expected = np.unique(np.round((dir_ref + 15) % 60, 1) % 60)
    b = inner.mean() > 0.95 and np.allclose(np.sort(dir_rot), np.sort(expected))
    is_ok = (
        utility.print_test(
            b,
            f"{colli_type} 15 deg: neighbours at {dist:.4f} mm for {inner.mean() * 100:.1f} % "
            f"of the holes, directions {dir_rot} (unrotated {dir_ref}, expected {expected})",
        )
        and is_ok
    )

    rc = holep.repeated_volume.radius / np.cos(np.pi / 6)
    lo = ref[:, :2].min(axis=0) - rc
    hi = ref[:, :2].max(axis=0) + rc
    inside = np.all(tr[:, :2] - rc >= lo - 1e-6) and np.all(tr[:, :2] + rc <= hi + 1e-6)
    ratio = len(tr) / len(ref)
    b = inside and abs(ratio - 1) < 0.02
    is_ok = (
        utility.print_test(
            b,
            f"{colli_type} 15 deg: {len(tr)} holes inside the area "
            f"(unrotated {len(ref)}, ratio {ratio:.4f})",
        )
        and is_ok
    )
    return is_ok


def run_child(control):
    # LEHR, small lattice (the overlap check cost grows with the square of the
    # number of copies): the lattice and the holes are rotated by 15 deg
    sim, holep = get_holep("lehr", 0, debug=True)
    holep.linear_repeat = [6, 6, 1]
    nm670.rotate_collimator_holes(holep, 15, extend=False)
    if control:
        # holes turned the other way
        holep.rotation = np.array(holep.rotation).T
    sim.world.material = "G4_AIR"
    sim.check_volumes_overlap = True
    sim.check_volumes_overlap_max_copies = 100
    source = sim.add_source("GenericSource", "source")
    source.particle = "gamma"
    source.energy.mono = 140 * gate.g4_units.keV
    source.number_of_primaries = 10
    sim.run()


def run_case(control):
    r = subprocess.run(
        [sys.executable, __file__, "--child", str(int(control))],
        capture_output=True,
        text=True,
    )
    return r.returncode, r.stdout + r.stderr


if __name__ == "__main__":
    if "--child" in sys.argv:
        run_child(sys.argv[-1] == "1")
        sys.exit(0)

    is_ok = True
    for c in ["lehr", "megp", "hegp"]:
        is_ok = check_positions(c) and is_ok

    overlap_msg = 'Some volumes overlap with the volume "spect_collimator_hole_param"'
    code, out = run_case(False)
    b = code == 0 and overlap_msg not in out
    is_ok = (
        utility.print_test(b, f"Geant4: no overlap at 15 deg (exit code {code})")
        and is_ok
    )
    if not b:
        print(out[-3000:])

    code, out = run_case(True)
    b = code != 0 and overlap_msg in out
    is_ok = (
        utility.print_test(
            b, f"Geant4 control: holes turned the other way overlap (exit code {code})"
        )
        and is_ok
    )
    if not b:
        print(out[-3000:])

    utility.test_ok(is_ok)
