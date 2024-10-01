import pathlib
from opengate.geometry.volumes import unite_volumes
from opengate.geometry.volumes import RepeatParametrisedVolume, BoxVolume
from opengate.actors.digitizers import *
from opengate.managers import Simulation
from opengate.utility import g4_units
from box import Box
from opengate.contrib.spect import ge_discovery_nm670 as discovery

# colors
red = [1, 0.7, 0.7, 0.8]
blue = [0.5, 0.5, 1, 0.8]
gray = [0.5, 0.5, 0.5, 1]
white = [1, 1, 1, 1]
yellow = [1, 1, 0, 1]
green = [0, 1, 0, 1]


def add_spect_head(sim, name="spect", collimator_type="lehr", debug=False):
    """
    Collimator:
    - False or "none" : no collimator
    - LEHR  : 1.11 mm holes
    - MELP  : 2.94 mm holes
    - HE    : 4 mm holes

    Collimator LEHR: Low Energy High Resolution    (for Tc99m)
    Collimator MELP: Medium Energy Low Penetration (for In111, Lu177)
    Collimator HE:   High Energy General Purpose   (for I131)

    """
    f = pathlib.Path(__file__).parent.resolve()
    fdb = f"{f}/spect_siemens_intevo_materials.db"
    if fdb not in sim.volume_manager.material_database.filenames:
        sim.volume_manager.add_material_database(fdb)

    # check overlap
    sim.check_volumes_overlap = debug

    # main box
    head = add_head_box(sim, name)

    # shielding (important)
    add_shielding(sim, head, collimator_type)

    # collimator
    colli = add_collimator(sim, head, collimator_type, debug)

    # crystal
    crystal = add_crystal(sim, head)

    # other elements
    back_comp = add_back_compartment(sim, head)
    light_guide = add_light_guide(sim, back_comp)
    # pmt = add_PMT_array(sim, head)
    # elec = add_electronics(sim, head)

    return head, colli, crystal


def add_head_box(sim, name):
    mm = g4_units.mm
    # bounding box
    head = sim.add_volume("Box", name)
    head.material = "G4_AIR"
    head.size = [260.0448 * mm, 685 * mm, 539 * mm]
    head.color = white
    return head


def add_shielding(sim, head, collimator_type):
    if collimator_type == "lehr" or collimator_type == "melp":
        return add_shielding_lehr_melp(sim, head)
    if collimator_type == "he":
        return add_shielding_he(sim, head)


def add_shielding_lehr_melp(sim, head):
    mm = g4_units.mm
    # shielding side thickness
    side_thickness = 12.7 * mm
    front_depth = 60 * mm
    side_depth = 215.0448 * mm - front_depth
    name = head.name

    # shielding
    back_shield = BoxVolume(name=f"{name}_back_shield")
    back_shield.size = [17.1 * mm, head.size[1], head.size[2]]

    # side shield Y pos
    side_shield_y_pos = BoxVolume(name=f"{name}_side_shield_y_pos")
    side_shield_y_pos.size = [side_depth, side_thickness, head.size[2]]

    # side shield Z pos
    side_shield_z_pos = BoxVolume(name=f"{name}_side_shield_z_pos")
    # gate.geometry.utility.copy_volume_user_info(side_shield_y_pos, side_shield_z_pos)
    side_shield_z_pos.size = [side_depth, head.size[1], side_thickness]

    # first volume from the 5 solids
    dx = -98.9724 * mm
    ddx = dx + front_depth / 2
    a = unite_volumes(back_shield, side_shield_y_pos, [ddx, 336.15 * mm, 0])
    a = unite_volumes(a, side_shield_y_pos, [ddx, -336.15 * mm, 0])
    a = unite_volumes(a, side_shield_z_pos, [ddx, 0, 263.15 * mm])
    shield = unite_volumes(
        a,
        side_shield_z_pos,
        [ddx, 0, -263.15 * mm],
        new_name=f"{name}_shielding_back_side",
    )
    sim.add_volume(shield)
    shield.mother = head.name
    shield.translation = [-dx, 0, 0]
    shield.color = gray
    shield.material = "Lead"

    # front shields
    front_shield_y_pos = BoxVolume(name=f"{name}_front_shield_y_pos")
    front_shield_y_pos.size = [front_depth, 76 * mm, 510.4 * mm]
    front_shield_z_pos = BoxVolume(name=f"{name}_front_shield_z_pos")
    front_shield_z_pos.size = [front_depth, 676.7 * mm, 76 * mm]

    # second volume from the 4 solids
    a = front_shield_y_pos
    t = 304.5 * mm
    a = unite_volumes(a, front_shield_y_pos, [0, -2 * t, 0])
    a = unite_volumes(a, front_shield_z_pos, [0, -t, 231.5 * mm])
    shield = unite_volumes(
        a, front_shield_z_pos, [0, -t, -231.5 * mm], new_name=f"{name}_shielding_front"
    )
    sim.add_volume(shield)
    shield.mother = head.name
    shield.translation = [-87.0776 * mm, t, 0]
    shield.color = gray
    shield.material = "Lead"

    return shield


