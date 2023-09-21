#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ~ import test019_linac_phsp_helpers as t
from test019_linac_phsp_helpers import *

if __name__ == "__main__":
    sim = init_test019(1)

    # start simulation
    sim.run()

    # print results
    stats = sim.output.get_actor("Stats")
    print(stats)

    h = sim.output.get_actor("PhaseSpace")
    print(h)

    # check the phsp tree if PDGCode is in there
    # PDGCode of gamma is 22
    print()
    fn2 = paths.output / "test019_hits.root"
    print("Checked Tree : ", fn2)
    data, keys, m = phsp.load(fn2)
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
    gate.test_ok(is_ok)
