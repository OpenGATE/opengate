from anytree import RenderTree
import numpy as np
from scipy.spatial.transform import Rotation

import opengate_core as g4
from ..definitions import __world_name__
from ..exception import fatal

"""
http://geant4-userdoc.web.cern.ch/geant4-userdoc/UsersGuides/ForApplicationDeveloper/html/Detector/Geometry/geomSolids.html#constructed-solid-geometry-csg-solids
"""


def box_add_size(box, thickness):
    box.size = [x + thickness for x in box.size]


def cons_add_size(cons, thickness):
    cons.rmax1 += thickness / 2
    cons.rmax2 += thickness / 2
    cons.dz += thickness


def translate_point_to_volume(simulation, volume, top, x):
    """

    Consider the point x in the current volume and return the coordinate of x in the top volume
    (that must be an ancestor).
    Translation only, do not consider rotation.
    """
    while volume.name != top:
        x += volume.translation
        volume = simulation.volume_manager.volumes[volume.mother]
    return x


def render_tree(tree, geometry, world_name):
    """
    Print a tree of volume
    """
    s = ""
    for pre, fill, node in RenderTree(tree[world_name]):
        v = geometry[node.name]
        s += f"{pre}{node.name} {v.type_name} {v.material}\n"

    # remove last break line
    return s[:-1]


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
    should_be_identity = np.allclose(R.dot(R.T), np.identity(R.shape[0], np.float64))
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
        fatal(f"This matrix is not a rotation matrix (not orthogonal): \n{rot}")
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
        fatal(s)
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
        fatal(f"The G4 matrix is not a rotation matrix (not orthogonal): \n{rot}")
    return r


def ensure_is_g4_translation(translation):
    if isinstance(translation, g4.G4ThreeVector):
        return translation
    else:
        return vec_np_as_g4(translation)


def ensure_is_g4_rotation(rotation):
    if isinstance(rotation, g4.G4RotationMatrix):
        return rotation
    else:
        return rot_np_as_g4(rotation)


def ensure_is_g4_transform(
    translation=(0, 0, 0), rotation=Rotation.identity().as_matrix()
):
    return g4.G4Transform3D(
        ensure_is_g4_rotation(rotation), ensure_is_g4_translation(translation)
    )


def get_translation_from_rotation_with_center(rot, center):
    center = np.array(center)
    t = rot.apply(-center) + center
    # note: apply is the same than rot.as_matrix().dot()
    return t


def get_transform_orbiting(initial_position, axis, angle_deg):
    angle_deg = list([angle_deg])
    translations = []
    rotations = []
    for ang in angle_deg:
        rot = Rotation.from_euler(axis, ang, degrees=True)
        t = rot.apply(np.array(initial_position))
        translations.append(t)
        rotations.append(rot.as_matrix())
    if len(translations) > 1:
        return translations, rotations
    else:
        return translations[0], rotations[0]


def get_transform_world_to_local(volume, repetition_index=None):
    """Calculate the rotation and translation needed
    to transform from the world reference frame
    into the local reference frame of this volume.

    If repetition_index is None:
    Returns two lists, the first with translation vectors,
    the second with rotation matrices. Each list entry corresponds
    to one physical volume of the Gate volume, i.e. one repetition.
    For non-repeated volumes, the lists will contain one item only.

    If repetition_index is a valid integer,
    return the translation and rotation for that repeated physical volume only.
    """

    volume._request_volume_tree_update()

    cumulative_translation = []
    cumulative_rotation = []
    # Note: access translation and rotation via user_info dictionary
    for i in range(volume.number_of_repetitions):
        ctr = volume.translation_list[i]
        crot = volume.rotation_list[i]
        for vol in volume.ancestor_volumes[::-1]:
            crot = np.matmul(vol.rotation_list[0], crot)
            ctr = vol.rotation_list[0].dot(ctr) + vol.translation_list[0]
        cumulative_translation.append(ctr)
        cumulative_rotation.append(crot)

    if repetition_index is None:
        return cumulative_translation, cumulative_rotation
    else:
        return (
            cumulative_translation[repetition_index],
            cumulative_rotation[repetition_index],
        )


def get_transform_world_to_local_old(vol_name):
    # cumulated translation and rotation
    ctr = [0, 0, 0]
    crot = Rotation.identity().as_matrix()
    first = True
    # FIXME for parallel world
    while vol_name != __world_name__:
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

        if pv.GetMotherLogical() == None:
            vol_name = __world_name__
        else:
            vol_name = pv.GetMotherLogical().GetName()

    return ctr, crot