def add_shielding_he(sim, head):
    mm = g4_units.mm
    # shielding side thickness
    side_thickness = 12.7 * mm
    front_depth = 60 * mm
    side_depth = 215.0448 * mm - front_depth
    name = head.name

    # shielding
    back_shield = BoxVolume(name=f"{name}_back_shield")
    back_shield.size = [17.1 * mm, head.size[1], head.size[2]]

    # side shield Y pos
    side_shield_y_pos = BoxVolume(name=f"{name}_side_shield_y_pos")
    side_shield_y_pos.size = [side_depth, side_thickness, head.size[2]]

    # side shield Z pos
    side_shield_z_pos = BoxVolume(name=f"{name}_side_shield_z_pos")
    # gate.geometry.utility.copy_volume_user_info(side_shield_y_pos, side_shield_z_pos)
    side_shield_z_pos.size = [side_depth, head.size[1], side_thickness]

    # first volume from the 5 solids
    dx = -98.9724 * mm
    ddx = dx + front_depth / 2
    a = unite_volumes(back_shield, side_shield_y_pos, [ddx, 336.15 * mm, 0])
    a = unite_volumes(a, side_shield_y_pos, [ddx, -336.15 * mm, 0])
    a = unite_volumes(a, side_shield_z_pos, [ddx, 0, 263.15 * mm])
    shield = unite_volumes(
        a,
        side_shield_z_pos,
        [ddx, 0, -263.15 * mm],
        new_name=f"{name}_shielding_back_side",
    )
    sim.add_volume(shield)
    shield.mother = head.name
    shield.translation = [-dx, 0, 0]
    shield.color = gray
    shield.material = "Lead"

    # front shields
    ofy = 35 * mm
    ofz = 30 * mm
    front_shield_y_pos = BoxVolume(name=f"{name}_front_shield_y_pos")
    front_shield_y_pos.size = [front_depth, 76 * mm - ofy, 510.4 * mm]
    front_shield_z_pos = BoxVolume(name=f"{name}_front_shield_z_pos")
    front_shield_z_pos.size = [front_depth, 676.7 * mm, 76 * mm - ofz]

    # second volume from the 4 solids
    a = front_shield_y_pos
    ty = 304.5 * mm + ofy / 2
    tz = 231.5 * mm + ofz / 2
    a = unite_volumes(a, front_shield_y_pos, [0, -2 * ty, 0])
    a = unite_volumes(a, front_shield_z_pos, [0, -ty, tz])
    shield = unite_volumes(
        a, front_shield_z_pos, [0, -ty, -tz], new_name=f"{name}_shielding_front"
    )
    sim.add_volume(shield)
    shield.mother = head.name
    shield.translation = [-87.0776 * mm, ty, 0]
    shield.color = blue
    shield.material = "Lead"

    return shield


def add_collimator(sim, head, collimator_type, debug):
    if (
        collimator_type is False
        or collimator_type is None
        or collimator_type == ""
        or collimator_type == "none"
    ):
        return add_collimator_empty(sim, head)
    collimator_type = collimator_type.lower()
    if collimator_type == "lehr":
        return add_collimator_lehr(sim, head, debug)
    if collimator_type == "melp":
        return add_collimator_melp(sim, head, debug)
    if collimator_type == "he":
        return add_collimator_he(sim, head, debug)
    col = ["None", "lehr", "melp", "he"]
    fatal(
        f'Cannot build the collimator "{collimator_type}". '
        f"Available collimator types are: {col}"
    )


def add_collimator_empty(sim, head):
    mm = g4_units.mm
    colli = sim.add_volume("Box", f"{head.name}_no_collimator")
    colli.mother = head.name
    colli.size = [59.7 * mm, 533 * mm, 387 * mm]
    colli.translation = [-96.7324 * mm, 0, 0]
    colli.color = blue
    colli.material = head.material
    return colli


