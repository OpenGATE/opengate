import opengate as gate
import numpy as np
import function as fun
import os, sys, logging
from function import mm
from opengate.tests import utility
import SimpleITK as sitk

# test MB slit

if __name__ == "__main__":
    #=====================================================
    # INITIALISATION
    #=====================================================
    
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    

    number_of_total_events    = 500_000
    
    paths = utility.get_default_test_paths(__file__, output_folder="test097_ElectronFlash_linac")
    
    sim                       = gate.Simulation()
    sim.verbose_level         = gate.logger.RUN
    sim.running_verbose_level = gate.logger.RUN
    sim.g4_verbose            = False
    sim.g4_verbose_level      = 1
    sim.visu                  = False
    sim.visu_type             = "qt"
    sim.random_engine         = "MersenneTwister"
    sim.random_seed           = 18101996
    sim.output_dir            = paths.output
    sim.number_of_threads     = 3
    sim.progress_bar          = True

    if sim.visu:
        sim.number_of_threads     = 1
        number_of_total_events    = 1
    number_of_events    = int(number_of_total_events/sim.number_of_threads) + 1
    
    sim.volume_manager.add_material_database(paths.data / "GateMaterials.db")

    
    #=====================================================
    # GEOMETRY
    #=====================================================
    
    EF_end     = fun.build_ElectronFlash(sim, material_colors=fun.material_colors)
    App40_end = fun.build_passive_collimation(sim, "app40", center_z=EF_end, material_colors=fun.material_colors)
    MB_end = fun.build_passive_collimation(sim, "mb_40_slit_11", center_z=App40_end, material_colors=fun.material_colors)
    
    
    #=====================================================
    # PHANTOMS
    #=====================================================
    
    dim_x, dim_y, dim_z = 100*mm, 100*mm, 20*mm
    dosephantom = fun.build_dosephantombox(sim, "Waterbox", "Water", center_z=MB_end+dim_z/2,dimension_x=dim_x, dimension_y=dim_y, dimension_z=dim_z, material_colors=fun.material_colors)

    #=====================================================
    # ACTORS
    #=====================================================

    dose                         = sim.add_actor("DoseActor", "dose")
    dose.attached_to             = "Waterbox"
    dose.output_filename         = "dose_test_MBslit.mhd"
    dose.hit_type                = "random"
    dose.size                    = [250, 250, 20]  # Number of voxels
    dose.spacing                 = [0.1 * mm, 0.1 * mm, 1 * mm]  # Voxel size
    dose.dose.active             = True
    dose.dose_uncertainty.active = False
    dose.edep_uncertainty.active = False


    #=====================================================
    # PHYSICS
    #=====================================================
    
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option4"
    sim.physics_manager.set_production_cut("world", "all", 2*mm)
    
        
    #=====================================================
    # SOURCE
    #=====================================================

    source = fun.add_source(sim, number_of_events)


    #=====================================================
    # START BEAMS
    #=====================================================

    sim.run()

    
    #=====================================================
    # Perform test
    #=====================================================
    
    path_reference_dose = paths.output_ref / "dose_reference_MBslit_dose.mhd"
    path_test_dose      = dose.dose.get_output_path()
    
    reference_profile = fun.obtain_pdd_from_image(path_reference_dose)
    test_profile      = fun.obtain_pdd_from_image(path_test_dose)
    is_ok, mae    = fun.evaluate_profile_similarity(reference_profile, test_profile)
    
    if is_ok:
        print("test003_ElectronFlash_linac.py : Profile comparison test passed.")
    else:
        print("test003_ElectronFlash_linac.py : Profile comparison test failed. MAE = {:.3f}".format(mae))

    
    
    
    
    