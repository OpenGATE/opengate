import opengate as gate
import numpy as np
import EF_function as fun
import os, sys, logging




if __name__ == "__main__":
    #=====================================================
    # INITIALISATION
    #=====================================================
    
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    
    number_of_total_events    = 1_000_000
    
    
    sim                       = gate.Simulation()
    sim.verbose_level         = gate.logger.RUN
    sim.running_verbose_level = gate.logger.RUN
    sim.g4_verbose            = False
    sim.g4_verbose_level      = 1
    sim.visu                  = False
    sim.visu_type             = "qt"
    sim.random_engine         = "MersenneTwister"
    sim.random_seed           = "auto"
    sim.output_dir            = "output"
    sim.number_of_threads     = 4
    sim.progress_bar          = True
    sim.volume_manager.add_material_database(gate_materials_path)
    if sim.visu:
        sim.number_of_threads     = 1
        number_of_total_events    = 1
    number_of_events    = int(number_of_total_events/sim.number_of_threads) + 1
    
    sim.volume_manager.add_material_database(paths.data / "GateMaterials.db")
    
    #=====================================================
    # GEOMETRY
    #=====================================================
    
    mm = fun.mm
    
    ###### Build Linac from titanium window up to BLD
    EF_end     = fun.build_ElectronFlash(sim, material_colors=fun.material_colors)
    
    
    ###### Build different BLDs (app100, app40)
    App100_end = fun.build_passive_collimation(sim, "app100", center_z=EF_end, material_colors=fun.material_colors)
    #App40_end = fun.build_passive_collimation(sim, "app40", center_z=EF_end, material_colors=fun.material_colors)
    
    ###### If the proper applicator is selected (app40), you can add the MB template or the beam shaper device
    #MB_end = fun.build_passive_collimation(sim, "mb_40_holes_11", center_z=App40_end, material_colors=fun.material_colors)
    
    #shaper40_end, (leaf1, leaf2, leaf3, leaf4) = fun.build_passive_collimation(sim, "shaper40", center_z=App40_end, material_colors=fun.material_colors)
    #fun.set_shaper_aperture(leaf1, leaf2, leaf3, leaf4, aperture_x_mm = 20, aperture_y_mm = 20)
    #fun.rotate_leaves_around_z(leaf1, leaf2, leaf3, leaf4, angle_deg = 45)
    
    
    #=====================================================
    # PHANTOMS
    #=====================================================

    ### Build a water phantom for openfield dose deposition - OK
    dim_x, dim_y, dim_z = 250*mm, 250*mm, 60*mm
    dosephantom = fun.build_dosephantombox(sim, "Waterbox", "Water", center_z=App100_end+dim_z/2,dimension_x=dim_x, dimension_y=dim_y, dimension_z=dim_z, material_colors=fun.material_colors)
    
    ### Build a water phantom for MB applications - OK
    #dim_x, dim_y, dim_z = 100*mm, 100*mm, 30*mm
    #dosephantom = fun.build_dosephantombox(sim, "Waterbox", "Water", center_z=MB_end+dim_z/2,dimension_x=dim_x, dimension_y=dim_y, dimension_z=dim_z, material_colors=fun.material_colors)

    ### Build a plane for phase space test
    #dim_x, dim_y, dim_z = 150*mm, 150*mm, 0.01*mm
    #phsp_plane = fun.build_dosephantombox(sim, "Phasespace_plane", "Air", center_z=MB_end+dim_z/2,dimension_x=dim_x, dimension_y=dim_y, dimension_z=dim_z, material_colors=fun.material_colors)
    

    
    #=====================================================
    # ACTORS
    #=====================================================

    ## DoseActor for PDD/profiles (openfield and shaper)
    dose                         = sim.add_actor("DoseActor", "dose")
    dose.attached_to             = "Waterbox"
    dose.output_filename         = "dose.mhd"
    dose.hit_type                = "random"
    dose.size                    = [120, 120, 30]  # Number of voxels
    dose.spacing                 = [1 * mm, 1 * mm, 2 * mm]  # Voxel size
    dose.dose.active             = True
    dose.dose_uncertainty.active = False
    dose.edep_uncertainty.active = False
    
    ## DoseActor for MB - OK
    #dose                         = sim.add_actor("DoseActor", "dose")
    #dose.attached_to             = "Waterbox"
    #dose.output_filename         = "dose.mhd"
    #dose.hit_type                = "random"
    #dose.size                    = [250, 250, 30]  # Number of voxels
    #dose.spacing                 = [0.1 * mm, 0.1 * mm, 1 * mm]  # Voxel size
    #dose.dose.active             = True
    #dose.dose_uncertainty.active = False
    #dose.edep_uncertainty.active = False
    
    ### PHSP actor for tests - OK
    #phsp                 = sim.add_actor("PhaseSpaceActor", "PhaseSpace")
    #phsp.attached_to     = phsp_plane.name
    #phsp.attributes      = ["KineticEnergy","PreDirection","EventPosition",]
    #phsp.output_filename = "phsp.root"


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
