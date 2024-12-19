from opengate.contrib.phantoms.nemaiec import dump_bg_activity
from opengate.utility import g4_units


def add_phantom_material(simulation):
    elems = ["H", "C", "O"]
    w = [0.080538, 0.599848, 0.319614]
    gcm3 = g4_units.g_cm3
    simulation.volume_manager.material_database.add_material_weights(
        "JASZCZAK_PMMA", elems, w, 1.19 * gcm3
    )


def add_jaszczak_phantom(simulation, name="jaszczak", check_overlap=False):
    # https://www.meditest.fr/documentation/4.pdf
    # unit
    add_phantom_material(simulation)

    # check overlap only for debug
    original_check_overlap_flag = simulation.check_volumes_overlap
    simulation.check_volumes_overlap = check_overlap

    # Outside structure
    jaszczak, internal_cylinder = add_jaszczak_body(simulation, name)
    jaszczak.material = "JASZCZAK_PMMA"

    simulation.check_volumes_overlap = original_check_overlap_flag
    return jaszczak, internal_cylinder


def add_jaszczak_body(sim, name):
    cm = g4_units.cm
    mm = g4_units.mm
    deg = g4_units.deg
    white = [1, 1, 1, 1]
    thickness = 3.2 * mm

    # main cylinder interior
    external_cylinder = sim.add_volume("Tubs", name=f"{name}_cylinder")
    external_cylinder.rmax = 21.6 * cm / 2.0 + thickness
    external_cylinder.rmin = 0
    external_cylinder.dz = 18.6 * cm / 2 + thickness * 2
    external_cylinder.sphi = 0 * deg
    external_cylinder.dphi = 360 * deg
    external_cylinder.material = "JASZCZAK_PMMA"
    external_cylinder.color = white

    # main cylinder interior
    internal_cylinder = sim.add_volume("Tubs", name=f"{name}_internal_cylinder")
    internal_cylinder.mother = external_cylinder.name
    internal_cylinder.rmax = 21.6 * cm / 2
    internal_cylinder.rmin = 0
    internal_cylinder.dz = 18.6 * cm / 2
    internal_cylinder.sphi = 0 * deg
    internal_cylinder.dphi = 360 * deg
    internal_cylinder.material = "G4_AIR"

    return external_cylinder, internal_cylinder


def add_background_source(
    simulation, jaszczak_name, src_name, activity_bqml, verbose=False
):
    # source
    bg = simulation.add_source("GenericSource", f"{jaszczak_name}_{src_name}")
    bg.attached_to = f"{jaszczak_name}_internal_cylinder"
    v = simulation.volume_manager.volumes[bg.attached_to]
    v_info = v.solid_info
    # (1 cm3 = 1 mL)
    """
    # no need to confine yet, nothing inside the cylinder -> should be done later
    bg.position.type = "box"
    bg.position.size = simulation.volume_manager.volumes[bg.mother].bounding_box_size
    # this source is confined only within the mother volume, it does not include daughter volumes
    # it is a tubs inside the box
    bg.position.confine = bg.mother
    """
    bg.particle = "e+"
    bg.energy.type = "F18"
    bg.activity = activity_bqml * v_info.cubic_volume

    if verbose:
        s = dump_bg_activity(simulation, jaszczak_name, src_name)
        print(s)
    return bg, v_info.cubic_volume
