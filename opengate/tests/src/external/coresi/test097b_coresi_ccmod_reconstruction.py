#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.utility import g4_units
import opengate.tests.utility as utility
from opengate.actors.coincidences import *
import opengate.contrib.compton_camera.macaco as macaco
import opengate.contrib.compton_camera.coresi_helpers as ch

if __name__ == "__main__":

    # get tests paths
    paths = utility.get_default_test_paths(
        __file__, gate_folder="", output_folder="test097_coresi_ccmod"
    )
    output_folder = paths.output
    data_folder = paths.data

    # units
    mm = g4_units.mm
    cm = g4_units.cm

    # Consider the coincidences from the macaco simulation
    coinc_file = output_folder / "coincidences.root"
    if not coinc_file.exists():
        raise Exception(f"File {coinc_file} not found")
    coincidences = uproot.open(coinc_file)["Coincidences"].arrays(library="pd")
    print(f"Coincidences file: {coinc_file}")
    print(f"Number of coincidences : {len(coincidences)}")

    print("Computing cones from the coincidences ...")
    data_cones = ccmod_make_cones(coincidences, energy_key_name="TotalEnergyDeposit")
    cones_filename = output_folder / "cones.root"
    root_write_trees(cones_filename, ["cones"], [data_cones])
    print(f"Cones file: {cones_filename.name}")
    print(f"Number of cones : {len(data_cones)}")

    # CORESI stage1: convert the root file
    print(f"Converting root cones to coresi data file format ...")
    data_filename = output_folder / "coincidences.dat"
    ch.coresi_convert_root_data(cones_filename, "cones", data_filename)
    print(f"Data file: {data_filename.name}")

    # Create default coresi config file
    coresi_config = ch.coresi_new_config()

    # set the main coresi parameters
    coresi_config["data_file"] = str(data_filename)
    coresi_config["n_events"] = len(data_cones)
    coresi_config["E0"] = 662  # in keV
    coresi_config["energy_range"] = [100, 700]  # in keV

    # set the camera parameters from macaco1
    coresi_config["cameras"]["n_cameras"] = 1

    # scatterer layer
    coresi_config["cameras"]["common_attributes"]["n_sca_layers"] = 1
    coresi_config["cameras"]["common_attributes"]["sca_material"] = "Si"
    coresi_config["cameras"]["common_attributes"]["sca_layer_0"]["center"] = [
        0,
        0,
        -2.74 + 0.26,
    ]  # cm
    coresi_config["cameras"]["common_attributes"]["sca_layer_0"]["size"] = [
        2.72,
        2.68,
        0.50,
    ]  # cm

    # absorber layer
    coresi_config["cameras"]["common_attributes"]["n_absorbers"] = 1
    coresi_config["cameras"]["common_attributes"]["abs_material"] = "Si"
    coresi_config["cameras"]["common_attributes"]["abs_layer_0"]["center"] = [
        0,
        0,
        2.51 + 0.51,
    ]  # cm
    coresi_config["cameras"]["common_attributes"]["abs_layer_0"]["size"] = [
        3.24,
        3.60,
        0.04,
    ]  # cm

    # (single) camera position
    p = coresi_config["cameras"]["position_0"]
    p["frame_origin"] = [0, 0, 0]
    p["Ox"] = [1, 0, 0]  # parallel to scatterer edge
    p["Oy"] = [0, 1, 0]  # parallel to scatterer edge
    p["Oz"] = [0, 0, 1]  # orthogonal to the camera, tw the source

    # reconstructed volume dimension
    v = coresi_config["volume"]
    v["volume_dimensions"] = [10, 10, 10]  # total size in cm
    v["n_voxels"] = [20, 20, 20]  # nb of voxels in each dimension
    v["volume_centre"] = [0, 0, 0]

    config_filename = output_folder / "coresi_config.yaml"
    ch.coresi_write_config(coresi_config, config_filename)
    print(f"Coresi config file: {config_filename}")

    # Mock the command line arguments
    sys.argv = ["coresi", "-c", str(config_filename)]

    # prepare coresi run
    try:
        import coresi.main
        import sys
    except ModuleNotFoundError:
        print(
            "Coresi module not available. Please install coresi first (https://github.com/CoReSi-SPECT/coresi)"
        )
        exit(1)

    # Run the reconstruction
    coresi.main.run()
