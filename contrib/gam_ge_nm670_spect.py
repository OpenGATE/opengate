import gam_gate as gam
import gam_g4 as g4
import pathlib
import copy
import time
from scipy.spatial.transform import Rotation

# unit
cm = gam.g4_units('cm')
mm = gam.g4_units('mm')
deg = gam.g4_units('deg')

# colors
red = [1, 0.7, 0.7, 0.8]
blue = [0.5, 0.5, 1, 0.8]
gray = [0.5, 0.5, 0.5, 1]
white = [1, 1, 1, 1]
yellow = [1, 1, 0, 1]
green = [0, 1, 0, 1]


def add_spect(sim, name='spect', debug=False):
    f = pathlib.Path(__file__).parent.resolve()
    sim.add_material_database(f'{f}/ge_nm670_spect_materials.db')

    # check overlap
    sim.g4_check_overlap_flag = False  # FIXME for debug

    # spect head
    head, lead_cover = add_spect_head(sim, name)

    # spect head
    crystal = add_spect_crystal(sim, name, lead_cover)

    # spect collimator
    colli = add_collimator(sim, name, head, debug)

    return head


def add_spect_head(sim, name):
    # bounding box
    spect_length = 19 * cm  # depends on the collimator type
    head = sim.add_volume('Box', name)
    head.material = 'G4_AIR'
    head.size = [57.6 * cm, 44.6 * cm, spect_length]
    head.color = white

    # shielding
    shielding = sim.add_volume('Box', f'{name}_shielding')
    shielding.mother = head.name
    shielding.size = head.size.copy()
    shielding.size[2] = 11.1375 * cm
    shielding.translation = [0, 0, -3.64 * cm]
    shielding.material = 'Steel'
    shielding.color = yellow

    # shielding lead cover
    lead_cover = sim.add_volume('Box', f'{name}_lead_cover')
    lead_cover.mother = shielding.name
    lead_cover.size = [57.6 * cm, 40.6 * cm, 10.1375 * cm]
    lead_cover.translation = [0, 0, 0.5 * cm]
    lead_cover.material = 'Lead'
    lead_cover.color = gray

    # shielding alu cover
    alu_cover = sim.add_volume('Box', f'{name}_alu_cover')
    alu_cover.mother = lead_cover.name
    alu_cover.size = [54 * cm, 40 * cm, 0.13 * cm]
    alu_cover.translation = [0, 0, 5.00375 * cm]
    alu_cover.material = 'Aluminium'
    alu_cover.color = blue

    # shielding reflector
    reflector = sim.add_volume('Box', f'{name}_reflector')
    reflector.mother = lead_cover.name
    reflector.size = [54 * cm, 40 * cm, 0.12 * cm]
    reflector.translation = [0, 0, 3.92625 * cm]
    reflector.material = 'TiO2'
    reflector.color = green

    # backside
    # The back-side is fairly complex, and may have a strong influence on the
    # spectrum: the model shown here is simplified
    backside = sim.add_volume('Box', f'{name}_backside')
    backside.mother = lead_cover.name
    backside.size = [54 * cm, 40 * cm, 8 * cm]
    backside.translation = [0, 0, -0.13375 * cm]
    backside.material = 'Pyrex66'
    backside.color = blue

    return head, lead_cover


def add_spect_crystal(sim, name, lead_cover):
    # mono-bloc crystal thickness 3/8 of inch
    crystal = sim.add_volume('Box', f'{name}_crystal')
    crystal.mother = lead_cover.name
    crystal.size = [54 * cm, 40 * cm, 0.9525 * cm]
    crystal.translation = [0, 0, 4.4625 * cm]
    crystal.material = 'NaITl'
    crystal.color = yellow
    return crystal


