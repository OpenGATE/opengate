import itk
import numpy as np
from box import Box
from .exception import fatal


def itk_get_image_size(image):
    return np.array(image.GetLargestPossibleRegion().GetSize()).astype(int)


def itk_get_image_index(image):
    return np.array(image.GetLargestPossibleRegion().GetIndex()).astype(int)


def itk_get_image_origin(image):
    return np.array(image.GetOrigin())


def itk_set_image_origin(image, origin):
    image.SetOrigin([float(o) for o in origin])


def itk_get_image_spacing(image):
    return np.array(image.GetSpacing())


def itk_set_image_spacing(image, spacing):
    image.SetSpacing([float(s) for s in spacing])


def itk_get_image_direction(image):
    return itk.GetArrayFromVnlMatrix(image.GetDirection().GetVnlMatrix().as_matrix())


def itk_set_image_direction(image, direction: np.ndarray):
    image.SetDirection(direction)


def itk_image_view_from_array(arr):
    """
    When the input numpy array is of shape [1,1,x], the conversion to itk image fails:
    the output image size is with the wrong dimensions.
    We thus 'patch' itk.image_view_from_array to correct the size.

    Not fully sure if this is the way to go.
    """
    image = itk.image_view_from_array(arr)
    if len(arr.shape) == 3 and arr.shape[1] == arr.shape[2] == 1:
        new_region = itk.ImageRegion[3]()
        new_region.SetSize([1, 1, arr.shape[0]])
        image.SetRegions(new_region)
        image.Update()
    return image


def itk_image_from_array(arr):
    image = itk.image_view_from_array(arr)
    if len(arr.shape) == 3 and arr.shape[1] == arr.shape[2] == 1:
        new_region = itk.ImageRegion[3]()
        new_region.SetSize([1, 1, arr.shape[0]])
        image.SetRegions(new_region)
        image.Update()
    return image


def itk_array_from_image(image):
    return itk.GetArrayFromImage(image)


def itk_array_view_from_image(image):
    return itk.GetArrayViewFromImage(image)


def create_3d_image(size, spacing, pixel_type="float", allocate=True, fill_value=0):
    dim = 3
    pixel_type = itk.ctype(pixel_type)
    image_type = itk.Image[pixel_type, dim]
    img = image_type.New()
    region = itk.ImageRegion[dim]()
    size = np.array(size)
    region.SetSize(size.tolist())
    region.SetIndex([0, 0, 0])
    spacing = np.array(spacing)
    img.SetRegions(region)
    img.SetSpacing(spacing)
    # (default origin and direction)
    if allocate:
        img.Allocate()
        img.FillBuffer(fill_value)
    return img


def read_image_info(path_to_image):
    path_to_image = str(path_to_image)
    image_IO = itk.ImageIOFactory.CreateImageIO(
        path_to_image, itk.CommonEnums.IOFileMode_ReadMode
    )
    if not image_IO:
        fatal(f"Cannot read the image file (itk): {path_to_image}")
    image_IO.SetFileName(path_to_image)
    image_IO.ReadImageInformation()
    info = Box()
    info.filename = path_to_image
    n = info.size = image_IO.GetNumberOfDimensions()
    info.size = np.ones(n).astype(int)
    info.spacing = np.ones(n)
    info.origin = np.ones(n)
    info.dir = np.ones((n, n))
    for i in range(n):
        info.size[i] = image_IO.GetDimensions(i)
        info.spacing[i] = image_IO.GetSpacing(i)
        info.origin[i] = image_IO.GetOrigin(i)
        info.dir[i] = image_IO.GetDirection(i)
    return info


def itk_imread(filename):
    return itk.imread(filename)


def itk_imwrite(img, file_path):
    itk.imwrite(img, str(file_path))
