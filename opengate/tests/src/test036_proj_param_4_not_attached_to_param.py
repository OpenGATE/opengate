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

    # sim.visu = True
    sim.visu_type = "qt"

    # remove one head
    head = sim.volume_manager.get_volume("SPECThead")
    head.translation = head.translation[0]
    head.rotation = head.rotation[0]

    # test another case that should fail
    proj2 = sim.add_actor("DigitizerProjectionActor", "proj2")
    proj2.attached_to = "crystal_pixel"
    proj2.output_filename = "proj2.mha"
    proj2.size = [128, 128]
    proj2.spacing = [5 * mm, 5 * mm]

    is_ok = True
    try:
        sim.run(start_new_process=True)
        is_ok = False
    except:
        pass
    utility.print_test(is_ok, f"The run should NOT be executed: ")
    utility.test_ok(is_ok)
