#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import opengate.contrib.spect.ge_discovery_nm670 as nm670
import opengate.contrib.phantoms.nemaiec as nemaiec
from opengate.image import get_translation_to_isocenter
from opengate.sources.base import set_source_rad_energy_spectrum
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


def create_simulation_test085(
    sim,
    paths,
    simu_name,
    ac=1e5,
    angle_tolerance=None,
    use_spect_head=False,
    use_spect_arf=False,
    use_phsp=False,
):
    # main options
    # sim.visu = True  # uncomment to enable visualisation
    sim.visu_type = "qt"
    # sim.visu_type = "vrml"
    sim.random_seed = "auto"
    sim.progress_bar = True
    sim.output_dir = paths.output
    sim.store_json_archive = True
    sim.store_input_files = False
    sim.json_archive_filename = f"simu_{simu_name}.json"
    sim.random_seed = "auto"  # 321654789
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
    radius = 28 * cm

    # visu
    if sim.visu:
        sim.number_of_threads = 1
        activity = 1000 * BqmL / sim.number_of_threads
        activity = 200 * BqmL / sim.number_of_threads

    # world
    world = sim.world
    world.size = [2 * m, 2 * m, 2 * m]
    # world.material = "G4_AIR"
    world.material = "G4_Galactic"

    # check option
    if use_spect_head and use_spect_arf:
        raise Exception("Cannot use both spect heads and ARFs.")

    # set the two spect heads
    spacing = [2.21 * mm * 2, 2.21 * mm * 2]
    size = [128, 128]
    heads = []
    actors = []
    if use_spect_arf:
        actors, heads = add_spect_arf(
            sim, data_folder, simu_name, radius, size, spacing
        )
    if use_spect_head:
        actors, heads = add_spect_heads(sim, simu_name, radius)

    # add phsp to check E spectra
    if use_phsp:
        actors, heads = add_phsp(
            sim, simu_name, radius, size, spacing, use_parallel_world=use_spect_head
        )

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
    sim.physics_manager.set_production_cut("phantom", "all", 1 * mm)
    sim.user_hook_after_init = check_process_user_hook

    # Mandatory for this actor ? since gamma processes are encompassed in GammaGeneralProc without.
    # FIXME no ?
    # s = f"/process/em/UseGeneralProcess false"
    # sim.g4_commands_before_init.append(s)

    if angle_tolerance is None:
        angle_tolerance = 20 * deg

    # add iec voxelized source
    iec_source_filename = data_folder / "iec_4mm_activity.mhd"
    source = sim.add_source("VoxelSource", "src")
    source.image = iec_source_filename
    source.position.translation = [0, 35 * mm, 0]
    set_source_rad_energy_spectrum(source, "tc99m")
    source.particle = "gamma"
    # source.direction.acceptance_angle.volumes = [h.name for h in det_planes]
    if len(heads) == 2:
        source.direction.acceptance_angle.volumes = [h.name for h in heads]
        source.direction.acceptance_angle.skip_policy = "SkipEvents"
        source.direction.acceptance_angle.intersection_flag = True
        source.direction.acceptance_angle.normal_flag = True
        source.direction.acceptance_angle.normal_vector = [0, 0, -1]
        source.direction.acceptance_angle.normal_tolerance = angle_tolerance
    _, volumes = nemaiec.get_default_sphere_centers_and_volumes()
    source.activity = activity * np.array(volumes).sum()
    print(f"Total activity is {source.activity / Bq}")

    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "stats")
    stats.output_filename = f"stats_{simu_name}.txt"

    # set the gantry orientation
    if len(heads) == 2:
        nm670.rotate_gantry(heads[0], radius, 0, 0, 1)
        nm670.rotate_gantry(heads[1], radius, 180, 0, 1)

    return source, actors


