#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from test094_helpers import *


def go():

    paths = utility.get_default_test_paths(__file__, output_folder="test099_pytomo")
    data_path = paths.data / "test099_pytomo"

    visu = False
    n_primary = 1e7
    sc = define_spect_config(data_path, visu, n_primary)
    sim = gate.Simulation()
    setup_scatter_simulation(sc, sim, visu)

    # run scatter
    sim.run(start_new_process=True)
    stats = sim.find_actors("stats")[0]
    print(stats)


if __name__ == "__main__":
    go()
