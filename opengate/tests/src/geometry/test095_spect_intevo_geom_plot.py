#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from opengate.tests import utility
from test095_spect_helpers import *
import json

if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, gate_folder="", output_folder="test095"
    )

    p = intevo.get_geometrical_parameters()
    collimators = p.collimators
    # collimators = ["lehr"]
    n = len(collimators)
    collimators.append(collimators[0])
    is_ok = True

    i = 0
    for colli_type in collimators:
        # rotate the gantry only for the last collimator
        if i == n:
            radius = 20 * gate.g4_units.cm
            rotation = 12
        else:
            radius = 0
            rotation = 0

        sim, fn = build_test_simu(paths, "intevo", colli_type, rotation, radius)

        # go
        sim.run(start_new_process=True)

        # compare the json files
        ref_json_file = paths.output_ref / fn
        print(ref_json_file)
        j_ref = json.load(open(ref_json_file))
        j_test = json.load(open(sim.user_hook_after_init_arg))
        added, removed, modified, same = utility.dict_compare(
            j_ref,
            j_test,
            tolerance=1e5,
            ignored_keys=[
                "copy_no",
            ],
        )
        b = len(added) == 0 and len(removed) == 0 and len(modified) == 0
        utility.print_test(b, f"Compare json volume info with reference")
        is_ok = is_ok and b
        i = i + 1

    utility.test_ok(is_ok)
