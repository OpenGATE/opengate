import gam
import gam_g4 as g4
import numpy as np


def get_vol_translation(vol):
    if 'translation' not in vol:
        gam.fatal(f'Cannot find the key "translation" into this volume: {vol}')
    try:
        t = g4.G4ThreeVector(vol.translation[0],
                             vol.translation[1],
                             vol.translation[2])
        return t
    except Exception as e:
        s = f'Cannot convert the translation {vol.translation} to a 3D vector. Exception is: '
        s += str(e)
        gam.fatal(s)


def is_rotation_matrix(R):
    """
    https://stackoverflow.com/questions/53808503/how-to-test-if-a-matrix-is-a-rotation-matrix
    """
    # square matrix test
    if R.ndim != 2 or R.shape[0] != R.shape[1]:
        return False
    should_be_identity = np.allclose(R.dot(R.T), np.identity(R.shape[0], np.float))
    should_be_one = np.allclose(np.linalg.det(R), 1)
    return should_be_identity and should_be_one


def get_vol_rotation(vol):
    if 'rotation' not in vol:
        gam.fatal(f'Cannot find the key "rotation" into this volume: {vol}')
    rot = vol.rotation
    if not is_rotation_matrix(rot):
        gam.fatal(f'The matrix for the volume "{vol.name}" is not a rotation matrix (not orthogonal): \n{rot}')
    try:
        r = g4.HepRep3x3(rot[0, 0], rot[0, 1], rot[0, 2],
                         rot[1, 0], rot[1, 1], rot[1, 2],
                         rot[2, 0], rot[2, 1], rot[2, 2])
    except Exception as e:
        s = f'Cannot convert the rotation {rot} to a 3x3 matrix. Exception is: '
        s += str(e)
        gam.fatal(s)
    a = g4.G4RotationMatrix()
    a.set(r)
    return a


def get_vol_transform(vol):
    translation = get_vol_translation(vol)
    rotation = get_vol_rotation(vol)
    transform = g4.G4Transform3D(rotation, translation)
    return transform


def get_translation_from_rotation_with_center(rot, center):
    center = np.array(center)
    t = rot.apply(-center) + center
    return t
