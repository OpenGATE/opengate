import pathlib
from opengate.utility import g4_units
from opengate.geometry.utility import repeat_array, repeat_ring

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
        sim.add_material_database(f / "siemens_biograph_materials.db")

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
    ring.translation = None
    ring.rotation = None
    ring.material = "G4_AIR"
    le = repeat_array(ring.name, [1, 1, 4], [0, 0 * mm, 56 * mm])
    ring.repeat = le
    ring.color = transparent

    # Block
    block = sim.add_volume("Box", f"{name}_block")
    block.mother = ring.name
    block.size = [20 * mm, 52 * mm, 52 * mm]
    block.translation = None
    block.rotation = None
    block.material = "VM2000"
    le = repeat_ring(block.name, -4.28572, 48, [438 * mm, 0, 0], [0, 0, 1])
    block.color = blue
    block.repeat = le

    # Crystal
    crystal = sim.add_volume("Box", f"{name}_crystal")
    crystal.mother = block.name
    crystal.size = [20 * mm, 3.98 * mm, 3.98 * mm]
    crystal.material = "LSO"
    crystal.translation = None
    crystal.rotation = None
    le = repeat_array(crystal.name, [1, 13, 13], [0, 4 * mm, 4 * mm])
    crystal.repeat = le
    crystal.color = red

    return pet


def add_digitizer(
    sim, pet_name, output_filename, hits_name="Hits", singles_name="Singles"
):
    # get crystal volume
    crystal = sim.get_volume_user_info(f"{pet_name}_crystal")
    block = sim.get_volume_user_info(f"{pet_name}_block")
    ring = sim.get_volume_user_info(f"{pet_name}_ring")

    # hits collection
    hc = sim.add_actor("DigitizerHitsCollectionActor", hits_name)
    hc.mother = crystal.name
    hc.output = output_filename
    hc.attributes = [
        "PostPosition",
        "TotalEnergyDeposit",
        "PreStepUniqueVolumeID",
        "GlobalTime",
    ]

    # singles collection
    sc = sim.add_actor("DigitizerReadoutActor", singles_name)
    sc.input_digi_collection = hc.name
    sc.group_volume = block.name
    # sc.group_volume = ring.name # (I checked that is it different from block)
    # sc.group_volume = crystal.name # (I checked that is it different from block)
    sc.discretize_volume = crystal.name
    sc.policy = "EnergyWeightedCentroidPosition"
    sc.output = hc.output

    return sc
