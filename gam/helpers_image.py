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


def create_3d_image(dimension, spacing, pixel_type='float'):
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
    img.FillBuffer(0)
    return img


def get_img_info(img):
    info = Box()
    info.size = np.array(itk.size(img)).astype(int)
    info.spacing = np.array(img.GetSpacing())
    info.origin = np.array(img.GetOrigin())
    info.dir = img.GetDirection()
    return info
