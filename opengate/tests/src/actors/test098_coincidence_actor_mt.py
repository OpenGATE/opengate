#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import opengate.tests.utility as utility
from opengate.actors.coincidences import CoincidenceSorter
from test098_coincidence_helpers import compare_coincidences
from test098_coincidence_simulation import create_simulation

if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, gate_folder="", output_folder="test098_coincidence_actor_mt"
    )

    sec = gate.g4_units.s

    sim, cc, root_filename = create_simulation(paths, num_threads=2)

    for policy in [
        "RemoveMultiples",
        "TakeAllGoods",
        "TakeWinnerOfGoods",
        "TakeIfOnlyOneGood",
        "TakeWinnerIfIsGood",
        "TakeWinnerIfAllAreGoods",
    ]:
        cc.multiples_policy = policy
        sim.run(start_new_process=True)

        # Calculate the coincidences using the Python implementation.
        sorter = CoincidenceSorter()
        sorter.window = 1e-9 * sec
        sorter.multiples_policy = policy

        coincidences_python = sorter.run(root_filename, "singles")

        # Check that the coincidences from the CoincidenceSorterActor are identical.
        identical = compare_coincidences(coincidences_python, str(root_filename))
        if identical:
            print(f"Policy '{policy}': OK")
        else:
            print(f"Policy '{policy}': not OK")
            utility.test_ok(False)

    utility.test_ok(True)
