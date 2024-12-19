from scipy.spatial.transform import Rotation
from box import Box
import opengate as gate
from opengate.utility import g4_units, get_contrib_path
from opengate.geometry.utility import get_grid_repetition
from opengate.geometry.volumes import unite_volumes, intersect_volumes, subtract_volumes
from opengate.geometry import volumes
import scipy
import numpy as np
import itk


def add_linac(sim, linac_name, sad=1000):
    # materials
    add_linac_materials(sim)

    # linac
    linac = add_empty_linac_box(sim, linac_name, sad)

    # add elements
    add_target(sim, linac.name)
    add_primary_collimator(sim, linac.name)
    add_flattening_filter(sim, linac.name)
    add_ionizing_chamber(sim, linac.name)
    add_back_scatter_plate(sim, linac.name)
    add_mirror(sim, linac.name)

    # kill actor above the target
    kill_around_target(sim, linac.name)

    return linac


def add_empty_linac_box(sim, linac_name, sad=1000):
    # units
    m = g4_units.m
    mm = g4_units.mm
    linac = sim.add_volume("Box", linac_name)
    linac.material = "G4_AIR"
    linac.size = [1 * m, 1 * m, 0.52 * m]
    translation_linac_box = np.array([0 * mm, 0, sad - linac.size[2] / 2 + 3.5 * mm])
    # Isocenter begin at the end of the target, That's why 3.5 mm is added.
    linac.translation = translation_linac_box
    linac.color = [1, 1, 1, 0]
    return linac


def add_linac_materials(sim):
    contrib_paths = get_contrib_path() / "linacs"
    file = contrib_paths / "elekta_versa_materials.db"
    sim.volume_manager.add_material_database(str(file))


def add_target(sim, linac_name):
    linac = sim.volume_manager.get_volume(linac_name)
    z_linac = linac.size[2]
    # unit
    mm = g4_units.mm
    nm = g4_units.nm

    # colors
    red = [1, 0.2, 0.2, 0.8]
    green = [0, 1, 0, 0.2]

    # material
    target_material = f"target_tungsten"
    copper = f"target_copper"

    # target
    target_support = sim.add_volume("Tubs", f"{linac_name}_target_support")
    target_support.mother = linac_name
    target_support.material = "G4_AIR"
    target_support.rmin = 0
    target_support.rmax = 15 * mm
    target_support.dz = 13.5 * mm / 2.0
    target_support.translation = [0, 0, z_linac / 2 - target_support.dz - 1 * nm]
    target_support.color = [0, 1, 0, 1]

    target = sim.add_volume("Tubs", f"{linac_name}_target")
    target.mother = target_support.name
    target.material = target_material
    target.rmin = 0
    target.rmax = 2.7 * mm
    target.dz = 1 * mm / 2.0
    target.translation = [0, 0, target_support.dz - 3 * mm]
    target.color = red

    target_support_top = sim.add_volume("Tubs", f"{linac_name}_target_support_top")
    target_support_top.mother = target_support.name
    target_support_top.material = copper
    target_support_top.rmin = 2.7 * mm
    target_support_top.rmax = 15 * mm
    target_support_top.dz = 3.5 * mm / 2.0
    target_support_top.translation = [0, 0, target_support.dz - 1.75 * mm]
    target_support_top.color = green

    target_support_bottom = sim.add_volume(
        "Tubs", f"{linac_name}_target_support_bottom"
    )
    target_support_bottom.mother = target_support.name

    target_support_bottom.material = copper
    target_support_bottom.rmin = 0
    target_support_bottom.rmax = 15 * mm
    target_support_bottom.dz = 10 * mm / 2.0
    target_support_bottom.translation = [0, 0, target_support.dz - 8.5 * mm]
    target_support_bottom.color = green

    return target_support


def kill_around_target(sim, linac_name):
    mm = g4_units.mm
    nm = g4_units.nm
    linac = sim.volume_manager.get_volume(linac_name)
    z_linac = linac.size[2]

    # above the target
    target_above = sim.add_volume("Tubs", f"target_kill_volume1")
    target_above.mother = linac_name
    target_above.material = "G4_AIR"
    target_above.rmin = 0
    target_above.rmax = 15 * mm
    target_above.dz = 0.5 * nm
    target_above.translation = [0, 0, z_linac / 2 - 0.5 * nm]
    target_above.color = [1, 0, 0, 1]

    # around the target
    target_around = sim.add_volume("Tubs", f"target_kill_volume2")
    target_around.mother = linac_name
    target_around.material = "G4_AIR"
    target_around.rmin = 15.1 * mm
    target_around.rmax = target_around.rmin + 1 * nm
    target_around.dz = 13.5 / 2 * mm
    target_around.translation = [0, 0, z_linac / 2 - target_around.dz - 1 * nm]
    target_around.color = [1, 0, 0, 1]

    # psycho killer
    killer = sim.add_actor("KillActor", f"target_kill")
    killer.attached_to = [target_above.name, target_around.name]


def add_primary_collimator(sim, linac_name):
    linac = sim.volume_manager.get_volume(linac_name)
    z_linac = linac.size[2]
    mm = g4_units.mm
    deg = g4_units.deg
    primary_collimator = sim.add_volume("Cons", f"{linac_name}_primary_collimator")
    primary_collimator.mother = linac_name
    primary_collimator.material = "mat_leaf"
    primary_collimator.rmin1 = 31.45 * mm
    primary_collimator.rmax1 = 82 * mm
    primary_collimator.rmin2 = 6.45 * mm
    primary_collimator.rmax2 = 82 * mm
    primary_collimator.dz = 101 * mm / 2.0
    primary_collimator.sphi = 0
    primary_collimator.dphi = 360 * deg
    primary_collimator.translation = [0, 0, z_linac / 2 - 70.6 * mm]
    primary_collimator.color = [0, 0, 1, 0.8]


