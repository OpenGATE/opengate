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


def add_pet(sim, name="pet", load_db=True):
    """
    Geometry of a PET Siemens Biograph
    https://doi.org/10.1002/mp.16032
    """

    # unit
    mm = g4_units.mm

    # material
    if load_db:
        f = pathlib.Path(__file__).parent.resolve()
        sim.volume_manager.add_material_database(f / "siemens_biograph_materials.db")

    # ring volume
    pet = sim.add_volume("Tubs", name)
    pet.rmax = 460 * mm
    pet.rmin = 410 * mm
    pet.dz = 270 * mm / 2.0
    pet.color = white
    pet.material = "G4_AIR"

    # sim.user_info.check_volumes_overlap = False
    sim.user_info.check_volumes_overlap = True

    # 4 rings
    ring = sim.add_volume("Tubs", f"{name}_ring")
    ring.mother = pet.name
    ring.rmax = 460 * mm
    ring.rmin = 410 * mm
    ring.dz = 56 * mm / 2
    ring.translation = get_grid_repetition([1, 1, 4], [0, 0 * mm, 56 * mm])
    ring.material = "G4_AIR"
    ring.color = transparent

    # Block
    block = sim.add_volume("Box", f"{name}_block")
    block.mother = ring.name
    block.size = [20 * mm, 52 * mm, 52 * mm]
    block.material = "VM2000"
    translations_ring, rotations_ring = get_circular_repetition(
        48, [438 * mm, 0, 0], start_angle_deg=-4.28572, axis=[0, 0, 1]
    )
    block.translation = translations_ring
    block.rotation = rotations_ring
    block.color = blue

    # Crystal
    crystal = sim.add_volume("Box", f"{name}_crystal")
    crystal.mother = block.name
    crystal.size = [20 * mm, 3.98 * mm, 3.98 * mm]
    crystal.material = "LSO"
    crystal.translation = get_grid_repetition([1, 13, 13], [0, 4 * mm, 4 * mm])
    crystal.color = red

    return pet


def add_digitizer(
    sim, pet_name, output_filename, hits_name="Hits", singles_name="Singles"
):
    # get crystal volume
    crystal = sim.volume_manager.volumes[f"{pet_name}_crystal"]
    block = sim.volume_manager.volumes[f"{pet_name}_block"]
    ring = sim.volume_manager.volumes[f"{pet_name}_ring"]

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

    # singles collection
    sc = sim.add_actor("DigitizerReadoutActor", singles_name)
    sc.authorize_repeated_volumes = True
    sc.attached_to = crystal.name
    sc.input_digi_collection = hc.name
    sc.group_volume = block.name
    # sc.group_volume = ring.name # (I checked that is it different from block)
    # sc.group_volume = crystal.name # (I checked that is it different from block)
    sc.discretize_volume = crystal.name
    sc.policy = "EnergyWeightedCentroidPosition"
    sc.output_filename = hc.output_filename

    return sc