def add_collimator_lehr(sim, head, debug):
    mm = g4_units.mm
    name = head.name
    colli = sim.add_volume("Box", f"{name}_lehr_collimator")
    colli.mother = name
    colli.size = [24.05 * mm, 533 * mm, 387 * mm]
    colli.translation = [-78.9074 * mm, 0, 0]
    colli.color = blue
    colli.material = "Lead"

    """
    #########################################################################
    #
    # 	Type	|	Diameter	|	Septial thickness	|	No. of holes
    # -----------------------------------------------------------------------
    # 	hex		|	1.11 mm		|	0.16 mm 			|	148000
    #
    #	y spacing	= diameter + septial = 1.27 mm
    #	z spacing	= 2 * (diameter + septial) * sin(60) = 2.19970453 mm
    #
    #	y translation	= y spacing / 2 = 0.635 mm
    #	z translation	= z spacing / 2 = 1.09985 mm
    #
    # 	(this translation from 0,0 is split between hole1 and hole2)
    #
    #	Nholes y	= (No. of holes / sin(60))^0.5 = 413.4
    #	Nholes z	= (No. of holes * sin(60))^0.5 = 358
    #
    #########################################################################
    """

    # hexagon
    hole = sim.add_volume("Hexagon", f"{name}_collimator_hole1")
    hole.height = 24.05 * mm
    hole.radius = 0.555 * mm
    hole.material = "G4_AIR"
    hole.mother = colli.name

    # parameterised holes
    size = [1, 414, 175]
    if debug:
        size = [1, 30, 20]
    tr = [0, 1.27 * mm, 2.1997 * mm, 0]
    rot = Rotation.from_euler("y", 90, degrees=True).as_matrix()
    offset = [0, 0.3175 * mm * 2, 0.549925 * mm * 2, 0]
    repeat_colli_hole(sim, hole, size, tr, rot, offset)

    return colli


def add_collimator_melp(sim, head, debug):
    name = head.name
    mm = g4_units.mm

    colli = sim.add_volume("Box", f"{name}_melp_collimator")
    colli.mother = name
    colli.size = [40.64 * mm, 533 * mm, 387 * mm]
    colli.translation = [-87.2024 * mm, 0, 0]
    colli.color = blue
    colli.material = "Lead"

    """
    #########################################################################
    #
    # 	Type	|	Diameter	|	Septial thickness	|	No. of holes
    # -----------------------------------------------------------------------
    # 	hex		|	2.94 mm		|	1.14 mm 			|	14000
    #
    #	y spacing	= diameter + septal = 4.08 mm
    #	z spacing	= 2 * (diameter + septal) * sin(60) = 7.06676729 mm
    #
    #	y translation	= y spacing / 2 = 2.04 mm
    #	z translation	= z spacing / 2 = 3.53338 mm
    #
    # 	(this translation from 0,0 is split between hole1 and hole2)
    #
    #	Nholes y	= (No. of holes / sin(60))^0.5 = 127.1448
    #	Nholes z	= (No. of holes * sin(60))^0.5 = 110.111
    #
    #########################################################################
    """

    # hexagon
    hole = sim.add_volume("Hexagon", f"{name}_collimator_hole1")
    hole.height = 40.64 * mm
    hole.radius = 1.47 * mm
    hole.material = "G4_AIR"
    hole.mother = colli.name
    hole.build_physical_volume = False  # FIXME remove
    hole.color = [1, 0, 0, 1]

    # parameterised holes
    size = [1, 128, 55]
    if debug:
        size = [1, 30, 20]
    tr = [0, 4.08 * mm, 7.066767 * mm, 0]
    rot = Rotation.from_euler("y", 90, degrees=True).as_matrix()
    offset = [0, 1.02 * mm * 2, 1.76669 * mm * 2, 0]
    repeat_colli_hole(sim, hole, size, tr, rot, offset)

    return colli


def repeat_colli_hole(sim, hole, size, tr, rot, offset):
    holep = RepeatParametrisedVolume(repeated_volume=hole)
    holep.linear_repeat = size
    holep.translation = tr[0:3]
    holep.rotation = rot
    holep.start = [-(x - 1) * y / 2.0 for x, y in zip(size, tr)]
    # do it twice, with the following offset
    holep.offset_nb = 2
    holep.offset = offset
    sim.volume_manager.add_volume(holep)
    return holep


