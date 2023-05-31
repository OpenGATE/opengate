#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import test019_linac_phsp_helpers as t
import opengate as gate

sim = t.init_test019(1)

s = sim.dump_tree_of_volumes()
print(s)

# sim.user_info.visu = True
source = sim.get_source_user_info("Default")
Bq = gate.g4_units("Bq")
# source.activity = 1 * Bq

t.run_test019(sim)
