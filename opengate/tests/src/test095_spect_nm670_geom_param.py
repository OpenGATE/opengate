#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from opengate.tests import utility
import opengate.contrib.spect.ge_discovery_nm670 as nm670

if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, gate_folder="", output_folder="test095"
    )

    # uncomment to regenerate the values
    # nm670.update_geometrical_parameters(store_to_file=True)

    p_ref = nm670.get_geometrical_parameters()
    p = nm670.update_geometrical_parameters()

    for key, v in p.items():
        print(f"{key}: {v}")

    added, removed, modified, same = utility.dict_compare(p, p_ref)
    if added or removed or modified:
        is_ok = False
        print("Error in the geometrical parameters")
        print(f"Added: {added}")
        print(f"Removed: {removed}")
        print(f"Modified: {modified}")
        print(f"Same: {same}")
        for key, v in p_ref.items():
            print(f"{key}: {v}")

    else:
        is_ok = True

    utility.test_ok(is_ok)
