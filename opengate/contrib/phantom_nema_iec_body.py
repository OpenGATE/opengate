import opengate as gate
import opengate_core as g4
from anytree import LevelOrderIter
import numpy as np
import math

iec_plastic = "IEC_PLASTIC"
water = "G4_WATER"
iec_lung = "G4_LUNG_ICRP"

# colors
red = [1, 0.7, 0.7, 0.8]
blue = [0.5, 0.5, 1, 0.8]
gray = [0.5, 0.5, 0.5, 1]


def create_material():
    n = g4.G4NistManager.Instance()
    elems = ["C", "H", "O"]
    nbAtoms = [5, 8, 2]
    gcm3 = gate.g4_units("g/cm3")
    n.ConstructNewMaterialNbAtoms("IEC_PLASTIC", elems, nbAtoms, 1.18 * gcm3)


def add_phantom(simulation, name="iec", check_overlap=False):
    # unit
    cm = gate.g4_units("cm")
    mm = gate.g4_units("mm")
    deg = gate.g4_units("deg")
    create_material()

    # check overlap only for debug
    simulation.g4_check_overlap_flag = check_overlap

    # Outside structure
    iec, _, _ = add_iec_structure(simulation, name)
    iec.material = iec_plastic
    iec.color = red

    # Inside space for the water, same than the shell, with 3 mm less
    interior, top_interior, c = add_iec_structure(
        simulation, f"{name}_interior", 3 * mm
    )
    interior.mother = iec.name
    interior.material = water
    interior.color = blue

    # central tube in iec_plastic
    add_central_cylinder(simulation, name, top_interior)

    # spheres
    add_all_spheres(simulation, name, c)

    return iec


def add_iec_structure(simulation, name, thickness=0.0):
    cm = gate.g4_units("cm")
    nm = gate.g4_units("nm")
    deg = gate.g4_units("deg")

    # top
    top_shell = simulation.new_solid("Tubs", f"{name}_top_shell")
    top_shell.rmax = 15 * cm - thickness
    top_shell.rmin = 0
    top_shell.dz = 21.4 * cm / 2 - thickness
    top_shell.sphi = 0 * deg
    top_shell.dphi = 180 * deg

    # Lower left half of phantom
    bottom_left_shell = simulation.new_solid("Tubs", f"{name}_bottom_left_shell")
    bottom_left_shell.rmax = 8 * cm - thickness
    bottom_left_shell.rmin = 0
    bottom_left_shell.dz = 21.4 * cm / 2 - thickness
    bottom_left_shell.sphi = 270 * deg
    bottom_left_shell.dphi = 90 * deg

    # Lower right half of phantom
    bottom_right_shell = simulation.new_solid("Tubs", f"{name}_bottom_right_shell")
    gate.copy_user_info(bottom_left_shell, bottom_right_shell)
    bottom_right_shell.sphi = 180 * deg
    bottom_right_shell.dphi = 90 * deg

    # slightly move the volumes to avoid large surface overlap during the union
    # unsure if it worth it
    tiny = 1 * nm

    # Bottom box
    # length = Z = sup-inf = is 21.4
    # bottom radius = Y = ant-post = 8 cm
    # width = X = left-right = in between the two bottom rounded  = 14 * cm
    # X total is 14 + 8 + 8 = 30 cm (main radius is 15cm)
    bottom_central_shell = simulation.new_solid("Box", f"{name}_bottom_central_shell")
    bottom_central_shell.size = [14 * cm + tiny, 8 * cm, 21.4 * cm]
    bottom_central_shell.size[1] -= thickness
    bottom_central_shell.size[2] -= 2 * thickness
    c = -bottom_central_shell.size[1] / 2 + tiny

    # union
    shell = gate.solid_union(top_shell, bottom_central_shell, [0, c, 0])
    shell = gate.solid_union(shell, bottom_left_shell, [7 * cm - tiny, tiny, 0])
    shell = gate.solid_union(shell, bottom_right_shell, [-7 * cm + tiny, tiny, 0])
    iec = simulation.add_volume_from_solid(shell, name)

    return iec, top_shell, c


