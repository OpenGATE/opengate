import gam_gate as gam

iec_plastic = 'IEC_PLASTIC'
water = 'G4_WATER'
iec_lung = 'G4_LUNG_ICRP'


def create_material():
    gcm3 = gam.g4_units('g/cm3')
    gam.new_material(f'ABS', 1.04 * gcm3, ['C', 'H', 'N'], [15, 17, 1])
    gam.new_material(f'Copper', 8.920 * gcm3, 'Cu')
    gam.new_material(f'LYSO', 7.1 * gcm3, 'Lu')
    gam.new_material(f'Lead', 11.4 * gcm3, 'Pb')
    gam.new_material(f'Lexan', 1.2 * gcm3, ['C', 'H', 'O'], [15, 16, 2])


def add_pet(sim, name='pet'):
    # unit
    mm = gam.g4_units('mm')

    # defined material
    create_material()

    # colors (similar to the ones of Gate)
    red = [1, 0, 0, 1]
    blue = [0, 0, 1, 1]
    green = [0, 1, 0, 1]
    yellow = [0.9, 0.9, 0.3, 1]
    gray = [0.5, 0.5, 0.5, 1]
    white = [1, 1, 1, 0.8]

    # check overlap for debug (can be switch off)
    sim.g4_check_overlap_flag = False

    # ring volume
    pet = sim.add_volume('Tubs', name)
    pet.rmax = 500 * mm
    pet.rmin = 360 * mm
    pet.dz = 164 * mm
    pet.color = gray

    # ------------------------------------------
    # 18 modules
    #   of 4x5 stack
    #       of 4x4 die
    #           of 2x2 crystal
    # ------------------------------------------

    # Module (each module has 4x5 stacks)
    module = sim.add_volume('Box', f'{name}_module')
    module.mother = pet.name
    module.size = [19 * mm, 131.4 * mm, 164 * mm]
    module.translation = None
    module.rotation = None
    module.material = 'ABS'
    module.color = blue
    le = gam.repeat_ring(module.name, 190, 18, [391.5 * mm, 0, 0], [0, 0, 1])  # FIXME
    module.repeat = le

    # Stack (each stack has 4x4 die)
    stack = sim.add_volume('Box', f'{name}_stack')
    stack.mother = module.name
    stack.size = [module.size[0], 32.6 * mm, 32.6 * mm]
    stack.material = 'G4_AIR'
    stack.translation = None
    stack.rotation = None
    le = gam.repeat_array(stack.name, [1, 4, 5], [0, 32.85 * mm, 32.85 * mm])
    stack.repeat = le
    stack.color = green

    # Die (each die has 2x2 crystal)
    die = sim.add_volume('Box', f'{name}_die')
    die.mother = stack.name
    die.size = [module.size[0], 8 * mm, 8 * mm]
    die.material = 'G4_AIR'
    die.translation = None
    die.rotation = None
    le = gam.repeat_array(die.name, [1, 4, 4], [0, 8 * mm, 8 * mm])
    die.repeat = le
    die.color = white

    # Crystal
    crystal = sim.add_volume('Box', f'{name}_crystal')
    crystal.mother = die.name
    crystal.size = [module.size[0], 4 * mm, 4 * mm]
    crystal.material = 'LYSO'
    crystal.translation = None
    crystal.rotation = None
    le = gam.repeat_array(crystal.name, [1, 2, 2], [0, 4 * mm, 4 * mm])
    crystal.repeat = le
    crystal.color = red

    # ------------------------------------------
    # Housing
    # ------------------------------------------

    # SiPMs HOUSING
    housing = sim.add_volume('Box', f'{name}_housing')
    housing.mother = pet.name
    housing.size = [1 * mm, 131 * mm, 164 * mm]
    housing.translation = None  # [408 * mm, 0, 0]
    housing.rotation = None
    housing.material = 'G4_AIR'
    housing.color = yellow
    le = gam.repeat_ring(module.name, 190, 18, [408 * mm, 0, 0], [0, 0, 1])
    housing.repeat = le

    # SiPMs UNITS
    sipms = sim.add_volume('Box', f'{name}_sipms')
    sipms.mother = housing.name

    sipms.size = [1 * mm, 32.6 * mm, 32.6 * mm]
    sipms.translation = None
    sipms.rotation = None
    sipms.material = 'G4_AIR'
    sipms.color = green
    spacing = 32.8 * mm
    le = gam.repeat_array(sipms.name, [1, 4, 5], [0, spacing, spacing])
    sipms.repeat = le

    # cooling plate
    coolingplate = sim.add_volume('Box', f'{name}_coolingplate')
    coolingplate.mother = pet.name
    coolingplate.size = [30 * mm, 130.2 * mm, 164 * mm]
    coolingplate.translation = None
    coolingplate.rotation = None
    coolingplate.material = 'Copper'
    coolingplate.color = blue
    le = gam.repeat_ring(module.name, 190, 18, [430 * mm, 0, 0], [0, 0, 1])
    coolingplate.repeat = le

    # ------------------------------------------
    # Shielding
    # ------------------------------------------

    # end shielding 1
    endshielding1 = sim.add_volume('Tubs', f'{name}_endshielding1')
    endshielding1.mother = 'world'
    endshielding1.translation = [0, 0, 95 * mm]
    endshielding1.rmax = 410 * mm
    endshielding1.rmin = 362.5 * mm
    endshielding1.dz = 25 * mm
    endshielding1.material = 'Lead'
    endshielding1.color = yellow

    # end shielding 2
    endshielding2 = sim.add_volume('Tubs', f'{name}_endshielding2')
    endshielding2.mother = 'world'
    endshielding2.translation = [0, 0, -95 * mm]
    endshielding2.rmax = 410 * mm
    endshielding2.rmin = 362.5 * mm
    endshielding2.dz = 25 * mm
    endshielding2.material = 'Lead'
    endshielding2.color = yellow

    # cover Lexan layer
    cover = sim.add_volume('Tubs', f'{name}_cover')
    cover.mother = 'world'
    cover.translation = [0, 0, 0]
    cover.rmax = 355.5 * mm
    cover.rmin = 354 * mm
    cover.dz = 392 * mm
    cover.material = 'Lexan'
    cover.color = white

    return pet
