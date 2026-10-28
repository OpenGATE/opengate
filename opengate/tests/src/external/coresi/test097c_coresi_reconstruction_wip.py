#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate.tests.utility as utility
from opengate.actors.coincidences import *
import opengate.contrib.compton_camera.coresi_helpers as ch

if __name__ == "__main__":

    # get tests paths
    paths = utility.get_default_test_paths(
        __file__, gate_folder="", output_folder="test097_coresi_ccmod"
    )
    output_folder = paths.output
    data_folder = paths.data

    # Create default coresi config file
    coresi_config = ch.coresi_new_config()

    # set the main coresi parameters
    data_filename = output_folder / "coincidences.dat"
    coresi_config["data_file"] = str(data_filename)
    coresi_config["n_events"] = 1000  # max number of events to process
    coresi_config["E0"] = [662]  # in keV
    coresi_config["energy_range"] = [100, 700]  # in keV

    # set the camera parameters from macaco1
    coresi_config["cameras"]["n_cameras"] = 1

    # scatterer layer (cm) volume name = "*_scatterer" (in holder1)
    ca = coresi_config["cameras"]["common_attributes"]
    ca["n_sca_layers"] = 1
    ca["sca_material"] = "LaBr3"
    ca["sca_layer_0"]["center"] = [0, 0, -2.74 - 0.01]
    ca["sca_layer_0"]["size"] = [2.72, 2.68, 0.50]

    # absorber layer (cm) volume name = "*_absorber" (in holder2)
    ca["n_absorbers"] = 1
    ca["abs_material"] = "LaBr3"
    ca["abs_layer_0"]["center"] = [0, 0, 2.51 - 0.01]
    ca["abs_layer_0"]["size"] = [3.24, 3.60, 1]

    # (single) camera position
    p = coresi_config["cameras"]["position_0"]
    p["frame_origin"] = [0, 0, -10]  # camera at -10 cm from the source
    p["Ox"] = [1, 0, 0]  # parallel to scatterer edge
    p["Oy"] = [0, 1, 0]  # parallel to scatterer edge
    p["Oz"] = [0, 0, 1]  # orthogonal to the camera, tw the source

    # reconstructed volume dimension
    v = coresi_config["volume"]
    v["volume_dimensions"] = [5, 5, 5]  # total size in cm
    v["n_voxels"] = [21, 21, 21]  # nb of voxels in each dimension
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
    print(f'Running coresi with command: "coresi -c {config_filename}"')
    coresi.main.run()