def add_central_cylinder(sim, name, top_interior):
    # unit
    cm = gate.g4_units("cm")
    deg = gate.g4_units("deg")

    cc = sim.add_volume("Tubs", f"{name}_center_cylinder")
    cc.mother = f"{name}_interior"
    cc.rmax = 2.5 * cm
    cc.rmin = 2.1 * cm
    cc.dz = top_interior.dz
    cc.sphi = 0 * deg
    cc.dphi = 360 * deg
    cc.material = iec_plastic
    cc.translation = [0, 3.5 * cm, 0]
    cc.color = red

    # central tube lung material
    hscc = sim.add_volume("Tubs", f"{name}_center_cylinder_hole")
    hscc.mother = f"{name}_interior"
    hscc.rmax = 2.1 * cm
    hscc.rmin = 0 * cm
    hscc.dz = top_interior.dz
    hscc.material = iec_lung
    hscc.translation = [0, 3.5 * cm, 0]
    hscc.color = gray


def add_all_spheres(simulation, name, c):
    # unit
    cm = gate.g4_units("cm")
    mm = gate.g4_units("mm")

    # all spheres
    v = f"{name}_interior"
    iec_add_sphere(
        simulation,
        name,
        v,
        10 * mm,
        1 * mm,
        3 * mm,
        [2.86 * cm, c + 2.39633 * cm, 3.7 * cm],
    )
    iec_add_sphere(
        simulation,
        name,
        v,
        13 * mm,
        1 * mm,
        3 * mm,
        [-2.86 * cm, c + 2.39633 * cm, 3.7 * cm],
    )
    iec_add_sphere(
        simulation, name, v, 17 * mm, 1 * mm, 3 * mm, [-5.72 * cm, 3.5 * cm, 3.7 * cm]
    )
    iec_add_sphere(
        simulation,
        name,
        v,
        22 * mm,
        1 * mm,
        3.5 * mm,
        [-2.86 * cm, 8.45367 * cm, 3.7 * cm],
    )
    iec_add_sphere(
        simulation,
        name,
        v,
        28 * mm,
        1 * mm,
        3.5 * mm,
        [2.86 * cm, 8.45367 * cm, 3.7 * cm],
    )
    iec_add_sphere(
        simulation, name, v, 37 * mm, 1 * mm, 3.5 * mm, [5.72 * cm, 3.5 * cm, 3.7 * cm]
    )


