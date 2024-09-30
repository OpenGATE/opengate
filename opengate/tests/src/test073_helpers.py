#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.sources.generic import set_source_rad_energy_spectrum
from opengate.exception import warning
from opengate.tests import utility
import opengate.contrib.spect.siemens_intevo as intevo
import opengate.contrib.spect.ge_discovery_nm670 as discovery
from scipy.spatial.transform import Rotation
import itk
import numpy as np


def create_sim_tests(sim, threads=1, digitizer=1, debug=False):
    # units
    m = gate.g4_units.m
    mm = gate.g4_units.mm
    Bq = gate.g4_units.Bq

    # main options
    sim.g4_verbose = False
    sim.g4_verbose_level = 1
    sim.number_of_threads = threads
    sim.visu = False

    # activity
    activity = 7000000 * Bq / sim.number_of_threads

    # world size
    world = sim.world
    world.size = [2.2 * m, 3.2 * m, 2 * m]
    world.material = "G4_AIR"

    # spect head
    head, colli, crystal = intevo.add_spect_head(
        sim, "spect", collimator_type="melp", debug=debug
    )
    head.translation = [0, 0, -280 * mm]
    head.rotation = Rotation.from_euler("y", 90, degrees=True).as_matrix()

    # spect digitizer
    if digitizer == 1:
        intevo.add_digitizer_test1(sim, head, crystal)
    if digitizer == 2:
        intevo.add_digitizer_test2(sim, head, crystal)

    # physics
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option3"
    sim.enable_decay = False
    sim.physics_manager.global_production_cuts.all = 100 * mm
    sim.physics_manager.set_production_cut("spect", "all", 0.1 * mm)

    # sources
    # sim.running_verbose_level = gate.EVENT
    s1 = sim.add_source("GenericSource", "s1")
    s1.particle = "gamma"
    s1.position.type = "sphere"
    s1.position.radius = 30 * mm
    s1.position.translation = [0, 0, 0]
    set_source_rad_energy_spectrum(s1, "Lu177")
    s1.direction.type = "iso"
    s1.activity = activity

    s2 = sim.add_source("GenericSource", "s2.")
    s2.particle = "gamma"
    s2.position.type = "sphere"
    s2.position.radius = 60 * mm
    s2.position.translation = [0, 200 * mm, 0]
    set_source_rad_energy_spectrum(s2, "Lu177")
    s2.direction.type = "iso"
    s2.activity = activity

    s3 = sim.add_source("GenericSource", "s3.")
    s3.particle = "gamma"
    s3.position.type = "sphere"
    s3.position.radius = 25 * mm
    s3.position.translation = [100, 0, 0 * mm]
    set_source_rad_energy_spectrum(s3, "Lu177")
    s3.direction.type = "iso"
    s3.activity = activity

    # add stat actor
    s = sim.add_actor("SimulationStatisticsActor", "stats")
    s.track_types_flag = True
    s.output_filename = "stats.txt"

    # timing
    sec = gate.g4_units.second
    stop = 1 * sec
    if sim.visu:
        stop = 0.001 * sec
    sim.run_timing_intervals = [[0, stop]]


def compare_stats(sim, filename):
    # compare stats
    warning("Compare stats")
    stats = sim.get_actor("stats")
    # force nb of thread to 1
    stats_ref = utility.read_stat_file(filename)
    stats.counts.runs = stats_ref.counts.runs
    is_ok = utility.assert_stats(stats, stats_ref, tolerance=0.01)
    return is_ok


def compare_root_hits(crystal, sim, root_filename, path, n=1):
    # compare root
    print()
    warning("Compare hits")
    gate_file = root_filename
    hc_file = sim.get_actor(f"Hits_{crystal.name}").get_output_path()
    checked_keys = [
        {"k1": "posX", "k2": "PostPosition_X", "tol": 3, "scaling": 1},
        {"k1": "posY", "k2": "PostPosition_Y", "tol": 6, "scaling": 1},
        {"k1": "posZ", "k2": "PostPosition_Z", "tol": 0.12, "scaling": 1},
        {"k1": "edep", "k2": "TotalEnergyDeposit", "tol": 0.004, "scaling": 1},
        {"k1": "time", "k2": "GlobalTime", "tol": 0.05, "scaling": 1e-9},
    ]
    is_ok = utility.compare_root2(
        gate_file,
        hc_file,
        "Hits",
        f"Hits_{crystal.name}",
        checked_keys,
        path / f"test073_test_{n}_hits.png",
        n_tol=16,
    )
    return is_ok


def compare_root_singles(crystal, sim, root_filename, path, sname, n=1):
    # Compare root files
    print()
    warning("Compare singles")
    hc_file = sim.get_actor(f"Singles_{crystal.name}").get_output_path()
    checked_keys = [
        {"k1": "globalPosX", "k2": "PostPosition_X", "tol": 3, "scaling": 1},
        {"k1": "globalPosY", "k2": "PostPosition_Y", "tol": 6, "scaling": 1},
        {"k1": "globalPosZ", "k2": "PostPosition_Z", "tol": 0.284, "scaling": 1},
        {"k1": "energy", "k2": "TotalEnergyDeposit", "tol": 0.0035, "scaling": 1},
    ]
    is_ok = utility.compare_root2(
        root_filename,
        hc_file,
        "Singles",
        sname,
        checked_keys,
        f"{path}/test050_test_{n}_singles.png",
        n_tol=8,
    )
    return is_ok