def add_flattening_filter(sim, linac_name):
    # unit
    mm = g4_units.mm
    deg = g4_units.deg

    # colors
    yellow = [0, 0.7, 0.7, 0.8]
    linac = sim.volume_manager.get_volume(linac_name)
    z_linac = linac.size[2]

    # bounding cylinder
    flattening_filter = sim.add_volume("Tubs", f"{linac_name}_flattening_filter")
    flattening_filter.mother = linac_name
    flattening_filter.material = "G4_AIR"
    flattening_filter.rmin = 0
    flattening_filter.rmax = 54 * mm
    flattening_filter.dz = 26.1 * mm / 2
    flattening_filter.translation = [0, 0, z_linac / 2 - 149.55 * mm]
    flattening_filter.color = [1, 0, 0, 0]  # invisible

    # create all cones
    def add_cone(sim, p):
        c = sim.add_volume("Cons", f"{linac_name}_flattening_filter_cone_{p.name}")
        c.mother = flattening_filter.name
        c.material = "flattening_filter_material_stain_steel"
        c.rmin1 = 0
        c.rmax1 = p.rmax1
        c.rmin2 = 0
        c.rmax2 = p.rmax2
        c.dz = p.dz
        c.sphi = 0
        c.dphi = 360 * deg
        c.translation = [0, 0, p.tr]
        c.color = yellow

    cones = np.array(
        [
            [0.001, 2.6, 1.2, flattening_filter.dz - 0.6],
            [2.6, 9, 4.9, flattening_filter.dz - 3.65],
            [9, 14.5, 4.9, flattening_filter.dz - 8.55],
            [14.5, 22.5, 5.5, flattening_filter.dz - 13.75],
            [22.5, 32.5, 5.6, flattening_filter.dz - 19.3],
        ]
    )

    cyl = volumes.TubsVolume(name=f"{linac_name}_flattening_filter_cyl_base")
    cyl.rmin = 0
    cyl.rmax = 46.5 * mm
    cyl.dz = 4 * mm

    trap = volumes.TrapVolume(name=f"{linac_name}_flattening_filter_trap_base")
    dz = 93 / 2 * mm
    dy1 = 171.39 / 2 * mm
    dy2 = 36.26 * mm / 2

    dx1 = 4 / 2 * mm
    alpha1 = 0
    alpha2 = alpha1
    phi = 0
    theta = 0
    dx2 = dx1
    dx3 = dx1
    dx4 = dx1

    trap.dx1 = dx1
    trap.dx2 = dx2
    trap.dx3 = dx3
    trap.dx4 = dx4
    trap.dy1 = dy1
    trap.dy2 = dy2
    trap.dz = dz
    trap.alp1 = alpha1
    trap.alp2 = alpha2
    trap.theta = theta
    trap.phi = phi
    rot = Rotation.from_euler("Y", -90, degrees=True).as_matrix()
    ff_base = intersect_volumes(cyl, trap, [0, 0, 0], rot)
    ff_base.name = f"{linac_name}_flattening_filter_base"
    sim.volume_manager.add_volume(ff_base, f"{linac_name}_flattening_filter_base")
    ff_base.mother = flattening_filter.name
    ff_base.translation = [0, 0, flattening_filter.dz - 24.1 * mm]
    ff_base.color = yellow
    ff_base.material = "flattening_filter_material_stain_steel"

    cons_1 = volumes.ConsVolume(name=f"{linac_name}_flattening_filter_cons_1")
    cons_1.rmin1 = 77 / 2 * mm
    cons_1.rmax1 = 93 / 2 * mm
    cons_1.rmin2 = 77 / 2 * mm
    cons_1.rmax2 = 93 / 2 * mm
    cons_1.dz = 3.5 * mm / 2.0
    cons_1.sphi = 0
    cons_1.dphi = 360 * deg

    ff_cons_1 = intersect_volumes(cons_1, trap, [0, 0, 0], rot)
    ff_cons_1.name = f"{linac_name}_flattening_filter_cons_1"
    sim.volume_manager.add_volume(ff_cons_1, f"{linac_name}_flattening_filter_cons_1")
    ff_cons_1.mother = flattening_filter.name
    ff_cons_1.material = "flattening_filter_material_stain_steel"
    ff_cons_1.translation = [0, 0, flattening_filter.dz - 20.35 * mm]
    ff_cons_1.color = yellow

    ff_cons_2 = sim.add_volume("ConsVolume", f"{linac_name}_flattening_filter_cons_2")
    ff_cons_2.rmin1 = 77 / 2 * mm
    ff_cons_2.rmax1 = 79.99 / 2 * mm
    ff_cons_2.rmin2 = 77 / 2 * mm
    ff_cons_2.rmax2 = 79.99 / 2 * mm
    ff_cons_2.dz = 3.5 * mm / 2.0
    ff_cons_2.sphi = 0
    ff_cons_2.dphi = 360 * deg
    ff_cons_2.mother = flattening_filter.name
    ff_cons_2.material = "flattening_filter_material_stain_steel"
    ff_cons_2.translation = [0, 0, flattening_filter.dz - 16.85 * mm]
    ff_cons_2.color = yellow

    ff_cons_3 = sim.add_volume("ConsVolume", f"{linac_name}_flattening_filter_cons_3")
    ff_cons_3.rmin1 = 73 / 2 * mm
    ff_cons_3.rmax1 = 77 / 2 * mm
    ff_cons_3.rmin2 = 73 / 2 * mm
    ff_cons_3.rmax2 = 77 / 2 * mm
    ff_cons_3.dz = 22.1 * mm / 2.0
    ff_cons_3.sphi = 0
    ff_cons_3.dphi = 360 * deg
    ff_cons_3.mother = flattening_filter.name
    ff_cons_3.material = "flattening_filter_material_stain_steel"
    ff_cons_3.translation = [0, 0, flattening_filter.dz - 11.05 * mm]
    ff_cons_3.color = yellow

    ff_cons_4 = sim.add_volume("ConsVolume", f"{linac_name}_flattening_filter_cons_4")
    ff_cons_4.rmin1 = 77 / 2 * mm
    ff_cons_4.rmax1 = 79 / 2 * mm
    ff_cons_4.rmin2 = 77 / 2 * mm
    ff_cons_4.rmax2 = 79 / 2 * mm
    ff_cons_4.dz = 15.1 * mm / 2.0
    ff_cons_4.sphi = 0
    ff_cons_4.dphi = 360 * deg
    ff_cons_4.mother = flattening_filter.name
    ff_cons_4.material = "flattening_filter_material_stain_steel"
    ff_cons_4.translation = [0, 0, flattening_filter.dz - 7.55 * mm]
    ff_cons_4.color = yellow

    ## cons 5 is for the moment an assumption of the secondary filter carrier design
    ff_cons_5 = sim.add_volume("ConsVolume", f"{linac_name}_flattening_filter_cons_5")
    ff_cons_5.rmin1 = 79.99 / 2 * mm
    ff_cons_5.rmax1 = 106 / 2 * mm
    ff_cons_5.rmin2 = 79.99 / 2 * mm
    ff_cons_5.rmax2 = 106 / 2 * mm
    ff_cons_5.dz = 5 * mm / 2.0
    ff_cons_5.sphi = 0
    ff_cons_5.dphi = 360 * deg
    ff_cons_5.mother = flattening_filter.name
    ff_cons_5.material = "flattening_filter_material_mild_steel"
    ff_cons_5.translation = [0, 0, flattening_filter.dz - 16.1 * mm]
    ff_cons_5.color = yellow

    i = 0
    for c in cones:
        cone = Box()
        cone.name = i
        cone.rmax2 = c[0] * mm
        cone.rmax1 = c[1] * mm
        cone.dz = c[2] * mm / 2  # /2 to keep same values than Gate (where dz was /2)
        cone.tr = c[3] * mm
        add_cone(sim, cone)
        i = i + 1


def add_ionizing_chamber(sim, linac_name):
    # unit
    mm = g4_units.mm

    # main cylinder
    linac = sim.volume_manager.get_volume(linac_name)
    z_linac = linac.size[2]
    ionizing_chamber = sim.add_volume("Tubs", f"{linac_name}_ionizing_chamber")
    ionizing_chamber.mother = linac_name
    ionizing_chamber.material = "G4_AIR"
    ionizing_chamber.rmin = 0
    ionizing_chamber.rmax = 45 * mm
    ionizing_chamber.dz = 9.28 * mm / 2
    ionizing_chamber.translation = [0, 0, z_linac / 2 - 172.5 * mm]
    ionizing_chamber.color = [0, 0, 0, 0]

    # layers
    def add_layer(sim, p):
        l = sim.add_volume("Tubs", f"{linac_name}_ionizing_chamber_mylar_layer_{p.i}")
        l.mother = ionizing_chamber.name
        l.material = "linac_mylar"
        l.rmin = 0
        l.rmax = 45 * mm
        l.dz = 0.012 * mm / 2
        l.translation = [0, 0, p.tr1]

        l = sim.add_volume("Tubs", f"{linac_name}_ionizing_chamber_carbon_layer_{p.i}")
        l.mother = ionizing_chamber.name
        l.material = "linac_carbon"
        l.rmin = 0
        l.rmax = 45 * mm
        l.dz = 0.000150 * mm / 2
        l.translation = [0, 0, p.tr2]

    layers = [
        [-2.634, -2.627925],
        [-0.434, -0.427925],
        [0.566, 0.572075],
        [1.566, 1.572075],
        [2.566, 2.572075],
        [3.566, 3.572075],
    ]
    i = 1
    for l in layers:
        ll = Box()
        ll.i = i
        ll.tr1 = l[0] * mm
        ll.tr2 = l[1] * mm
        add_layer(sim, ll)
        i = i + 1


def add_back_scatter_plate(sim, linac_name):
    # back_scatter_plate
    linac = sim.volume_manager.get_volume(linac_name)
    z_linac = linac.size[2]
    mm = g4_units.mm
    bsp = sim.add_volume("Box", f"{linac_name}_back_scatter_plate")
    bsp.mother = linac_name
    bsp.material = "linac_aluminium"
    bsp.size = [116 * mm, 84 * mm, 3 * mm]
    bsp.translation = [0, 0, z_linac / 2 - 187.5 * mm]
    bsp.color = [1, 0.7, 0.7, 0.8]


