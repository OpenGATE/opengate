import gam_gate as gam
import gam_g4 as g4
from anytree import LevelOrderIter
import numpy as np
import math

iec_plastic = 'IEC_PLASTIC'
water = 'G4_WATER'
iec_lung = 'G4_LUNG_ICRP'


def create_material():
    n = g4.G4NistManager.Instance()
    elems = ['C', 'H', 'O']
    nbAtoms = [5, 8, 2]
    gcm3 = gam.g4_units('g/cm3')
    n.ConstructNewMaterial('IEC_PLASTIC', elems, nbAtoms, 1.18 * gcm3)


def add_phantom(simulation, name='iec'):
    # unit
    cm = gam.g4_units('cm')
    mm = gam.g4_units('mm')
    deg = gam.g4_units('deg')
    create_material()

    # colors
    red = [1, 0.7, 0.7, 0.8]
    blue = [0.5, 0.5, 1, 0.8]
    gray = [0.5, 0.5, 0.5, 1]

    # check overlap
    simulation.g4_check_overlap_flag = True  # FIXME for debug

    # top 
    top_shell = simulation.new_solid('Tubs', f'{name}_top_shell')
    top_shell.rmax = 15 * cm
    top_shell.rmin = 0
    top_shell.dz = 21.4 * cm / 2
    top_shell.sphi = 0 * deg
    top_shell.dphi = 180 * deg

    # Lower left half of phantom
    bottom_left_shell = simulation.new_solid('Tubs', f'{name}_bottom_left_shell')
    bottom_left_shell.rmax = 8 * cm
    bottom_left_shell.rmin = 0
    bottom_left_shell.dz = 21.4 * cm / 2
    bottom_left_shell.sphi = 270 * deg
    bottom_left_shell.dphi = 90 * deg

    # Lower right half of phantom
    bottom_right_shell = simulation.new_solid('Tubs', f'{name}_bottom_right_shell')
    gam.vol_copy(bottom_left_shell, bottom_right_shell)
    bottom_right_shell.sphi = 180 * deg

    # Bottom box
    bottom_central_shell = simulation.new_solid('Box', f'{name}_bottom_central_shell')
    bottom_central_shell.size = [14 * cm, 8 * cm, 21.4 * cm]

    c = -bottom_central_shell.size[1] / 2

    # union
    shell = gam.solid_union(top_shell, bottom_left_shell, [7 * cm, 0, 0])
    shell = gam.solid_union(shell, bottom_central_shell, [0, c, 0])
    shell = gam.solid_union(shell, bottom_right_shell, [-7 * cm, 0, 0])
    iec = simulation.add_volume_from_solid(shell, name)
    iec.material = iec_plastic
    iec.color = red

    # Inside space for the water, same than the shell, with 0.3cm less
    thickness = 0.3 * cm
    top_interior = simulation.new_solid('Tubs', f'{name}_top_interior')
    gam.vol_copy(top_shell, top_interior)
    top_interior.rmax -= thickness
    top_interior.dz -= thickness
    bottom_left_interior = simulation.new_solid('Tubs', f'{name}_bottom_left_interior')
    gam.vol_copy(bottom_left_shell, bottom_left_interior)

    bottom_left_interior.rmax -= thickness
    bottom_left_interior.dz -= thickness
    bottom_right_interior = simulation.new_solid('Tubs', f'{name}_bottom_right_interior')
    gam.vol_copy(bottom_left_interior, bottom_right_interior)
    bottom_right_interior.sphi = 180 * deg
    bottom_central_interior = simulation.new_solid('Box', f'{name}_bottom_central_interior')
    gam.vol_copy(bottom_central_shell, bottom_central_interior)
    bottom_central_interior.size[1] -= thickness
    bottom_central_interior.size[2] -= thickness

    # union
    interior = gam.solid_union(top_interior, bottom_left_interior, [7 * cm, 0, 0])
    interior = gam.solid_union(interior, bottom_central_interior, [0, c + thickness / 2, 0])
    interior = gam.solid_union(interior, bottom_right_interior, [-7 * cm, 0, 0])
    interior = simulation.add_volume_from_solid(interior, f'{name}_interior')
    interior.mother = name
    interior.material = water
    interior.color = blue
    interior.color = [1, 0, 0, 1]

    # central tube in iec_plastic
    cc = simulation.add_volume('Tubs', f'{name}_center_cylinder')
    cc.mother = f'{name}_interior'
    cc.rmax = 2.5 * cm
    cc.rmin = 2.1 * cm
    cc.dz = top_interior.dz
    cc.sphi = 0 * deg
    cc.dphi = 360 * deg
    cc.material = iec_plastic
    cc.translation = [0, 3.5 * cm, 0]
    cc.color = red

    # central tube lung material
    hscc = simulation.add_volume('Tubs', f'{name}_center_cylinder_hole')
    hscc.mother = f'{name}_interior'
    hscc.rmax = 2.1 * cm
    hscc.rmin = 0 * cm
    hscc.dz = top_interior.dz
    hscc.material = iec_lung
    hscc.translation = [0, 3.5 * cm, 0]
    hscc.color = gray

    # spheres
    v = f'{name}_interior'
    iec_add_sphere(simulation, name, v,
                   10 * mm, 1 * mm, 3 * mm, [2.86 * cm, c + 2.39633 * cm, 3.7 * cm])
    iec_add_sphere(simulation, name, v,
                   13 * mm, 1 * mm, 3 * mm, [-2.86 * cm, c + 2.39633 * cm, 3.7 * cm])
    iec_add_sphere(simulation, name, v,
                   17 * mm, 1 * mm, 3 * mm, [-5.72 * cm, 3.5 * cm, 3.7 * cm])
    iec_add_sphere(simulation, name, v,
                   22 * mm, 1 * mm, 3.5 * mm, [-2.86 * cm, 8.45367 * cm, 3.7 * cm])
    iec_add_sphere(simulation, name, v,
                   28 * mm, 1 * mm, 3.5 * mm, [2.86 * cm, 8.45367 * cm, 3.7 * cm])
    iec_add_sphere(simulation, name, v,
                   37 * mm, 1 * mm, 3.5 * mm, [5.72 * cm, 3.5 * cm, 3.7 * cm])

    return iec


