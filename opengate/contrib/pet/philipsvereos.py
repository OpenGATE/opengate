from scipy.spatial.transform import Rotation
from opengate.utility import g4_units
from opengate.geometry.utility import repeat_ring, repeat_array

# colors (similar to the ones of Gate)
red = [1, 0, 0, 1]
blue = [0, 0, 1, 1]
green = [0, 1, 0, 1]
yellow = [0.9, 0.9, 0.3, 1]
gray = [0.5, 0.5, 0.5, 1]
white = [1, 1, 1, 0.8]


def create_material():
    gcm3 = g4_units.g_cm3
    new_material_nb_atoms(f"ABS", 1.04 * gcm3, ["C", "H", "N"], [15, 17, 1])
    new_material_weights(f"Copper", 8.920 * gcm3, "Cu")
    new_material_nb_atoms(f"LYSO", 7.1 * gcm3, ["Lu", "Y", "Si", "O"], [18, 2, 10, 50])
    new_material_nb_atoms(f"LYSO_debug", 7.1 * gcm3, ["Lu", "O"], [1, 50])
    new_material_weights(f"Lead", 11.16 * gcm3, ["Pb", "Sb"], [0.95, 0.05])
    new_material_nb_atoms(f"Lexan", 1.2 * gcm3, ["C", "H", "O"], [15, 16, 2])
    new_material_weights(f"CarbonFiber", 1.78 * gcm3, "C")


def add_pet(sim, name="pet", create_housing=True, create_mat=True):
    """
    Geometry of a PET Philips VEREOS
    Salvadori J, Labour J, Odille F, Marie PY, Badel JN, Imbert L, Sarrut D.
    Monte Carlo simulation of digital photon counting PET.
    EJNMMI Phys. 2020 Apr 25;7(1):23.
    doi: 10.1186/s40658-020-00288-w
    """

    # unit
    mm = g4_units.mm

    # define the materials (if needed)
    if create_mat:
        create_material()

    # ring volume
    pet = sim.add_volume("Tubs", name)
    pet.rmax = 500 * mm
    pet.rmin = 360 * mm
    pet.dz = 164 * mm / 2.0
    pet.color = gray
    pet.material = "G4_AIR"

    # ------------------------------------------
    # 18 modules
    #   of 4x5 stack
    #       of 4x4 die
    #           of 2x2 crystal
    # ------------------------------------------

    # Module (each module has 4x5 stacks)
    module = sim.add_volume("Box", f"{name}_module")
    module.mother = pet.name
    module.size = [19 * mm, 131.4 * mm, 164 * mm]
    module.translation = None
    module.rotation = None
    module.material = "ABS"
    module.color = blue
    le = repeat_ring(module.name, 190, 18, [391.5 * mm, 0, 0], [0, 0, 1])
    module.repeat = le

    # Stack (each stack has 4x4 die)
    stack = sim.add_volume("Box", f"{name}_stack")
    stack.mother = module.name
    stack.size = [module.size[0], 32.6 * mm, 32.6 * mm]
    stack.material = "G4_AIR"
    stack.translation = None
    stack.rotation = None
    le = repeat_array(stack.name, [1, 4, 5], [0, 32.85 * mm, 32.85 * mm])
    stack.repeat = le
    stack.color = green

    # Die (each die has 2x2 crystal)
    die = sim.add_volume("Box", f"{name}_die")
    die.mother = stack.name
    die.size = [module.size[0], 8 * mm, 8 * mm]
    die.material = "G4_AIR"
    die.translation = None
    die.rotation = None
    le = repeat_array(die.name, [1, 4, 4], [0, 8 * mm, 8 * mm])
    die.repeat = le
    die.color = white

    # Crystal
    crystal = sim.add_volume("Box", f"{name}_crystal")
    crystal.mother = die.name
    crystal.size = [module.size[0], 4 * mm, 4 * mm]
    crystal.material = "LYSO"
    crystal.translation = None
    crystal.rotation = None
    le = repeat_array(crystal.name, [1, 2, 2], [0, 4 * mm, 4 * mm])
    crystal.repeat = le
    crystal.color = red

    # ------------------------------------------
    # Housing
    # ------------------------------------------

    if not create_housing:
        return pet

    # SiPMs HOUSING
    housing = sim.add_volume("Box", f"{name}_housing")
    housing.mother = pet.name
    housing.size = [1 * mm, 131 * mm, 164 * mm]
    housing.translation = None  # [408 * mm, 0, 0]
    housing.rotation = None
    housing.material = "G4_AIR"
    housing.color = yellow
    le = repeat_ring(module.name, 190, 18, [408 * mm, 0, 0], [0, 0, 1])
    housing.repeat = le

    # SiPMs UNITS
    sipms = sim.add_volume("Box", f"{name}_sipms")
    sipms.mother = housing.name

    sipms.size = [1 * mm, 32.6 * mm, 32.6 * mm]
    sipms.translation = None
    sipms.rotation = None
    sipms.material = "G4_AIR"
    sipms.color = green
    spacing = 32.8 * mm
    le = repeat_array(sipms.name, [1, 4, 5], [0, spacing, spacing])
    sipms.repeat = le

    # cooling plate
    coolingplate = sim.add_volume("Box", f"{name}_coolingplate")
    coolingplate.mother = pet.name
    coolingplate.size = [30 * mm, 130.2 * mm, 164 * mm]
    coolingplate.translation = None
    coolingplate.rotation = None
    coolingplate.material = "Copper"
    coolingplate.color = blue
    le = repeat_ring(module.name, 190, 18, [430 * mm, 0, 0], [0, 0, 1])
    coolingplate.repeat = le

    # ------------------------------------------
    # Shielding
    # ------------------------------------------

    # end shielding 1
    endshielding1 = sim.add_volume("Tubs", f"{name}_endshielding1")
    endshielding1.mother = "world"
    endshielding1.translation = [0, 0, 95 * mm]
    endshielding1.rmax = 410 * mm
    endshielding1.rmin = 362.5 * mm
    endshielding1.dz = 25 * mm / 2.0
    endshielding1.material = "Lead"
    endshielding1.color = yellow

    # end shielding 2
    endshielding2 = sim.add_volume("Tubs", f"{name}_endshielding2")
    endshielding2.mother = "world"
    endshielding2.translation = [0, 0, -95 * mm]
    endshielding2.rmax = 410 * mm
    endshielding2.rmin = 362.5 * mm
    endshielding2.dz = 25 * mm / 2.0
    endshielding2.material = "Lead"
    endshielding2.color = yellow

    # cover Lexan layer
    cover = sim.add_volume("Tubs", f"{name}_cover")
    cover.mother = "world"
    cover.translation = [0, 0, 0]
    cover.rmax = 355.5 * mm
    cover.rmin = 354 * mm
    cover.dz = 392 * mm / 2.0
    cover.material = "Lexan"
    cover.color = white

    return pet


