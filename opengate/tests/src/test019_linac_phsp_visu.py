#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import test019_linac_phsp_helpers as t
import opengate as gate

if __name__ == "__main__":
    sim = t.init_test019(1)

    sim.user_info.visu = True
    sim.user_info.visu_type = "vrml"
    sim.user_info.visu_filename = "geant4VisuFile.wrl"

    source = sim.get_source_user_info("Default")
    Bq = gate.g4_units("Bq")
    source.activity = 1 * Bq

    s = sim.dump_tree_of_volumes()
    print(s)

    t.run_test019(sim)