def add_phantom_old(simulation, name="iec"):
    cm = gate.g4_units("cm")
    mm = gate.g4_units("mm")
    deg = gate.g4_units("deg")
    create_material()

    # colors
    white = [1, 1, 1, 1]
    red = [1, 0, 0, 1]
    blue = [0, 0, 1, 1]
    lightblue = [0.4, 0.4, 1, 1]
    gray = [0.5, 0.5, 0.5, 1]
    green = [0, 1, 0, 1]

    # material
    simulation.g4_check_overlap_flag = False

    # main volume
    iec = simulation.add_volume("Tubs", name)
    iec.rmax = 17 * cm
    iec.rmin = 0 * cm
    iec.dz = 22 * cm / 2
    iec.sphi = 0 * deg
    iec.dphi = 360 * deg
    iec.material = "G4_AIR"
    iec.color = white

    # ---------------------
    # Upper Half of Phantom

    # Upper outer shell
    uos = simulation.add_volume("Tubs", f"{name}_upperadius_outer_shell")
    uos.mother = name
    uos.rmax = 15 * cm
    uos.rmin = 14.7 * cm
    uos.dz = 21.4 * cm / 2
    uos.sphi = 0 * deg
    uos.dphi = 180 * deg
    uos.material = iec_plastic
    uos.translation = [0, -3.5 * cm, 0]

    # Upper interior
    ui = simulation.add_volume("Tubs", f"{name}_upper_interior")
    gate.copy_user_info(uos, ui)
    ui.rmax = uos.rmin
    ui.rmin = 0 * cm
    ui.material = "G4_WATER"

    # iec_plastic Shell Surrounding Lung Insert (Center Cylinder)
    cc = simulation.add_volume("Tubs", f"{name}_center_cylinder")
    cc.mother = f"{name}_upper_interior"
    cc.rmax = 2.5 * cm
    cc.rmin = 2.1 * cm
    cc.dz = uos.dz
    cc.sphi = 0 * deg
    cc.dphi = 360 * deg
    cc.material = iec_plastic
    cc.translation = [0, 3.5 * cm, 0]

    # Hollow Space in Central Cylinder
    hscc = simulation.add_volume("Tubs", f"{name}_center_cylinder_hole")
    hscc.mother = f"{name}_upper_interior"
    hscc.rmax = 2.1 * cm
    hscc.rmin = 0 * cm
    hscc.dz = uos.dz
    hscc.material = "G4_LUNG_ICRP"
    hscc.translation = [0, 3.5 * cm, 0]

    # Exterior Shell of Upper Half of Phantom

    # Top Side
    ts = simulation.add_volume("Tubs", f"{name}_top_shell")
    ts.mother = name
    ts.rmax = 15 * cm
    ts.rmin = 0 * cm
    ts.dz = 0.3 * cm / 2
    ts.sphi = 0 * deg
    ts.dphi = 180 * deg
    ts.translation = [0, -3.5 * cm, 10.85 * cm]
    ts.material = iec_plastic

    # bottom side
    bs = simulation.add_volume("Tubs", f"{name}_bottom_shell")
    gate.copy_user_info(ts, bs)
    bs.translation[2] *= -1

    # Lower left half of phantom
    blos = simulation.add_volume("Tubs", f"{name}_bottom_left_outer_shell")
    blos.mother = name
    blos.rmax = 8 * cm
    blos.rmin = 7.7 * cm
    blos.dz = 21.4 * cm / 2
    blos.sphi = 270 * deg
    blos.dphi = 90 * deg
    blos.translation = [7 * cm, -3.5 * cm, 0]
    blos.material = iec_plastic

    # Lower Left interior
    lli = simulation.add_volume("Tubs", f"{name}_lower_left_interior")
    gate.copy_user_info(blos, lli)
    lli.rmax = blos.rmin
    lli.rmin = 0
    lli.material = "G4_WATER"

    # Lower right half of phantom
    bros = simulation.add_volume("Tubs", f"{name}_bottom_right_outer_shell")
    gate.copy_user_info(blos, bros)
    bros.sphi = 180 * deg
    bros.translation[0] *= -1

    # Lower right interior
    lri = simulation.add_volume("Tubs", f"{name}_lower_right_interior")
    gate.copy_user_info(lli, lri)
    lri.sphi = 180 * deg
    lri.translation[0] *= -1

    # Bottom box
    bb = simulation.add_volume("Box", f"{name}_bottom_box")
    bb.size = [14 * cm, 0.3 * cm, 21.4 * cm]
    bb.translation = [0, -11.35 * cm, 0]
    bb.mother = name
    bb.material = iec_plastic

    # Interior box
    ib = simulation.add_volume("Box", f"{name}_interior_box")
    gate.copy_user_info(bb, ib)
    ib.material = "G4_WATER"
    ib.size[1] = 7.7 * cm
    ib.translation[1] = -7.35 * cm

    # top shell
    ts2 = simulation.add_volume("Tubs", f"{name}_top_shell2")
    ts2.mother = name
    ts2.rmax = 8 * cm
    ts2.rmin = 0 * cm
    ts2.dz = 0.3 * cm / 2
    ts2.sphi = 270 * deg
    ts2.dphi = 90 * deg
    ts2.material = iec_plastic
    ts2.translation = [7 * cm, -3.5 * cm, 10.85 * cm]

    # top shell
    ts3 = simulation.add_volume("Tubs", f"{name}_top_shell3")
    gate.copy_user_info(ts2, ts3)
    ts3.sphi = 180 * deg
    ts3.translation[0] *= -1

    # top shell
    ts4 = simulation.add_volume("Box", f"{name}_top_shell4")
    ts4.mother = name
    ts4.size = [14 * cm, 8 * cm, 0.3 * cm]
    ts4.material = iec_plastic
    ts4.translation = [0 * cm, -7.5 * cm, 10.85 * cm]

    # bottom shell
    bs2 = simulation.add_volume("Tubs", f"{name}_bottom_shell2")
    gate.copy_user_info(ts2, bs2)
    bs2.translation[2] *= -1

    # bottom shell
    bs3 = simulation.add_volume("Tubs", f"{name}_bottom_shell3")
    gate.copy_user_info(ts3, bs3)
    bs3.translation[2] *= -1

    # bottom shell
    bs4 = simulation.add_volume("Box", f"{name}_bottom_shell4")
    gate.copy_user_info(ts4, bs4)
    bs4.translation[2] *= -1

    # spheres
    iec_add_sphere(
        simulation,
        name,
        f"{name}_interior_box",
        10 * mm,
        1 * mm,
        3 * mm,
        [2.86 * cm, 2.39633 * cm, 3.7 * cm],
    )
    iec_add_sphere(
        simulation,
        name,
        f"{name}_interior_box",
        13 * mm,
        1 * mm,
        3 * mm,
        [-2.86 * cm, 2.39633 * cm, 3.7 * cm],
    )
    iec_add_sphere(
        simulation,
        name,
        f"{name}_upper_interior",
        17 * mm,
        1 * mm,
        3 * mm,
        [-5.72 * cm, 3.5 * cm, 3.7 * cm],
    )
    iec_add_sphere(
        simulation,
        name,
        f"{name}_upper_interior",
        22 * mm,
        1 * mm,
        3.5 * mm,
        [-2.86 * cm, 8.45367 * cm, 3.7 * cm],
    )
    iec_add_sphere(
        simulation,
        name,
        f"{name}_upper_interior",
        28 * mm,
        1 * mm,
        3.5 * mm,
        [2.86 * cm, 8.45367 * cm, 3.7 * cm],
    )
    iec_add_sphere(
        simulation,
        name,
        f"{name}_upper_interior",
        37 * mm,
        1 * mm,
        3.5 * mm,
        [5.72 * cm, 3.5 * cm, 3.7 * cm],
    )

    # colors
    uiv = simulation.volume_manager.volumes_user_info
    tree = gate.build_tree(uiv)
    vol = tree[iec.name]
    for v in LevelOrderIter(vol):
        vv = uiv[v.name]
        if vv.material == water:
            vv.color = blue
        if vv.material == iec_plastic:
            vv.color = lightblue
        if vv.material == iec_lung:
            vv.color = gray
        if "sphere" in vv.name:
            vv.color = green
        if "capillary" in vv.name:
            vv.color = green

    ts2.color = [1, 0, 0, 1]

    return iec


