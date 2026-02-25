#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.utility import g4_units
import opengate.tests.utility as utility
from opengate.actors.coincidences import *
import opengate.contrib.compton_camera.macaco as macaco
from scipy.spatial.transform import Rotation
import opengate.contrib.compton_camera.coresi_helpers as coresi

if __name__ == "__main__":

    # get tests paths
    paths = utility.get_default_test_paths(
        __file__, gate_folder="", output_folder="test097_coresi_ccmod"
    )
    output_folder = paths.output
    data_folder = paths.data

    # units
    m = g4_units.m
    mm = g4_units.mm
    cm = g4_units.cm
    keV = g4_units.keV
    Bq = g4_units.Bq
    MBq = 1e6 * g4_units.Bq
    sec = g4_units.s

    # sim
    sim = gate.Simulation()
    sim.visu = False
    sim.visu_type = "vrml"
    sim.random_seed = "auto"
    sim.output_dir = output_folder
    sim.number_of_threads = 1

    # world
    world = sim.world
    world.size = [0.5 * m, 0.5 * m, 0.7 * m]
    sim.world.material = "G4_AIR"

    # add two cameras
    name1 = "macaco1"
    macaco1 = macaco.add_macaco1_camera(sim, name1)
    camera1 = macaco1["camera"]
    scatterer = macaco1["scatterer"]
    absorber = macaco1["absorber"]
    camera1.translation = [0, 0, 10 * cm]

    """
    name2 = "macaco2"
    camera2 = macaco.add_macaco1_camera(sim, name2)
    camera2.rotation = Rotation.from_euler("x", -90, degrees=True).as_matrix()
    camera2.translation = [0, 10 * cm, 0 * cm]
    """

    # stats
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.output_filename = "stats.txt"

    # PhaseSpace Actor
    phsp = sim.add_actor("PhaseSpaceActor", "PhaseSpace")
    phsp.attached_to = camera1  # [scatterer.name, absorber.name]
    print(phsp.attached_to)
    phsp.attributes = [
        "TotalEnergyDeposit",
        "PreKineticEnergy",
        "PostKineticEnergy",
        "PostPosition",
        "ProcessDefinedStep",
        "ParticleName",
        "EventID",
        "ParentID",
        "PDGCode",
        "TrackVertexKineticEnergy",
        "GlobalTime",
        "PreStepUniqueVolumeID",
        "PreStepUniqueVolumeIDAsInt",
    ]
    phsp.output_filename = "phsp.root"
    phsp.steps_to_store = "allsteps"

    # macaco.add_macaco1_camera_digitizer(sim, scatterer, absorber)

    # physics
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option2"
    sim.physics_manager.set_production_cut("world", "all", 1 * mm)
    sim.physics_manager.set_production_cut(camera1.name, "all", 0.1 * mm)
    # sim.physics_manager.set_production_cut(camera2.name, "all", 0.1 * mm)

    # source
    source = sim.add_source("GenericSource", "src")
    source.particle = "gamma"
    source.energy.mono = 662 * keV
    source.position.type = "sphere"
    source.position.radius = 0.25 * mm
    source.position.translation = [0, 0, 0]
    source.direction.type = "iso"
    source.activity = 0.847 * MBq / sim.number_of_threads

    # acquisition time
    if sim.visu:
        source.activity = 10 * Bq
    sim.run_timing_intervals = [[0 * sec, 5 * sec]]

    # special hook to prepare coresi config file.
    # For each camera, we must find the names of all layers (scatterer and absorber).
    # In this simple macaco1 case, there is only one of each.
    cameras = {
        name1: {
            "scatter_layer_names": [f"{name1}_scatterer"],
            "absorber_layer_names": [f"{name1}_absorber"],
        }
    }
    yaml_filename = paths.output / "coresi_config.yaml"
    param = coresi.set_hook_coresi_config(sim, cameras, yaml_filename)

    # go
    sim.run()

    # print stats
    print(stats)

    # open the root file and create coincidences
    print()
    root_file = uproot.open(phsp.get_output_path())
    tree = root_file["PhaseSpace"]
    hits = tree.arrays(library="pd")
    singles = ccmod_ideal_singles(hits)
    coinc = ccmod_ideal_coincidences(singles)
    print(f"Output file: {phsp.get_output_path()}")
    print(f"Number of hits: {len(hits)} ")
    print(f"Found: {len(singles)} singles")
    print(f"Found: {len(coinc)} coincidences")

    # write the new root with coinc
    coinc_filename = str(phsp.get_output_path()).replace(".root", "_coinc.root")
    root_write_trees(
        coinc_filename, ["hits", "singles", "coincidences"], [hits, singles, coinc]
    )
    print(f"Output file: {coinc_filename}")
    print()

    # CORESI stage1: we retrieve the coresi config built during the hook
    coresi_config = param["coresi_config"]
    # optional: change the volume information
    # TODO LATER : set parameters from an image
    coresi_config["volume"]["volume_dimensions"] = [20, 20, 0.5]
    coresi.coresi_write_config(coresi_config, yaml_filename)
    print(f"Coresi config file: {coinc_filename}")

    # CORESI stage2: convert the root file
    data_filename = output_folder / "coincidences.dat"
    coresi.coresi_convert_root_data(coinc_filename, "coincidences", data_filename)
