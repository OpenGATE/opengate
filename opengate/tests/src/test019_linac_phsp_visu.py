#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import test019_linac_phsp_helpers as test019
import opengate as gate

if __name__ == "__main__":
    sim = test019.init_test019(1)

    sim.user_info.visu = True
    sim.user_info.visu_type = "vrml"
    sim.user_info.visu_filename = "geant4VisuFile.wrl"

    source = sim.get_source_user_info("Default")
    Bq = gate.g4_units.Bq
    source.activity = 1 * Bq

    s = sim.dump_tree_of_volumes()
    print(s)

    test019.run_test019(sim)
