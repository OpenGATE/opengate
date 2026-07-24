#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
import uproot
from opengate.tests.src.geometry.test019_phsp_actor_helpers import (
    build_phsp_actor_simulation,
)

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "", output_folder="test019")
    sec = gate.g4_units.s

    sim, source, stats_actor, ta2 = build_phsp_actor_simulation(
        paths.output,
        [(0.0 * sec, 1.0 * sec)],
        66,
        random_seed=321654,
    )

    # run the simulation once with no particle in the phsp
    source.direction.momentum = [0, 0, 1]
    ta2.output_filename = "test019_phsp_actor_empty.root"

    # run
    sim.run(start_new_process=True)
    print(stats_actor)

    # check if empty (the root file does not exist)
    is_ok = ta2.total_number_of_entries == 0
    utility.print_test(is_ok, f"empty phase space = {ta2.total_number_of_entries}")
    print()

    # redo with the right direction
    source.direction.momentum = [0, 0, -1]
    ta2.output_filename = "test019_phsp_actor.root"
    sim.run(start_new_process=True)
    print(stats_actor)

    # check if exists and NOT empty
    hits = uproot.open(ta2.get_output_path_string())["PhaseSpace"]
    is_ok2 = source.n - 10 < hits.num_entries < source.n + 10
    utility.print_test(is_ok2, f"Number of entries = {hits.num_entries} / {source.n}")
    print()

    is_ok = is_ok and is_ok2
    utility.test_ok(is_ok)
