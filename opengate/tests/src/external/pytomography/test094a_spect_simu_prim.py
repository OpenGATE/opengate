#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
from test099_helpers import *


def go():

    paths = utility.get_default_test_paths(__file__, output_folder="test099_pytomo")
    data_path = paths.data / "test099_pytomo" / "data"

    visu = False
    n_primary = 2e8
    n_primary = 2e7  # 27 min linux
    sc = define_spect_config(data_path, visu, n_primary)
    sim = gate.Simulation()
    sim.visu_type = "qt"

    setup_primary_simulation(sc, sim, visu)
    print(sc)

    # run primary only (no scatter)
    sim.run(start_new_process=False)
    stats = sim.find_actors("stats")[0]
    print(stats)


if __name__ == "__main__":
    go()
