#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import subprocess

from opengate.utility import g4_units
import opengate.tests.utility as utility
from opengate.actors.coincidences import *
import opengate.contrib.compton_camera.macaco as macaco
import opengate.contrib.compton_camera.coresi_helpers as ch


def main(dependency="test097a_ccmod_simulation.py"):
    # get tests paths
    paths = utility.get_default_test_paths(
        __file__, gate_folder="", output_folder="test097_coresi_ccmod"
    )
    output_folder = paths.output

    # units
    ns = g4_units.ns

    scatt_file = output_folder / "ThrScatt.root"
    abs_file = output_folder / "ThrAbs.root"

    # The test needs the output of the simulation step.
    # When this script is launched via the opengate_tests suite, the
    # dependency="test097a_ccmod_simulation.py" signature on main() is used by
    # the runner to schedule test097a before test097b. The fallback below is
    # only for standalone execution of this script.
    if not scatt_file.exists() or not abs_file.exists():
        subdir = os.path.dirname(__file__)
        print(f"Missing input singles files, running {dependency} first.")
        subprocess.call(["python", paths.current / subdir / dependency])

    if not scatt_file.exists() or not abs_file.exists():
        utility.test_ok(
            False,
            exceptions=[
                f"Required input files were not created: {scatt_file.name}, {abs_file.name}"
            ],
        )

    # compute the coincidences
    print(f"Computing coincidences from {scatt_file.name} and {abs_file.name}")
    merge_file = output_folder / "singles.root"
    coinc_file = output_folder / "coincidences.root"
    coincidences = macaco.macaco1_merge_and_compute_coincidences(
        scatt_file,
        abs_file,
        time_windows=12 * ns,
        output_root_filename=merge_file,
        scatt_tree_name="ThrScatt",
        abs_tree_name="ThrAbs",
        merged_tree_name="Singles",
    )
    root_write_trees(coinc_file, ["Coincidences"], [coincidences])
    print(f"Merged singles file: {merge_file}")
    print(f"Coincidences file: {coinc_file}")
    print(f"Number of singles in coincidences {len(coincidences)}")

    # Consider the coincidences from the macaco simulation
    # (no need to re-read the file, but this is to show an example)
    coinc_file = output_folder / "coincidences.root"
    if not coinc_file.exists():
        raise Exception(f"File {coinc_file} not found")
    coincidences = uproot.open(coinc_file)["Coincidences"].arrays(library="pd")
    print(f"Reading the coincidences file: {coinc_file.name}")
    print(f"Number of singles in coincidences : {len(coincidences)}")

    # cones
    print()
    print("Computing cones from the coincidences ...")
    data_cones = ccmod_make_cones(coincidences, energy_key_name="TotalEnergyDeposit")
    cones_filename = output_folder / "cones.root"
    root_write_trees(cones_filename, ["cones"], [data_cones])
    print(f"Cones file: {cones_filename.name}")
    print(f"Number of cones (coincidences) : {len(data_cones)}")

    # CORESI stage1: convert the root file
    print()
    print(f"Converting root cones to coresi data file format ...")
    data_filename = output_folder / "coincidences.dat"
    ch.coresi_convert_root_data(cones_filename, "cones", data_filename)
    print(f"Data file: {data_filename.name}")

    is_ok = (
        merge_file.exists()
        and coinc_file.exists()
        and cones_filename.exists()
        and data_filename.exists()
        and len(coincidences) > 0
        and len(data_cones) > 0
    )
    utility.test_ok(is_ok)


if __name__ == "__main__":
    main()
