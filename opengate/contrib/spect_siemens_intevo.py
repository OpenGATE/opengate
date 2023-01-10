import opengate as gate
import pathlib
from scipy.spatial.transform import Rotation

# unit
cm = gate.g4_units("cm")
mm = gate.g4_units("mm")
deg = gate.g4_units("deg")

# colors
red = [1, 0.7, 0.7, 0.8]
blue = [0.5, 0.5, 1, 0.8]
gray = [0.5, 0.5, 0.5, 1]
white = [1, 1, 1, 1]
yellow = [1, 1, 0, 1]
green = [0, 1, 0, 1]


def add_intevo_spect_head(sim, name="spect", collimator_type="lehr", debug=False):
    """
    Collimators:
    - False : no collimator
    - LEHR  : 1.11 mm holes
    - MELP  : 3.94 mm holes
    - HE    : 4 mm holes

    Collimator LEHR: Low Energy High Resolution    (for Tc99m)
    Collimator MEGP: Medium Energy Low Penetration (for In111, Lu177)
    Collimator HE:   High Energy General Purpose   (for I131)

    """
    f = pathlib.Path(__file__).parent.resolve()
    fdb = f"{f}/spect_siemens_intevo_materials.db"
    if fdb not in sim.volume_manager.material_database.filenames:
        sim.add_material_database(fdb)

    # check overlap
    sim.g4_check_overlap_flag = True  # set to True for debug # FIXME

    # main box
    head = add_head_box(sim, name)
    add_shielding(sim, head)

    # collimator
    colli = add_collimator(sim, head, collimator_type, debug)

    # crystal
    # crystal = add_crystal(sim, head)

    # other elements
    # back_comp = add_back_compartment(sim, head)
    # light_guide = add_light_guide(sim, head)
    # pmt = add_PMT_array(sim, head)
    # elec = add_electronics(sim, head)

    return head, colli


def add_head_box(sim, name):
    # bounding box
    head = sim.add_volume("Box", name)
    head.material = "G4_AIR"  # FIXME or Vacuum ?
    head.size = [260.0448 * mm, 685 * mm, 539 * mm]
    head.color = white
    return head


def add_shielding(sim, head):
    # shielding side thickness
    side_thickness = 12.7 * mm
    front_depth = 60 * mm
    side_depth = 215.0448 * mm - front_depth
    name = head.name

    # shielding
    back_shield = sim.new_solid("Box", f"{name}_back_shield")
    back_shield.size = [17.1 * mm, head.size[1], head.size[2]]

    # side shield Y pos
    side_shield_y_pos = sim.new_solid("Box", f"{name}_side_shield_y_pos")
    side_shield_y_pos.size = [side_depth, side_thickness, head.size[2]]

    # side shield Z pos
    side_shield_z_pos = sim.new_solid("Box", f"{name}_side_shield_z_pos")
    gate.copy_volume_user_info(side_shield_y_pos, side_shield_z_pos)
    side_shield_z_pos.size = [side_depth, head.size[1], side_thickness]

    # first volume from the 5 solids
    dx = -98.9724 * mm
    ddx = dx + front_depth / 2
    a = gate.solid_union(back_shield, side_shield_y_pos, [ddx, 336.15 * mm, 0])
    a = gate.solid_union(a, side_shield_y_pos, [ddx, -336.15 * mm, 0])
    a = gate.solid_union(a, side_shield_z_pos, [ddx, 0, 263.15 * mm])
    a = gate.solid_union(a, side_shield_z_pos, [ddx, 0, -263.15 * mm])
    shield = sim.add_volume_from_solid(a, f"{name}_shielding_back_side")
    shield.mother = head.name
    shield.translation = [-dx, 0, 0]
    shield.color = gray

    # front shields
    front_shield_y_pos = sim.new_solid("Box", f"{name}_front_shield_y_pos")
    front_shield_y_pos.size = [front_depth, 76 * mm, 510.4 * mm]
    front_shield_z_pos = sim.new_solid("Box", f"{name}_front_shield_z_pos")
    front_shield_z_pos.size = [front_depth, 676.7 * mm, 76 * mm]

    # second volume from the 4 solids
    a = front_shield_y_pos
    t = 304.5 * mm
    a = gate.solid_union(a, front_shield_y_pos, [0, -2 * t, 0])
    a = gate.solid_union(a, front_shield_z_pos, [0, -t, 231.5 * mm])
    a = gate.solid_union(a, front_shield_z_pos, [0, -t, -231.5 * mm])
    shield = sim.add_volume_from_solid(a, f"{name}_shielding_front")
    shield.mother = head.name
    shield.translation = [-87.0776 * mm, t, 0]
    shield.color = gray

    return shield