def add_collimator_he(sim, head, debug):
    name = head.name
    mm = g4_units.mm

    """gate.fatal(
        f"the Intevo HE collimator is not implemented yet. Need to move the shielding ..."
    )"""

    colli = sim.add_volume("Box", f"{name}_he_collimator")
    colli.mother = name
    colli.size = [59.7 * mm, 583 * mm, 440 * mm]
    colli.translation = [-96.7324 * mm, 0, 0]
    colli.color = blue
    colli.material = "Lead"

    """
    #########################################################################
    #
    # 	Type	|	Diameter	|	Septial thickness	|	No. of holes
    # -----------------------------------------------------------------------
    # 	hex		|	4.0 mm		|	2.0 mm 				|	8000
    #
    #	y spacing	= diameter + septial = 6.0 mm
    #	z spacing	= 2 * (diameter + septial) * sin(60) = 10.39230485 mm
    #
    #	y translation	= y spacing / 2 = 3.0 mm
    #	z translation	= z spacing / 2 = 5.196152423 mm
    #
    # 	(this translation from 0,0 is split between hole1 and hole2)
    #
    #	Nholes y	= (No. of holes / sin(60))^0.5 = 96.11245657
    #	Nholes z	= (No. of holes * sin(60))^0.5 = 83.23582901
    #
    #########################################################################
    """

    # hexagon
    hole = sim.add_volume("Hexagon", f"{name}_collimator_hole1")
    hole.height = 59.7 * mm
    hole.radius = 2.0 * mm
    hole.material = "G4_AIR"
    hole.mother = colli.name

    # parameterised holes
    size = [1, 96, 42]
    if debug:
        size = [1, 30, 20]
    tr = [0, 6 * mm, 10.39230485 * mm, 0]
    rot = Rotation.from_euler("y", 90, degrees=True).as_matrix()
    offset = [0, -1.5 * mm * 2, -2.598076212 * mm * 2, 0]
    repeat_colli_hole(sim, hole, size, tr, rot, offset)

    return colli


def add_crystal(sim, head):
    mm = g4_units.mm
    front_shield_size = 76 * mm * 2

    name = head.name
    crystal_sheath = sim.add_volume("Box", f"{name}_crystal_sheath")
    crystal_sheath.mother = name
    crystal_sheath.size = [
        0.3048 * mm,  # , 591 * mm, 445 * mm
        head.size[1] - front_shield_size,
        head.size[2] - front_shield_size,
    ]
    crystal_sheath.translation = [-66.73 * mm, 0, 0]
    crystal_sheath.material = "Aluminium"
    crystal_sheath.color = red

    crystal = sim.add_volume("Box", f"{name}_crystal")
    crystal.mother = name
    crystal.size = [
        9.5 * mm,  # , 591 * mm, 445 * mm
        head.size[1] - front_shield_size,
        head.size[2] - front_shield_size,
    ]

    crystal.translation = [-61.8276 * mm, 0, 0]
    crystal.material = "NaI"
    crystal.color = yellow

    return crystal


def add_back_compartment(sim, head):
    mm = g4_units.mm
    name = head.name
    back_compartment = sim.add_volume("Box", f"{name}_back_compartment")
    back_compartment.mother = name
    back_compartment.size = [147.5 * mm, 651.0 * mm, 485.0 * mm]
    back_compartment.translation = [16.6724 * mm, 0, 0]
    back_compartment.material = "G4_AIR"  # FIXME strange ?
    back_compartment.color = green

    return back_compartment


def add_light_guide(sim, back_compartment):
    mm = g4_units.mm
    name = back_compartment.name
    light_guide = sim.add_volume("Box", f"{name}_light_guide")
    light_guide.mother = name
    light_guide.size = [9.5 * mm, 643.0 * mm, 477.1037366 * mm]
    light_guide.translation = [-69.0 * mm, 0, 0]
    light_guide.material = "Glass"
    light_guide.color = green

    return light_guide


def add_digitizer(sim, head, crystal):
    digit_chain = {}

    # hits
    hc = add_digitizer_hits(sim, head, crystal)
    digit_chain[hc.name] = hc

    # singles
    sc = add_digitizer_adder(sim, head, crystal, hc)
    digit_chain[sc.name] = sc

    # blurring
    eb, sb = add_digitizer_blur(sim, head, crystal, sc)
    digit_chain[eb.name] = eb
    digit_chain[sb.name] = sb

    # energy windows
    cc = add_digitizer_ene_win(sim, head, crystal, sb)
    digit_chain[cc.name] = cc

    # projection
    proj = add_digitizer_proj(sim, crystal, cc)
    digit_chain[proj.name] = proj

    return digit_chain


def add_digitizer_test1(sim, head, crystal):
    digit_chain = {}

    # hits
    hc = add_digitizer_hits(sim, head, crystal)
    digit_chain[hc.name] = hc

    # singles
    sc = add_digitizer_adder(sim, head, crystal, hc)
    digit_chain[sc.name] = sc

    # energy windows
    cc = add_digitizer_ene_win(sim, head, crystal, sc)
    digit_chain[cc.name] = cc

    # projection
    proj = add_digitizer_proj(sim, crystal, cc)
    digit_chain[proj.name] = proj

    return digit_chain


