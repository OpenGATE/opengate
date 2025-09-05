import opengate as gate
import numpy as np
import function as fun
import os, sys, logging
from function import mm
from opengate.tests import utility

if __name__ == "__main__":
    #=====================================================
    # INITIALISATION
    #=====================================================
    
    
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    

    number_of_total_events    = 500_000
    
    paths = utility.get_default_test_paths(__file__, output_folder="test103_ElectronFlash_linac")
    
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
    shaper40_end, (leaf1, leaf2, leaf3, leaf4) = fun.build_passive_collimation(sim, "shaper40", center_z=App40_end, material_colors=fun.material_colors)
    fun.set_shaper_aperture(leaf1, leaf2, leaf3, leaf4, aperture_x_mm = 25, aperture_y_mm = 35)
    fun.rotate_leaves_around_z(leaf1, leaf2, leaf3, leaf4, angle_deg = 45)
    #=====================================================
    # PHANTOMS
    #=====================================================
    
    dim_x, dim_y, dim_z = 150*mm, 150*mm, 0.01*mm
    phsp_plane = fun.build_dosephantombox(sim, "Phasespace_plane", "Air", center_z=shaper40_end+dim_z/2,dimension_x=dim_x, dimension_y=dim_y, dimension_z=dim_z, material_colors=fun.material_colors)
    
    #=====================================================
    # ACTORS
    #=====================================================

    phsp                 = sim.add_actor("PhaseSpaceActor", "PhaseSpace")
    phsp.attached_to     = phsp_plane.name
    phsp.attributes      = ["KineticEnergy","PreDirection","EventPosition",]
    phsp.output_filename = "phsp_test_shaper40.root"


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
    
    path_reference_root_phsp = paths.output_ref / "phsp_reference_shaper40.root"
    path_test_root_phsp      = phsp.get_output_path()

    keys = ["KineticEnergy" ,"PreDirection_X","PreDirection_Y","EventPosition_X","EventPosition_Y"]
    tols = [0.8, 0.8, 0.8, 0.8, 0.8]
    br = "PhaseSpace;1"
    is_ok = utility.compare_root3(
            path_reference_root_phsp,
            path_test_root_phsp,
            br,
            br,
            keys,
            keys,
            tols,
            None,
            None,
            paths.output / "test_EF_shaper40.png",
            nb_bins=150,
            hits_tol = 10**6
        )
    
    
    