def iec_add_sphere(sim, name, vol, diam, sph_thick, cap_thick, position):
    mm = gate.g4_units("mm")
    cm = gate.g4_units("cm")
    d = f"{(diam / mm):.0f}mm"
    rad = diam / 2

    # interior sphere
    sph = sim.add_volume("Sphere", f"{name}_sphere_{d}")
    sph.mother = vol
    sph.translation = np.array(position)  # need to copy the array!
    sph.rmax = rad
    sph.rmin = 0
    sph.material = "G4_WATER"

    # outer sphere shell
    sphs = sim.add_volume("Sphere", f"{name}_sphere_shell_{d}")
    sphs.mother = vol
    sphs.translation = np.array(position)
    sphs.rmax = rad + sph_thick
    sphs.rmin = rad
    sphs.material = iec_plastic

    # capillary
    cap = sim.add_volume("Tubs", f"{name}_capillary_{d}")
    cap.mother = vol
    cap.translation = np.array(position)
    cap.material = "G4_WATER"
    cap.rmax = 0.25 * cm
    cap.rmin = 0 * cm
    # 21.4/2 = 10.7 interior height (top_interior)
    thickness = 0.3 * cm
    h = 21.4 / 2 * cm - thickness
    cap.dz = (h - 3.7 * cm - rad - sph_thick) / 2.0
    cap.translation[2] = 3.7 * cm + rad + sph_thick + cap.dz

    # capillary outer shell
    caps = sim.add_volume("Tubs", f"{name}_capillary_shell_{d}")
    gate.copy_user_info(cap, caps)
    caps.material = iec_plastic
    caps.rmax = cap_thick
    caps.rmin = cap.rmax


def add_spheres_sources(
    simulation,
    iec_name,
    src_name,
    spheres,
    activity_Bq_mL,
    verbose=False,
    source_type="GenericSource",
):
    spheres_diam = [10, 13, 17, 22, 28, 37]
    sources = []
    if spheres == "all":
        spheres = spheres_diam
    for sphere, ac in zip(spheres, activity_Bq_mL):
        if sphere in spheres_diam:
            if ac > 0:
                s = add_one_sphere_source(
                    simulation,
                    iec_name,
                    src_name,
                    float(sphere),
                    float(ac),
                    source_type=source_type,
                )
                sources.append(s)
        else:
            gate.fatal(
                f"Error the sphere of diameter {sphere} does not exists in {spheres_diam}"
            )
    # verbose ?
    if verbose:
        s = dump_spheres_activity(simulation, iec_name, src_name)
        t = compute_total_spheres_activity(simulation, iec_name, src_name)
        print(s)
        print(f"Total activity is {t} Bq")
    return sources


