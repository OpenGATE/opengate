#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import yaml
import uproot
from pathlib import Path
import opengate_core as g4
from opengate.exception import fatal
from opengate.utility import g4_units
from opengate.geometry.utility import vec_g4_as_np, rot_g4_as_np


# --- Custom List for Inline YAML Formatting ---
class FlowList(list):
    """A custom list that will be dumped as [x, y, z] in YAML."""

    pass


def flow_list_representer(dumper, data):
    return dumper.represent_sequence("tag:yaml.org,2002:seq", data, flow_style=True)


yaml.add_representer(FlowList, flow_list_representer)


def convert_to_flowlist(data):
    """
    Recursively traverse the dictionary.
    Convert any list containing only simple scalars (int, float, str) to FlowList
    so they appear as [a, b, c] in the YAML output.
    """
    if isinstance(data, dict):
        return {k: convert_to_flowlist(v) for k, v in data.items()}
    elif isinstance(data, list):
        # Check if list is "simple" (contains only primitives, no dicts or nested lists)
        is_simple = all(
            isinstance(i, (int, float, str, bool)) or i is None for i in data
        )

        if is_simple:
            return FlowList(data)
        else:
            # If list contains complex objects, process them recursively but keep the list as is
            return [convert_to_flowlist(i) for i in data]
    else:
        return data


def coresi_new_config():
    # get current path of the script
    current_dir = Path(__file__).parent.resolve()
    print(current_dir)
    # read the yaml file
    with open(current_dir / "coresi_default_config.yaml", "r") as f:
        config = yaml.safe_load(f)
    return config


def set_hook_coresi_config(sim, cameras, filename):
    """
    Prepare everything to create the coresi config file at the init of the simulation.
    The param structure allows retrieving the coresi config at the end of the simulation.
    """
    # create the param structure
    param = {
        "cameras": cameras,
        "filename": filename,
        "coresi_config": coresi_new_config(),
    }
    sim.user_hook_after_init = create_coresi_config
    sim.user_hook_after_init_arg = param
    return param


def create_coresi_config(simulation_engine, param):
    # (note: simulation_engine is not used here but must be the first param)
    coresi_config = param["coresi_config"]
    cameras = param["cameras"]

    for camera in cameras.values():
        c = coresi_config["cameras"]
        c["n_cameras"] += 1
        scatter_layer_names = camera["scatter_layer_names"]
        absorber_layer_names = camera["absorber_layer_names"]

        for layer_name in scatter_layer_names:
            coresi_add_scatterer(coresi_config, layer_name)
        for layer_name in absorber_layer_names:
            coresi_add_absorber(coresi_config, layer_name)


def coresi_add_scatterer(coresi_config, layer_name):
    # find all volumes ('touchable' in Geant4 terminology)
    touchables = g4.FindAllTouchables(layer_name)
    if len(touchables) != 1:
        fatal(f"Cannot find unique volume for layer {layer_name}: {touchables}")
    touchable = touchables[0]

    # current nb of scatterers
    id = coresi_config["cameras"]["common_attributes"]["n_sca_layers"]
    coresi_config["cameras"]["common_attributes"]["n_sca_layers"] += 1
    layer = {
        "center": [0, 0, 0],
        "size": [0, 0, 0],
    }
    coresi_config["cameras"]["common_attributes"][f"sca_layer_{id}"] = layer

    # Get the information: WARNING in cm!
    cm = g4_units.cm
    translation = vec_g4_as_np(touchable.GetTranslation(0)) / cm
    solid = touchable.GetSolid(0)
    pMin_local = g4.G4ThreeVector()
    pMax_local = g4.G4ThreeVector()
    solid.BoundingLimits(pMin_local, pMax_local)
    size = [
        (pMax_local.x - pMin_local.x) / cm,
        (pMax_local.y - pMin_local.y) / cm,
        (pMax_local.z - pMin_local.z) / cm,
    ]
    layer["center"] = translation.tolist()
    layer["size"] = size


def coresi_add_absorber(coresi_config, layer_name):
    # find all volumes ('touchable' in Geant4 terminology)
    touchables = g4.FindAllTouchables(layer_name)
    if len(touchables) != 1:
        fatal(f"Cannot find unique volume for layer {layer_name}: {touchables}")
    touchable = touchables[0]

    # current nb of scatterers
    id = coresi_config["cameras"]["common_attributes"]["n_absorbers"]
    coresi_config["cameras"]["common_attributes"]["n_absorbers"] += 1
    layer = {
        "center": [0, 0, 0],
        "size": [0, 0, 0],
    }
    coresi_config["cameras"]["common_attributes"][f"abs_layer_{id}"] = layer

    # Get the information: WARNING in cm!
    cm = g4_units.cm
    translation = vec_g4_as_np(touchable.GetTranslation(0)) / cm
    solid = touchable.GetSolid(0)
    pMin_local = g4.G4ThreeVector()
    pMax_local = g4.G4ThreeVector()
    solid.BoundingLimits(pMin_local, pMax_local)
    size = [
        (pMax_local.x - pMin_local.x) / cm,
        (pMax_local.y - pMin_local.y) / cm,
        (pMax_local.z - pMin_local.z) / cm,
    ]
    layer["center"] = translation.tolist()
    layer["size"] = size


def coresi_write_config(coresi_config, filename):
    # Convert vectors to FlowList just before writing
    formatted_config = convert_to_flowlist(coresi_config)

    with open(filename, "w") as f:
        yaml.dump(
            formatted_config, f, default_flow_style=False, sort_keys=False, indent=2
        )


def coresi_convert_root_data(root_filename, branch_name, output_filename):
    root_file = uproot.open(root_filename)
    tree = root_file[branch_name]
    # Load all needed branches at once
    arrays = tree.arrays(
        ["X1", "Y1", "Z1", "Energy1", "X2", "Y2", "Z2", "EnergyRest"], library="np"
    )

    with open(output_filename, "w") as fout:
        n = len(arrays["X1"])
        for i in range(n):
            # Energy in keV and position in mm, as expected by coresi
            line = (
                f"2\t1\t"
                f"{arrays['X1'][i]:.2f}\t"
                f"{arrays['Y1'][i]:.2f}\t"
                f"{arrays['Z1'][i]:.2f}\t"
                f"{arrays['Energy1'][i]*1000:.2f}\t"
                f"2\t"
                f"{arrays['X2'][i]:.2f}\t"
                f"{arrays['Y2'][i]:.2f}\t"
                f"{arrays['Z2'][i]:.2f}\t"
                f"{arrays['EnergyRest'][i]*1000:.2f}\t"
                f"3\t0\t0\t0\t0\n"
            )
            fout.write(line)