def add_digitizer_test2(sim, head, crystal):
    digit_chain = {}

    # hits
    hc = add_digitizer_hits(sim, head, crystal)
    digit_chain[hc.name] = hc

    # singles
    sc = add_digitizer_adder(sim, head, crystal, hc)
    digit_chain[sc.name] = sc

    # blurring
    eb, sb = add_digitizer_blur_test2(sim, head, crystal, sc)
    digit_chain[eb.name] = eb
    digit_chain[sb.name] = sb

    # energy windows
    cc = add_digitizer_ene_win(sim, head, crystal, sb)
    digit_chain[cc.name] = cc

    # projection
    proj = add_digitizer_proj(sim, crystal, cc)
    digit_chain[proj.name] = proj

    return digit_chain


def add_digitizer_hits(sim, head, crystal):
    # hits
    hc = sim.add_actor("DigitizerHitsCollectionActor", f"Hits_{crystal.name}")
    hc.attached_to = crystal.name
    hc.output_filename = ""  # No output
    hc.attributes = [
        "PostPosition",
        "TotalEnergyDeposit",
        "PreStepUniqueVolumeID",
        "PostStepUniqueVolumeID",
        "GlobalTime",
    ]
    return hc


def add_digitizer_adder(sim, head, crystal, hc):
    # singles
    sc = sim.add_actor("DigitizerAdderActor", f"Singles_{crystal.name}")
    sc.attached_to = hc.attached_to
    sc.input_digi_collection = hc.name
    # sc.policy = "EnergyWeightedCentroidPosition"
    sc.policy = "EnergyWinnerPosition"
    sc.output_filename = ""
    sc.group_volume = None
    return sc


def add_digitizer_blur_test2(sim, head, crystal, sc):
    mm = g4_units.mm
    keV = g4_units.keV
    MeV = g4_units.MeV
    eb = sim.add_actor("DigitizerBlurringActor", f"Singles_{crystal.name}_eblur")
    eb.output_filename = sc.output_filename
    eb.attached_to = crystal.name
    eb.input_digi_collection = sc.name
    eb.blur_attribute = "TotalEnergyDeposit"
    eb.blur_method = "Linear"
    eb.blur_resolution = 0.13
    eb.blur_reference_value = 80 * keV
    eb.blur_slope = -0.09 * 1 / MeV

    # spatial blurring
    sb = sim.add_actor("DigitizerSpatialBlurringActor", f"Singles_{crystal.name}_sblur")
    sb.output_filename = f"output/{head.name}_singles.root"
    sb.attached_to = crystal.name
    sb.input_digi_collection = eb.name
    sb.blur_attribute = "PostPosition"
    sb.blur_fwhm = 10 * mm
    sb.keep_in_solid_limits = True

    return eb, sb


def add_digitizer_blur(sim, head, crystal, sc):
    mm = g4_units.mm
    keV = g4_units.keV
    MeV = g4_units.MeV
    eb = sim.add_actor("DigitizerBlurringActor", f"Singles_{crystal.name}_eblur")
    eb.output_filename = sc.output_filename
    eb.attached_to = crystal.name
    eb.input_digi_collection = sc.name
    eb.blur_attribute = "TotalEnergyDeposit"
    eb.blur_method = "Linear"
    eb.blur_resolution = 0.13
    eb.blur_reference_value = 80 * keV
    eb.blur_slope = -0.09 * 1 / MeV

    # spatial blurring
    sb = sim.add_actor("DigitizerSpatialBlurringActor", f"Singles_{crystal.name}_sblur")
    sb.output_filename = f"output/{head.name}_singles.root"
    sb.attached_to = crystal.name
    sb.input_digi_collection = eb.name
    sb.blur_attribute = "PostPosition"
    sb.blur_fwhm = 3.9 * mm
    sb.keep_in_solid_limits = True

    return eb, sb