def compute_sphere_activity(simulation, iec_name, src_name, diam):
    mm = gate.g4_units("mm")
    cm3 = gate.g4_units("cm3")
    Bq = gate.g4_units("Bq")
    d = f"{(diam / mm):.0f}mm"
    sname = f"{src_name}_{iec_name}_{d}"
    if sname not in simulation.source_manager.user_info_sources:
        return None
    src = simulation.get_source_user_info(sname)
    vname = src.mother
    v = simulation.get_volume_user_info(vname)
    s = simulation.get_solid_info(v)
    ac = src.activity
    return ac / Bq, s.cubic_volume / cm3, sname, vname


def compute_total_spheres_activity(simulation, iec_name, src_name):
    spheres_diam = [10, 13, 17, 22, 28, 37]
    a = 0
    for diam in spheres_diam:
        ac, _, _, _ = compute_sphere_activity(simulation, iec_name, src_name, diam)
        a += ac
    return a


def dump_spheres_activity(simulation, iec_name, src_name):
    spheres_diam = [10, 13, 17, 22, 28, 37]
    out = ""
    i = 0
    for diam in spheres_diam:
        ac, vol, sname, vname = compute_sphere_activity(
            simulation, iec_name, src_name, diam
        )
        out += (
            f"{vname:<20} {sname:<20} "
            f"{vol:10.2f} mL   {ac:10.2f} Bq   {ac / vol:10.2f} Bq/mL\n"
        )
        i += 1
    return out[:-1]


def dump_bg_activity(simulation, iec_name, src_name):
    cm3 = gate.g4_units("cm3")
    Bq = gate.g4_units("Bq")
    BqmL = Bq / cm3
    sname = f"{iec_name}_{src_name}"
    if sname not in simulation.source_manager.user_info_sources:
        return
    src = simulation.get_source_user_info(sname)
    vname = src.mother
    v = simulation.get_volume_user_info(vname)
    s = simulation.get_solid_info(v)
    ac = src.activity
    out = (
        f"Volume = {vname:<20} Source = {sname:<20} "
        f"{s.cubic_volume / cm3:10.2f} mL   {ac / Bq:10.2f} Bq   {ac / s.cubic_volume / BqmL:10.2f} Bq/mL"
    )
    return out


def add_one_sphere_source(
    simulation, iec_name, src_name, diameter, activity_Bq_mL, source_type
):
    mm = gate.g4_units("mm")
    mL = gate.g4_units("mL")
    d = f"{(diameter / mm):.0f}mm"
    sname = f"{iec_name}_sphere_{d}"

    # compute volume in mL (and check)
    volume_ref = 4 / 3 * np.pi * np.power(diameter / mm / 2, 3) * 0.001
    v = simulation.get_volume_user_info(sname)
    s = simulation.get_solid_info(v)
    volume = s.cubic_volume / mL
    if not math.isclose(volume_ref, volume, rel_tol=1e-7):
        gate.fatal(
            f"Error while estimating the sphere volume {sname}: {volume_ref} vs {volume}"
        )

    source = simulation.add_source(source_type, f"{src_name}_{iec_name}_{d}")
    source.mother = sname
    # default values
    source.particle = "e+"
    source.energy.type = "F18"
    source.direction.type = "iso"
    source.activity = activity_Bq_mL * s.cubic_volume
    source.position.type = "sphere"
    source.position.radius = diameter / 2 * mm
    source.position.translation = [0, 0, 0]
    # print(f"Sphere volume {s.cubic_volume} cc")

    return source


def add_background_source(
    simulation, iec_name, src_name, activity_Bq_mL, verbose=False
):
    # source
    bg = simulation.add_source("GenericSource", f"{iec_name}_{src_name}")
    bg.mother = f"{iec_name}_interior"
    v = simulation.get_volume_user_info(bg.mother)
    s = simulation.get_solid_info(v)
    # (1 cm3 = 1 mL)
    bg.position.type = "box"
    bg.position.size = gate.get_volume_bounding_box_size(simulation, bg.mother)
    # this source is confined only within the mother volume, it does not include daughter volumes
    bg.position.confine = bg.mother
    bg.particle = "e+"
    bg.energy.type = "F18"
    bg.activity = activity_Bq_mL * s.cubic_volume
    # verbose ?
    if verbose:
        # print(f"Bg volume {s.cubic_volume} cc")
        s = dump_bg_activity(simulation, iec_name, src_name)
        print(s)
    return bg


