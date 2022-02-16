import itk
import numpy as np
from box import Box
import gam_gate as gam
from scipy.spatial.transform import Rotation


def update_image_py_to_cpp(py_img, cpp_img, copy_data=False):
    cpp_img.set_spacing(py_img.GetSpacing())
    cpp_img.set_origin(py_img.GetOrigin())
    # It is really a pain to convert GetDirection into
    # something that can be read by SetDirection !
    d = py_img.GetDirection().GetVnlMatrix().as_matrix()
    rotation = itk.GetArrayFromVnlMatrix(d)
    cpp_img.set_direction(rotation)
    if copy_data:
        arr = itk.array_view_from_image(py_img)
        cpp_img.from_pyarray(arr)


def itk_dir_to_rotation(dir):
    return itk.GetArrayFromVnlMatrix(dir.GetVnlMatrix().as_matrix())


def create_3d_image(dimension, spacing, pixel_type='float', fill_value=0):
    dim = 3
    pixel_type = itk.ctype(pixel_type)
    image_type = itk.Image[pixel_type, dim]
    img = image_type.New()
    region = itk.ImageRegion[dim]()
    size = np.array(dimension)
    region.SetSize(size.tolist())
    region.SetIndex([0, 0, 0])
    spacing = np.array(spacing)
    img.SetRegions(region)
    img.SetSpacing(spacing)
    # (default origin and direction)
    img.Allocate()
    img.FillBuffer(fill_value)
    return img


def create_image_like(like_image):
    info = get_image_info(like_image)
    img = create_3d_image(info.size, info.spacing)
    img.SetOrigin(info.origin)
    img.SetDirection(info.dir)
    return img


def get_image_info(img):
    info = Box()
    info.size = np.array(itk.size(img)).astype(int)
    info.spacing = np.array(img.GetSpacing())
    info.origin = np.array(img.GetOrigin())
    info.dir = img.GetDirection()
    return info


def get_cpp_image(cpp_image):
    arr = cpp_image.to_pyarray()
    image = itk.image_from_array(arr)
    image.SetOrigin(cpp_image.origin())
    image.SetSpacing(cpp_image.spacing())
    return image


def get_image_center(image):
    info = get_image_info(image)
    center = info.size * info.spacing / 2.0  # + info.spacing / 2.0
    return center


def get_physical_volume(sim, vol_name, physical_volume_index):
    vol = sim.volume_manager.get_volume(vol_name)
    vols = vol.g4_physical_volumes
    if len(vols) == 0:
        gam.fatal(f'The function "attach_image_to_volume" can only be used after initialization')
    if physical_volume_index is None and len(vols) > 1:
        gam.fatal(f'There are {len(vols)} physical volumes attached to the {vol_name}, '
                  f'"physical_volume_index" must be set explicitly.')
    if physical_volume_index is not None and len(vols) <= physical_volume_index:
        gam.fatal(f'Cannot find phys vol {physical_volume_index}, in the list of physical '
                  f'volumes of {vol_name} ({len(vols)})')
    if physical_volume_index is None:
        return vols[0]
    return vols[physical_volume_index]


def attach_image_to_physical_volume(phys_vol_name, image,
                                    initial_translation=None,
                                    initial_rotation=Rotation.identity()):
    if initial_translation is None:
        initial_translation = [0, 0, 0]
    # FIXME rotation not implemented yet
    # get transfor from world
    translation, rotation = gam.get_transform_world_to_local(phys_vol_name)
    # compute origin
    info = get_image_info(image)
    origin = -info.size * info.spacing / 2.0 + info.spacing / 2.0 + initial_translation
    origin = Rotation.from_matrix(rotation).apply(origin) + translation
    # set origin and direction
    image.SetOrigin(origin)
    image.SetDirection(rotation)