def add_collimator(sim, name, head, debug):
    # mono-bloc crystal thickness 3/8 of inch
    colli_trd = sim.add_volume('Trd', f'{name}_collimator_trd')
    colli_trd.mother = head.name
    colli_trd.dx2 = 56.8 * cm / 2.0
    colli_trd.dy2 = 42.8 * cm / 2.0
    colli_trd.dx1 = 57.6 * cm / 2.0
    colli_trd.dy1 = 44.6 * cm / 2.0
    colli_trd.dz = 4.18 * cm / 2.0
    colli_trd.translation = [0, 0, 4.02 * cm]
    # colli_box = sim.add_volume('Box', f'{name}_collimator_box')
    # colli_box.size = [0, 21.3 * cm, 3.2 * cm]
    colli_trd.material = 'G4_AIR'
    colli_trd.color = red

    # PSD (Position Sensitive Detection)
    psd = sim.add_volume('Box', f'{name}_collimator_psd')
    psd.mother = colli_trd.name
    psd.size = [54.6 * cm, 40.6 * cm, 0.1 * cm]
    psd.translation = [0, 0, 2.04 * cm]
    psd.material = 'Aluminium'
    psd.color = green

    # PSD layer
    psd_layer = sim.add_volume('Box', f'{name}_collimator_psd_layer')
    psd_layer.mother = colli_trd.name
    psd_layer.size = [54.6 * cm, 40.6 * cm, 0.15 * cm]
    psd_layer.translation = [0, 0, 1.915 * cm]
    psd_layer.material = 'PVC'
    psd_layer.color = red

    # Alu cover
    alu_cover = sim.add_volume('Box', f'{name}_collimator_alu_cover')
    alu_cover.mother = colli_trd.name
    alu_cover.size = [54.6 * cm, 40.6 * cm, 0.05 * cm]
    alu_cover.translation = [0, 0, -2.065 * cm]
    alu_cover.material = 'Aluminium'
    alu_cover.color = blue

    # air gap
    air_gap = sim.add_volume('Box', f'{name}_collimator_air_gap')
    air_gap.mother = colli_trd.name
    air_gap.size = [54.6 * cm, 40.6 * cm, 0.38 * cm]
    air_gap.translation = [0, 0, 1.65 * cm]
    air_gap.material = 'G4_AIR'
    air_gap.color = blue

    # core
    core = sim.add_volume('Box', f'{name}_collimator_core')
    core.mother = colli_trd.name
    core.size = [54.6 * cm, 40.6 * cm, 3.5 * cm]
    core.translation = [0, 0, -0.29 * cm]
    core.material = 'Lead'
    core.color = blue

    colli_with_param(sim, name, core, debug)
    # colli_with_repeater(sim, name, core, debug)
    # colli_with_bool(sim, name, core, debug)
    # colli_with_bool2(sim, name, core, debug)

    return colli_trd


def colli_with_bool2(sim, name, core, debug):
    print("version2")
    hole_translation = [2.94449 * mm, 1.7 * mm, 0]
    hole_repeat = [183, 235, 1]
    # hole_repeat = [10, 10, 1]
    start = [-(hole_repeat[0] * hole_translation[0]) / 2.0,
             -(hole_repeat[1] * hole_translation[1]) / 2.0,
             0]
    if debug:
        hole_repeat = [20, 20, 1]

    # one single hole
    hole = sim.new_solid('Polyhedra', f'{name}_collimator_hole')
    hole.phi_start = 0 * deg
    hole.phi_total = 360 * deg
    hole.num_side = 6
    hole.num_zplanes = 2
    h = 3.5 * cm
    hole.zplane = [-h / 2, h - h / 2]
    hole.radius_inner = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    r = 0.075 * cm
    hole.radius_outer = [r] * hole.num_side

    rotation = Rotation.identity().as_matrix()
    translation = start.copy()
    solid = None

    col_translation = [0, 0, 0]
    for j in range(hole_repeat[1]):
        holei = sim.new_solid('Polyhedra', f'{name}_collimator_hole_{j}')
        gam.vol_copy(hole, holei)
        if j == 0:
            solid = gam.solid_multi_union_start(hole, col_translation.copy(), Rotation.identity().as_matrix())
        else:
            gam.solid_multi_union_add(solid, holei, col_translation.copy(), Rotation.identity().as_matrix())
        col_translation[1] += hole_translation[1]
        # print(col_translation)

    for i in range(hole_repeat[0]):
        print('i', i, translation)
        hole_vol = sim.add_volume_from_solid(solid, f'{name}_collimator_hole_row_{i}')
        hole_vol.material = 'G4_AIR'
        hole_vol.mother = core.name
        hole_vol.translation = translation.copy()
        # print(translation, hole_vol)
        translation[0] += hole_translation[0]