def generate_pos_dir_one_sphere(center, radius, n, rs=np.random):
    """
    This function should be useful to generate conditional data for condGAN.
    It samples the position in a sphere and isotropic direction.
    The center/radius is the center and radius of the sphere
    A numpy array of (n,6) is returned.
    3 first = position
    3 last = direction
    """
    # uniform random vector of size n
    p = generate_pos_one_sphere(center, radius, n, rs)
    # direction
    v = gate.generate_isotropic_directions(n, rs=rs)
    # concat all
    return np.column_stack((p, v))


def generate_pos_one_sphere(center, radius, n, rs=np.random):
    # uniform random vector of size n
    u = rs.uniform(0, 1, size=n)
    r = np.cbrt((u * radius**3))
    phi = rs.uniform(0, 2 * np.pi, n)
    theta = np.arccos(rs.uniform(-1, 1, n))
    # position in cartesian
    x = r * np.sin(theta) * np.cos(phi) + center[0]
    y = r * np.sin(theta) * np.sin(phi) + center[1]
    z = r * np.cos(theta) + center[2]
    # concat all
    return np.column_stack((x, y, z))


def generate_pos_dir_spheres(centers, radius, n_samples, shuffle, rs=np.random):
    """
    This function generate conditional data for condGAN.
    It samples the position in several spheres, with isotropic direction.
    The center/radius are the center and radius of the spheres.
    n_samples is the number of samples per sphere, with a total of n.
    Samples can be shuffled (by default).
    A numpy array of (n,6) is returned.
    """
    cond = None
    for rad, center, n in zip(radius, centers, n_samples):
        # approximate -> if the last one we complete to reach n
        x = generate_pos_dir_one_sphere(center, rad, n, rs=rs)
        if cond is None:
            cond = x
        else:
            cond = np.vstack((cond, x))

    # shuffle
    if shuffle:
        # it seems that permutation is **much** faster than shuffle
        # (checked 2022/06/047 on osx)

        # https://github.com/numpy/numpy/issues/11013
        # sstart = time.time()
        # np.random.shuffle(cond)
        # send = time.time()
        # print(f'shuffle 1 {send - sstart:0.4f} sec')

        # sstart = time.time()
        cond = cond.take(rs.permutation(cond.shape[0]), axis=0)
        # send = time.time()
        # print(f'shuffle 2 {send - sstart:0.4f} sec')

    return cond


def generate_pos_spheres(centers, radius, n_samples, shuffle, rs=np.random):
    """
    Like generate_pos_dir_spheres, but position only
    """
    cond = None
    for rad, center, n in zip(radius, centers, n_samples):
        # approximate -> if the last one we complete to reach n
        x = generate_pos_one_sphere(center, rad, n, rs)
        if cond is None:
            cond = x
        else:
            cond = np.vstack((cond, x))

    # shuffle
    if shuffle:
        cond = cond.take(rs.permutation(cond.shape[0]), axis=0)

    return cond


def get_n_samples_from_ratio(n, ratio):
    """
    For a given proportion of activities (in ratio) and total number of particle n,
    compute the list of particle for each index.
    """
    i = 0
    total = 0
    n_samples = []
    for r in ratio:
        if i == len(ratio) - 1:
            # last one ?
            m = n - total
        else:
            m = int(round(n * r))
        n_samples.append(m)
        total += m
        i += 1
    return n_samples


def compute_sphere_centers_and_volumes(sim, name):
    spheres_diam = [10, 13, 17, 22, 28, 37]
    centers = []
    volumes = []
    mm = gate.g4_units("mm")
    for diam in spheres_diam:
        # retrieve the name of the sphere volume
        d = f"{(diam / mm):.0f}mm"
        vname = f"{name}_sphere_{d}"
        v = sim.get_volume_user_info(vname)
        s = sim.get_solid_info(v)
        # from the solid get the center position
        center = v.translation
        centers.append(center)
        # and the volume
        volumes.append(s.cubic_volume)
    return centers, volumes


def get_default_sphere_centers_and_volumes():
    """
    Global spheres centers in the phantom, to avoid using the phantom in same cases.
    Were computed with 10/06/2022 version.
    No translation. To be recomputed with compute_sphere_centers_and_volumes
    """
    centers = [
        [28.6, -16.0367, 37.0],
        [-28.6, -16.0367, 37.0],
        [-57.2, 35.0, 37.0],
        [-28.6, 84.5367, 37.0],
        [28.6, 84.5367, 37.0],
        [57.2, 35.0, 37.0],
    ]
    volumes = [
        523.5987755982989,
        1150.3465099894627,
        2572.4407845144424,
        5575.279762570685,
        11494.040321933857,
        26521.84878038063,
    ]
    return centers, volumes
