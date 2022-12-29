#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import test019_linac_phsp_helpers as t

sim = t.init_test019(1)

s = sim.dump_volumes_tree()
print(s)

t.run_test019(sim)