def get_circular_repetition(
    number_of_repetitions,
    first_translation,
    angular_step_deg="auto_full_circle",
    start_angle_deg=0.0,
    additional_rotation=Rotation.identity().as_matrix(),
    axis=(0, 0, 1),
):
    """Generate translations and rotations to repeat volumes in a circle.

    This helper function generates translations and rotations for a volume to be repeated in a circle,
    e.g. in a PET ring. The returned lists with translations and rotations can be used as input to the translation
    and rotation parameter of any repeatable volume in Gate.

    Args:
        number_of_repetitions (int) : How many times should the volume be repeated?
        first_translation (3-vector) : Where should the first copy of the volume be placed (wrt. to the mother volume)?
        angular_step_deg (float, optional) : The angular step in degrees between subsequent repetitions.
            Accepts a number or two special arguments, 'auto_full_circle' and 'auto_half_circle',
            to determine the angular step automatically. Default: 'auto_full_circle'
        start_angle_deg (int, optional) : The angle at which the repetition starts.
            The first volume copy is placed at `first_translation` and then rotated by `start_angle_deg`.
            Default: 0.
        additional_rotation (3x3 rotation matrix, optional) : Additional rotation to be applied to all copies,
            e.g. if the volume is tilted. Default: 3x3 identity.
        axis (3-vector, optional) : The axis (in the mother's frame of reference) around which
            the circular repetition is performed. Default: [0, 0, 1], i.e. z-axis, circle in the x-y-plane.

    Returns:
        list : A list of translation vectors, one for each repetition.
        list : A list of rotation matrices, one for each repetition.
    """
    if not is_rotation_matrix(additional_rotation):
        fatal(f"Invalid rotation matrix 'additional_rotation': {additional_rotation}.")

    if angular_step_deg == "auto_full_circle":
        angular_step_deg = 360.0 / number_of_repetitions
    elif angular_step_deg == "auto_half_circle":
        angular_step_deg = 180.0 / number_of_repetitions
    elif not isinstance(angular_step_deg, (int, float)):
        fatal(
            f"The input variable 'angular_step_deg' should be a number (int, float) "
            f"or one of the following terms 'auto_full_circle', 'auto_half_circle'. "
            f"Received: {angular_step_deg} which is of type {type(angular_step_deg).__name__}. "
        )
    angular_step_rad = np.deg2rad(angular_step_deg)
    start_angle_rad = np.deg2rad(start_angle_deg)
    translations = []
    rotations = []
    for angle in np.arange(
        start_angle_rad,
        start_angle_rad + number_of_repetitions * angular_step_rad,
        angular_step_rad,
    ):
        rot = Rotation.from_rotvec(angle * np.array(axis))
        rotations.append(rot.as_matrix().dot(additional_rotation))
        translations.append(rot.apply(first_translation))

    return translations, rotations


def get_grid_repetition(size, spacing, start=None, return_lut=False):
    """Generate a list of 3-vectors to be used as 'translation' parameter of a repeated volume.

    Args:
        size (list, np.ndarray) : 3-item list or numpy array specifying the number of repetitions
            along the axes x, y, z.
        spacing (list, np.ndarray) : 3-item list or numpy array specifying the spacing along the axes x, y, z
            between the translation vectors.
        start (optional): Optional 3-item list or numpy array specifying the first translation vector on the grid.
            If not provided, the grid is centered around (0,0,0).
        return_lut (bool, optional) : If true, the functions also returns a dictionary mapping copy index
            to the respective translation vector for later reference.

    Returns:
        list : A list of translations vectors.
        dict : (Optional) A dictionary mapping copy index to the respective translation vector. Only if `return_lut` is `True`.
    """
    if not len(size) == 3:
        fatal(
            f"Input `size` must be a 3-item list or numpy array. Found length {len(size)}."
        )
    if not len(spacing) == 3:
        fatal(
            f"Input `spacing` must be a 3-item list or numpy array. Found length {len(spacing)}."
        )

    size = np.asarray(size)
    spacing = np.asarray(spacing)

    if start is None:
        start = -(size - 1) * spacing / 2.0
    translations = [start + spacing * np.array(pos) for pos in np.ndindex(*size)]

    if return_lut is True:
        lut = dict([(i, tr) for i, tr in enumerate(translations)])
        return translations, lut
    else:
        return translations


def volume_orbiting_transform(axis, start, end, n, initial_t, initial_rot):
    angle = start
    step_angle = (end - start) / n
    translations = []
    rotations = []
    for r in range(n):
        irot = Rotation.from_matrix(initial_rot)
        t, rot = get_transform_orbiting(initial_t, axis, angle)
        rot = Rotation.from_matrix(rot)
        rot = rot * irot
        translations.append(t)
        r = rot.as_matrix()
        rotations.append(r)
        angle += step_angle
    return translations, rotations