def add_digitizer_ene_win(sim, head, crystal, sc):
    # energy windows
    cc = sim.add_actor("DigitizerEnergyWindowsActor", f"EnergyWindows_{crystal.name}")
    keV = g4_units.keV
    channels = [
        {"name": f"spectrum_{head.name}", "min": 3 * keV, "max": 515 * keV},
        {"name": f"scatter1_{head.name}", "min": 96 * keV, "max": 104 * keV},
        {"name": f"peak113_{head.name}", "min": 104.52 * keV, "max": 121.48 * keV},
        {"name": f"scatter2_{head.name}", "min": 122.48 * keV, "max": 133.12 * keV},
        {"name": f"scatter3_{head.name}", "min": 176.46 * keV, "max": 191.36 * keV},
        {"name": f"peak208_{head.name}", "min": 192.4 * keV, "max": 223.6 * keV},
        {"name": f"scatter4_{head.name}", "min": 224.64 * keV, "max": 243.3 * keV},
    ]
    cc.attached_to = sc.attached_to
    cc.input_digi_collection = sc.name
    cc.channels = channels
    cc.output_filename = ""  # No output
    return cc


def add_digitizer_proj(sim, crystal, cc):
    mm = g4_units.mm
    deg = g4_units.deg
    # projection
    proj = sim.add_actor("DigitizerProjectionActor", f"Projection_{crystal.name}")
    proj.attached_to = cc.attached_to
    proj.input_digi_collections = [x["name"] for x in cc.channels]
    proj.spacing = [4.7951998710632 * mm, 4.7951998710632 * mm]
    proj.size = [128, 128]
    proj.output_filename = "proj.mhd"
    proj.origin_as_image_center = False
    r1 = Rotation.from_euler("y", 90 * deg)
    r2 = Rotation.from_euler("x", 90 * deg)
    proj.detector_orientation_matrix = (r2 * r1).as_matrix()
    return proj


def add_digitizer_v2_old(sim, crystal_name, name):
    # create main chain
    mm = g4_units.mm
    digitizer = Digitizer(sim, crystal_name, name)

    # Singles
    sc = digitizer.add_module("DigitizerAdderActor", f"{name}_singles")
    sc.group_volume = None
    sc.policy = "EnergyWinnerPosition"

    # detection efficiency
    ea = digitizer.add_module("DigitizerEfficiencyActor")
    ea.efficiency = 0.86481

    # energy blurring
    keV = g4_units.keV
    MeV = g4_units.MeV
    eb = digitizer.add_module("DigitizerBlurringActor")
    eb.blur_attribute = "TotalEnergyDeposit"
    eb.blur_method = "InverseSquare"
    eb.blur_resolution = 0.13
    eb.blur_reference_value = 80 * keV
    eb.blur_slope = -0.09 * 1 / MeV  # fixme unsure about unit

    # spatial blurring
    # Source: HE4SPECS - FWHM = 3.9 mm
    # FWHM = 2.sigma.sqrt(2ln2) -> sigma = 1.656 mm
    sb = digitizer.add_module("DigitizerSpatialBlurringActor")
    sb.blur_attribute = "PostPosition"
    sb.blur_fwhm = 3.9 * mm
    sb.keep_in_solid_limits = True

    # energy windows (Energy range. 35-588 keV)
    cc = digitizer.add_module("DigitizerEnergyWindowsActor", f"{name}_energy_window")
    keV = g4_units.keV
    # 112.9498 keV  = 6.20 %
    # 208.3662 keV  = 10.38 %
    p1 = 112.9498 * keV
    p2 = 208.3662 * keV
    channels = [
        {"name": "spectrum", "min": 35 * keV, "max": 588 * keV},
        *energy_windows_peak_scatter("peak113", "scatter1", "scatter2", p1, 0.2, 0.1),
        *energy_windows_peak_scatter("peak208", "scatter3", "scatter4", p2, 0.2, 0.1),
    ]
    cc.channels = channels

    # projection
    proj = digitizer.add_module("DigitizerProjectionActor", f"{name}_projection")
    channel_names = [c["name"] for c in channels]
    proj.input_digi_collections = channel_names
    proj.spacing = [4.7951998710632 * mm / 2, 4.7951998710632 * mm / 2]
    proj.size = [256, 256]
    # by default, the origin of the images are centered
    # set to False here to keep compatible with previous version
    # proj.origin_as_image_center = False
    # projection plane: it depends on how the spect device is described
    # here, we need this rotation
    proj.detector_orientation_matrix = Rotation.from_euler(
        "yx", (90, 90), degrees=True
    ).as_matrix()

    # end
    return digitizer


