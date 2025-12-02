#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import test060_phsp_source_helpers as t
import opengate as gate
from opengate.tests import utility


paths = utility.get_default_test_paths(
    __file__, "test060_PhsSource_ParticleName_direct", output_folder="test060"
)

# units
m = gate.g4_units.m
mm = gate.g4_units.mm
cm = gate.g4_units.cm
nm = gate.g4_units.nm
Bq = gate.g4_units.Bq
MeV = gate.g4_units.MeV
deg = gate.g4_units.deg


def main():
    print("create reference PhS file")
    t.create_test_phs(
        particle="proton",
        phs_name=paths.output / "test_proton_offset",
        number_of_particles=1,
        translation=[10 * cm, 5 * cm, 0 * mm],
    )
    print("testing rotation")
    t.test_source_rotation(
        source_file_name=paths.output / "test_proton_offset.root",
        phs_file_name_out=paths.output / "test_source_rotation.root",
    )

    dirX_ok = t.check_value_from_root_file(
        file_name_root=paths.output / "test_source_rotation.root",
        key="PreDirection_X",
        ref_value=0,
    )
    print("PhS source rotation dirX_ok is correct: ", dirX_ok)

    dirY_ok = t.check_value_from_root_file(
        file_name_root=paths.output / "test_source_rotation.root",
        key="PreDirection_Y",
        ref_value=-0.5,
    )
    print("PhS source rotation dirY_ok is correct: ", dirY_ok)

    dirZ_ok = t.check_value_from_root_file(
        file_name_root=paths.output / "test_source_rotation.root",
        key="PreDirection_Z",
        ref_value=(1.0 - 0.5**2) ** 0.5,
    )
    print("PhS source rotation dirZ_ok is correct: ", dirZ_ok)

    # this is the end, my friend
    utility.test_ok(dirX_ok and dirY_ok and dirZ_ok)


if __name__ == "__main__":
    main()
