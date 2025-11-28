#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate_core as g4
from opengate.geometry.utility import vec_g4_as_np, rot_g4_as_np
from opengate.exception import fatal
from opengate.utility import g4_units
import yaml
import uproot


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
    config = {
        "data_file": "coinc.dat",
        "data_type": "GATE",
        "n_events": 0,
        "starts_at": 0,
        "E0": [],
        "remove_out_of_range_energies": False,
        "energy_range": [120, 150],
        "energy_threshold": 5,
        "log_dir": None,
        "cameras": {
            "n_cameras": 0,
            "common_attributes": {
                "n_sca_layers": 0,
                "sca_material": "Si",
                "abs_material": "Si",
                "n_absorbers": 0,
            },
            "position_0": {
                "frame_origin": [0, 0, 0],
                "Ox": [1, 0, 0],  # parallel to scatterer edge
                "Oy": [0, 1, 0],  # parallel to scatterer edge
                "Oz": [0, 0, 1],  # orthogonal to the camera, tw the source"
            },
        },
        "volume": {
            "volume_dimensions": [10, 10, 10],  # in cm?
            "n_voxels": [50, 50, 1],  # in voxels
            "volume_centre": [0, 0, 0],  # in cm?
        },
        "lm_mlem": {
            "cone_thickness": "angular",
            "model": "cos1rho2",
            "last_iter": 0,
            "first_iter": 0,
            "n_sigma": 2,
            "width_factor": 1,
            "checkpoint_dir": "checkpoints",
            "save_every": 76,
            "sensitivity": False,
            "sensitivity_model": "like_system_matrix",
            "sensitivity_point_samples": 1,
        },
    }

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
    print("todo")