def add_digitizer_lu177(sim, crystal_name, name):
    # create main chain
    mm = g4_units.mm
    digitizer = Digitizer(sim, crystal_name, name)

    # Singles
    sc = digitizer.add_module("DigitizerAdderActor", f"{name}_singles")
    sc.group_volume = None
    sc.policy = "EnergyWinnerPosition"

    # detection efficiency
    ea = digitizer.add_module("DigitizerEfficiencyActor")
    ea.efficiency = 0.86481

    # energy blurring
    keV = g4_units.keV
    eb = digitizer.add_module("DigitizerBlurringActor")
    eb.blur_attribute = "TotalEnergyDeposit"
    eb.blur_method = "InverseSquare"
    eb.blur_resolution = 0.0945
    eb.blur_reference_value = 140.57 * keV
    # eb.blur_resolution = 0.13
    # eb.blur_reference_value = 80 * keV
    # eb.blur_slope = -0.09 * 1 / MeV  # fixme unsure about unit

    # spatial blurring
    # Source: HE4SPECS - FWHM = 3.9 mm
    # FWHM = 2.sigma.sqrt(2ln2) -> sigma = 1.656 mm
    sb = digitizer.add_module("DigitizerSpatialBlurringActor")
    sb.blur_attribute = "PostPosition"
    sb.blur_fwhm = 3.9 * mm
    sb.keep_in_solid_limits = True

    # energy windows (Energy range. 35-588 keV)
    cc = digitizer.add_module("DigitizerEnergyWindowsActor", f"{name}_energy_window")
    keV = g4_units.keV
    # 112.9498 keV  = 6.20 %
    # 208.3662 keV  = 10.38 %
    p1 = 112.9498 * keV
    p2 = 208.3662 * keV
    channels = [
        *energy_windows_peak_scatter("peak113", "scatter1", "scatter2", p1, 0.2, 0.1),
        *energy_windows_peak_scatter("peak208", "scatter3", "scatter4", p2, 0.2, 0.1),
    ]
    cc.channels = channels

    # projection
    proj = digitizer.add_module("DigitizerProjectionActor", f"{name}_projection")
    channel_names = [c["name"] for c in channels]
    proj.input_digi_collections = channel_names
    proj.spacing = [4.7951998710632 * mm / 2, 4.7951998710632 * mm / 2]
    proj.size = [256, 256]
    # by default, the origin of the images are centered
    # set to False here to keep compatible with previous version
    # proj.origin_as_image_center = False
    # projection plane: it depends on how the spect device is described
    # here, we need this rotation
    proj.detector_orientation_matrix = Rotation.from_euler(
        "yx", (90, 90), degrees=True
    ).as_matrix()

    # end
    return digitizer


def add_digitizer_tc99m(sim, crystal_name, name):
    # create main chain
    mm = g4_units.mm
    digitizer = Digitizer(sim, crystal_name, name)

    # Singles
    sc = digitizer.add_module("DigitizerAdderActor", f"{name}_singles")
    sc.group_volume = None
    sc.policy = "EnergyWinnerPosition"

    # detection efficiency
    ea = digitizer.add_module("DigitizerEfficiencyActor")
    ea.efficiency = 0.86481  # FAKE

    # energy blurring
    keV = g4_units.keV
    eb = digitizer.add_module("DigitizerBlurringActor")
    eb.blur_attribute = "TotalEnergyDeposit"
    eb.blur_method = "InverseSquare"
    eb.blur_resolution = 0.0945
    eb.blur_reference_value = 140.57 * keV

    # spatial blurring
    # Source: HE4SPECS - FWHM = 3.9 mm
    # FWHM = 2.sigma.sqrt(2ln2) -> sigma = 1.656 mm
    sb = digitizer.add_module("DigitizerSpatialBlurringActor")
    sb.blur_attribute = "PostPosition"
    # intrinsic spatial resolution at 140 keV for 9.5 mm thick NaI
    sb.blur_fwhm = 3.9 * mm
    sb.keep_in_solid_limits = True

    # energy windows (Energy range. 35-588 keV)
    cc = digitizer.add_module("DigitizerEnergyWindowsActor", f"{name}_energy_window")
    channels = [
        {"name": f"scatter", "min": 108.57749938965 * keV, "max": 129.5924987793 * keV},
        {"name": f"peak140", "min": 129.5924987793 * keV, "max": 150.60751342773 * keV},
    ]
    cc.channels = channels

    # projection
    proj = digitizer.add_module("DigitizerProjectionActor", f"{name}_projection")
    channel_names = [c["name"] for c in channels]
    proj.input_digi_collections = channel_names
    proj.spacing = [4.7951998710632 * mm / 2, 4.7951998710632 * mm / 2]
    proj.size = [256, 256]
    # by default, the origin of the images are centered
    # set to False here to keep compatible with previous version
    # proj.origin_as_image_center = False
    # projection plane: it depends on how the spect device is described
    # here, we need this rotation
    proj.detector_orientation_matrix = Rotation.from_euler(
        "yx", (90, 90), degrees=True
    ).as_matrix()
    # proj.output_filename = "proj.mhd"

    # end
    return digitizer