def add_shielding_old(sim, head):
    """
    Warning, it works but make visualisation is very slow (unsure why)
    """

    # shielding side thickness
    side_thickness = 12.7 * mm

    # shielding
    name = head.name
    back_shield = sim.new_solid("Box", f"{name}_back_shield")
    back_shield.size = [17.1 * mm, head.size[1], head.size[2]]

    # side shield Y pos
    side_shield_y_pos = sim.new_solid("Box", f"{name}_side_shield_y_pos")
    side_shield_y_pos.size = [215.0448 * mm, side_thickness, head.size[2]]

    # side shield Z pos
    side_shield_z_pos = sim.new_solid("Box", f"{name}_side_shield_z_pos")
    gate.copy_volume_user_info(side_shield_y_pos, side_shield_z_pos)
    side_shield_z_pos.size = [215.0448 * mm, head.size[1], side_thickness]

    # front shields
    front_shield_y_pos = sim.new_solid("Box", f"{name}_front_shield_y_pos")
    front_shield_y_pos.size = [60 * mm, 76 * mm, 510.4 * mm]
    front_shield_z_pos = sim.new_solid("Box", f"{name}_front_shield_z_pos")
    front_shield_z_pos.size = [60 * mm, 676.7 * mm, 76 * mm]

    dx = -98.9724 * mm
    a = gate.solid_union(back_shield, side_shield_y_pos, [dx, 336.15 * mm, 0])
    a = gate.solid_union(a, front_shield_z_pos, [-87.0776 * mm + dx, 0, 231.5 * mm])
    a = gate.solid_union(a, front_shield_z_pos, [-87.0776 * mm + dx, 0, -231.5 * mm])
    a = gate.solid_union(a, side_shield_y_pos, [dx, -336.15 * mm, 0])
    a = gate.solid_union(a, side_shield_z_pos, [dx, 0, 263.15 * mm])
    a = gate.solid_union(a, side_shield_z_pos, [dx, 0, -263.15 * mm])
    a = gate.solid_union(a, front_shield_y_pos, [-87.0776 * mm + dx, 304.5 * mm, 0])
    a = gate.solid_union(a, front_shield_y_pos, [-87.0776 * mm + dx, -304.5 * mm, 0])

    shield = sim.add_volume_from_solid(a, f"{name}_shielding")
    shield.mother = head.name
    shield.translation = [98.9724 * mm, 0, 0]
    shield.color = gray

    return shield


def add_collimator(sim, head, collimator_type, debug):
    if collimator_type is False or collimator_type is None or collimator_type == "":
        return add_collimator_empty(sim, head)
    collimator_type = collimator_type.lower()
    if collimator_type == "lehr":
        return add_collimator_lehr(sim, head, debug)
    if collimator_type == "melp":
        return add_collimator_melp(sim, head, debug)
    if collimator_type == "he":
        return add_collimator_he(sim, head, debug)
    col = ["None", "lehr", "melp", "he"]
    gate.fatal(
        f'Cannot build the collimator "{collimator_type}". '
        f"Available collimator types are: {col}"
    )


def add_collimator_empty(sim, head):
    colli = sim.add_volume("Box", f"{head.name}_no_collimator")
    colli.mother = head.name
    colli.size = [59.7 * mm, 533 * mm, 387 * mm]
    colli.translation = [-96.7324 * mm, 0, 0]
    colli.color = blue
    colli.material = head.material
    return colli


def add_collimator_lehr(sim, head, debug):
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
    hole1 = sim.add_volume("Hexagon", f"{name}_collimator_hole1")
    hole1.height = 24.05 * mm
    hole1.radius = 0.555 * mm
    hole1.material = "G4_AIR"
    hole1.mother = colli.name

    # parameterised holes
    size = [1, 414, 175]
    if debug:
        size = [1, 20, 10]
    tr = [0, 1.27 * mm, 2.1997 * mm, 0]
    rot = Rotation.from_euler("y", 90, degrees=True).as_matrix()
    holep = gate.build_param_repeater(sim, colli.name, hole1.name, size, tr, rot)

    # do it twice, with the following offset
    holep.offset_nb = 2
    holep.offset = [0, 0.3175 * mm * 2, 0.549925 * mm * 2, 0]

    return colli


def add_collimator_melp(sim, head, debug):
    name = head.name

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
    #	y spacing	= diameter + septial = 4.08 mm
    #	z spacing	= 2 * (diameter + septial) * sin(60) = 7.06676729 mm
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
    hole1 = sim.add_volume("Hexagon", f"{name}_collimator_hole1")
    hole1.height = 40.64 * mm
    hole1.radius = 1.47 * mm
    hole1.material = "G4_AIR"
    hole1.mother = colli.name

    # parameterised holes
    size = [1, 128, 55]
    if debug:
        size = [1, 20, 10]
    tr = [0, 4.08 * mm, 7.066767 * mm, 0]
    rot = Rotation.from_euler("y", 90, degrees=True).as_matrix()
    holep = gate.build_param_repeater(sim, colli.name, hole1.name, size, tr, rot)

    # do it twice, with the following offset
    holep.offset_nb = 2
    holep.offset = [0, -1.02 * mm * 2, -1.76669 * mm * 2, 0]

    return colli


def add_collimator_he(sim, head, debug):
    name = head.name

    gate.fatal(
        f"the Intevo HE collimator is not implemented yet. Need to move the shielding ..."
    )

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
    hole1 = sim.add_volume("Hexagon", f"{name}_collimator_hole1")
    hole1.height = 59.7 * mm
    hole1.radius = 2.0 * mm
    hole1.material = "G4_AIR"
    hole1.mother = colli.name

    # parameterised holes
    size = [1, 96, 42]
    if debug:
        size = [1, 20, 10]
    tr = [0, 6 * mm, 10.39230485 * mm, 0]
    rot = Rotation.from_euler("y", 90, degrees=True).as_matrix()
    holep = gate.build_param_repeater(sim, colli.name, hole1.name, size, tr, rot)

    # do it twice, with the following offset
    holep.offset_nb = 2
    holep.offset = [0, -1.5 * mm * 2, -2.598076212 * mm * 2, 0]

    return colli
