#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import test019_linac_phsp_helpers as t

if __name__ == "__main__":
    sim = t.init_test019(1)

    s = sim.dump_tree_of_volumes()
    print(s)
    source = sim.get_source_user_info("Default")

    t.run_test019(sim)
