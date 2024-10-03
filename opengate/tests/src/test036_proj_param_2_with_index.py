#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import test036_adder_depth_helpers as t036
from opengate.tests import utility
from opengate import g4_units

if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, "gate_test036_adder_depth", "test036"
    )

    # create and run the simulation
    mm = g4_units.mm
    sim = t036.create_simulation("param", paths)

    # enlarge the source
    source = sim.source_manager.get_source_info("src2")
    source.position.radius = 150 * mm

    # add a proj actor to a repeated volume
    proj = sim.add_actor("DigitizerProjectionActor", "proj2")
    proj.attached_to = "SPECThead"  # <-- there is two copy
    proj.physical_volume_index = 0  # <-- the first one is considered
    proj.output_filename = "proj2.mha"
    proj.size = [128, 128]
    proj.spacing = [5 * mm, 5 * mm]

    # start simulation
    sim.run()

    # test the output
    stats = sim.get_actor("Stats")
    is_ok = utility.assert_images(
        paths.output_ref / "proj1.mha",
        proj.get_output_path(),
        stats,
        tolerance=38,
        ignore_value=0,
        axis="y",
        sum_tolerance=1.5,
        fig_name=paths.output / f"proj_index.png",
    )
    utility.print_test(is_ok, f"Compare image proj:")
    utility.test_ok(is_ok)
