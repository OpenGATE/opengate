#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
import uproot


def simulation(
    output, File_name, job_id, number_of_particles, visu, verbose, actor, Erange
):

    paths = utility.get_default_test_paths(__file__, output_folder=output)

    # create the simulation
    sim = gate.Simulation()
    # main options
    sim.visu = visu
    sim.g4_verbose = verbose
    sim.random_seed = "auto"  # FIXME to be replaced by a fixed number at the end
    sim.random_engine = "MersenneTwister"
    sim.output_dir = paths.output
    sim.number_of_threads = 1
    sim.progress_bar = True

    # units
    mm = gate.g4_units.mm
    cm = gate.g4_units.cm
    m = gate.g4_units.m
    MeV = gate.g4_units.MeV
    ns = gate.g4_units.ns
    gcm3 = gate.g4_units.g_cm3

    #  change world size
    world = sim.world
    world.size = [3 * m, 3 * m, 3 * m]
    world.material = "G4_Galactic"

    # patient
    """
    ct = sim.add_volume("Image", "ct")
    ct.image = paths.data / f"1mm-carbo-volume.mhd"
    if visu :
        ct.image = paths.data / f"visu-carbo-volume.mhd"
    ct.mother = "world"
    ct.material = "G4_C"
    ct.voxel_materials = [
        # range format [)
        [-2000, -700, "G4_C"],
        ]
    ct.dump_label_image = "labels.mhd"
    """

    ct = sim.add_volume("Image", vol_name)
    ct.image = paths.data / f"ct_4mm.mhd"
    if sim.visu:
        ct.image = paths.data / f"ct_40mm.mhd"
    ct.material = "G4_AIR"
    f1 = str(paths.data / "Schneider2000MaterialsTable.txt")
    f2 = str(paths.data / "Schneider2000DensitiesTable.txt")
    tol = 0.05 * gcm3
    (
        ct.voxel_materials,
        materials,
    ) = gate.geometry.materials.HounsfieldUnit_to_material(sim, tol, f1, f2)
    ct.dump_label_image = paths.output / "labels.mhd"
    ct.mother = "world"
    ct.load_input_image()

    # physics
    sim.physics_manager.physics_list_name = "QGSP_BIC_HP_EMY"

    sim.physics_manager.apply_cuts = False  # default
    sim.physics_manager.global_production_cuts.gamma = 0.1 * mm
    sim.physics_manager.global_production_cuts.electron = 0.1 * mm
    sim.physics_manager.global_production_cuts.positron = 0.1 * mm
    sim.physics_manager.global_production_cuts.proton = 0.1 * mm

    sim.physics_manager.set_max_step_size("ct", 0.1 * mm)
    sim.physics_manager.set_user_limits_particles(["proton"])

    # source of proton
    # FIXME to replace by a more realistic proton beam, see tests 044
    source = sim.add_source("GenericSource", "DEFAULT")
    source.energy.mono = Erange * MeV
    source.particle = "proton"
    source.position.type = "point"
    source.position.radius = 1 * mm
    source.position.translation = [0 * mm, -300 * mm, 0 * mm]
    source.n = number_of_particles
    source.direction.type = "momentum"
    source.direction.momentum = [0, 1, 0]

    #LOOKHERE :: if database not well implanted, has to be modified
    with uproot.open(paths.data / "data_merge_proton.root") as root_file:
        histo = root_file["standard_Weight"]["Weight"].to_hist()
        vect_p = histo.to_numpy()[0]
    with uproot.open(paths.data / "data_merge_neutron.root") as root_file:
        histo = root_file["standard_Weight"]["Weight"].to_hist()
        vect_n = histo.to_numpy()[0]

    vpg_tle = sim.add_actor(actor, actor_name)
    vpg_tle.attached_to = vol_name
    vpg_tle.output_filename = paths.output / f"{File_name}.nii.gz"
    vpg_tle.size = [125, 125, 189]  # the same size than ct image is stronly adviced
    vpg_tle.spacing = [
        4,
        4,
        4,
    ]  # the same spacing is stronly adviced
    vpg_tle.timebins = 250
    vpg_tle.timerange = 5 * ns
    vpg_tle.energybins = 250
    vpg_tle.energyrange = Erange * MeV
    vpg_tle.prot_E.active = True
    vpg_tle.neutr_E.active = True
    vpg_tle.prot_tof.active = True
    vpg_tle.neutr_tof.active = True
    vpg_tle.weight = True  # True to obtain weighted time spectra
    vpg_tle.vect_p = vect_p
    vpg_tle.vect_n = vect_n

    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "stats")
    stats.track_types_flag = True
    stats.output_filename = paths.output / f"stat_{job_id}_{File_name}.txt"

    return sim

#features of simulation that can be modify
output = "stage1a"
File_name = "vpg"
actor_name = "vpg_tle"
vol_name = "ct"

number_of_particles = 1e2
#if analog is used, should be replace (Erange = 10 MeV and differenciate from the source energy)
actor = "VoxelizedPromptGammaTLEActor"
#source Energy andrange of the actor
Erange = 130
if __name__ == "__main__":
    sim = simulation(
        output, File_name, 0, number_of_particles, False, False, actor, Erange
    )
    # start simulation
    sim.run()
