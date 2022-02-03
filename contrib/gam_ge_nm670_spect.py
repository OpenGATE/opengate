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


def add_spect(sim, name='spect', collimator=True, debug=False):
    f = pathlib.Path(__file__).parent.resolve()
    sim.add_material_database(f'{f}/ge_nm670_spect_materials.db')

    # check overlap
    sim.g4_check_overlap_flag = False  # set to True for debug

    # spect head
    head, lead_cover = add_spect_head(sim, name)

    # spect head
    crystal = add_spect_crystal(sim, name, lead_cover)

    # spect collimator
    if collimator:
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

    return colli_trd


def colli_with_param(sim, name, core, debug):
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
    hole.material = 'G4_AIR'
    hole.mother = core.name

    # because this volume will be parameterised, we need to prevent
    # the creation of the physical volume
    hole.build_physical_volume = False

    # parameterised holes
    holep = sim.add_volume('RepeatParametrised', f'{name}_collimator_hole_param')
    holep.mother = core.name
    holep.translation = None
    holep.rotation = None
    holep.repeated_volume_name = hole.name
    # number of repetition
    holep.linear_repeat = [183, 235, 1]
    if debug:
        holep.linear_repeat = [10, 10, 1]
    # translation for each repetition
    holep.translation = [2.94449 * mm, 1.7 * mm, 0]
    # starting position
    holep.start = [-(holep.linear_repeat[0] * holep.translation[0]) / 2.0,
                   -(holep.linear_repeat[1] * holep.translation[1]) / 2.0, 0]

    # dot it twice, with the following offset
    holep.offset_nb = 2
    holep.offset = [1.47224 * mm, 0.85 * mm, 0]