def add_mirror(sim, linac_name):
    # unit
    mm = g4_units.mm
    blue = [0, 0, 1, 0.8]

    # main box
    linac = sim.volume_manager.get_volume(linac_name)
    z_linac = linac.size[2]
    m = sim.add_volume("Box", f"{linac_name}_mirror")
    m.mother = linac_name
    m.material = "G4_AIR"
    m.size = [137 * mm, 137 * mm, 1.5 * mm]
    m.translation = [0, 0, z_linac / 2 - 227.5 * mm]
    rot = Rotation.from_euler("x", 37.5, degrees=True)
    m.rotation = rot.as_matrix()

    # mylar
    l = sim.add_volume("Box", f"{linac_name}_mirror_mylar_layer")
    l.mother = m.name
    l.material = "linac_mylar"
    l.size = [110 * mm, 110 * mm, 0.0012 * mm]
    l.translation = [0, 0, 0.15 * mm]
    l.color = blue

    # alu
    l = sim.add_volume("Box", f"{linac_name}_mirror_alu_layer")
    l.mother = m.name
    l.material = "linac_aluminium"
    l.size = [110 * mm, 110 * mm, 0.0003 * mm]
    l.translation = [0, 0, -0.6 * mm]
    l.color = blue


def enable_brem_splitting(sim, linac_name, splitting_factor):
    # create a region
    linac_target = sim.volume_manager.get_volume(f"{linac_name}_target")
    region_linac = sim.physics_manager.add_region(name=f"{linac_target.name}_region")
    region_linac.associate_volume(linac_target)
    # set the brem splitting
    s = f"/process/em/setSecBiasing eBrem {region_linac.name} {splitting_factor} 50 MeV"
    sim.g4_commands_after_init.append(s)


def add_electron_source(sim, linac_name, ekin, sx, sy):
    MeV = g4_units.MeV
    mm = g4_units.mm
    nm = g4_units.nm
    deg = g4_units.deg
    source = sim.add_source("GenericSource", f"{linac_name}_e-_source")
    source.particle = "e-"
    source.attached_to = f"{linac_name}_target"
    source.energy.type = "gauss"
    source.energy.mono = ekin * MeV
    source.energy.sigma_gauss = source.energy.mono * (0.08 / 2.35)
    source.position.type = "disc"
    source.position.sigma_x = sx * mm
    source.position.sigma_y = sy * mm
    source.position.translation = [0, 0, 0.5 * mm - 1 * nm]
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, -1]
    source.direction_relative_to_attached_volume = True
    source.n = 10
    return source


def set_cut_on_linac_head(sim, linac_name, particles, cuts):
    ##FIXME Probably not adapted to the current geometry of the LINAC, need to be corrected
    l_volume = [
        f"{linac_name}_mlc",
        "jaw_box_right",
        "jaw_box_left",
        f"{linac_name}_primary_collimator",
        f"{linac_name}_flattening_filter",
        f"{linac_name}_back_scatter_plate",
        f"{linac_name}_target_support_top",
        f"{linac_name}_target_support_bottom",
    ]
    mm = g4_units.mm
    reg = sim.physics_manager.add_region(name=f"{linac_name}_region")
    for volume in l_volume:
        reg.associate_volume(volume)
    if type(particles) == str:
        if particles == "all":
            reg.production_cuts.gamma = cuts
            reg.production_cuts.electron = cuts
            reg.production_cuts.positron = cuts
    else:
        for i, particle in enumerate(particles):
            if particle == "gamma":
                reg.production_cuts.gamma = cuts[i]
            elif particle == "electron":
                reg.production_cuts.electron = cuts[i]
            elif particle == "positron":
                reg.production_cuts.positron = cuts[i]


def add_phase_space_plane(sim, linac_name, src_phsp_distance):
    mm = g4_units.mm
    m = g4_units.m
    nm = g4_units.nm
    plane = sim.add_volume("Tubs", f"{linac_name}_phsp_plane")
    plane.mother = linac_name
    plane.material = "G4_AIR"
    plane.rmin = 0
    plane.rmax = 0.5 * m / 2 - 0.1 * mm
    plane.dz = 1 * nm  # half height
    linac = sim.volume_manager.get_volume(linac_name)
    z_linac = linac.size[2]
    plane.translation = [0 * mm, 0 * mm, +z_linac / 2 - src_phsp_distance]
    plane.color = [1, 0, 0, 1]  # red
    return plane


def add_phase_space_actor(sim, plane_name, i=0):
    if i == 0:
        phsp = sim.add_actor("PhaseSpaceActor", f"{plane_name}_phsp")
    else:
        phsp = sim.add_actor("PhaseSpaceActor", f"{plane_name}_phsp_" + str(i))
    phsp.attached_to = plane_name
    phsp.attributes = [
        "KineticEnergy",
        "Weight",
        "PrePosition",
        "PrePositionLocal",
        "PreDirection",
        "PreDirectionLocal",
        "PDGCode",
    ]
    return phsp


def add_phase_space_source(sim, plane_name):
    source = sim.add_source("PhaseSpaceSource", "phsp_source_global")
    source.attached_to = plane_name
    source.position_key = "PrePositionLocal"
    source.direction_key = "PreDirectionLocal"
    # source.weight_key = "Weight"
    source.global_flag = False
    source.particle = ""
    source.batch_size = 100000
    # source.translate_position = True
    return source


def mlc_leaf(linac_name):
    mm = g4_units.mm
    interleaf_gap = 0.09 * mm
    leaf_length = 155 * mm
    leaf_height = 90 * mm
    leaf_mean_width = 1.76 * mm
    tongues_length = 0.8 * mm

    cyl = volumes.TubsVolume(name=f"{linac_name}_cylinder_leaf")
    cyl.rmin = 0
    cyl.rmax = 170 * mm

    box_rot_leaf = volumes.BoxVolume(name=f"{linac_name}_Box_leaf")
    box_rot_leaf.size = [200 * mm, leaf_length, leaf_height]

    trap_leaf = volumes.TrapVolume(name=f"{linac_name}_trap_leaf")
    dz = leaf_height / 2
    dy1 = leaf_length / 2
    dx1 = 1.94 * mm / 2
    dx3 = 1.58 * mm / 2
    theta = 0

    alpha1 = 0
    alpha2 = alpha1
    phi = 0
    dy2 = dy1
    dx2 = dx1
    dx4 = dx3

    trap_leaf.dx1 = dx1
    trap_leaf.dx2 = dx2
    trap_leaf.dx3 = dx3
    trap_leaf.dx4 = dx4
    trap_leaf.dy1 = dy1
    trap_leaf.dy2 = dy2
    trap_leaf.dz = dz
    trap_leaf.alp1 = alpha1
    trap_leaf.alp2 = alpha2
    trap_leaf.theta = theta
    trap_leaf.phi = phi

    rot_leaf = Rotation.from_euler("Z", -90, degrees=True).as_matrix()
    rot_cyl = Rotation.from_euler("X", 90, degrees=True).as_matrix()

    trap_tongue = volumes.TrapVolume(name=f"{linac_name}_trap_tongue")
    dz = tongues_length / 2
    dy1 = leaf_length / 2

    ##FIXME I need to remove 2 um to the tongues to avoid an overleap between leaves
    dx1 = (interleaf_gap - 2.2 * 10 ** (-3) * mm) / 2
    dx3 = dx1
    alpha1 = 0
    alpha2 = alpha1
    theta = np.arctan((1.58 * mm - 1.94 * mm) * 0.5 / leaf_height)
    phi = 0
    dy2 = dy1
    dx2 = dx1
    dx4 = dx1

    trap_tongue.dx1 = dx1
    trap_tongue.dx2 = dx2
    trap_tongue.dx3 = dx3
    trap_tongue.dx4 = dx4
    trap_tongue.dy1 = dy1
    trap_tongue.dy2 = dy2
    trap_tongue.dz = dz
    trap_tongue.alp1 = alpha1
    trap_tongue.alp2 = alpha2
    trap_tongue.theta = theta
    trap_tongue.phi = phi

    bool_leaf = intersect_volumes(box_rot_leaf, trap_leaf, [0, 0, 0], rot_leaf)
    bool_tongue = intersect_volumes(box_rot_leaf, trap_tongue, [0, 0, 0], rot_leaf)
    bool_leaf = unite_volumes(
        bool_leaf, bool_tongue, [0 * mm, (leaf_mean_width + interleaf_gap) / 2, 0 * mm]
    )
    bool_leaf = intersect_volumes(bool_leaf, cyl, [92.5 * mm, 0, 7.5 * mm], rot_cyl)

    return bool_leaf


