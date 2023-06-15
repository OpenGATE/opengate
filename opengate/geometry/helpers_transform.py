import opengate as gate
import opengate_core as g4
import numpy as np
from scipy.spatial.transform import Rotation
from box import Box

"""
A rotation matrix (3x3) can be represented by:
- G4RotationMatrix in module opengate_core
- np.array in module numpy
- Rotation in module scipy.spatial.transform

With scipy and np:
- rot_np = rot_scipy.as_matrix()
- rot_scipy = Rotation.from_matrix(rot_np)

With G4RotationMatrix
- rot_g4 = rot_np_as_g4(rot_np)
- rot_np = rot_g4_as_np(rot_g4)

Also for G4ThreeVector
- v_np = vec_g4_as_np(v_g4)
- v_g4 = vec_np_as_g4(v_np)
"""


def is_rotation_matrix(R):
    """
    https://stackoverflow.com/questions/53808503/how-to-test-if-a-matrix-is-a-rotation-matrix
    """
    # square matrix test
    if R.ndim != 2 or R.shape[0] != R.shape[1]:
        return False
    should_be_identity = np.allclose(R.dot(R.T), np.identity(R.shape[0], np.float_))
    should_be_one = np.allclose(np.linalg.det(R), 1)
    return should_be_identity and should_be_one


def vec_np_as_g4(v):
    return g4.G4ThreeVector(v[0], v[1], v[2])


def vec_g4_as_np(v):
    vnp = np.zeros(3)
    vnp[0] = v.x
    vnp[1] = v.y
    vnp[2] = v.z
    return vnp


def rot_np_as_g4(rot):
    if not is_rotation_matrix(rot):
        gate.fatal(f"This matrix is not a rotation matrix (not orthogonal): \n{rot}")
    try:
        r = g4.HepRep3x3(
            rot[0, 0],
            rot[0, 1],
            rot[0, 2],
            rot[1, 0],
            rot[1, 1],
            rot[1, 2],
            rot[2, 0],
            rot[2, 1],
            rot[2, 2],
        )
    except Exception as e:
        s = f"Cannot convert the rotation {rot} to a 3x3 matrix. Exception is: "
        s += str(e)
        gate.fatal(s)
    a = g4.G4RotationMatrix()
    a.set(r)
    return a


def rot_g4_as_np(rot):
    r = np.zeros(shape=(3, 3))
    r[0, 0] = rot.xx()
    r[0, 1] = rot.xy()
    r[0, 2] = rot.xz()
    r[1, 0] = rot.yx()
    r[1, 1] = rot.yy()
    r[1, 2] = rot.yz()
    r[2, 0] = rot.zx()
    r[2, 1] = rot.zy()
    r[2, 2] = rot.zz()
    if not is_rotation_matrix(r):
        gate.fatal(f"The G4 matrix is not a rotation matrix (not orthogonal): \n{rot}")
    return r


def get_vol_g4_translation(vol):
    # the input can be a class UserInfo or a Box
    if isinstance(vol, gate.UserInfo):
        vd = vol.__dict__
    else:
        vd = vol
    if "translation" not in vd:
        gate.fatal(f'Cannot find the key "translation" into this volume: {vol}')
    try:
        t = vec_np_as_g4(vol.translation)
        return t
    except Exception as e:
        s = f"Cannot convert the translation {vol.translation} to a 3D vector. Exception is: "
        s += str(e)
        gate.fatal(s)


def get_vol_g4_rotation(vol):
    # the input can be a class UserInfo or a Box
    if isinstance(vol, gate.UserInfo):
        vd = vol.__dict__
    else:
        vd = vol
    if "rotation" not in vd:
        gate.fatal(f'Cannot find the key "rotation" into this volume: {vol}')
    return rot_np_as_g4(vol.rotation)


def get_vol_g4_transform(vol):
    translation = get_vol_g4_translation(vol)
    rotation = get_vol_g4_rotation(vol)
    return g4.G4Transform3D(rotation, translation)


def get_translation_from_rotation_with_center(rot, center):
    center = np.array(center)
    t = rot.apply(-center) + center
    # note: apply is the same than rot.as_matrix().dot()
    return t


def get_transform_orbiting(position, axis, angle_deg):
    p = np.array(position)
    rot = Rotation.from_euler(axis, angle_deg, degrees=True)
    t = rot.apply(p)
    return t, rot.as_matrix()


def get_transform_world_to_local(vol_name):
    # cumulated translation and rotation
    ctr = [0, 0, 0]
    crot = Rotation.identity().as_matrix()
    first = True
    while vol_name != gate.__world_name__:
        pv = g4.G4PhysicalVolumeStore.GetInstance().GetVolume(vol_name, False)
        tr = vec_g4_as_np(pv.GetObjectTranslation())
        rot = rot_g4_as_np(pv.GetObjectRotation())
        if first:
            ctr = tr
            crot = rot
            first = False
        else:
            crot = np.matmul(rot, crot)
            ctr = rot.dot(ctr) + tr
        vol_name = pv.GetMotherLogical().GetName()

    return ctr, crot


def repeat_ring(name, start_deg, nb, translation, axis=[0, 0, 1]):
    """
    Build a repeater for the given volume name, according to a ring rotation.
        start_deg *must* be in degrees
        nb is the number of repeated positions
        translation is the initial translation of the volume according to the center
        axis is the rotation axis
    The output is a dict (Box) of all positions (name + translation + rotation) than can be set
    to the 'repeat' member of a volume.
    """
    le = []
    step = np.pi * 2 / nb
    angle = np.deg2rad(start_deg)
    for i in range(nb):
        e = Box()
        e.name = f"{name}_{i}"
        r = Rotation.from_rotvec(angle * np.array(axis))
        e.rotation = r.as_matrix()
        e.translation = r.apply(translation)
        le.append(e)
        angle += step
    return le


def repeat_array(name, size, translation):
    start = [-(x - 1) * y / 2.0 for x, y in zip(size, translation)]
    return repeat_array_start(name, start, size, translation)


def repeat_array_start(name, start, size, translation):
    le = [
        {
            "name": f"{name}_{x}_{y}_{z}",
            "rotation": Rotation.identity().as_matrix(),
            "translation": [
                start[0] + translation[0] * x,
                start[1] + translation[1] * y,
                start[2] + translation[2] * z,
            ],
        }
        for x, y, z in np.ndindex(size[0], size[1], size[2])
    ]
    return le


def build_param_repeater(
    sim, mother_name, repeated_vol_name, size, translation, rot=None
):
    vol = sim.get_volume_user_info(repeated_vol_name)
    vol.build_physical_volume = False
    param = sim.add_volume("RepeatParametrised", f"{repeated_vol_name}_param")
    param.mother = mother_name
    param.repeated_volume_name = repeated_vol_name
    param.rotation = rot
    param.linear_repeat = size
    param.translation = translation
    param.start = [-(x - 1) * y / 2.0 for x, y in zip(size, translation)]
    param.offset_nb = 1
    param.offset = [0, 0, 0]
    return param


def volume_orbiting_transform(axis, start, end, n, initial_t, initial_rot):
    angle = start
    step_angle = (end - start) / n
    translations = []
    rotations = []
    for r in range(n):
        irot = Rotation.from_matrix(initial_rot)
        t, rot = gate.get_transform_orbiting(initial_t, axis, angle)
        rot = Rotation.from_matrix(rot)
        rot = rot * irot
        translations.append(t)
        r = gate.rot_np_as_g4(rot.as_matrix())
        rotations.append(r)
        angle += step_angle
    return translations, rotations