def add_phantom_old(simulation, name='iec'):
    cm = gam.g4_units('cm')
    mm = gam.g4_units('mm')
    deg = gam.g4_units('deg')
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
    iec = simulation.add_volume('Tubs', 'iec')
    iec.rmax = 17 * cm
    iec.rmin = 0 * cm
    iec.dz = 22 * cm / 2
    iec.sphi = 0 * deg
    iec.dphi = 360 * deg
    iec.material = 'G4_AIR'
    iec.color = white

    # ---------------------
    # Upper Half of Phantom

    # Upper outer shell
    uos = simulation.add_volume('Tubs', 'upperadius_outer_shell')
    uos.mother = 'iec'
    uos.rmax = 15 * cm
    uos.rmin = 14.7 * cm
    uos.dz = 21.4 * cm / 2
    uos.sphi = 0 * deg
    uos.dphi = 180 * deg
    uos.material = iec_plastic
    uos.translation = [0, -3.5 * cm, 0]

    # Upper interior
    ui = simulation.add_volume('Tubs', 'upper_interior')
    gam.vol_copy(uos, ui)
    ui.rmax = uos.rmin
    ui.rmin = 0 * cm
    ui.material = 'G4_WATER'

    # iec_plastic Shell Surrounding Lung Insert (Center Cylinder)
    cc = simulation.add_volume('Tubs', 'center_cylinder')
    cc.mother = 'upper_interior'
    cc.rmax = 2.5 * cm
    cc.rmin = 2.1 * cm
    cc.dz = uos.dz
    cc.sphi = 0 * deg
    cc.dphi = 360 * deg
    cc.material = iec_plastic
    cc.translation = [0, 3.5 * cm, 0]

    # Hollow Space in Central Cylinder
    hscc = simulation.add_volume('Tubs', 'center_cylinder_hole')
    hscc.mother = 'upper_interior'
    hscc.rmax = 2.1 * cm
    hscc.rmin = 0 * cm
    hscc.dz = uos.dz
    hscc.material = 'G4_LUNG_ICRP'
    hscc.translation = [0, 3.5 * cm, 0]

    # Exterior Shell of Upper Half of Phantom

    # Top Side
    ts = simulation.add_volume('Tubs', 'top_shell')
    ts.mother = 'iec'
    ts.rmax = 15 * cm
    ts.rmin = 0 * cm
    ts.dz = 0.3 * cm / 2
    ts.sphi = 0 * deg
    ts.dphi = 180 * deg
    ts.translation = [0, -3.5 * cm, 10.85 * cm]
    ts.material = iec_plastic

    # bottom side
    bs = simulation.add_volume('Tubs', 'bottom_shell')
    gam.vol_copy(ts, bs)
    bs.translation[2] *= -1

    # Lower left half of phantom
    blos = simulation.add_volume('Tubs', 'bottom_left_outer_shell')
    blos.mother = 'iec'
    blos.rmax = 8 * cm
    blos.rmin = 7.7 * cm
    blos.dz = 21.4 * cm / 2
    blos.sphi = 270 * deg
    blos.dphi = 90 * deg
    blos.translation = [7 * cm, -3.5 * cm, 0]
    blos.material = iec_plastic

    # Lower Left interior
    lli = simulation.add_volume('Tubs', 'lower_left_interior')
    gam.vol_copy(blos, lli)
    lli.rmax = blos.rmin
    lli.rmin = 0
    lli.material = 'G4_WATER'

    # Lower right half of phantom
    bros = simulation.add_volume('Tubs', 'bottom_right_outer_shell')
    gam.vol_copy(blos, bros)
    bros.sphi = 180 * deg
    bros.translation[0] *= -1

    # Lower right interior
    lri = simulation.add_volume('Tubs', 'lower_right_interior')
    gam.vol_copy(lli, lri)
    lri.sphi = 180 * deg
    lri.translation[0] *= -1

    # Bottom box
    bb = simulation.add_volume('Box', 'bottom_box')
    bb.size = [14 * cm, 0.3 * cm, 21.4 * cm]
    bb.translation = [0, -11.35 * cm, 0]
    bb.mother = 'iec'
    bb.material = iec_plastic

    # Interior box
    ib = simulation.add_volume('Box', 'interior_box')
    gam.vol_copy(bb, ib)
    ib.material = 'G4_WATER'
    ib.size[1] = 7.7 * cm
    ib.translation[1] = -7.35 * cm

    # top shell
    ts2 = simulation.add_volume('Tubs', 'top_shell2')
    ts2.mother = 'iec'
    ts2.rmax = 8 * cm
    ts2.rmin = 0 * cm
    ts2.dz = 0.3 * cm / 2
    ts2.sphi = 270 * deg
    ts2.dphi = 90 * deg
    ts2.material = iec_plastic
    ts2.translation = [7 * cm, -3.5 * cm, 10.85 * cm]

    # top shell
    ts3 = simulation.add_volume('Tubs', 'top_shell3')
    gam.vol_copy(ts2, ts3)
    ts3.sphi = 180 * deg
    ts3.translation[0] *= -1

    # top shell
    ts4 = simulation.add_volume('Box', 'top_shell4')
    ts4.mother = 'iec'
    ts4.size = [14 * cm, 8 * cm, 0.3 * cm]
    ts4.material = iec_plastic
    ts4.translation = [0 * cm, -7.5 * cm, 10.85 * cm]

    # bottom shell
    bs2 = simulation.add_volume('Tubs', 'bottom_shell2')
    gam.vol_copy(ts2, bs2)
    bs2.translation[2] *= -1

    # bottom shell
    bs3 = simulation.add_volume('Tubs', 'bottom_shell3')
    gam.vol_copy(ts3, bs3)
    bs3.translation[2] *= -1

    # bottom shell
    bs4 = simulation.add_volume('Box', 'bottom_shell4')
    gam.vol_copy(ts4, bs4)
    bs4.translation[2] *= -1

    # spheres
    iec_add_sphere(simulation, name, 'interior_box',
                   10 * mm, 1 * mm, 3 * mm, [2.86 * cm, 2.39633 * cm, 3.7 * cm])
    iec_add_sphere(simulation, name, 'interior_box',
                   13 * mm, 1 * mm, 3 * mm, [-2.86 * cm, 2.39633 * cm, 3.7 * cm])
    iec_add_sphere(simulation, name, 'upper_interior',
                   17 * mm, 1 * mm, 3 * mm, [-5.72 * cm, 3.5 * cm, 3.7 * cm])
    iec_add_sphere(simulation, name, 'upper_interior',
                   22 * mm, 1 * mm, 3.5 * mm, [-2.86 * cm, 8.45367 * cm, 3.7 * cm])
    iec_add_sphere(simulation, name, 'upper_interior',
                   28 * mm, 1 * mm, 3.5 * mm, [2.86 * cm, 8.45367 * cm, 3.7 * cm])
    iec_add_sphere(simulation, name, 'upper_interior',
                   37 * mm, 1 * mm, 3.5 * mm, [5.72 * cm, 3.5 * cm, 3.7 * cm])

    # colors
    tree = simulation.volume_manager.build_tree()
    vol = tree[iec.name]
    for v in LevelOrderIter(vol):
        vv = simulation.volume_manager.user_info_volumes[v.name]
        if vv.material == water:
            vv.color = blue
        if vv.material == iec_plastic:
            vv.color = lightblue
        if vv.material == iec_lung:
            vv.color = gray
        if 'sphere' in vv.name:
            vv.color = green
        if 'capillary' in vv.name:
            vv.color = green

    ts2.color = [1, 0, 0, 1]

    return iec