def add_mlc(sim, linac_name):

    mm = g4_units.mm
    cm = g4_units.cm
    linac = sim.volume_manager.get_volume(linac_name)
    leaf_height = 90 * mm
    z_linac = linac.size[2]
    center_mlc = 349.3 * mm + 3.5 * mm
    interleaf_gap = 0.09 * mm
    leaf_width = 1.76 * mm
    leaf_lenght = 155 * mm
    nb_leaf = 160
    rotation_angle = np.arctan((1.94 * mm - 1.58 * mm) * 0.5 / leaf_height)

    mlc = sim.add_volume("Box", f"{linac_name}_mlc")
    mlc_bank_rotation = Rotation.from_euler(
        "X", np.arctan(3.25 / 349.3), degrees=False
    ).as_matrix()
    mlc.rotation = mlc_bank_rotation
    mlc.size = [linac.size[0] - 2 * cm, linac.size[1] - 2 * cm, 100 * mm]
    mlc.translation = np.array([0, 0, z_linac / 2 - center_mlc])
    mlc.mother = linac_name
    mlc.color = [0, 0, 0, 0]

    leaf_color = [0.92, 0.61, 0.32, 0.4]
    leaf = mlc_leaf(linac_name)
    leaf.name = f"{linac_name}_leaf"
    sim.volume_manager.add_volume(leaf, f"{linac_name}_leaf")
    leaf.material = "mat_leaf"
    leaf.mother = mlc
    leaf.color = leaf_color

    size = [2, int(0.5 * nb_leaf), 1]
    tr_blocks = np.array([leaf_lenght, leaf_width + interleaf_gap, 0])
    leaves_pos = np.array(get_grid_repetition(size, tr_blocks))
    l_rotation = []
    l_center_translation = []

    for i in range(len(leaves_pos)):
        if i <= int(nb_leaf / 4) - 1:
            angle = 2 * rotation_angle * (i - int(nb_leaf / 4)) + rotation_angle
        elif int(nb_leaf / 4) - 1 < i <= 2 * int(nb_leaf / 4) - 1:
            angle = 2 * rotation_angle * (i - int(nb_leaf / 4) + 1) - rotation_angle
        elif 2 * int(nb_leaf / 4) - 1 < i <= 3 * int(nb_leaf / 4) - 1:
            angle = 2 * rotation_angle * (i - 3 * int(nb_leaf / 4)) + rotation_angle
        elif 3 * int(nb_leaf / 4) - 1 < i:
            angle = 2 * rotation_angle * (i - 3 * int(nb_leaf / 4) + 1) - rotation_angle

        cos_angle = np.cos(np.abs(angle))
        sin_angle = np.sin(np.abs(angle))
        tan_angle_pos = np.tan(np.pi / 2 - rotation_angle - np.abs(angle))
        tan_angle_neg = np.tan(np.pi / 2 - rotation_angle + np.abs(angle))

        left = (leaf_width / 2) * (cos_angle + sin_angle / tan_angle_pos)
        right = (leaf_width / 2) * (cos_angle - sin_angle / tan_angle_neg)

        if angle < 0:
            l_center_translation.append([left, right])
        else:
            l_center_translation.append([right, left])

        if leaves_pos[i, 0] > 0:
            rot = Rotation.from_euler("X", angle, degrees=False).as_matrix()
            l_rotation.append(rot)
        else:
            rot = Rotation.from_euler("XZ", [angle, np.pi], degrees=False).as_matrix()
            l_rotation.append(rot)

    translation_to_apply = []
    l_center_translation = l_center_translation[: int(len(l_center_translation) / 2)]

    for i in range(len(l_center_translation)):
        if i != 0:
            translation_to_apply.append(
                l_center_translation[i - 1][1] + l_center_translation[i][0]
            )

    translation_to_apply = np.array(translation_to_apply) - leaf_width
    translation_to_apply = translation_to_apply[
        : int(len(translation_to_apply) / 2) + 1
    ]
    translation_to_apply[-1] = translation_to_apply[-1] / 2
    final_translation_to_apply = []
    for j in range(len(translation_to_apply)):
        final_translation_to_apply.append(np.sum(translation_to_apply[j:]))

    final_translation_to_apply = np.array(
        (
            (
                (-np.array(final_translation_to_apply)).tolist()
                + final_translation_to_apply[::-1]
            )
            * 2
        )
    )
    for i in range(len(leaves_pos)):
        leaves_pos[i, 1] += final_translation_to_apply[i]
    leaf.translation = leaves_pos
    leaf.rotation = np.array(l_rotation)

    return leaf


def trap_g4_param(
    obj, dx1, dx2, dx3, dx4, dy1, dy2, dz, theta=0, phi=0, alpha1=0, alpha2=0
):
    obj.dx1 = dx1
    obj.dx2 = dx2
    obj.dx3 = dx3
    obj.dx4 = dx4
    obj.dy1 = dy1
    obj.dy2 = dy2
    obj.dz = dz
    obj.alp1 = alpha1
    obj.alp2 = alpha2
    obj.theta = theta
    obj.phi = phi


def add_jaws(sim, linac_name):
    return [add_jaw(sim, linac_name, "left"), add_jaw(sim, linac_name, "right")]


