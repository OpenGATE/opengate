#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import opengate.contrib.spect.ge_discovery_nm670 as nm670
import opengate.contrib.phantoms.nemaiec as nemaiec
from opengate.image import get_translation_to_isocenter
from opengate.sources.utility import set_source_energy_spectrum
from pathlib import Path
import numpy as np
import opengate_core as g4


def check_process_user_hook(simulation_engine):
    p_name = "gamma"
    g4_particle_table = g4.G4ParticleTable.GetParticleTable()
    particle = g4_particle_table.FindParticle(particle_name=p_name)
    if particle is None:
        raise Exception(f"Something went wrong. Could not find particle {p_name}.")
    pm = particle.GetProcessManager()
    process_list = pm.GetProcessList()
    for i in range(process_list.size()):
        processName = str(process_list[i].GetProcessName())
        print(processName)


def create_simulation_test085(sim, paths, ac=1e5, angle_tolerance=None):

    # main options
    # sim.visu = True  # uncomment to enable visualisation
    sim.visu_type = "qt"
    # sim.visu_type = "vrml"
    sim.random_seed = "auto"
    sim.progress_bar = True
    sim.output_dir = paths.output
    sim.store_json_archive = True
    sim.store_input_files = False
    sim.json_archive_filename = "simu.json"
    sim.random_seed = 321654789
    data_folder = Path(paths.data) / "test085"

    # units
    mm = gate.g4_units.mm
    cm = gate.g4_units.cm
    m = gate.g4_units.m
    Bq = gate.g4_units.Bq
    cm3 = gate.g4_units.cm3
    BqmL = Bq / cm3
    deg = gate.g4_units.deg

    # options
    activity = ac * BqmL / sim.number_of_threads
    radius = 20 * cm

    # visu
    if sim.visu:
        sim.number_of_threads = 1
        activity = 1000 * BqmL / sim.number_of_threads

    # world
    world = sim.world
    world.size = [2 * m, 2 * m, 2 * m]
    world.material = "G4_AIR"

    # set the two spect heads
    spacing = [2.21 * mm * 2, 2.21 * mm * 2]
    size = [128, 128]
    pth = data_folder / "arf_034_nm670_tc99m_v2.pth"
    det_plane1, arf1 = nm670.add_arf_detector(
        sim, radius, 0, size, spacing, "lehr", "detector", 1, pth
    )
    det_plane2, arf2 = nm670.add_arf_detector(
        sim, radius, 180, size, spacing, "lehr", "detector", 2, pth
    )
    det_planes = [det_plane1, det_plane2]
    arfs = [arf1, arf2]

    # IEC voxelization
    # voxelize_iec_phantom -o data/iec_1mm.mhd --spacing 1 --output_source data/iec_1mm_activity.mhd -a 1 1 1 1 1 1
    # voxelize_iec_phantom -o data/iec_4.42mm.mhd --spacing 4.42 --output_source data/iec_4.42mm_activity.mhd -a 1 1 1 1 1 1
    # voxelize_iec_phantom -o data/iec_4mm.mhd --spacing 4 --output_source data/iec_4mm_activity.mhd -a 1 1 1 1 1 1

    # phantom
    if not sim.visu:
        iec_vox_filename = data_folder / "iec_4mm.mhd"
        iec_label_filename = data_folder / "iec_4mm_labels.json"
        db_filename = data_folder / "iec_4mm.db"
        vox = sim.add_volume("ImageVolume", "phantom")
        vox.image = iec_vox_filename
        vox.read_label_to_material(iec_label_filename)
        vox.translation = get_translation_to_isocenter(vox.image)
        sim.volume_manager.add_material_database(str(db_filename))
    else:
        phantom = nemaiec.add_iec_phantom(sim, name="phantom")

    # physics
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option3"
    sim.physics_manager.set_production_cut("world", "all", 100 * mm)
    sim.physics_manager.set_production_cut("phantom", "all", 2 * mm)
    sim.user_hook_after_init = check_process_user_hook

    # Mandatory for this actor, since gamma processes are encompassed in GammaGeneralProc without.
    # s = f"/process/em/UseGeneralProcess false"
    # sim.g4_commands_before_init.append(s)

    if angle_tolerance is None:
        angle_tolerance = 10 * deg

    # add iec voxelized source
    iec_source_filename = data_folder / "iec_4mm_activity.mhd"
    source = sim.add_source("VoxelSource", "src")
    source.image = iec_source_filename
    source.position.translation = [0, 35 * mm, 0]
    source.particle = "gamma"
    set_source_energy_spectrum(source, "tc99m", "radar")  # After particle definition
    source.direction.acceptance_angle.volumes = [h.name for h in det_planes]
    source.direction.acceptance_angle.skip_policy = "SkipEvents"
    source.direction.acceptance_angle.intersection_flag = True
    source.direction.acceptance_angle.normal_flag = True
    source.direction.acceptance_angle.normal_vector = [0, 0, -1]
    source.direction.acceptance_angle.normal_tolerance = angle_tolerance
    _, volumes = nemaiec.get_default_sphere_centers_and_volumes()
    source.activity = activity * np.array(volumes).sum()
    print(f"Total activity is {source.activity/ Bq}")

    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "stats")
    stats.output_filename = "stats.txt"

    # set the gantry orientation
    nm670.rotate_gantry(det_plane1, radius, 0, 0, 1)
    nm670.rotate_gantry(det_plane2, radius, 180, 0, 1)
