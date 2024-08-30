#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import test019_linac_phsp_helpers as test019
from opengate.tests import utility

if __name__ == "__main__":
    sim = test019.init_test019(1)

    # start simulation
    sim.run()

    # print results
    stats = sim.get_actor("Stats")
    print(stats)

    h = sim.get_actor("PhaseSpace")
    print(h)

    # check the phsp tree if PDGCode is in there
    # PDGCode of gamma is 22
    print()
    fn2 = h.get_output_path()
    print("Checked Tree : ", fn2)
    data, keys, m = test019.phsp.load(fn2)
    print(data, keys)
    # find PDGCode
    if "PDGCode" in keys:
        print("PDGCode key found")
        # all particles should be gamma, we check only first one
        # PDGCode of gamma is 22
        if data[0, keys.index("PDGCode")] == 22:
            is_ok = True
            # ~ print("index: ",keys.index("PDGCode"))
        else:
            is_ok = False

    else:
        is_ok = False

    # this is the end, my friend
    utility.test_ok(is_ok)