def add_jaw(sim, linac_name, side):
    nm = g4_units.nm
    mm = g4_units.mm
    um = g4_units.um
    cm = g4_units.cm
    jaw_x = 210 * mm
    jaw_y = 220 * mm
    jaw_z = 77 * mm
    linac = sim.volume_manager.get_volume(linac_name)
    center_jaw_z = 470.5 * mm

    ## Traps definition for three trapzoid composing the front f&ace of the jaw in the order of G4 paramaters : dx1,dx2,dx3,dx4,dy1,dy2,dz
    traps_y_dimensions = [
        [32 * mm, 32 * mm, 32 * mm],
        [194 * mm, 200 * mm, 210 * mm],
        [32 * mm, 32 * mm, 32 * mm],
        [194 * mm, 200 * mm, 210 * mm],
        [84.822 * mm, 87.964 * mm, 93.2 * mm],
        [84.822 * mm, 87.964 * mm, 93.2 * mm],
        [10 * mm, 29 * mm, 16 * mm],
    ]

    traps_y_positions = [
        [0, 0, 0],
        [
            jaw_y / 2 - 16.3 * mm - (93.2 - 84.822) * mm - (84.822) / 2 * mm,
            jaw_y / 2 - 16.3 * mm - (93.2 - 87.964) * mm - (87.964) / 2 * mm,
            jaw_y / 2 - 16.3 * mm - 93.2 / 2 * mm,
        ],
        [
            jaw_z / 2 - 22 * mm - 10 * mm / 2,
            jaw_z / 2 - 32 * mm - 29 * mm / 2,
            jaw_z / 2 - 32 * mm - 29 * mm - 16 * mm / 2,
        ],
    ]

    boxes_to_complete_traps_y_dimensions = [
        [194 * mm, 200 * mm, 210 * mm],
        [(109.5 - 84.822) * mm, (109.5 - 87.964) * mm, 16.3 * mm],
        [10 * mm, 29 * mm, 16 * mm],
    ]
    boxes_to_complete_traps_y_positions = [
        [0, 0, 0],
        [
            jaw_y / 2 - (109.5 - 84.822) / 2 * mm,
            jaw_y / 2 - (109.5 - 87.964) / 2 * mm,
            jaw_y / 2 - 16.3 / 2 * mm,
        ],
        [
            jaw_z / 2 - 22 * mm - 10 * mm / 2,
            jaw_z / 2 - 32 * mm - 29 * mm / 2,
            jaw_z / 2 - 32 * mm - 29 * mm - 16 * mm / 2,
        ],
    ]
    middle_trap_dimension = [
        [32 * mm, 32 * mm],
        [73.2 * mm, 73.2 * mm],
        [45 * mm, 45 * mm],
    ]
    middle_trap_position = [
        0,
        jaw_y / 2 - 109.5 * mm - 73.2 * mm / 2,
        jaw_z / 2 - 32 * mm - 45 * mm / 2,
    ]

    jaw_box = sim.volume_manager.add_volume("Box", "jaw_box_" + side)
    jaw_box.mother = linac_name
    jaw_box.size = np.array([jaw_x, jaw_y, jaw_z])
    jaw_box.translation = [0, 0, linac.size[2] / 2 - center_jaw_z - 3.5 * mm]
    jaw_box.color = [0, 0, 0, 0]

    middle_trap = sim.volume_manager.add_volume("Trap", "middle_trap_" + side)
    trap_g4_param(
        middle_trap,
        middle_trap_dimension[0][1] / 2,
        middle_trap_dimension[0][1] / 2,
        middle_trap_dimension[0][0] / 2,
        middle_trap_dimension[0][0] / 2,
        middle_trap_dimension[1][0] / 2,
        middle_trap_dimension[1][1] / 2,
        middle_trap_dimension[2][0] / 2,
    )
    middle_trap.translation = middle_trap_position
    middle_trap.color = [0.8, 0.4, 0.65, 0.6]
    middle_trap.mother = jaw_box.name
    middle_trap.material = "mat_leaf"

    for i in range(1, len(traps_y_positions)):
        traps = sim.volume_manager.add_volume("Trap", "trap_" + side + "_" + str(i))
        trap_g4_param(
            traps,
            traps_y_dimensions[0][i] / 2,
            traps_y_dimensions[1][i] / 2,
            traps_y_dimensions[2][i] / 2,
            traps_y_dimensions[3][i] / 2,
            traps_y_dimensions[4][i] / 2,
            traps_y_dimensions[5][i] / 2,
            traps_y_dimensions[6][i] / 2,
        )

        traps.translation = [
            traps_y_positions[0][i],
            traps_y_positions[1][i],
            traps_y_positions[2][i],
        ]
        traps.mother = jaw_box.name
        traps.material = "mat_leaf"
        traps.color = [0.8, 0.4, 0.65, 0.6]

    # Jaws curve tips
    cylindre = volumes.TubsVolume(name=f"{linac_name}_cyl_leaf" + "_" + side)
    cylindre.rmin = 0
    cylindre.rmax = 135 * mm
    cylindre.dz = jaw_x
    rot_cyl = Rotation.from_euler("Y", 90, degrees=True).as_matrix()

    for i in range(3):
        box = volumes.BoxVolume(name="Box_to_complete_traps_y_" + side + "_" + str(i))
        box.size = [
            boxes_to_complete_traps_y_dimensions[0][i],
            boxes_to_complete_traps_y_dimensions[1][i],
            boxes_to_complete_traps_y_dimensions[2][i],
        ]
        box.translation = [
            boxes_to_complete_traps_y_positions[0][i],
            boxes_to_complete_traps_y_positions[1][i],
            boxes_to_complete_traps_y_positions[2][i],
        ]
        box.mother = jaw_box.name
        the_box = intersect_volumes(
            box,
            cylindre,
            [
                0,
                boxes_to_complete_traps_y_dimensions[1][i] / 2 - 135 * mm,
                jaw_z / 2 - 35 * mm - boxes_to_complete_traps_y_positions[2][i],
            ],
            rot_cyl,
        )
        sim.volume_manager.add_volume(the_box, "curved_" + box.name)
        the_box.mother = jaw_box.name
        the_box.material = "mat_leaf"
        the_box.color = [0.8, 0.4, 0.65, 0.6]

    top_jaw_box = volumes.BoxVolume(name="top_jaw_box_" + side)
    top_jaw_box.size = [194 * mm, jaw_y, 22 * mm]
    top_jaw_box.translation = [0, 0, jaw_z / 2 - 22 * mm / 2]

    top_jaw_box = intersect_volumes(
        top_jaw_box,
        cylindre,
        [
            0,
            top_jaw_box.size[1] / 2 - 135 * mm,
            jaw_z / 2 - 35 * mm - top_jaw_box.translation[2],
        ],
        rot_cyl,
    )
    dimension_corner = np.array(
        [
            np.sqrt(22**2 + 6.9**2) * mm,
            np.sqrt(22**2 + 6.9**2) * 6.9 / 22 * mm,
            22 * mm + 10 * um,
        ]
    )

    for i in range(2):
        corner_to_remove = volumes.BoxVolume(
            name="corner_to_remove_" + side + "_" + str(i)
        )
        corner_to_remove.size = dimension_corner
        angle_for_corner = np.arctan(6.9 / 22) * 180 / np.pi
        if i == 1:
            angle_for_corner = -angle_for_corner
        rot_for_corner = Rotation.from_euler("z", -angle_for_corner, degrees=True)
        translation_to_apply = np.array(
            [
                194 * mm / 2 - corner_to_remove.size[0] / 2,
                -jaw_y / 2 - corner_to_remove.size[1] / 2,
                0,
            ]
        )
        t = gate.geometry.utility.get_translation_from_rotation_with_center(
            rot_for_corner,
            [+corner_to_remove.size[0] / 2, -corner_to_remove.size[1] / 2, 0],
        )
        if i == 1:
            translation_to_apply[0] = -translation_to_apply[0]
            t = gate.geometry.utility.get_translation_from_rotation_with_center(
                rot_for_corner,
                [-corner_to_remove.size[0] / 2, -corner_to_remove.size[1] / 2, 0],
            )
        translation_to_apply += t
        top_jaw_box = subtract_volumes(
            top_jaw_box,
            corner_to_remove,
            translation_to_apply,
            rot_for_corner.as_matrix(),
        )
    sim.volume_manager.add_volume(top_jaw_box, "curved_" + top_jaw_box.name)
    top_jaw_box.material = "mat_leaf"
    top_jaw_box.mother = jaw_box.name
    top_jaw_box.color = [0.8, 0.4, 0.65, 0.6]

    below_top_jaw_box = volumes.BoxVolume(name="below_top_jaw_box_" + side)
    below_top_jaw_box.size = [154 * mm, jaw_y - (109.5 - 84.822) * mm, 10 * mm]
    below_top_jaw_box_size = list(below_top_jaw_box.size)
    below_top_jaw_box.translation = [
        0,
        jaw_y / 2 - (109.5 - 84.822) * mm - (jaw_y - (109.5 - 84.822)) / 2 * mm,
        jaw_z / 2 - 22 * mm - 10 * mm / 2,
    ]
    dimension_corner = np.array(
        [
            np.sqrt(22**2 + 6.9**2) * mm,
            np.sqrt(22**2 + 6.9**2) * 6.9 / 22 * mm,
            10 * mm + 10 * um,
        ]
    )
    for i in range(2):
        corner_to_remove = volumes.BoxVolume(
            name="corner_to_remove_" + side + "_" + str(i + 2)
        )
        corner_to_remove.size = dimension_corner
        angle_for_corner = np.arctan(6.9 / 22) * 180 / np.pi
        if i == 1:
            angle_for_corner = -angle_for_corner
        rot_for_corner = Rotation.from_euler("z", -angle_for_corner, degrees=True)
        translation_to_apply = np.array(
            [
                194 * mm / 2 - corner_to_remove.size[0] / 2,
                -(jaw_y - (109.5 - 84.822) * mm) / 2 - corner_to_remove.size[1] / 2,
                0,
            ]
        )
        t = gate.geometry.utility.get_translation_from_rotation_with_center(
            rot_for_corner,
            [+corner_to_remove.size[0] / 2, -corner_to_remove.size[1] / 2, 0],
        )
        if i == 1:
            translation_to_apply[0] = -translation_to_apply[0]
            t = gate.geometry.utility.get_translation_from_rotation_with_center(
                rot_for_corner,
                [-corner_to_remove.size[0] / 2, -corner_to_remove.size[1] / 2, 0],
            )
        translation_to_apply += t
        below_top_jaw_box = subtract_volumes(
            below_top_jaw_box,
            corner_to_remove,
            translation_to_apply,
            rot_for_corner.as_matrix(),
        )
    left_edge_box_to_remove = volumes.BoxVolume(name="left_edge_box_to_remove_" + side)
    left_edge_box_to_remove.size = [12.05 * mm, 59 * mm, 10 * mm + 10 * um]
    size_box = left_edge_box_to_remove.size
    # [- 154 * mm / 2 + size_box[0] / 2, below_top_jaw_box_size[1] / 2 - 89 * mm - size_box[1] / 2,
    #  jaw_z / 2 - 22 * mm - 10 * mm / 2]
    below_top_jaw_box = subtract_volumes(
        below_top_jaw_box,
        left_edge_box_to_remove,
        [
            -154 * mm / 2 + size_box[0] / 2,
            -below_top_jaw_box_size[1] / 2 + 80 * mm + size_box[1] / 2,
            0,
        ],
        np.identity(3),
    )
    sim.volume_manager.add_volume(
        below_top_jaw_box, "truncated_" + below_top_jaw_box.name
    )
    below_top_jaw_box.material = "mat_leaf"
    below_top_jaw_box.mother = jaw_box.name
    below_top_jaw_box.color = [0.8, 0.4, 0.65, 0.6]

    for i in range(2):
        trap_to_complete_jaw = sim.volume_manager.add_volume(
            "Trap", "trap_to_complete_jaw_" + side + "_" + str(i)
        )
        alpha = np.arctan(0.5 * 20 / 20.8775)
        if i == 1:
            alpha = -alpha
        trap_g4_param(
            trap_to_complete_jaw,
            1 * nm / 2,
            20 * mm / 2,
            1 * nm / 2,
            20 * mm / 2,
            20.8775 / 2 * mm,
            20.8775 / 2 * mm,
            10 * mm / 2,
            alpha1=alpha,
            alpha2=alpha,
        )

        trap_to_complete_jaw.color = [0.8, 0.4, 0.65, 0.6]
        trap_to_complete_jaw.mother = jaw_box.name
        if i == 0:
            trap_to_complete_jaw.translation = [
                jaw_x / 2 - (210 - 194) / 2 * mm - 20 / 2 * mm - 10 / 2 * mm + 1 * nm,
                jaw_y / 2 - (109.5 - 84.822) * mm - 20.8775 / 2 * mm,
                jaw_z / 2 - 22 * mm - 10 * mm / 2,
            ]
        if i == 1:
            trap_to_complete_jaw.translation = [
                -(
                    jaw_x / 2
                    - (210 - 194) / 2 * mm
                    - 20 / 2 * mm
                    - 10 / 2 * mm
                    + 1 * nm
                ),
                jaw_y / 2 - (109.5 - 84.822) * mm - 20.8775 / 2 * mm,
                jaw_z / 2 - 22 * mm - 10 * mm / 2,
            ]
        trap_to_complete_jaw.color = [0.8, 0.4, 0.65, 0.6]
        trap_to_complete_jaw.material = "mat_leaf"

    for i in range(2):
        traps_edge_jaw = sim.volume_manager.add_volume(
            "Trap", "traps_edge_jaw_" + side + "_" + str(i)
        )
        alpha = -np.arctan(0.5 * 6.324 / 10.64)
        if i == 1:
            alpha = -alpha

        # alpha = 0
        trap_g4_param(
            traps_edge_jaw,
            (1 * nm) / 2,
            (57.5 * mm) / 2,
            (1 * nm) / 2,
            (57.5 * mm) / 2,
            21.28 * mm / 2 * mm,
            21.28 * mm / 2 * mm,
            15 * mm / 2,
            alpha1=alpha,
            alpha2=alpha,
        )
        traps_edge_jaw.color = [0.8, 0.4, 0.65, 0.6]
        traps_edge_jaw.mother = jaw_box.name
        traps_edge_jaw.translation = np.array(
            [
                jaw_x / 2
                - (210 - 194) / 2 * mm
                - 20 * mm
                - 0.5 * 21.28 * mm * np.tan(alpha)
                - 57.5 * mm / 2,
                jaw_y / 2 - (109.5 - 84.822) * mm - 20.8775 * mm - 21.28 * mm / 2,
                jaw_z / 2 - 32 * mm - 15 * mm / 2,
            ]
        )
        if i == 1:
            traps_edge_jaw.translation[0] = (
                -jaw_x / 2
                + (210 - 194) / 2 * mm
                + 20 * mm
                - 0.5 * 21.28 * mm * np.tan(alpha)
                + 57.5 * mm / 2
            )
        rot_angle = np.arctan(87.964 / ((200 - 32) / 2))
        if i == 1:
            rot_angle = -rot_angle
        rot = Rotation.from_euler("z", rot_angle * 180 / np.pi, degrees=True)
        rot_inversion = Rotation.from_euler(
            "xz", [180, -180 + rot_angle * 180 / np.pi], degrees=True
        )
        vec_translation_for_rotation = np.array(
            [57.5 * mm / 2 + 0.5 * 21.28 * mm * np.tan(alpha), 21.28 * mm / 2, 0]
        )
        if i == 1:
            vec_translation_for_rotation[0] = (
                -57.5 * mm / 2 + 0.5 * 21.28 * mm * np.tan(alpha)
            )
        t = gate.geometry.utility.get_translation_from_rotation_with_center(
            rot, vec_translation_for_rotation
        )
        traps_edge_jaw.translation += t
        translation_for_overlap_correction = np.array([32.19 * um, -32.19 * um, 0])
        if i == 1:
            translation_for_overlap_correction[0] = -translation_for_overlap_correction[
                0
            ]
        traps_edge_jaw.translation += np.array(translation_for_overlap_correction)
        if i == 0:
            traps_edge_jaw.rotation = rot.as_matrix()
        else:
            traps_edge_jaw.rotation = rot_inversion.as_matrix()
        traps_edge_jaw.material = "mat_leaf"

    band_box_to_add_left_side = sim.volume_manager.add_volume(
        "Box", "band_box_to_add_left_side_" + side
    )
    band_box_to_add_left_side.size = [20 * mm, 10 * mm, 10 * mm]
    band_box_to_add_left_side.translation = [
        -194 * mm / 2 + band_box_to_add_left_side.size[0] / 2,
        -jaw_y / 2 + 70 * mm + band_box_to_add_left_side.size[1] / 2,
        jaw_z / 2 - 22 * mm - 10 * mm / 2,
    ]
    band_box_to_add_left_side.mother = jaw_box.name
    band_box_to_add_left_side.color = [0.8, 0.4, 0.65, 0.6]
    band_box_to_add_left_side.material = "mat_leaf"

    if side == "left":
        jaw_box.translation += np.array([0, -jaw_y / 2, 0])
    if side == "right":
        rot_jaw = Rotation.from_euler("Z", 180, degrees=True).as_matrix()
        jaw_box.translation += np.array([0, jaw_y / 2, 0])
        jaw_box.rotation = rot_jaw

    return jaw_box