def iec_add_sphere(sim, name, vol, diam, sph_thick, cap_thick, position):
    mm = gam.g4_units('mm')
    cm = gam.g4_units('cm')
    d = f'{(diam / mm):.0f}mm'
    rad = diam / 2

    # interior sphere
    sph = sim.add_volume('Sphere', f'{name}_sphere_{d}')
    sph.mother = vol
    sph.translation = np.array(position)  # need to copy the array!
    sph.rmax = rad
    sph.rmin = 0
    sph.material = 'G4_WATER'

    # outer sphere shell
    sphs = sim.add_volume('Sphere', f'{name}_sphere_shell_{d}')
    sphs.mother = vol
    sphs.translation = np.array(position)
    sphs.rmax = rad + sph_thick
    sphs.rmin = rad
    sphs.material = iec_plastic

    # capillary
    cap = sim.add_volume('Tubs', f'{name}_capillary_{d}')
    cap.mother = vol
    cap.translation = np.array(position)
    cap.material = 'G4_WATER'
    cap.rmax = 0.25 * cm
    cap.rmin = 0 * cm
    # 21.4/2 = 10.7 interior height (top_interior)
    thickness = 0.3 * cm
    h = 21.4 / 2 * cm - thickness
    cap.dz = (h - 3.7 * cm - rad - sph_thick) / 2.0
    cap.translation[2] = 3.7 * cm + rad + sph_thick + cap.dz

    # capillary outer shell
    caps = sim.add_volume('Tubs', f'{name}_capillary_shell_{d}')
    gam.vol_copy(cap, caps)
    caps.material = iec_plastic
    caps.rmax = cap_thick
    caps.rmin = cap.rmax


