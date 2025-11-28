#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from box import Box


def coresi_new_config():
    config = Box(
        {
            "data_file": "coinc.dat",
            "data_type": "GATE",
            "n_events": 0,
            "starts_at": 0,
            "E0": [],
            "remove_out_of_range_energies": False,
            "energy_range": [120, 150],
            "energy_threshold": 5,
            "log_dir": None,
            "cameras": {"n_cameras": 0},
            "volume": {
                "volume_dimensions": [10, 10, 10],  # in cm
                "n_voxels": [50, 50, 1],
                "volume_centre": [0, 0, 0],
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
    )
    return config
