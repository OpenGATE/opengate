#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import uproot
from opengate.tests import utility
from opengate.contrib.protonct.protonct import protonct


def compare_root_files(path1, path2, tree):
    tree1 = uproot.open(path1)[tree]
    df1 = tree1.arrays(library="pd")

    tree2 = uproot.open(path2)[tree]
    df2 = tree2.arrays(library="pd")

    return df1.equals(df2)


if __name__ == "__main__":
    # =====================================================
    # INITIALISATION
    # =====================================================

    paths = utility.get_default_test_paths(__file__, output_folder="test101_protonct")

    protonct(paths.output, projections=10, protons_per_projection=100, seed=1234)

    # =====================================================
    # Perform test
    # =====================================================

    path_phasespace_in = paths.output / "PhaseSpaceIn.root"
    path_phasespace_out = paths.output / "PhaseSpaceOut.root"

    path_reference_phasespace_in = paths.output_ref / "PhaseSpaceIn.root"
    path_reference_phasespace_out = paths.output_ref / "PhaseSpaceOut.root"

    print(path_reference_phasespace_in)
    print(path_reference_phasespace_out)
    print(path_phasespace_in)
    print(path_phasespace_out)

    is_ok = compare_root_files(
        path_reference_phasespace_in, path_phasespace_in, "PhaseSpaceIn"
    )
    print(is_ok)
    is_ok = is_ok and compare_root_files(
        path_reference_phasespace_out, path_phasespace_out, "PhaseSpaceOut"
    )

    utility.test_ok(is_ok)
