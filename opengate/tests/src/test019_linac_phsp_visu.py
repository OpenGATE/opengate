#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import test019_linac_phsp_helpers as test019
import opengate as gate

if __name__ == "__main__":
    sim = test019.init_test019(1)

    sim.visu = True
    sim.visu_type = "vrml"
    sim.visu_filename = "geant4VisuFile.wrl"

    source = sim.get_source_user_info("Default")
    source.activity = 1 * gate.g4_units.Bq

    print(sim.volume_manager.dump_volume_tree())

    test019.run_test019(sim)
