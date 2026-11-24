#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ForceDirection: sampling of the direction in the cone, "uniform" and
"log" (angular_acceptance.angle_sampling).

A point gamma source in vacuum, forced in a cone of 30 deg around -z; a
phase space on a large plane below stores the direction and the weight of
each particle. For both samplings, the weighted counts in rings of theta
must be the isotropic ones, N (cos theta_a - cos theta_b) / 2 (N: number
of events); the "log" sampling puts more particles near the axis.
"""

import numpy as np
import uproot
import opengate as gate
from opengate.tests import utility


def run(paths, sampling, n):
    m = gate.g4_units.m
    cm = gate.g4_units.cm
    nm = gate.g4_units.nm
    keV = gate.g4_units.keV
    deg = gate.g4_units.deg

    sim = gate.Simulation()
    sim.output_dir = paths.output
    sim.random_seed = 123456
    sim.world.size = [2 * m, 2 * m, 2 * m]
    sim.world.material = "G4_Galactic"

    plane = sim.add_volume("Box", "plane")
    plane.size = [1.8 * m, 1.8 * m, 1 * nm]
    plane.translation = [0, 0, -10 * cm]
    plane.material = "G4_Galactic"

    source = sim.add_source("GenericSource", "source")
    source.particle = "gamma"
    source.energy.mono = 140 * keV
    source.position.type = "point"
    source.direction.type = "iso"
    source.number_of_primaries = n
    aa = source.direction.angular_acceptance
    aa.policy = "ForceDirection"
    aa.enable_intersection_check = False
    aa.enable_angle_check = True
    aa.target_volumes = [plane.name]
    aa.angle_check_reference_vector = [0, 0, -1]
    aa.angle_tolerance_max = 30 * deg
    aa.angle_sampling = sampling
    aa.angle_sampling_scale = 3 * deg

    phsp = sim.add_actor("PhaseSpaceActor", "phsp")
    phsp.attached_to = plane.name
    phsp.attributes = ["PreDirection", "Weight"]
    phsp.output_filename = f"test085_fd_sampling_{sampling}.root"

    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option4"
    sim.run(start_new_process=True)

    df = uproot.open(phsp.get_output_path())["phsp"].arrays(library="np")
    theta = np.arccos(np.clip(-df["PreDirection_Z"], -1, 1))
    return theta / deg, df["Weight"]


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, None, "test085")
    n = 200000
    edges = np.array([0, 2, 5, 10, 20, 30])
    expected = n * (np.cos(np.radians(edges[:-1])) - np.cos(np.radians(edges[1:]))) / 2

    is_ok = True
    near_axis = {}
    for sampling in ("uniform", "log"):
        theta, w = run(paths, sampling, n)
        b = len(theta) == n
        utility.print_test(b, f"{sampling}: {len(theta)} particles on the plane ({n})")
        is_ok = is_ok and b
        counts, _ = np.histogram(theta, bins=edges, weights=w)
        var, _ = np.histogram(theta, bins=edges, weights=w**2)
        z = (counts - expected) / np.sqrt(var)
        for i in range(len(expected)):
            b = abs(z[i]) < 4
            utility.print_test(
                b,
                f"{sampling}: ring {edges[i]}-{edges[i + 1]} deg, weighted "
                f"{counts[i]:.1f} vs expected {expected[i]:.1f} (z {z[i]:+.2f})",
            )
            is_ok = is_ok and b
        near_axis[sampling] = np.mean(theta < 5)

    b = near_axis["log"] > 3 * near_axis["uniform"]
    utility.print_test(
        b,
        f"fraction of the particles below 5 deg: log {near_axis['log']:.3f}, "
        f"uniform {near_axis['uniform']:.3f} (log > 3 x uniform)",
    )
    is_ok = is_ok and b
    utility.test_ok(is_ok)
