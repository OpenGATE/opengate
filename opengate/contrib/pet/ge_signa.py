import pathlib
from opengate.utility import g4_units
from opengate.geometry.utility import get_grid_repetition, get_circular_repetition

# colors
red = [1, 0, 0, 1]
blue = [0, 0, 1, 1]
green = [0, 1, 0, 1]
yellow = [0.9, 0.9, 0.3, 1]
gray = [0.5, 0.5, 0.5, 1]
white = [1, 1, 1, 0.8]
transparent = [1, 1, 1, 0]


def create_LYSO_material(sim):
    g_cm3 = g4_units.g_cm3
    sim.volume_manager.material_database.add_material_weights(
        "LYSO", ["Lu", "Y", "Si", "O"], [0.7299, 0.0279, 0.0628, 0.1794], 7.21 * g_cm3    
    )
    

def add_pet(sim, name="pet"):
    """
    Geometry of a PET/MR SIGNA GE
    """

    # unit
    mm = g4_units.mm
   
    create_LYSO_material(sim)

     # ring volume
    pet = sim.add_volume("Tubs", "pet")
    pet.rmax = 350 * mm
    pet.rmin = 290 * mm
    pet.dz = 135 * mm
    pet.color = gray
    pet.material = "G4_AIR"

    # module
    module = sim.add_volume("Box", "module")
    module.mother = pet.name
    module.size = [64.5 * mm, 25 * mm, 250.4  * mm]
    translations_ring, rotations_ring = get_circular_repetition(
        28, [0 * mm, 324.3 * mm, 0 ], start_angle_deg=190, axis=[0, 0, 1]
    )
    module.translation = translations_ring
    module.rotation = rotations_ring
    module.material = "G4_AIR"
    module.color = white

    
    # unit
    unit = sim.add_volume("Box", "unit")
    unit.mother = module.name
    unit.size =  [ module.size[0] , module.size[1] , 47.84 * mm ]
    unit.material = "G4_AIR"
    unit.translation = get_grid_repetition([1, 1, 5], [0, 0 * mm, 50.64 * mm])
    unit.color = blue

    
    # block
    block = sim.add_volume("Box", "block")
    block.mother = unit.name
    block.size =  [ 15.9 * mm , module.size[1] , 47.84 * mm ]
    block.material = "G4_AIR"
    block.translation = get_grid_repetition([4, 1, 1], [16.2 * mm, 0 * mm, 0 * mm])
    block.color = red
    
    # optical
    optical = sim.add_volume("Box", "optical")
    optical.mother = block.name
    optical.size =  [ 15.9 * mm , module.size[1] , 15.9 * mm ]
    optical.material = "G4_AIR"
    optical.translation = get_grid_repetition([1, 1, 3], [0, 0 , 15.97 * mm])
    optical.color = yellow
    
    # Crystal
    crystal = sim.add_volume("Box", "crystal")
    crystal.mother = optical.name
    crystal.size = [3.95 * mm, module.size[1], 5.3 * mm]
    crystal.material = "LYSO"
    crystal.translation = get_grid_repetition([1, 1, 1], [3.9833 * mm ,0 * mm, 5.3 * mm])
    crystal.color = green

    return pet


