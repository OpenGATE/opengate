import json
import itk
import numpy as np
import math

from opengate import utility
import opengate.geometry.volumes
from opengate.utility import fatal, g4_units
from opengate.geometry.volumes import unite_volumes
from opengate.sources.gansources import generate_isotropic_directions

iec_plastic = "IEC_PLASTIC"
water = "G4_WATER"
iec_lung = "G4_LUNG_ICRP"

# colors
red = [1, 0.7, 0.7, 0.8]
blue = [0.5, 0.5, 1, 0.8]
gray = [0.5, 0.5, 0.5, 1]
transparent = [0, 0, 0, 0]


def create_material(simulation):
    elems = ["C", "H", "O"]
    nb_atoms = [5, 8, 2]
    gcm3 = g4_units.g_cm3
    simulation.volume_manager.material_database.add_material_nb_atoms(
        "IEC_PLASTIC", elems, nb_atoms, 1.18 * gcm3
    )


def add_iec_phantom(
    simulation,
    name="iec",
    check_overlap=False,
    sphere_starting_angle=False,
    toggle_sphere_order=False,
):
    # https://www.nuclemed.be/product.php?cat=102&prod=297 ???
    # unit
    mm = g4_units.mm
    create_material(simulation)

    # check overlap only for debug
    original_check_overlap_flag = simulation.check_volumes_overlap
    simulation.check_volumes_overlap = check_overlap

    # Outside structure
    iec, _, _ = add_iec_body(simulation, name)
    iec.material = iec_plastic
    iec.color = red

    # Inside space for the water, same as the shell, with 3 mm less
    thickness = 3 * mm
    thickness_z = 10 * mm
    interior, top_interior, _ = add_iec_body(
        simulation, f"{name}_interior", thickness, thickness_z
    )
    interior.mother = iec.name
    interior.material = water
    interior.color = blue

    # central tube in iec_plastic
    add_iec_central_cylinder(simulation, name, top_interior)

    # spheres
    add_iec_all_spheres(
        simulation, name, thickness_z, sphere_starting_angle, toggle_sphere_order
    )

    simulation.check_volumes_overlap = original_check_overlap_flag
    return iec


def add_iec_body(simulation, name, thickness=0.0, thickness_z=0.0):
    cm = g4_units.cm
    nm = g4_units.nm
    deg = g4_units.deg

    # total length
    length = 21.4 * cm

    # top
    top_shell = opengate.geometry.volumes.TubsVolume(name=f"{name}_top_shell")
    top_shell.rmax = 15 * cm - thickness
    top_shell.rmin = 0
    top_shell.dz = length / 2 - thickness_z
    top_shell.sphi = 0 * deg
    top_shell.dphi = 180 * deg

    # Lower left half of phantom
    bottom_left_shell = opengate.geometry.volumes.TubsVolume(
        name=f"{name}_bottom_left_shell"
    )
    bottom_left_shell.rmax = 8 * cm - thickness
    bottom_left_shell.rmin = 0
    bottom_left_shell.dz = length / 2 - thickness_z
    bottom_left_shell.sphi = 270 * deg
    bottom_left_shell.dphi = 90 * deg

    # Lower right half of phantom
    bottom_right_shell = opengate.geometry.volumes.TubsVolume(
        name=f"{name}_bottom_right_shell"
    )
    bottom_right_shell.configure_like(bottom_left_shell)
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
    bottom_central_shell = opengate.geometry.volumes.BoxVolume(
        name=f"{name}_bottom_central_shell"
    )
    bottom_central_shell.size = [14 * cm + tiny, 8 * cm, length]
    bottom_central_shell.size[1] -= thickness
    bottom_central_shell.size[2] -= 2 * thickness_z
    c = -bottom_central_shell.size[1] / 2 + tiny

    # union
    t_bc = unite_volumes(top_shell, bottom_central_shell, translation=[0, c, 0])
    t_bc_bl = unite_volumes(
        t_bc, bottom_left_shell, translation=[7 * cm - tiny, tiny, 0]
    )
    iec = unite_volumes(
        t_bc_bl,
        bottom_right_shell,
        translation=[-7 * cm + tiny, tiny, 0],
        new_name=name,
    )
    simulation.volume_manager.add_volume(iec)

    return iec, top_shell, c


def add_iec_central_cylinder(sim, name, top_interior):
    # unit
    cm = g4_units.cm
    deg = g4_units.deg

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


def add_iec_all_spheres(
    simulation, name, thickness_z, starting_angle=False, reverse_order=False
):
    """
    Starting angle : in deg. Indicate the (angle) position of the first smallest sphere.
    It is 180 deg by default.
    """
    # unit
    cm = g4_units.cm
    mm = g4_units.mm
    deg = g4_units.deg

    """
    The spheres are positioned in a circle every 60 deg.
    It can be modified.
    """
    v = f"{name}_interior"
    h_relative = 2.7 * cm
    r = 11.45367 * cm / 2
    ang = 360 / 6 * deg
    if starting_angle is False:
        starting_angle = 3 * ang
    a = starting_angle

    spheres_diam = [37, 28, 22, 17, 13, 10]
    if reverse_order:
        spheres_diam.reverse()

    for sd in spheres_diam:
        px = np.cos(a) * r
        py = np.sin(a) * r + 3.5 * cm
        add_iec_one_sphere(
            simulation,
            name,
            v,
            sd * mm,
            1 * mm,
            3.5 * mm,
            [px, py, h_relative],
            thickness_z,
        )
        a += ang


