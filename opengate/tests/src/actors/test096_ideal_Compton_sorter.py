#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from opengate.actors.coincidences import ccmod_ideal_singles
from opengate.actors.coincidences import ccmod_ideal_coincidences
from opengate.actors.coincidences import ccmod_make_cones
import uproot
import numpy as np
import pandas as pd
from test096_ideal_Compton_sorter_helpers import *


def main():

    # If output_singles.root does not exist, run a simulation to generate it
    paths = utility.get_default_test_paths(__file__, output_folder="test096")
    root_filename = paths.output / "PhaseSpace.root"
    create_and_run_cc_simulation()

    root_file = uproot.open(root_filename)
    phSp_tree = root_file["PhaseSpace"]
    n = int(phSp_tree.num_entries)
    print(f"There are {n} hits saved")
    # save it into pandas data frame
    data = phSp_tree.arrays(library="pd")

    data_singles = ccmod_ideal_singles(data)
    data_coinc = ccmod_ideal_coincidences(data_singles)
    data_cones = ccmod_make_cones(data_coinc, energy_key_name="IdealTotalEnergyDeposit")

    # compare cones from GATE9 and from GATE10
    # Compare with reference output

    ref_folder = paths.output_ref
    ref_filename = ref_folder / "CC_idealprocessing_Singles.root"
    file = uproot.open(ref_filename)
    Sn = file["Singles"]
    data_GATE9 = Sn.arrays(library="pd")
    data_GATE9 = data_GATE9.drop(
        columns=["layerName"]
    )  # To avoid warning coming from conversion to pd
    data_GATE9 = data_GATE9.drop(
        columns=["volumeID"]
    )  # To avoid warning coming from conversion to pd

    data_GATE9["IdealTotalEnergyDeposit"] = (
        data_GATE9["energyIni"] - data_GATE9["energyFinal"]
    )
    # by hand since different  attribute names and pre-processing
    nSingles = data_GATE9["eventID"].value_counts()
    # keep only events with more than one nSingles
    data_GATE9 = data_GATE9[data_GATE9["eventID"].isin(nSingles[nSingles > 1].index)]
    data_GATE9["CoincID"] = pd.factorize(data_GATE9["eventID"])[0]

    data_cones_GATE9 = ccmod_make_cones(
        data_GATE9,
        energy_key_name="IdealTotalEnergyDeposit",
        posX_key_name="globalPosX",
        posY_key_name="globalPosY",
        posZ_key_name="globalPosZ",
    )

    keV = gate.g4_units.keV
    E1 = data_cones["Energy1"] / keV
    E1_GATE9 = data_cones_GATE9["Energy1"] / keV

    is_ok = utility.check_diff(
        np.mean(E1), np.mean(E1_GATE9), 5, f"Energy mean  difference in keV:"
    )
    # The test is not ok. But either with physics knowledge
    is_ok = (
        utility.check_diff(
            np.max(E1), np.max(E1_GATE9), 1, f"Energy max difference in keV:"
        )
        and is_ok
    )
    # 477.6keV for back scattering of 662 keV
    is_ok = (
        utility.check_diff(
            len(E1), len(E1_GATE9), 5, f"Number of coincidences difference :"
        )
        and is_ok
    )
    #

    # plot
    # f, ax = plt.subplots(1, 2, figsize=(25, 10))
    # utility.plot_hist(ax[0], E1, f"E1 (keV)")
    # utility.plot_hist(ax[0], E1_GATE9, f"E1(keV) GATE9 )")

    # fn = paths.output / "test096_ideal_coinc_opt2.png"
    # plt.savefig(fn)
    # print(f"Plot in {fn}")

    utility.test_ok(is_ok)


if __name__ == "__main__":
    main()
