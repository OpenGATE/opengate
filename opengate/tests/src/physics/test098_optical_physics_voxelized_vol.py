#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Oct  3 15:07:07 2025

@author: mabbas
"""

import opengate as gate
from opengate.tests import utility
from opengate.utility import g4_units
import SimpleITK as sitk
import numpy as np

if __name__ == "__main__":
    
    paths = utility.get_default_test_paths(__file__,"gate_test098",output_folder="gate_test098")
    
    cm = g4_units.cm
    mm = g4_units.mm
    eV = g4_units.eV
    nm = g4_units.nm
    
    sim = gate.Simulation()
    sim.output_dir = paths.output
    sim.g4_verbose = False
    sim.visu = False
    sim.visu_type = "vrml"
    sim.check_volumes_overlap = False
    sim.number_of_threads = 2
    sim.random_seed = "auto"    
    
    sim.volume_manager.add_material_database(paths.gate_data / "GateMaterials.db")
    
    sim.physics_manager.special_physics_constructors.G4OpticalPhysics = True

    sim.physics_manager.optical_properties_file = paths.gate_data / "Materials.xml"    
    
    sim.world.size = [6 * cm, 6 * cm, 2 * cm]
    sim.world.material = "Air"
    
    img_path = paths.data / "vox_volume.mhd" 
    
    img = sitk.ReadImage(img_path)
    Spacing = img.GetSpacing()
    Size = np.array(img.GetSize())  # Image size in number of voxels
    Size2 = np.array(
        [Size[i] * Spacing[i] for i in range(len(Size))]
    )  # Image size in mm      
    
    vox = sim.add_volume("ImageVolume","image")
    vox.image = img_path
    vox.material = "Air"
    vox.voxel_materials = [[-0.5, 0.5, "Fat",], [0.5, 1.5, "Muscle"]]
    vox.translation = [0, 0, 0]
    
    phsp_plane = sim.add_volume("BoxVolume","phsp_plane")
    phsp_plane.material = "Air"
    phsp_plane.size = [5*cm, 5*cm, 1*nm]
    phsp_plane.translation = [0,0,(Size2[2]/2)*mm+phsp_plane.size[2]/2]
    
    phsp = sim.add_actor("PhaseSpaceActor", "phsp")
    phsp.attached_to = phsp_plane.name
    phsp.attributes = ["PostPosition"]
    phsp.steps_to_store = "exiting"
    phsp.output_filename = "test098_vox_volume.root"    
    
    source = sim.add_source("GenericSource", "source")
    source.particle = "opticalphoton"
    source.energy.type = "mono"
    source.energy.mono = 1.913*eV
    source.position.type = "disc"
    source.position.radius = 1.25*cm
    source.direction.type = "momentum"
    source.direction.momentum = [0,0,1]
    source.position.translation = [0,0,-(Size2[2]/2)*mm]
    source.n = 1e6/sim.number_of_threads
    
    sim.run()
    
    compare = utility.compare_root3
    
    root_ref_path = paths.data / "test098_box_volume.root"
    root_output_path = sim.output_dir / phsp.output_filename
    
    branch = "phsp;1"
    keys = ["PostPosition_X","PostPosition_Y","PostPosition_Z"]
    tols = [0.3, 0.3, 1e-4]
    scalings = [1, 1, 1]
    img = paths.output / "figure.png"
    
    is_ok = compare(root_ref_path, root_output_path, branch, branch, keys, keys, tols, scalings, scalings, img)
    
    utility.test_ok(is_ok)