#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import test019_linac_phsp_helpers as test019

if __name__ == "__main__":
    sim = test019.init_test019(1)

    s = sim.volume_manager.print_volume_tree()
    source = sim.get_source_user_info("Default")

    test019.run_test019(sim)