def compare_proj_images(crystal, sim, stats, image_filename, path, n=1):
    # compare images with Gate
    print()
    print("Compare images (old spacing/origin)")
    # read image and force change the offset to be similar to old Gate
    proj = sim.get_actor(f"Projection_{crystal.name}")
    fr = image_filename
    f1 = path / f"projections_test{n}.mhd"
    f2 = path / f"projections_test{n}_offset.mhd"
    img = itk.imread(f1)
    spacing = np.array(proj.projection.image.GetSpacing())
    origin = spacing / 2.0
    origin[2] = 0.5
    spacing[2] = 1
    img.SetSpacing(spacing)
    img.SetOrigin(origin)
    itk.imwrite(img, f2)

    is_ok = utility.assert_images(
        fr,
        f2,
        stats,
        tolerance=69,
        ignore_value=0,
        axis="y",
        sum_tolerance=6,
        fig_name=path / f"test073_test_{n}.png",
    )
    return is_ok


def test073_setup_sim(sim, spect_type, collimator_type):
    # units
    m = gate.g4_units.m
    mm = gate.g4_units.mm

    # main options
    sim.g4_verbose = False
    sim.g4_verbose_level = 1
    sim.number_of_threads = 4
    # sim.visu = True
    sim.visu_type = "vrml"
    # sim.random_seed = 321654987

    # world size
    world = sim.world
    world.size = [2.2 * m, 3.2 * m, 2 * m]
    world.material = "G4_AIR"

    # spect ?
    if spect_type == "intevo":
        head, colli, crystal = intevo.add_spect_head(
            sim, "spect", collimator_type=collimator_type, debug=sim.visu
        )
        head.translation = [0, 0, -280 * mm]
        head.rotation = Rotation.from_euler("y", 90, degrees=True).as_matrix()
    if spect_type == "discovery":
        head, colli, crystal = discovery.add_spect_head(
            sim, "spect", collimator_type=collimator_type, debug=sim.visu
        )
        head.translation = [0, 0, -280 * mm]

    # source
    source = sim.add_source("GenericSource", "source")
    source.particle = "gamma"
    source.position.type = "sphere"
    source.position.radius = 30 * mm
    source.position.translation = [0, 0, 0]
    source.direction.type = "iso"
    source.direction.acceptance_angle.volumes = [head.name]
    source.direction.acceptance_angle.intersection_flag = True

    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "stats")
    stats.track_types_flag = True

    # physics
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option3"
    sim.enable_decay = False
    sim.physics_manager.global_production_cuts.all = 100 * mm
    sim.physics_manager.set_production_cut("spect", "all", 0.1 * mm)

    return head, stats, source


def compare_root_spectrum(ref_output, output, png_filename):
    # compare root
    print()
    warning("Compare spectrum")
    checked_keys = [
        {"k1": "PostPosition_X", "k2": "PostPosition_X", "tol": 1.3, "scaling": 1},
        {"k1": "PostPosition_Y", "k2": "PostPosition_Y", "tol": 1.2, "scaling": 1},
        {"k1": "PostPosition_Z", "k2": "PostPosition_Z", "tol": 0.3, "scaling": 1},
        {
            "k1": "TotalEnergyDeposit",
            "k2": "TotalEnergyDeposit",
            "tol": 0.003,
            "scaling": 1,
        },
        {"k1": "GlobalTime", "k2": "GlobalTime", "tol": 1.1e7, "scaling": 1},
    ]
    is_ok = utility.compare_root2(
        ref_output,
        output,
        "spectrum",
        "spectrum",
        checked_keys,
        png_filename,
        n_tol=16,
    )
    return is_ok


def compare_root_spectrum2(ref_output, output, png_filename):
    # compare root
    print()
    warning("Compare spectrum")
    checked_keys = [
        {"k1": "PostPosition_X", "k2": "PostPosition_X", "tol": 1.5, "scaling": 1},
        {"k1": "PostPosition_Y", "k2": "PostPosition_Y", "tol": 2.0, "scaling": 1},
        {"k1": "PostPosition_Z", "k2": "PostPosition_Z", "tol": 0.4, "scaling": 1},
        {
            "k1": "TotalEnergyDeposit",
            "k2": "TotalEnergyDeposit",
            "tol": 0.004,
            "scaling": 1,
        },
        {"k1": "GlobalTime", "k2": "GlobalTime", "tol": 1.2e7, "scaling": 1},
    ]
    is_ok = utility.compare_root2(
        ref_output,
        output,
        "spectrum",
        "spectrum",
        checked_keys,
        png_filename,
        n_tol=16,
    )
    return is_ok
