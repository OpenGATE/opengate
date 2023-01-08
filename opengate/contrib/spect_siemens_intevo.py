import opengate as gate
import pathlib

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
    if fdb not in sim.volume_manager.user_material_databases:
        sim.add_material_database(fdb)

    # check overlap
    sim.g4_check_overlap_flag = True  # set to True for debug # FIXME

    # main box
    head = add_head_box(sim, name)
    shielding = add_shielding(sim, head)

    # collimator
    # colli = add_collimator(sim, head, collimator_type)

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


def add_shielding(sim, head):
    # shielding
    name = head.name
    back_shield = sim.add_volume("Box", f"{name}_back_shield")
    back_shield.mother = head.name
    back_shield.size = [17.1 * mm, 676.7 * mm, 510.4 * mm]
    back_shield.translation = [98.9724 * mm, 0, 0]
    # backcomp(x) + backcomp(x)/2 + shieldBack/2 = 16.6724 + 147.5/2 + 17.1/2
    back_shield.material = "Lead"
    back_shield.color = gray

    # side shield Y pos
    side_shield_y_pos = sim.add_volume("Box", f"{name}_side_shield_y_pos")
    side_shield_y_pos.mother = head.name
    side_shield_y_pos.size = [215.0448 * mm, 12.7 * mm, 510.4 * mm]
    side_shield_y_pos.translation = [0, 336.15 * mm, 0]
    side_shield_y_pos.material = "Lead"
    side_shield_y_pos.color = gray
    print(side_shield_y_pos)

    # side shield Y neg
    side_shield_y_neg = sim.add_volume("Box", f"{name}_side_shield_y_neg")
    side_shield_y_neg = side_shield_y_pos.copy()
    side_shield_y_neg.translation[1] = -side_shield_y_neg.translation[1]
