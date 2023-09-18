#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import test060_PhsSource_helpers as t
import opengate as gate


paths = gate.get_default_test_paths(
    __file__, "test060_PhsSource_ParticleName_direct", output_folder="test060"
)

# units
m = gate.g4_units("m")
mm = gate.g4_units("mm")
cm = gate.g4_units("cm")
nm = gate.g4_units("nm")
Bq = gate.g4_units("Bq")
MeV = gate.g4_units("MeV")
deg: float = gate.g4_units("deg")


def main():
    print("create reference PhS file")
    t.create_test_Phs(
        particle="proton",
        phs_name=paths.output / "test_proton_offset",
        number_of_particles=1,
        translation=[10 * cm, 5 * cm, 0 * mm],
    )
    print("Testing PhS source particle name")
    t.test_source_name(
        source_file_name=paths.output / "test_proton_offset.root",
        phs_file_name_out=paths.output / "test_source_electron.root",
    )
    is_ok = t.check_value_from_root_file(
        file_name_root=paths.output / "test_source_electron.root",
        key="ParticleName",
        ref_value="e-",
    )
    # this is the end, my friend
    gate.test_ok(is_ok)


if __name__ == "__main__":
    main()
