#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import test061_TPPhsSource_helpers as t
import opengate as gate
from opengate.tests import utility

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, output_folder="test061")
    ref_path = paths.output_ref

    # units
    m = gate.g4_units.m
    mm = gate.g4_units.mm
    cm = gate.g4_units.cm
    nm = gate.g4_units.nm
    Bq = gate.g4_units.Bq
    MeV = gate.g4_units.MeV
    deg: float = gate.g4_units.deg

    # print("create reference PhS file")
    # t.create_test_Phs(
    #     particle="proton",
    #     phs_name=paths.output / "test_proton",
    #     number_of_particles=1,
    #     translation=[0 * cm, 0 * cm, 0 * mm],
    # )
    print("Testing TPPhS source rotations")

    sim = t.test_source_rotation_a(
        plan_file_name=ref_path / "PlanSpot.txt",
        phs_list_file_name="PhsList.txt",
        phs_folder_name=ref_path,
        output_dir=paths.output,
        phs_file_name_out="output.root",
    )

    file_name_root = sim.get_actor("PhaseSpace").get_output_path()

    a = t.check_value_from_root_file(
        file_name_root=file_name_root,
        key="KineticEnergy",
        ref_value=150 * MeV,
    )
    b = t.check_value_from_root_file(
        file_name_root=file_name_root,
        key="PrePositionLocal_X",
        ref_value=-60,
    )
    c = t.check_value_from_root_file(
        file_name_root=file_name_root,
        key="PrePositionLocal_Y",
        ref_value=50,
    )
    d = t.check_value_from_root_file(
        file_name_root=file_name_root,
        key="PrePositionLocal_Z",
        ref_value=0,
    )

    e = t.check_value_from_root_file(
        file_name_root=file_name_root,
        key="PreDirectionLocal_X",
        ref_value=-0.012,
    )
    f = t.check_value_from_root_file(
        file_name_root=file_name_root,
        key="PreDirectionLocal_Y",
        ref_value=0.01,
    )

    # this is the end, my friend
    utility.test_ok(all([a, b, c, d, e, f]))