def retrieve_offset_data_to_apply(
    offset_type: object, collimation_type: object
) -> object:
    mlc_offset_thales_to_radiation_field = [
        [
            -149.19,
            -144.56,
            -135.25,
            -125.90,
            -116.51,
            -107.06,
            -97.57,
            -88.03,
            -78.45,
            -68.81,
            -59.12,
            -49.39,
            -39.61,
            -29.78,
            -19.9,
            -9.98,
            0,
            10.02,
            20.10,
            30.22,
            40.39,
            50.61,
            60.88,
            71.19,
            81.55,
            91.97,
            102.43,
            112.94,
            123.49,
            134.1,
            144.75,
            155.44,
            166.19,
            176.98,
            187.92,
            198.71,
            209.64,
        ],
        [
            -5.53,
            -5.17,
            -4.47,
            -3.82,
            -3.22,
            -2.67,
            -2.16,
            -1.70,
            -1.29,
            -0.93,
            -0.61,
            -0.35,
            -0.13,
            0.04,
            0.16,
            0.23,
            0.25,
            0.23,
            0.15,
            0.03,
            -0.14,
            -0.36,
            -0.63,
            -0.94,
            -1.31,
            -1.72,
            -2.18,
            -2.69,
            -3.25,
            -3.85,
            -4.51,
            -5.20,
            -5.95,
            -6.74,
            -7.58,
            -8.47,
            -9.4,
        ],
    ]

    jaws_offset_thales_to_radiation_field = [
        [
            -127.57,
            -117.93,
            -108.26,
            -98.56,
            -88.83,
            -79.08,
            -69.29,
            -59.48,
            -49.64,
            -39.77,
            -29.87,
            -19.94,
            -9.99,
            -0,
            10.01,
            20.06,
            30.13,
            40.23,
            50.36,
            60.52,
            70.71,
            80.92,
            91.17,
            101.44,
            111.74,
            122.07,
            132.43,
            142.82,
            153.23,
            163.68,
            174.15,
            184.64,
            195.17,
            205.72,
        ],
        [
            -2.18,
            -1.82,
            -1.49,
            -1.19,
            -0.92,
            -0.68,
            -0.46,
            -0.28,
            -0.12,
            0.01,
            0.11,
            0.18,
            0.23,
            0.24,
            0.22,
            0.18,
            0.11,
            0.01,
            -0.13,
            -0.28,
            -0.47,
            -0.69,
            -0.93,
            -1.21,
            -1.51,
            -1.84,
            -2.20,
            -2.59,
            -3,
            -3.44,
            -3.91,
            -4.41,
            -4.94,
            -5.49,
        ],
    ]

    mlc_offset_light_field_to_radiation_field = [
        [
            -149.19,
            -144.56,
            -135.25,
            -125.90,
            -116.51,
            -107.06,
            -97.57,
            -88.03,
            -78.45,
            -68.81,
            -59.12,
            -49.39,
            -39.61,
            -29.78,
            -19.9,
            -9.98,
            0,
            10.02,
            20.10,
            30.22,
            40.39,
            50.61,
            60.88,
            71.19,
            81.55,
            91.97,
            102.43,
            112.94,
            123.49,
            134.1,
            144.75,
            155.44,
            166.19,
            176.98,
            187.92,
            198.71,
            209.64,
        ],
        [
            0.28,
            0.28,
            0.28,
            0.27,
            0.27,
            0.27,
            0.27,
            0.27,
            0.27,
            0.26,
            0.26,
            0.26,
            0.26,
            0.26,
            0.26,
            0.25,
            0.25,
            0.25,
            0.25,
            0.25,
            0.25,
            0.25,
            0.25,
            0.25,
            0.25,
            0.25,
            0.24,
            0.24,
            0.24,
            0.24,
            0.24,
            0.24,
            0.24,
            0.24,
            0.24,
            0.24,
            0.24,
        ],
    ]

    jaws_offset_light_field_to_radiation_field = [
        [
            -127.57,
            -117.93,
            -108.26,
            -98.56,
            -88.83,
            -79.08,
            -69.29,
            -59.48,
            -49.64,
            -39.77,
            -29.87,
            -19.94,
            -9.99,
            -0,
            10.01,
            20.06,
            30.13,
            40.23,
            50.36,
            60.52,
            70.71,
            80.92,
            91.17,
            101.44,
            111.74,
            122.07,
            132.43,
            142.82,
            153.23,
            163.68,
            174.15,
            184.64,
            195.17,
            205.72,
        ],
        [
            0.25,
            0.25,
            0.25,
            0.25,
            0.25,
            0.25,
            0.25,
            0.24,
            0.24,
            0.24,
            0.24,
            0.24,
            0.24,
            0.24,
            0.24,
            0.24,
            0.24,
            0.24,
            0.24,
            0.24,
            0.24,
            0.24,
            0.23,
            0.23,
            0.23,
            0.23,
            0.23,
            0.23,
            0.23,
            0.23,
            0.23,
            0.23,
            0.23,
            0.23,
        ],
    ]

    if collimation_type == "jaw":
        if offset_type == "from thales":
            return (
                jaws_offset_thales_to_radiation_field[0],
                jaws_offset_thales_to_radiation_field[1],
            )
        elif offset_type == "from light field":
            return (
                jaws_offset_light_field_to_radiation_field[0],
                jaws_offset_light_field_to_radiation_field[1],
            )

    elif collimation_type == "mlc":
        if offset_type == "from thales":
            return (
                mlc_offset_thales_to_radiation_field[0],
                mlc_offset_thales_to_radiation_field[1],
            )
        elif offset_type == "from light field":
            return (
                mlc_offset_light_field_to_radiation_field[0],
                mlc_offset_thales_to_radiation_field[1],
            )


