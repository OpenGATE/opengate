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

    # add a proj actor: it should not run because one of its parent is repeated
    proj = sim.add_actor("DigitizerProjectionActor", "proj")
    proj.attached_to = "crystal"
    proj.output_filename = "proj1.mha"
    proj.size = [128, 128]
    proj.spacing = [5 * mm, 5 * mm]

    # start simulation
    is_ok = True
    try:
        sim.run()
        is_ok = False
    except:
        pass
    utility.print_test(is_ok, f"The simulation should not run")

    utility.test_ok(is_ok)