def add_pet_debug(sim, name="pet", create_housing=True, create_mat=True):
    """
    FIXME DEBUG
    """

    # unit
    mm = g4_units.mm

    # define the materials (if needed)
    if create_mat:
        create_material()

    # ring volume
    pet = sim.add_volume("Tubs", name)
    pet.rmax = 500 * mm
    pet.rmin = 360 * mm
    pet.dz = 164 * mm / 2.0
    pet.color = gray
    pet.material = "G4_AIR"

    # ------------------------------------------
    # 18 modules
    #   of 4x5 stack
    #       of 4x4 die
    #           of 2x2 crystal
    # ------------------------------------------

    # Module (18 modules around 360 deg)
    module = sim.add_volume("Box", f"{name}_crystal")
    module.mother = pet.name
    module.size = [19 * mm, 131.4 * mm, 164 * mm]
    module.translation = None
    module.rotation = None
    module.material = "LYSO"
    module.color = blue
    le = repeat_ring(module.name, 190, 18, [391.5 * mm, 0, 0], [0, 0, 1])
    module.repeat = le

    """# Stack (4x5 in a module)
    stack = sim.add_volume("Box", f"{name}_stack")
    stack.mother = module.name
    stack.size = [module.size[0], 32.6 * mm, 32.6 * mm]
    stack.material = "G4_AIR"
    stack.translation = None
    stack.rotation = None
    le = repeat_array(stack.name, [1, 4, 5], [0, 32.85 * mm, 32.85 * mm])
    stack.repeat = le
    stack.color = green

    # Die (4x4 in a stack)
    die = sim.add_volume("Box", f"{name}_die")
    die.mother = stack.name
    die.size = [module.size[0], 8 * mm, 8 * mm]
    die.material = "G4_AIR"
    die.translation = None
    die.rotation = None
    le = repeat_array(die.name, [1, 4, 4], [0, 8 * mm, 8 * mm])
    die.repeat = le
    die.color = white

    # Crystal (2x2 in a die)
    crystal = sim.add_volume("Box", f"{name}_crystal")
    crystal.mother = die.name
    crystal.size = [module.size[0], 4 * mm, 4 * mm]
    crystal.material = "LYSO"
    crystal.translation = None
    crystal.rotation = None
    le = repeat_array(crystal.name, [1, 2, 2], [0, 4 * mm, 4 * mm])
    crystal.repeat = le
    crystal.color = red"""

    # ------------------------------------------
    # Housing
    # ------------------------------------------

    if not create_housing:
        return pet

    # SiPMs HOUSING
    housing = sim.add_volume("Box", f"{name}_housing")
    housing.mother = pet.name
    housing.size = [1 * mm, 131 * mm, 164 * mm]
    housing.translation = None  # [408 * mm, 0, 0]
    housing.rotation = None
    housing.material = "G4_AIR"
    housing.color = yellow
    le = repeat_ring(module.name, 190, 18, [408 * mm, 0, 0], [0, 0, 1])
    housing.repeat = le

    # SiPMs UNITS
    sipms = sim.add_volume("Box", f"{name}_sipms")
    sipms.mother = housing.name

    sipms.size = [1 * mm, 32.6 * mm, 32.6 * mm]
    sipms.translation = None
    sipms.rotation = None
    sipms.material = "G4_AIR"
    sipms.color = green
    spacing = 32.8 * mm
    le = repeat_array(sipms.name, [1, 4, 5], [0, spacing, spacing])
    sipms.repeat = le

    # cooling plate
    coolingplate = sim.add_volume("Box", f"{name}_coolingplate")
    coolingplate.mother = pet.name
    coolingplate.size = [30 * mm, 130.2 * mm, 164 * mm]
    coolingplate.translation = None
    coolingplate.rotation = None
    coolingplate.material = "Copper"
    coolingplate.color = blue
    le = repeat_ring(module.name, 190, 18, [430 * mm, 0, 0], [0, 0, 1])
    coolingplate.repeat = le

    # ------------------------------------------
    # Shielding
    # ------------------------------------------

    # end shielding 1
    endshielding1 = sim.add_volume("Tubs", f"{name}_endshielding1")
    endshielding1.mother = "world"
    endshielding1.translation = [0, 0, 95 * mm]
    endshielding1.rmax = 410 * mm
    endshielding1.rmin = 362.5 * mm
    endshielding1.dz = 25 * mm / 2.0
    endshielding1.material = "Lead"
    endshielding1.color = yellow

    # end shielding 2
    endshielding2 = sim.add_volume("Tubs", f"{name}_endshielding2")
    endshielding2.mother = "world"
    endshielding2.translation = [0, 0, -95 * mm]
    endshielding2.rmax = 410 * mm
    endshielding2.rmin = 362.5 * mm
    endshielding2.dz = 25 * mm / 2.0
    endshielding2.material = "Lead"
    endshielding2.color = yellow

    # cover Lexan layer
    cover = sim.add_volume("Tubs", f"{name}_cover")
    cover.mother = "world"
    cover.translation = [0, 0, 0]
    cover.rmax = 355.5 * mm
    cover.rmin = 354 * mm
    cover.dz = 392 * mm / 2.0
    cover.material = "Lexan"
    cover.color = white

    return pet


def add_table(sim, name="pet"):
    """
    Add a patient table
    """

    # unit
    mm = g4_units.mm
    cm = g4_units.cm
    deg = g4_units.deg

    # main bed
    bed = sim.add_volume("Tubs", f"{name}_bed")
    bed.mother = "world"
    bed.rmax = 439 * mm
    bed.rmin = 406 * mm
    bed.dz = 200 * cm / 2.0
    bed.sphi = 0 * deg
    bed.dphi = 70 * deg
    bed.translation = [0, 25 * cm, 0]
    bed.rotation = Rotation.from_euler("z", -125, degrees=True).as_matrix()
    bed.material = "CarbonFiber"
    bed.color = white

    # interior of the bed
    bedin = sim.add_volume("Tubs", f"{name}_bedin")
    bedin.mother = bed.name
    bedin.rmax = 436.5 * mm
    bedin.rmin = 408.5 * mm
    bedin.dz = 200 * cm / 2.0
    bedin.sphi = 0 * deg
    bedin.dphi = 69 * deg
    bedin.translation = [0, 0, 0]
    bedin.rotation = Rotation.from_euler("z", 0.5, degrees=True).as_matrix()
    bedin.material = "G4_AIR"
    bedin.color = red

    return bed
