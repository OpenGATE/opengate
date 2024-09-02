import numpy as np
import SimpleITK as sitk
from box import Box
from .exception import fatal
from .utility import ensure_filename_is_str


def itk_get_image_size(image):
    return np.array(image.GetSize()).astype(int)


def itk_get_image_index(image):
    return 0, 0, 0


def itk_get_image_origin(image):
    return np.array(image.GetOrigin())


def itk_set_image_origin(image, origin):
    image.SetOrigin([float(o) for o in origin])


def itk_get_image_spacing(image):
    return np.array(image.GetSpacing())


def itk_set_image_spacing(image, spacing):
    image.SetSpacing([float(s) for s in spacing])


def itk_get_image_direction(image):
    return np.array(image.GetDirection()).reshape((3, 3))


def itk_set_image_direction(image, direction: np.ndarray):
    image.SetDirection([float(d) for d in direction.ravel()])


def itk_image_view_from_array(arr):
    # Not VIEW with sitk
    return sitk.GetImageFromArray(arr)


def itk_image_from_array(arr):
    return sitk.GetImageFromArray(arr)


def itk_array_from_image(image):
    return sitk.GetArrayFromImage(image)


def itk_array_view_from_image(image):
    return sitk.GetArrayViewFromImage(image)


def create_3d_image(
    size, spacing, origin=(0, 0, 0), pixel_type="float", allocate=True, fill_value=0
):
    if not len(size) == 3:
        fatal(f"size should be a 3-vector, received {size}.")

    if allocate is False:
        fatal(f"create_3d_image: with SimpleITK, allocate must always be True")

    pixel_types = {
        "float": sitk.sitkFloat32,
        "double": sitk.sitkFloat64,
        "int": sitk.sitkInt32,
    }
    pixel_type = pixel_type.lower()
    if pixel_type not in pixel_types:
        fatal(
            f"Unknown pixel_type '{pixel_type}'. Known types are 'float', 'int', 'double."
        )
    image_type = pixel_types[pixel_type]

    # be sure size is int
    size = [int(s) for s in size]

    # image creating allocate the data and set it to 0
    img = sitk.Image(size, image_type)
    itk_set_image_spacing(img, spacing)
    itk_set_image_origin(img, origin)
    img = img + fill_value

    return img


def read_image_info(path_to_image):
    path_to_image = ensure_filename_is_str(path_to_image)
    info = Box()
    info.filename = path_to_image
    reader = sitk.ImageFileReader()
    reader.SetImageIO("MetaImageIO")
    reader.SetFileName(path_to_image)
    info.size = itk_get_image_size(reader)
    info.origin = itk_get_image_origin(reader)
    info.spacing = itk_get_image_spacing(reader)
    info.dir = itk_get_image_direction(reader)
    return info


def itk_imread(filename):
    return sitk.ReadImage(filename)


def itk_imwrite(img, filename):
    return sitk.WriteImage(img, filename)