def add_iec_one_sphere(
    sim, name, vol, diam, sph_thick, cap_thick, position, thickness_z
):
    mm = g4_units.mm
    cm = g4_units.cm
    d = f"{(diam / mm):.0f}mm"
    rad = diam / 2
    h_relative = position[2]

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
    h = 21.4 / 2 * cm - thickness_z
    cap.dz = (h - h_relative - rad - sph_thick) / 2.0
    cap.translation[2] = h_relative + rad + sph_thick + cap.dz

    # capillary outer shell
    caps = sim.add_volume("Tubs", f"{name}_capillary_shell_{d}")
    caps.configure_like(cap)
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
            fatal(
                f"Error the sphere of diameter {sphere} does not exists in {spheres_diam}"
            )
    # verbose ?
    if verbose:
        s = dump_spheres_activity(simulation, iec_name, src_name)
        t = compute_total_spheres_activity(simulation, iec_name, src_name)
        print(s)
        print(f"Total activity is {t} Bq")
    return sources


def add_spheres_sources_equal(sim, iec_name, src_name, total_activity):
    Bq = g4_units.Bq
    sources = add_spheres_sources(sim, iec_name, src_name, "all", [1.0] * 6)
    t = compute_total_spheres_activity(sim, iec_name, src_name) * Bq
    for source in sources:
        # set the total activity to the asked number of particle
        source.activity = (source.activity / t) * total_activity
    return sources


def compute_sphere_activity(simulation, iec_name, src_name, diam):
    mm = g4_units.mm
    cm3 = g4_units.cm3
    Bq = g4_units.Bq
    d = f"{(diam / mm):.0f}mm"
    sname = f"{src_name}_{iec_name}_{d}"
    if sname not in simulation.source_manager.sources:
        return None, None, None, None
    src = simulation.source_manager.get_source(sname)
    vname = src.attached_to
    v = simulation.volume_manager.volumes[vname]
    s = v.solid_info
    ac = src.activity
    return ac / Bq, s.cubic_volume / cm3, sname, vname


def compute_total_spheres_activity(simulation, iec_name, src_name):
    spheres_diam = [10, 13, 17, 22, 28, 37]
    a = 0
    for diam in spheres_diam:
        ac, _, _, _ = compute_sphere_activity(simulation, iec_name, src_name, diam)
        if ac is None:
            continue
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
        if ac is None:
            continue
        out += (
            f"{vname:<20} {sname:<20} "
            f"{vol:10.2f} mL   {ac:10.2f} Bq   {ac / vol:10.2f} Bq/mL\n"
        )
        i += 1
    return out[:-1]


def dump_bg_activity(simulation, iec_name, src_name):
    cm3 = g4_units.cm3
    Bq = g4_units.Bq
    BqmL = Bq / cm3
    sname = f"{iec_name}_{src_name}"
    if sname not in simulation.source_manager.sources:
        return
    src = simulation.source_manager.get_source(sname)
    v = simulation.volume_manager.volumes[src.attached_to]
    s = v.solid_info
    ac = src.activity
    out = (
        f"Volume = {v.name:<20} Source = {sname:<20} "
        f"{s.cubic_volume / cm3:10.2f} mL   {ac / Bq:10.2f} Bq   {ac / s.cubic_volume / BqmL:10.2f} Bq/mL"
    )
    return out


def add_one_sphere_source(
    simulation, iec_name, src_name, diameter, activity_Bq_mL, source_type
):
    mm = g4_units.mm
    mL = g4_units.mL
    d = f"{(diameter / mm):.0f}mm"
    sname = f"{iec_name}_sphere_{d}"

    # compute volume in mL (and check)
    volume_ref = 4 / 3 * np.pi * np.power(diameter / mm / 2, 3) * 0.001
    v = simulation.volume_manager.volumes[sname]
    s = v.solid_info
    volume = s.cubic_volume / mL
    if not math.isclose(volume_ref, volume, rel_tol=1e-7):
        fatal(
            f"Error while estimating the sphere volume {sname}: {volume_ref} vs {volume}"
        )

    source = simulation.add_source(source_type, f"{src_name}_{iec_name}_{d}")
    source.attached_to = sname
    # default values
    source.particle = "e+"
    source.energy.type = "F18"
    source.direction.type = "iso"
    source.activity = activity_Bq_mL * s.cubic_volume
    source.position.type = "sphere"
    source.position.radius = diameter / 2 * mm
    source.position.translation = [0, 0, 0]
    return source


