#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import test060_phsp_source_helpers as t
import opengate as gate
import uproot
import numpy as np
import gatetools.phsp as phsp
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
deg: float = gate.g4_units.deg


def create_root_file(file_name):
    # create numpy arrays
    kinetic_energy = np.array([100, 2.0, 3.0, 80, 2.0, 3.0, 2.0, 110.0, 3.0, 111.0, 2])
    pdg_code = np.array([2212, 11, 11, 2212, 11, 11, 11, 2212, 11, 2212, 11])
    pre_direction_local_x = np.zeros(11)
    pre_direction_local_y = np.zeros(11)
    pre_direction_local_z = np.ones(11)
    pre_position_local_x = np.zeros(11)
    pre_position_local_y = np.zeros(11)
    pre_position_local_z = np.zeros(11)
    pre_direction_x = np.zeros(11)
    pre_direction_y = np.zeros(11)
    pre_direction_z = np.ones(11)
    pre_position_x = np.zeros(11)
    pre_position_y = np.zeros(11)
    pre_position_z = np.zeros(11)
    weight = np.ones(11)

    # generate root file
    tfile = uproot.recreate(file_name)
    tfile["PhaseSpace1"] = {
        "KineticEnergy": kinetic_energy,
        "PDGCode": pdg_code,
        "PreDirectionLocal_X": pre_direction_local_x,
        "PreDirectionLocal_Y": pre_direction_local_y,
        "PreDirectionLocal_Z": pre_direction_local_z,
        "PrePositionLocal_X": pre_position_local_x,
        "PrePositionLocal_Y": pre_position_local_y,
        "PrePositionLocal_Z": pre_position_local_z,
        "PreDirection_X": pre_direction_x,
        "PreDirection_Y": pre_direction_y,
        "PreDirection_Z": pre_direction_z,
        "PrePosition_X": pre_position_x,
        "PrePosition_Y": pre_position_y,
        "PrePosition_Z": pre_position_z,
        "Weight": weight,
    }
    tfile.close()


def main():
    print("create reference PhS file")
    create_root_file(paths.output / "test_phs.root")

    print("testing until primary")
    t.test_source_until_primary(
        source_file_name=paths.output / "test_phs.root",
        phs_file_name_out=paths.output / "test_source_untilPrimary.root",
    )

    # load data from root file
    data_ref, keys_ref, m_ref = phsp.load(
        paths.output / "test_source_untilPrimary.root"
    )
    # the root file should contain 9 particles
    # print(m_ref)

    # there should be 3 protons in the root file
    index = keys_ref.index("PDGCode")
    particle_list = data_ref[:, index]
    # print(particle_list)
    count = np.count_nonzero(particle_list == 2212)
    is_ok = False
    if m_ref == 9 and count == 3:
        is_ok = True
        print("test ok")

    # this is the end, my friend
    utility.test_ok(is_ok)


if __name__ == "__main__":
    main()
