#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
import pathlib
import os
import subprocess

# This test is to be run after test069_sim_as_dict.py
# It checks whether the simulation is recreated correctly from the JSON file,
# but does not actually run any simulation.

if __name__ == "__main__":
    pathFile = pathlib.Path(__file__).parent.resolve()
    paths = utility.get_default_test_paths(__file__)

    # the test069_sim_as_dict.py is needed first
    if not os.path.isfile(paths.output / "simu_test069.json"):
        print(f"Running test069_sim_as_dict.py")
        subprocess.call(["python", paths.current / "test069_sim_as_dict.py"])

    # create the simulation
    sim = gate.create_sim_from_json(paths.output / "test069" / "simu_test069.json")

    # Assert that objects have been read back correctly
    assert "rod" in sim.volume_manager.volumes
    m = gate.g4_units.m
    assert sim.volume_manager.world_volume.size == [1.5 * m, 1.5 * m, 1.5 * m]
    assert "rod_region" in sim.physics_manager.regions
    assert pathlib.Path(paths.output / "test069" / "patient-4mm.mhd").exists()
    assert (
        sim.volume_manager.get_volume("waterbox_with_hole").creator_volumes[0].name
        == "Waterbox"
    )

    # If we make it until here without exception, the test is passed
    utility.test_ok(True)
