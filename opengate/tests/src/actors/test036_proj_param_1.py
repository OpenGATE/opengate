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
    sim = t036.create_simulation("param", paths, "_par1")

    # sim.visu = True
    sim.visu_type = "qt"

    # remove one head
    head = sim.volume_manager.get_volume("SPECThead")
    head.translation = head.translation[0]
    head.rotation = head.rotation[0]

    # enlarge the source
    source = sim.source_manager.get_source("src2")
    source.position.radius = 150 * mm

    if sim.visu:
        source = sim.source_manager.get_source("src2")
        source.activity = source.activity / 1000
        source = sim.source_manager.get_source("src1")
        source.activity = source.activity / 1000

    # add a proj actor
    proj = sim.add_actor("DigitizerProjectionActor", "proj")
    proj.attached_to = "crystal"
    fname = "proj1.mha"
    proj.output_filename = fname.replace(".mha", "-1.mha")
    proj.size = [128, 128]
    proj.spacing = [5 * mm, 5 * mm]

    # start simulation
    sim.run()

    # test the output
    stats = sim.get_actor("Stats")
    is_ok = utility.assert_images(
        paths.output_ref / fname,
        proj.get_output_path("counts"),
        stats,
        tolerance=38,
        ignore_value_data2=0,
        axis="y",
        fig_name=paths.output / f"proj.png",
        sum_tolerance=1.5,
    )
    utility.print_test(is_ok, f"Compare image proj:")
    utility.test_ok(is_ok)