def get_plane_position_and_distance_to_crystal(collimator_type):
    """
    This has been computed with t043_distances
    - first : distance from head center to the PSD (translation for the plane)
    - second: distance from PSD to center of the crystal
    - third : distance from the head boundary to the PSD (for spect_radius info)
    """
    if collimator_type == "lehr":
        return 61.1, 47.875, 33.9

    if collimator_type == "melp":
        return 84.1, 70.875, 10.9

    if collimator_type == "he":
        return 92.1, 78.875, 2.9

    fatal(
        f'Unknown collimator type "{collimator_type}", please use lehr or megp or hegp'
    )


def compute_plane_position_and_distance_to_crystal(collimator_type):
    sim = Simulation()
    spect, colli, crystal = add_spect_head(sim, "spect", collimator_type, debug=True)
    pos = discovery.get_volume_position_in_head(
        sim, "spect", f"{collimator_type}_collimator", "min", axis=0
    )
    y = discovery.get_volume_position_in_head(sim, "spect", "crystal", "center", axis=0)
    crystal_distance = y - pos
    psd = spect.size[2] / 2.0 - pos
    return pos, crystal_distance, psd


def add_detection_plane_for_arf(
    sim, plane_size, colli_type, radius, gantry_angle_deg=0, det_name=None
):
    if det_name is None:
        det_name = "arf_plane"

    # rotation like the detector (needed), see in digitizer ProjectionActor
    r = Rotation.from_euler("yx", (90, 90), degrees=True)

    # FIXME
    mm = g4_units.mm
    plane_size = [533 * mm, 387 * mm]

    # plane
    nm = g4_units.nm
    detector_plane = sim.add_volume("Box", det_name)
    detector_plane.material = "G4_Galactic"
    detector_plane.color = [1, 0, 0, 1]
    detector_plane.size = [plane_size[0], plane_size[1], 1 * nm]

    # (fake) initial head rotation
    head = Box()
    head.translation = None
    head.rotation = None
    ri = set_head_orientation(head, colli_type, radius, gantry_angle_deg)

    # orientation
    detector_plane.rotation = (ri * r).as_matrix()
    detector_plane.translation = ri.apply([radius, 0, 0])

    return detector_plane


def set_head_orientation(head, collimator_type, radius, gantry_angle_deg=0):
    # pos is the distance from entrance detection plane and head boundary
    pos, _, _ = compute_plane_position_and_distance_to_crystal(collimator_type)
    distance = radius - pos
    # rotation X180 is to set the detector head-foot
    # rotation Z90 is the gantry angle
    r = Rotation.from_euler("xz", (180, 90 + gantry_angle_deg), degrees=True)
    head.translation = r.apply([distance, 0, 0])
    head.rotation = r.as_matrix()
    return r


def create_simu_for_arf_training_dataset(
    sim, colli_type, max_E, activity, rr, radius=None
):
    ui = sim.user_info
    mm = g4_units.mm
    cm = g4_units.cm
    Bq = g4_units.Bq
    keV = g4_units.keV
    if radius is None:
        radius = 500 * mm

    # world
    sim.world.material = "G4_Galactic"

    # spect
    head, _, crystal = add_spect_head(sim, "spect", colli_type, debug=ui.visu)

    # rotation like default
    set_head_orientation(head, colli_type, radius)

    # detector input plane position: 1 nm width, 1 nm before the collimator
    sim.add_parallel_world("arf_world")
    plane_size = [533 * mm, 387 * mm]
    arf_plane = add_detection_plane_for_arf(sim, plane_size, colli_type, radius)
    arf_plane.mother = "arf_world"

    # sources
    s1 = sim.add_source("GenericSource", "source")
    s1.particle = "gamma"
    s1.activity = activity / ui.number_of_threads
    if ui.visu:
        s1.activity = 5000 * Bq
    s1.position.type = "sphere"
    s1.position.radius = 57.6 * cm / 2
    s1.position.translation = [0, 0, 0]
    s1.direction.type = "iso"
    s1.energy.type = "range"
    s1.energy.min_energy = 3 * keV
    s1.energy.max_energy = max_E
    s1.direction.acceptance_angle.volumes = [arf_plane.name]
    s1.direction.acceptance_angle.intersection_flag = True

    # arf actor for building the training dataset
    arf = sim.add_actor("ARFTrainingDatasetActor", "ARF (training)")
    arf.attached_to = arf_plane.name
    arf.output_filename = f"arf.root"
    arf.russian_roulette = rr

    # stats
    sim.add_actor("SimulationStatisticsActor", "stats")

    return arf