def add_central_cylinder_source(
    simulation, iec_name, src_name, activity_Bq_mL, verbose=False
):
    # source
    bg = simulation.add_source("GenericSource", f"{iec_name}_{src_name}")
    bg.attached_to = f"{iec_name}_center_cylinder_hole"
    v = simulation.volume_manager.volumes[bg.attached_to]
    s = v.solid_info
    # (1 cm3 = 1 mL)
    bg.position.type = "box"
    bg.position.size = simulation.volume_manager.volumes[
        bg.attached_to
    ].bounding_box_size
    # this source is confined only within the mother volume, it does not include daughter volumes
    # it is a tubs inside the box
    bg.position.confine = bg.attached_to
    bg.particle = "e+"
    bg.energy.type = "F18"
    bg.activity = activity_Bq_mL * s.cubic_volume
    # verbose ?
    if verbose:
        # print(f"Bg volume {s.cubic_volume} cc")
        s = dump_bg_activity(simulation, iec_name, src_name)
        print(s)
    return bg


def add_background_source(
    simulation, iec_name, src_name, activity_Bq_mL, verbose=False
):
    # source
    bg = simulation.add_source("GenericSource", f"{iec_name}_{src_name}")
    bg.attached_to = f"{iec_name}_interior"
    v = simulation.volume_manager.volumes[bg.attached_to]
    s = v.solid_info
    # (1 cm3 = 1 mL)
    bg.position.type = "box"
    bg.position.size = simulation.volume_manager.volumes[
        bg.attached_to
    ].bounding_box_size
    # this source is confined only within the mother volume, it does not include daughter volumes
    bg.position.confine = bg.attached_to
    bg.particle = "e+"
    bg.energy.type = "F18"
    bg.activity = activity_Bq_mL * s.cubic_volume
    # the confine procedure from G4 seems to be confused when using a boolean solid like {iec_name}_interior
    # (or I did understand correctly how it works)
    # so, we need to move the source for correct sampling of the volume
    mm = g4_units.mm
    bg.position.translation = [0, 35 * mm, 0]
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
    v = generate_isotropic_directions(n, rs=rs)
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


def compute_sphere_centers_and_volumes_OLD_NEVER_CALLED(sim, name):
    spheres_diam = [10, 13, 17, 22, 28, 37]
    centers = []
    volumes = []
    mm = g4_units.mm
    for diam in spheres_diam:
        # retrieve the name of the sphere volume
        d = f"{(diam / mm):.0f}mm"
        v = sim.volume_manager.volumes[f"{name}_sphere_{d}"]
        s = v.solid_info
        # from the solid get the center position
        center = v.translation
        centers.append(center)
        # and the volume
        volumes.append(s.cubic_volume)
    return centers, volumes


def get_default_sphere_centers_and_volumes_old():
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


def get_default_sphere_centers_and_volumes():
    """
    Global spheres centers in the phantom, to avoid using the phantom in same cases.
    Were computed with 23/08/2023 version.
    No translation. To be recomputed with compute_sphere_centers_and_volumes
    """
    centers = [
        [-28.634175, 84.59584593, 27.0],
        [28.634175, 84.59584593, 27.0],
        [57.26835, 35.0, 27.0],
        [28.634175, -14.59584593, 27.0],
        [-28.634175, -14.59584593, 27.0],
        [-57.26835, 35.0, 27.0],
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


def add_iec_phantom_vox_FIXME_TO_REMOVE(sim, name, image_filename, labels_filename):
    iec = sim.add_volume("Image", name)
    iec.image = image_filename
    iec.material = "IEC_PLASTIC"
    labels = utility.read_json_file(labels_filename)
    iec.voxel_materials = []
    create_material(sim)
    material_list = {}
    for l in labels:
        mat = "IEC_PLASTIC"
        if "capillary" in l:
            mat = "G4_WATER"
        if "cylinder_hole" in l:
            mat = "G4_AIR"
        if "world" in l:
            mat = "G4_AIR"
        if "interior" in l:
            mat = "G4_WATER"
        if "sphere" in l:
            mat = "G4_WATER"
        if "shell" in l:
            mat = "IEC_PLASTIC"
        material_list[l] = mat
        m = [labels[l]["label"], labels[l]["label"] + 1, mat]
        iec.voxel_materials.append(m)
    return iec, material_list


def create_iec_phantom_source_vox(
    image_filename, labels_filename, source_filename, activities=None
):
    if activities is None:
        activities = {
            "iec_sphere_10mm": 1.0,
            "iec_sphere_13mm": 1.0,
            "iec_sphere_17mm": 1.0,
            "iec_sphere_22mm": 1.0,
            "iec_sphere_28mm": 1.0,
            "iec_sphere_37mm": 1.0,
        }

    img = itk.imread(image_filename)
    labels = utility.read_json_file(labels_filename)
    img_arr = itk.GetArrayViewFromImage(img)

    for label in labels:
        l = labels[label]["label"]
        if "sphere" in label and "shell" not in label:
            img_arr[img_arr == l] = activities[label]
        else:
            img_arr[img_arr == l] = 0

    # The coordinate system is different from IEC analytical volume
    # 35mm should be added in Y
    itk.imwrite(img, source_filename)
