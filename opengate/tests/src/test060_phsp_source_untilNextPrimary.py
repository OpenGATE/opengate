import test060_phsp_source_helpers as t
import opengate as gate
import uproot
import numpy as np
import pandas as pd
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


def createRootFile(file_name):
    # # create pandas dataframe
    df = pd.DataFrame(
        {
            "KineticEnergy": [100, 2.0, 3.0, 80, 2.0, 3.0, 2.0, 110.0, 3.0, 111.0, 2],
            "PDGCode": [2212, 11, 11, 2212, 11, 11, 11, 2212, 11, 2212, 11],
            "PreDirectionLocal_X": np.zeros(11),
            "PreDirectionLocal_Y": np.zeros(11),
            "PreDirectionLocal_Z": np.ones(11),
            "PrePositionLocal_X": np.zeros(11),
            "PrePositionLocal_Y": np.zeros(11),
            "PrePositionLocal_Z": np.zeros(11),
            "PreDirection_X": np.zeros(11),
            "PreDirection_Y": np.zeros(11),
            "PreDirection_Z": np.ones(11),
            "PrePosition_X": np.zeros(11),
            "PrePosition_Y": np.zeros(11),
            "PrePosition_Z": np.zeros(11),
            "Weight": np.ones(11),
        }
    )
    # PDGCode proton = 2212
    # PDGCode electron = 11
    # PDGCode positron = -11
    # PDGCode photon = 22
    # PDGCode neutron = 2112
    # # "ParticleName": ["gamma", "e-", "e+"],
    # # df["ParticleName"] = df["ParticleName"].astype(str)
    # df = df.astype({"ParticleName": "char"})

    # print(df, df.dtypes)

    # generate root file
    tfile = uproot.recreate(file_name)

    tfile["PhaseSpace1"] = df
    tfile.close()


def main():
    print("create reference PhS file")
    createRootFile(paths.output / "test_phs.root")

    print("testing until primary")
    t.test_source_untilPrimary(
        source_file_name=paths.output / "test_phs.root",
        phs_file_name_out=paths.output / "test_source_untilPrimary.root",
    )

    is_ok = t.check_value_from_root_file(
        file_name_root=paths.output / "test_source_translation.root",
        key="PrePositionLocal_X",
        ref_value=30 * mm,
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