def colli_with_bool(sim, name, core, debug):
    # parameters for all the holes
    """
    Warning : there are 183 x 235 'holes'. While it can be created with simple repeater,
    it takes a very long computation time (>30sec) for building the geometry. I dont know exactly
    why (probably G4PVPlacement performs some processes related to the number of daughters, each time
    a new daughter is added).

    The current solution is to create intermediate boolean volume merging a 'column' of holes
    as a single volume. This volume is then repeated and everything goes fine.
    No idea if this approach slow down the running. To be checked.
    """
    hole_translation = [2.94449 * mm, 1.7 * mm, 0]
    hole_repeat = [183, 235, 1]
    if debug:
        hole_repeat = [20, 20, 1]

    # one single hole
    hole = sim.new_solid('Polyhedra', f'{name}_collimator_hole1')
    hole.phi_start = 0 * deg
    hole.phi_total = 360 * deg
    hole.num_side = 6
    hole.num_zplanes = 2
    h = 3.5 * cm
    hole.zplane = [-h / 2, h - h / 2]
    hole.radius_inner = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    r = 0.075 * cm
    hole.radius_outer = [r] * hole.num_side

    # compute a solid with a column of holes
    h = copy.deepcopy(hole)
    for i in range(hole_repeat[1]):
        hole2 = sim.new_solid('Polyhedra', f'{name}_collimator_hole2')
        gam.vol_copy(hole, hole2)
        h = gam.solid_union(h, hole2, [0, i * 1.7 * mm, 0])
    hole = sim.add_volume_from_solid(h, f'{name}_collimator_hole12')
    hole.material = 'G4_AIR'
    hole.mother = core.name
    start = [-(hole_repeat[0] * hole_translation[0]) / 2.0,
             -(hole_repeat[1] * hole_translation[1]) / 2.0, 0]
    hole.translation = None
    hole.rotation = None

    # repeat for all rows
    size = [hole_repeat[0], 1, 1]
    rh = gam.repeat_array(hole.name, start, size, hole_translation)
    hole.repeat = rh

    # repeat with offset
    r2 = copy.deepcopy(hole.repeat)
    for r in r2:
        r['name'] = f'{r["name"]}_2'
        r['translation'][0] += 1.47224 * mm
        r['translation'][1] += 0.85 * mm
    hole.repeat = hole.repeat + r2


def colli_with_repeater(sim, name, core, debug):
    # parameters for all the holes
    hole_translation = [2.94449 * mm, 1.7 * mm, 0]
    hole_repeat = [183, 235, 1]
    # hole_repeat = [48, 230, 1]
    hole2_offset = [1.47224 * mm, 0.85 * mm, 0]
    if debug:
        hole_repeat = [20, 20, 1]

    # one single hole
    hole = sim.add_volume('Polyhedra', f'{name}_collimator_hole')
    hole.phi_start = 0 * deg
    hole.phi_total = 360 * deg
    hole.num_side = 6
    hole.num_zplanes = 2
    h = 3.5 * cm
    hole.zplane = [-h / 2, h - h / 2]
    hole.radius_inner = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    r = 0.075 * cm
    hole.radius_outer = [r] * hole.num_side

    start = [-(hole_repeat[0] * hole_translation[0]) / 2.0,
             -(hole_repeat[1] * hole_translation[1]) / 2.0, 0]
    size = hole_repeat
    rh = gam.repeat_array(hole.name, start, size, hole_translation)
    hole.repeat = rh
    hole.translation = None
    hole.rotation = None
    hole.material = 'G4_AIR'
    hole.mother = core.name

    hole2 = sim.add_volume('Polyhedra', f'{name}_collimator_hole_2')
    gam.vol_copy(hole, hole2)
    start[0] += hole2_offset[0]
    start[1] += hole2_offset[1]
    rh = gam.repeat_array(hole2.name, start, size, hole_translation)
    hole2.repeat = rh
    hole2.translation = None
    hole2.rotation = None
    hole2.material = 'G4_AIR'
    hole2.mother = core.name


def colli_with_param(sim, name, core, debug):
    # parameters for all the holes
    hole_translation = [2.94449 * mm, 1.7 * mm, 0]
    hole_repeat = [183, 235, 1]
    hole_repeat = [48, 230, 1]
    hole2_offset = [1.47224 * mm, 0.85 * mm, 0]
    if debug:
        hole_repeat = [20, 20, 1]

    # one single hole
    hole = sim.add_volume('Polyhedra', f'{name}_collimator_hole')
    hole.phi_start = 0 * deg
    hole.phi_total = 360 * deg
    hole.num_side = 6
    hole.num_zplanes = 2
    h = 3.5 * cm
    hole.zplane = [-h / 2, h - h / 2]
    hole.radius_inner = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    r = 0.075 * cm
    hole.radius_outer = [r] * hole.num_side
    hole.build_physical_volume = False
    hole.material = 'G4_AIR'

    """hole = sim.add_volume('Box', f'{name}_collimator_hole')
    hole.size = [0.075 * cm, 0.075 * cm, 3.5 * cm]
    hole.build_physical_volume = False
    hole.material = 'G4_AIR'"""

    holep = sim.add_volume('Parametrised', f'{name}_collimator_hole_param')
    # holep.material = 'G4_AIR'
    holep.mother = core.name
    holep.repeated_vol = hole.name
