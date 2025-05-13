#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Apr  2 09:48:30 2025

@author: fava
"""
import opengate as gate
from opengate.utility import g4_units
import opengate.tests.utility as utility
import opengate_core as g4
import uproot
import numpy as np
from scipy.spatial.transform import Rotation
import SimpleITK as sitk


if __name__ == "__main__":

    paths = utility.get_default_test_paths(__file__, output_folder="test092")

    # Define the Simulation object
    sim = gate.Simulation()

    # Add a material database
    sim.volume_manager.add_material_database(paths.data / "GateMaterials.db")
    sim.physics_manager.special_physics_constructors.G4OpticalPhysics = True
    paths.test_data = paths.data / "test092"
    sim.physics_manager.optical_properties_file = paths.test_data / "Materials.xml"

    # Define the units used in the simulation set-up
    m = gate.g4_units.m
    cm = gate.g4_units.cm
    keV = gate.g4_units.keV
    eV = gate.g4_units.eV
    Bq = gate.g4_units.Bq
    mm = gate.g4_units.mm
    sec = gate.g4_units.second
    gcm3 = gate.g4_units.g_cm3
    deg = g4_units.deg

    sim.visu = False
    sim.visu_type = "vrml"

    world = sim.world
    world.size = [3 * m, 3 * m, 3 * m]
    world.material = "Air"

    img = sitk.ReadImage(
        paths.test_data / "vox_volume.mhd"
    )  # Extraction des caractéristiques de l'images - chemin de l'image test (voxels de 1mm)
    Spacing = img.GetSpacing()  # Taille de voxel en mm
    Size = np.array(img.GetSize())  # Taille de l'image en nombre de voxels
    Size2 = np.array(
        [Size[i] * Spacing[i] for i in range(len(Size))]
    )  # Taille de l'image en mm
    Center = Size2 / 2  # Pour placer la source

    patient = sim.add_volume("Image", name="patient")
    patient.image = paths.test_data / "vox_volume.mhd"  # image CT
    patient.material = "Air"
    patient.dump_label_image = (
        paths.test_data / "labels_vox_volume.mhd"
    )  # Vérifier que tout correspond à du muscle
    patient.translation = [0, 0, 0]
    patient.voxel_materials = [[-2, 2, "Muscle"]]  # Valeurs des voxels == 1
    # patient.voxel_materials = [[-500, -49, "Fat"],[-49, 150, "Muscle"]]

    #####################################################################

    # dose = sim.add_actor("DoseActor", "dose")
    # dose.output_filename = "../output/imageVolume_photon_unique.mhd"
    # dose.attached_to = patient.name
    # dose.size = [Size[0],Size[1],Size[2]]  # Même nombre de voxels que l'image
    # mm = gate.g4_units.mm
    # dose.spacing = [
    #     Spacing[i] * mm for i in range(len(Spacing))
    # ]  # Même taille de voxel que l'image
    # dose.translation = [0, 0, 0]
    # dose.edep_uncertainty.active = False
    # dose.hit_type = "random"

    ################################################ SOURCE DE PHOTONS OPTIQUES
    source = sim.add_source("GenericSource", "mysource")
    source.particle = "opticalphoton"
    source.energy.type = "mono"
    source.energy.mono = 1.913 * eV
    # source.position.type = "box"  # plane source
    source.position.type = "point"
    # source.position.size = [5.5 * cm, 2.6 * cm, 0]
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    source.position.translation = [
        0,
        0,
        -Center[2] * mm,
    ]  # La source est à l'interface entre l'image et l'extérieur
    source.n = 1 / sim.number_of_threads

    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.track_types_flag = True

    sim.run()
    print(stats)