def add_spheres_sources(simulation, iec_name, src_name, spheres, activity_per_mL, weighted=False):
    spheres_diam = [10, 13, 17, 22, 28, 37]
    sources = []
    if spheres == 'all':
        spheres = spheres_diam
    for sphere, ac in zip(spheres, activity_per_mL):
        if sphere in spheres_diam:
            if ac > 0:
                s = add_one_sphere_source(simulation, iec_name, src_name, float(sphere), float(ac), weighted)
                sources.append(s)
        else:
            gam.fatal(f'Error the sphere of diameter {sphere} does not exists in {spheres_diam}')
    return sources


def add_one_sphere_source(simulation, iec_name, src_name, diameter, activity_per_mL, weighted):
    mm = gam.g4_units('mm')
    mL = gam.g4_units('mL')
    d = f'{(diameter / mm):.0f}mm'
    sname = f'{iec_name}_sphere_{d}'

    # compute volume in mL (and check)
    volume_ref = 4 / 3 * np.pi * np.power(diameter / mm / 2, 3) * 0.001
    v = simulation.get_volume_user_info(sname)
    s = simulation.get_solid_info(v)
    volume = s.cubic_volume / mL
    if not math.isclose(volume_ref, volume, rel_tol=1e-7):
        gam.fatal(f'Error while estimating the sphere volume {sname}: {volume_ref} vs {volume}')

    # print(f'volume {d} : {volume} mL')

    source = simulation.add_source('Generic', f'{src_name}_{iec_name}_{d}')
    source.particle = 'e+'
    source.energy.type = 'F18'
    source.direction.type = 'iso'
    if weighted:
        # source.activity = activity_per_mL
        # source.weight = volume
        ac = activity_per_mL * volume
        source.activity = ac / np.sqrt(volume)
        source.weight = source.activity
        print(diameter, volume, source.activity, source.weight, source.activity * source.weight)
    else:
        source.activity = activity_per_mL * volume
    source.position.type = 'sphere'
    source.position.radius = diameter / 2 * mm
    source.position.translation = [0, 0, 0]
    source.mother = sname

    '''
    # debug
    print('volume in mm3', volume / 0.001)
    print('volume in mL', volume)
    source.particle = 'gamma'
    source.energy.type = 'mono'  # 'F18'
    MeV = gam.g4_units('MeV')
    source.energy.mono = 5000 * MeV
    source.direction.type = 'momentum'
    source.direction.momentum = [0, 0, 1]
    print('act = ', source.activity / Bq)
    '''
    return source