def add_digitizer(
        sim, pet_name, output_filename, hits_name="Hits", singles_name="Singles"
):

    # unit
    mm = g4_units.mm
    keV = g4_units.keV
    ps = g4_units.ps
    
    
    # get crystal volume
    crystal = sim.volume_manager.volumes["crystal"]
    unit = sim.volume_manager.volumes["unit"]

    # hits collection
    hc = sim.add_actor("DigitizerHitsCollectionActor", hits_name)
    hc.attached_to = crystal.name
    hc.authorize_repeated_volumes = True
    hc.output_filename = output_filename
    hc.attributes = [
        "PostPosition",
        "TotalEnergyDeposit",
        "PreStepUniqueVolumeID",
        "GlobalTime",
    ]

    # ADDER
    sc_adder = sim.add_actor("DigitizerAdderActor", f"Singles_{crystal.name}_adder")
    sc_adder.attached_to = hc.attached_to
    sc_adder.authorize_repeated_volumes = True
    sc_adder.input_digi_collection = hc.name
    sc_adder.discretize_volume = crystal.name
    sc_adder.policy = "EnergyWeightedCentroidPosition"
    #sc_adder.output =  output_filename
    
    # READOUT 
    sc_ro = sim.add_actor("DigitizerReadoutActor",  f"Singles_{crystal.name}_readout")
    sc_ro.authorize_repeated_volumes = True
    sc_ro.attached_to = sc_adder.attached_to
    sc_ro.input_digi_collection = sc_adder.name
    sc_ro.group_volume = unit.name
    sc_ro.discretize_volume = crystal.name
    sc_ro.policy = "EnergyWinnerPosition"
    #sc_ro.output_filename =  output_filename

    # SPATIAL BLURRING
    sc_sp_blur = sim.add_actor("DigitizerSpatialBlurringActor", f"Singles_{crystal.name}_sp_blur")
    sc_sp_blur.attached_to = sc_ro.attached_to
    sc_sp_blur.authorize_repeated_volumes = True
    sc_sp_blur.input_digi_collection = sc_ro.name
    sc_sp_blur.keep_in_solid_limits = False
    sc_sp_blur.use_truncated_Gaussian = True
    sc_sp_blur.blur_attribute = "PostPosition"
    sc_sp_blur.blur_fwhm = [1*mm, 1*mm, 1*mm]
    #sc_sp_blur.output_filename =  output_filename

    # EFFICIENCY
    sc_efficiency = sim.add_actor("DigitizerEfficiencyActor",f"Singles_{crystal.name}_efficiency")
    sc_efficiency.attached_to = sc_sp_blur.attached_to
    sc_efficiency.authorize_repeated_volumes = True  
    sc_efficiency.input_digi_collection = sc_sp_blur.name
    sc_efficiency.efficiency = 0.93
    #sc_eff.output_filename =  output_filename
    
    # ENERGY BLURRING
    sc_energy_blur = sim.add_actor("DigitizerBlurringActor", f"Singles_{crystal.name}_energy_blur")
    sc_energy_blur.attached_to = sc_efficiency.attached_to
    sc_energy_blur.authorize_repeated_volumes = True
    sc_energy_blur.input_digi_collection = sc_efficiency.name
    sc_energy_blur.blur_attribute = "TotalEnergyDeposit"
    sc_energy_blur.blur_method = "InverseSquare" 
    sc_energy_blur.blur_resolution = 0.12
    sc_energy_blur.blur_reference_value = 511 * keV
    #sc_ebergy_blur.output_filename =  output_filename

    # TIME BLURRING
    sc_time_blur = sim.add_actor("DigitizerBlurringActor", f"Singles_{crystal.name}_time_blur")
    sc_time_blur.input_digi_collection = sc_energy_blur.name
    sc_time_blur.attached_to = sc_energy_blur.attached_to
    sc_time_blur.authorize_repeated_volumes = True     
    sc_time_blur.blur_attribute = "GlobalTime"
    sc_time_blur.blur_method = "Gaussian"
    sc_time_blur.blur_fwhm = 270 * ps
    #sc_time_blur.output_filename =  output_filename


    # ENERGY WINDOW 
    sc_energy_window = sim.add_actor("DigitizerEnergyWindowsActor",f"{singles_name}" )
    sc_energy_window.attached_to = sc_time_blur.attached_to
    sc_energy_window.authorize_repeated_volumes = True     
    sc_energy_window.input_digi_collection = sc_time_blur.name
    sc_energy_window.channels = [
        {"name": f"{singles_name}", "min": 425 * keV, "max": 650 * keV}]
    sc_energy_window.output_filename =  output_filename
    
    return sc_energy_window

## Sorter: 4.57 takeAllGoods minsecDiff 3
