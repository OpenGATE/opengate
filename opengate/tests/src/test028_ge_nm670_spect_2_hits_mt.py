#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import test028_ge_nm670_spect_2_helpers as test028
from opengate.tests import utility
from pathlib import Path

if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, "", output_folder="test028_hits_mt"
    )

    # create the simulation
    sim = gate.Simulation()

    # main description
    test028.create_spect_simu(sim, paths, number_of_threads=3)

    # go
    sim.run()

    # check
    output_ref_folder = Path(str(paths.output_ref).replace("_mt", ""))
    output_ref_filename = "proj028_counts.mhd".replace("_mt", "")
    print(output_ref_folder)
    print(output_ref_filename)
    is_ok = test028.test_spect_root(sim, paths)

    utility.test_ok(is_ok)
