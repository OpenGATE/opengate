#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import test028_ge_nm670_spect_2_helpers as test028
from opengate.tests import utility
from pathlib import Path

if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, "", output_folder="test028_proj_mt"
    )

    # create the simulation
    sim = gate.Simulation()
    cm = gate.g4_units.cm

    # main description
    spect = test028.create_spect_simu(sim, paths, 4)
    proj = test028.test_add_proj(sim)

    # rotate spect
    test028.nm670.rotate_gantry(spect, 10 * cm, -15)

    # go
    sim.run()

    # check
    proj_out = sim.get_actor("Projection")
    output_ref_folder = Path(str(paths.output_ref).replace("_mt", ""))
    output_ref_filename = "proj028_counts.mhd".replace("_mt", "")
    print(output_ref_folder)
    print(output_ref_filename)
    is_ok = test028.test_spect_proj(
        sim, paths, proj_out, output_ref_folder, output_ref_filename
    )

    utility.test_ok(is_ok)