def add_spect_arf(sim, data_folder, simu_name, radius, size, spacing):
    pth = data_folder / "arf_034_nm670_tc99m_v2.pth"
    det_plane1, arf1 = nm670.add_arf_detector(
        sim, radius, 0, size, spacing, "lehr", "spect", 1, pth
    )
    det_plane2, arf2 = nm670.add_arf_detector(
        sim, radius, 180, size, spacing, "lehr", "spect", 2, pth
    )
    det_planes = [det_plane1, det_plane2]

    arf1.output_filename = f"projection_1_{simu_name}.mhd"
    arf2.output_filename = f"projection_2_{simu_name}.mhd"
    arfs = [arf1, arf2]
    return arfs, det_planes


def add_spect_heads(sim, simu_name, radius):
    mm = gate.g4_units.mm
    heads, crystals = nm670.add_spect_two_heads(
        sim, "spect", "lehr", debug=sim.visu, radius=radius
    )
    digit1 = nm670.add_digitizer_tc99m_v2(
        sim, crystals[0].name, "digit1", spectrum_channel=False
    )
    digit2 = nm670.add_digitizer_tc99m_v2(
        sim, crystals[1].name, "digit2", spectrum_channel=False
    )

    hits1 = digit1.find_module("hits")
    hits1.attributes.append("Weight")
    hits2 = digit2.find_module("hits")
    hits2.attributes.append("Weight")

    proj1 = digit1.find_module("projection")
    proj1.output_filename = f"projection_1_{simu_name}.mhd"
    proj2 = digit2.find_module("projection")
    proj2.output_filename = f"projection_2_{simu_name}.mhd"
    projs = [proj1, proj2]

    sim.physics_manager.set_production_cut(crystals[0].name, "all", 2 * mm)
    sim.physics_manager.set_production_cut(crystals[1].name, "all", 2 * mm)

    return projs, heads


def add_phsp_old(sim, simu_name, radius, size, spacing, use_parallel_world):

    if use_parallel_world:
        sim.add_parallel_world("world2")

    plane_size = [spacing[0] * size[0], spacing[1] * size[1]]
    print(f"plane size = {plane_size}")
    phsp_plane1 = nm670.add_detection_plane_for_arf(
        sim, plane_size, "lehr", radius, 0, "spect_1"
    )
    phsp_plane2 = nm670.add_detection_plane_for_arf(
        sim, plane_size, "lehr", radius, 180, "spect_2"
    )
    nm670.set_head_orientation(phsp_plane1, "lehr", -radius, 0)
    nm670.set_head_orientation(phsp_plane2, "lehr", -radius, 180)

    if use_parallel_world:
        phsp_plane1.mother = "world2"
        phsp_plane2.mother = "world2"

    phsp1 = sim.add_actor("PhaseSpaceActor", "phsp1")
    phsp1.attached_to = phsp_plane1
    phsp1.attributes = ["KineticEnergy", "PrePositionLocal", "Weight"]
    phsp1.output_filename = f"phsp_1_{simu_name}.root"
    phsp2 = sim.add_actor("PhaseSpaceActor", "phsp2")
    phsp2.attached_to = phsp_plane2
    phsp2.attributes = ["KineticEnergy", "PrePositionLocal", "Weight"]
    phsp2.output_filename = f"phsp_2_{simu_name}.root"

    phsps = [phsp1, phsp2]
    planes = [phsp_plane1, phsp_plane2]

    return phsps, planes


def add_phsp(sim, simu_name, radius, size, spacing, use_parallel_world):

    phsp_sphere = sim.add_volume("Sphere", "phsp_sphere")
    phsp_sphere.rmax = 30 * gate.g4_units.cm
    phsp_sphere.rmin = phsp_sphere.rmax - 2 * gate.g4_units.mm
    phsp_sphere.color = [1, 0, 0, 1]

    phsp1 = sim.add_actor("PhaseSpaceActor", "phsp1")
    phsp1.attached_to = phsp_sphere
    phsp1.attributes = ["KineticEnergy", "PrePositionLocal", "Weight"]
    phsp1.output_filename = f"phsp_1_{simu_name}.root"

    phsps = [phsp1]
    planes = [phsp_sphere]

    return phsps, planes
