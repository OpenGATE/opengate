import gam_gate as gam
import gam_g4 as g4
from scipy.spatial.transform import Rotation
from anytree import LevelOrderIter
import numpy as np

iec_plastic = 'IEC_PLASTIC'
water = 'G4_WATER'
iec_lung = 'G4_LUNG_ICRP'


def create_material():
    gcm3 = gam.g4_units('g/cm3')
    gam.new_material(f'ABS', 1.04 * gcm3, ['C', 'H', 'N'], [15, 17, 1])
    gam.new_material(f'LYSO', 7.1 * gcm3, 'Lu')


def add_pet(sim, name='pet'):
    # unit
    mm = gam.g4_units('mm')
    deg = gam.g4_units('deg')
    create_material()

    # colors
    red = [1, 0.7, 0.7, 0.8]
    blue = [0.5, 0.5, 1, 0.8]
    green = [0.5, 1, 0.5, 0.8]
    gray = [0.5, 0.5, 0.5, 1]
    white = [1, 1, 1, 0.8]

    # check overlap
    sim.g4_check_overlap_flag = True  # for debug

    # ring volume
    pet = sim.add_volume('Tubs', name)
    pet.rmax = 500 * mm
    pet.rmin = 360 * mm
    pet.dz = 164 * mm
    pet.color = gray

    # Module (each module has 4x5 stacks)
    module = sim.add_volume('Box', f'{name}_module')
    module.mother = pet.name
    module.size = [19 * mm, 131.4 * mm, 164 * mm]
    module.translation = None
    module.rotation = None
    module.material = 'ABS'
    module.color = blue
    le = gam.repeat_ring(module.name, 190 * deg, 18, [391.5 * mm, 0, 0], [0, 0, 1])
    module.repeat = le

    # Stack (each stack has 4x4 die)
    stack = sim.add_volume('Box', f'{name}_stack')
    stack.mother = module.name
    stack.size = [module.size[0], 32.6 * mm, 32.6 * mm]
    stack.material = 'G4_AIR'
    stack.color = green
    stack.translation = None
    stack.rotation = None
    # compute starting coordinate of the center of the stack such as its border coincides
    # with the border of the module (warning 32.85 instead of 32.6, because there is a
    # small space bw stack)
    sy = module.size[1] / 4
    sz = module.size[2] / 5
    start = -np.array(module.size) / 2
    start[0] = 0
    start[1] += sy / 2
    start[2] += sz / 2
    le = gam.repeat_array(stack.name, start, [1, 4, 5], [0., sy, sz])
    stack.repeat = le

    # Die (each die has 2x2 crystal)
    die = sim.add_volume('Box', f'{name}_die')
    die.mother = stack.name
    die.size = [module.size[0], 8 * mm, 8 * mm]
    die.material = 'G4_AIR'
    die.color = white
    die.translation = None
    die.rotation = None
    # stack is 32.6 = 8x4 + 0.6 mm
    spacing = stack.size[1] / 4
    start = -np.array(stack.size) / 2
    start[0] = 0
    start[1] += spacing / 2
    start[2] += spacing / 2
    le = gam.repeat_array(die.name, start, [1, 4, 4], [0., spacing, spacing])
    die.repeat = le

    # Crystal
    crystal = sim.add_volume('Box', f'{name}_crystal')
    crystal.mother = die.name
    crystal.size = [module.size[0], 4 * mm, 4 * mm]
    crystal.material = 'LYSO'
    crystal.color = red
    crystal.translation = None
    crystal.rotation = None
    spacing = die.size[1] / 2
    start = -np.array(die.size) / 2
    start[0] = 0
    start[1] += spacing / 2
    start[2] += spacing / 2
    le = gam.repeat_array(crystal.name, start, [1, 2, 2], [0., spacing, spacing])
    crystal.repeat = le

    # FIXME need housing (later)
    # SiPMs HOUSING
    # SiPMs UNITS
    # coolingplate
    # endshielding1
    # endshielding2
    # cover Lexan layer

    return pet