def define_pos_jaws_rectangular_field(y_field, sad=1000):
    mm = g4_units.mm
    center_jaws = 470.5 * mm
    jaws_height = 77 * mm
    center_curve_jaws = center_jaws - (jaws_height / 2 - 35 * mm)

    jaws_y_aperture = y_field / 2 * center_curve_jaws / sad
    pos_y_jaws = np.array(
        [-int(10 * jaws_y_aperture) / 10, int(10 * jaws_y_aperture) / 10]
    )
    return pos_y_jaws


def define_pos_mlc_jaws_rectangular_field(
    mlc, x_field, y_field, sad=1000, opposite_leaf_gap=0
):
    mm = g4_units.mm

    center_mlc = 349.3 * mm
    center_jaws = 470.5 * mm
    jaws_height = 77 * mm
    center_curve_mlc = center_mlc - 7.5 * mm
    leaf_width = 1.76 * mm + 0.09 * mm
    center_curve_jaws = center_jaws - (jaws_height / 2 - 35 * mm)

    #### way to correct the thales correction at the isocenter of an offset to obtain the light field ####
    #### Not used here since we directly have the offset to apply from thales to obtain the radiation field

    # R_mlc = 170 * mm
    # R_jaws = 135 * mm
    # theta_x = np.arctan(0.5 * x_field / sad)
    # theta_y = np.arctan(0.5 * y_field / sad)

    # mlc_x_aperture = (x_field / 2) * (center_curve_mlc + R_mlc * np.sin(theta_x)) / sad - R_mlc * (1 - np.cos(theta_x))
    # jaws_y_aperture = (y_field / 2) * (center_curve_jaws + R_jaws * np.sin(theta_y)) / sad - R_jaws * (1 - np.cos(theta_y))
    ###############################################

    mlc_position, mlc_offset = retrieve_offset_data_to_apply("from thales", "mlc")
    jaw_position, jaw_offset = retrieve_offset_data_to_apply("from thales", "jaw")

    f_offset_mlc = scipy.interpolate.interp1d(mlc_position, mlc_offset, kind="cubic")
    f_offset_jaw = scipy.interpolate.interp1d(jaw_position, jaw_offset, kind="cubic")

    mlc_x_aperture = (center_curve_mlc / sad) * (
        x_field / 2 - f_offset_mlc(x_field / 2)
    )
    jaws_y_aperture = (center_curve_jaws / sad) * (
        y_field / 2 - f_offset_jaw(y_field / 2)
    )

    max_field_jaw = np.sqrt(110**2 - (jaws_height / 2) ** 2)
    max_y_aperture = (110 * mm - max_field_jaw) + jaws_y_aperture
    y_position_for_opening = max_y_aperture * 349.3 / (470.5 - (jaws_height / 2))

    leaves_position_y = mlc.translation[:, 1]
    leaves_ID = np.arange(160)
    leaves_to_open = leaves_ID[
        (leaves_position_y > -(y_position_for_opening + leaf_width / 2))
        & (leaves_position_y < y_position_for_opening + leaf_width / 2)
    ]
    leaves_to_open_left = leaves_to_open[leaves_to_open < 80]
    leaves_to_open_right = leaves_to_open[leaves_to_open >= 80]

    opposite_leaf_gap = opposite_leaf_gap * center_mlc / sad
    pos_x_leaves = np.zeros(160)
    pos_x_leaves[0:80] -= opposite_leaf_gap / 2
    pos_x_leaves[80:160] += opposite_leaf_gap / 2
    pos_x_leaves[leaves_to_open_left] = -mlc_x_aperture
    pos_x_leaves[leaves_to_open_right] = mlc_x_aperture
    pos_x_leaves = np.array(10 * pos_x_leaves, dtype=int) / 10
    pos_y_jaws = np.array(
        [-int(10 * jaws_y_aperture) / 10, int(10 * jaws_y_aperture) / 10]
    )

    return pos_x_leaves, pos_y_jaws


