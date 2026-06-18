#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
import uproot
from opengate.contrib.protonct.protonct import protonct
from opengate.tests import utility


def load_tree_arrays(path, tree_name):
    with uproot.open(path) as root_file:
        tree = root_file[tree_name]
        arrays = tree.arrays(library="np")
        return tree.num_entries, arrays


def check_phase_space(
    path,
    tree_name,
    expected_z,
    expected_entries=None,
    min_entries=None,
    max_entries=None,
):
    num_entries, arrays = load_tree_arrays(path, tree_name)
    is_ok = True

    if expected_entries is not None:
        is_ok = (
            utility.print_test(
                int(num_entries) == expected_entries,
                f"{tree_name} entries: {int(num_entries)} (expected {expected_entries})",
            )
            and is_ok
        )
    else:
        is_ok = (
            utility.print_test(
                min_entries <= int(num_entries) <= max_entries,
                f"{tree_name} entries: {int(num_entries)} (expected in [{min_entries}, {max_entries}])",
            )
            and is_ok
        )

    run_ids = np.unique(arrays["RunID"])
    is_ok = (
        utility.print_test(
            len(run_ids) == 10 and np.array_equal(run_ids, np.arange(10)),
            f"{tree_name} run ids: {run_ids.tolist()}",
        )
        and is_ok
    )

    kinetic_energy = arrays["KineticEnergy"]
    is_ok = (
        utility.print_test(
            np.all(kinetic_energy > 0),
            f"{tree_name} positive kinetic energy",
        )
        and is_ok
    )

    z_positions = arrays["Position_Z"]
    is_ok = (
        utility.print_test(
            np.allclose(z_positions, expected_z, atol=1e-6),
            f"{tree_name} z position fixed at {expected_z}",
        )
        and is_ok
    )

    direction_z = arrays["Direction_Z"]
    is_ok = (
        utility.print_test(
            np.all(direction_z > 0),
            f"{tree_name} forward-going tracks",
        )
        and is_ok
    )

    return is_ok, arrays


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, output_folder="test101_protonct")

    projections = 10
    protons_per_projection = 100
    expected_in_entries = projections * protons_per_projection

    protonct(
        paths.output,
        projections=projections,
        protons_per_projection=protons_per_projection,
        seed=1234,
    )

    path_phasespace_in = paths.output / "PhaseSpaceIn.root"
    path_phasespace_out = paths.output / "PhaseSpaceOut.root"

    is_ok_in, in_arrays = check_phase_space(
        path_phasespace_in,
        "PhaseSpaceIn",
        expected_z=-109.9999995,
        expected_entries=expected_in_entries,
    )
    is_ok_out, out_arrays = check_phase_space(
        path_phasespace_out,
        "PhaseSpaceOut",
        expected_z=110.0000005,
        min_entries=850,
        max_entries=950,
    )

    is_ok = is_ok_in and is_ok_out

    mean_in_energy = float(np.mean(in_arrays["KineticEnergy"]))
    mean_out_energy = float(np.mean(out_arrays["KineticEnergy"]))
    is_ok = (
        utility.print_test(
            mean_out_energy < mean_in_energy,
            f"Mean output energy lower than input energy: {mean_out_energy:.3f} < {mean_in_energy:.3f}",
        )
        and is_ok
    )

    utility.test_ok(is_ok)
