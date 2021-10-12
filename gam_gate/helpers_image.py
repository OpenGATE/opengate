import itk
import numpy as np
from box import Box


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