def field(mlc, jaws, pos_x_leaves, pos_y_jaws):
    mlc.translation[:, 0] += pos_x_leaves
    for i, jaw in enumerate(jaws):
        jaw.translation[1] += pos_y_jaws[i]


def convert_degree_minuts_to_decimal_degree(degree, minuts):
    decimal_degree = degree + 1 / 60 * minuts
    return decimal_degree


def set_rectangular_field(mlc, jaws, x_field, y_field, sad=1000, opposite_leaf_gap=0):
    pos_x_leaves, pos_y_jaws = define_pos_mlc_jaws_rectangular_field(
        mlc, x_field, y_field, sad, opposite_leaf_gap
    )

    field(mlc, jaws, pos_x_leaves, pos_y_jaws)


def linac_rotation(sim, linac_name, angles, cp_id="all_cp"):
    gantry_angle = angles[0]
    collimation_angle = angles[1]
    linac = sim.volume_manager.get_volume(linac_name)
    rotations = []
    translations = []
    if cp_id == "all_cp":
        nb_cp_id = len(gantry_angle)
        cp_id = np.arange(0, nb_cp_id, 1)
    translation_linac = linac.translation
    for n in cp_id:
        rot = Rotation.from_euler(
            "YZ", [gantry_angle[n], collimation_angle[n]], degrees=True
        )
        t = gate.geometry.utility.get_translation_from_rotation_with_center(
            rot, [0, 0, -translation_linac[2]]
        )
        rot = rot.as_matrix()
        rotations.append(rot)
        translations.append(np.array(t) + translation_linac)
    linac.add_dynamic_parametrisation(translation=translations, rotation=rotations)


def translation_from_sad(sim, linac_name, translation, sad=1000):
    linac = sim.volume_manager.get_volume(linac_name)
    linac.translation = np.array(translation)
    linac.translation[2] += sad - linac.size[2] / 2


def rotation_around_user_point(
    sim, linac_name, str_axes, angle_list, point_coordinate=[0, 0, 0]
):
    point_coordinate = np.array(point_coordinate)
    linac = sim.volume_manager.get_volume(linac_name)
    translation = linac.translation
    rot = Rotation.from_euler(str_axes, angle_list, degrees=True)
    new_translation = gate.geometry.utility.get_translation_from_rotation_with_center(
        rot, point_coordinate - np.array(translation)
    )
    linac.translation = translation + new_translation
    linac.rotation = rot.as_matrix()


def jaw_dynamic_translation(jaw, jaw_positions, side, cp_id="all_cp", sad=1000):
    mm = g4_units.mm
    translations = []
    rotations = []
    jaw_height = 77 * mm
    center_jaw = 470.5 * mm
    center_curve_jaw = center_jaw - (jaw_height / 2 - 35 * mm)
    rot_jaw = Rotation.from_euler("Z", 180, degrees=True).as_matrix()
    if cp_id == "all_cp":
        nb_cp_id = len(jaw_positions)
        cp_id = np.arange(0, nb_cp_id, 1)
    for n in cp_id:
        jaw_position, jaw_offset = retrieve_offset_data_to_apply("from thales", "jaw")
        f_offset_jaw = scipy.interpolate.interp1d(
            jaw_position, jaw_offset, kind="cubic"
        )
        if side == "left":
            jaw_pos = -jaw_positions[n]
        if side == "right":
            jaw_pos = jaw_positions[n]
        jaws_y_aperture = (center_curve_jaw / sad) * (jaw_pos - f_offset_jaw(jaw_pos))
        if side == "left":
            jaws_y_aperture = -jaws_y_aperture
            rotations.append(np.identity(3))
        if side == "right":
            rotations.append(rot_jaw)
        jaw_translation = jaw.translation + np.array([0, jaws_y_aperture, 0])
        translations.append(jaw_translation)
    jaw.add_dynamic_parametrisation(translation=translations, rotation=rotations)


def mlc_leaves_dynamic_translation(
    mlc, leaves_position, cp_id="all_cp", sad=1000, only_return_position=False
):
    mm = g4_units.mm
    center_mlc = 349.3 * mm
    center_curve_mlc = center_mlc - 7.5 * mm
    nb_leaves = 160
    motion_leaves_t = []
    motion_leaves_r = []
    mlc_leaves_name = []

    mlc_position, mlc_offset = retrieve_offset_data_to_apply("from thales", "mlc")
    f_offset_mlc = scipy.interpolate.interp1d(mlc_position, mlc_offset, kind="cubic")

    for i in range(nb_leaves):
        mlc_leaves_name.append(mlc.name + "_rep_" + str(i))

    for i in range(nb_leaves):
        motion_leaves_t.append([])
        motion_leaves_r.append([])

    translation_mlc = []
    if cp_id == "all_cp":
        nb_cp_id = len(leaves_position)
        cp_id = np.arange(0, nb_cp_id, 1)
    for n in cp_id:
        mlc_x_aperture_left = (center_curve_mlc / sad) * (
            leaves_position[n] - f_offset_mlc(-leaves_position[n])
        )
        mlc_x_aperture_right = (center_curve_mlc / sad) * (
            leaves_position[n] - f_offset_mlc(leaves_position[n])
        )
        mlc_x_aperture = np.array(
            mlc_x_aperture_left[:80].tolist() + mlc_x_aperture_right[80:].tolist()
        )
        for i in range(len(mlc_x_aperture)):
            translation_mlc.append(np.copy(mlc.translation[i]))
            motion_leaves_t[i].append(
                translation_mlc[i] + np.array([mlc_x_aperture[i], 0, 0])
            )
            motion_leaves_r[i].append(mlc.rotation[i])
    for i in range(nb_leaves):
        mlc.add_dynamic_parametrisation(
            repetition_index=i, translation=motion_leaves_t[i]
        )


def set_linac_head_motion(
    sim, linac_name, jaws, mlc, rt_plan_parameters, cp_id="all_cp", sad=1000
):
    leaves_position = rt_plan_parameters["leaves"]
    jaw_1_positions = rt_plan_parameters["jaws 1"]
    jaw_2_positions = rt_plan_parameters["jaws 2"]
    linac_head_positions = rt_plan_parameters["gantry angle"]
    collimation_rotation = rt_plan_parameters["collimation angle"]
    mlc_leaves_dynamic_translation(mlc, leaves_position, cp_id, sad)
    jaw_dynamic_translation(jaws[0], jaw_1_positions, "left", cp_id, sad)
    jaw_dynamic_translation(jaws[1], jaw_2_positions, "right", cp_id, sad)
    linac_rotation(sim, linac_name, [linac_head_positions, collimation_rotation], cp_id)


def get_patient_translation_and_rotation_from_RT_plan_to_IEC(rt_plan_parameters, img):
    isocenter = rt_plan_parameters["isocenter"][0]
    image = itk.imread(img)
    offset = np.array(image.GetOrigin())
    dim = np.array(image.GetLargestPossibleRegion().GetSize())
    spacing = np.array(image.GetSpacing())

    # IMAGE ROTATION ACCORDING TO IEC 61217

    size = (dim - 1) * spacing
    center = offset + size / 2
    rotation_to_apply = Rotation.from_euler("X", -90, degrees=True).as_matrix()

    isocenter_vector = isocenter - center
    rotated_isocenter_vector = np.dot(rotation_to_apply, isocenter_vector)

    isocenter_rot_img = center + rotated_isocenter_vector
    translation_to_apply = center - isocenter_rot_img

    return (translation_to_apply, rotation_to_apply)


def set_time_intervals_from_rtplan(sim, rt_plan_parameters, cp_id="all_cp"):
    MU = rt_plan_parameters["weight"]
    sec = gate.g4_units.s
    sim.run_timing_intervals = []
    if cp_id == "all_cp":
        nb_cp_id = len(MU)
        cp_id = np.arange(0, nb_cp_id, 1)
    for i in cp_id:
        if i == 0:
            sim.run_timing_intervals.append([0, MU[0] * sec])
        else:
            sim.run_timing_intervals.append(
                [np.sum(MU[:i]) * sec, np.sum(MU[: i + 1]) * sec]
            )
