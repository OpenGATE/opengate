from scipy.spatial.transform import Rotation
import opengate_core as g4
from .definitions import __gate_list_objects__
from .geometry.utility import get_transform_world_to_local

ITK_LIBRARY = "SimpleITK"
# ITK_LIBRARY = "ITK"

if ITK_LIBRARY == "SimpleITK":
    from .image_sitk import *
else:
    from .image_itk import *


def update_image_py_to_cpp(py_img, cpp_img, copy_data=False):
    # update metadata to cpp side
    cpp_img.set_size(itk_get_image_size(py_img))
    cpp_img.set_spacing(itk_get_image_spacing(py_img))
    cpp_img.set_origin(itk_get_image_origin(py_img))
    cpp_img.set_direction(itk_get_image_direction(py_img))
    # this is needed
    cpp_img.set_region(
        itk_get_image_index(py_img),
        itk_get_image_size(py_img),
    )
    if copy_data:
        arr = itk_array_view_from_image(py_img)
        cpp_img.from_pyarray(arr, "C")


def update_image_cpp_to_py(cpp_image):
    arr = cpp_image.to_pyarray("C")
    image = itk_image_view_from_array(arr)
    itk_set_image_origin(image, cpp_image.origin())
    itk_set_image_spacing(image, cpp_image.spacing())
    return image


def create_image_like(like_image, allocate=True, pixel_type=None, fill_value=0):
    # TODO fix pixel_type -> copy from image rather than argument
    info = get_info_from_image(like_image)
    img = create_3d_image(
        info.size,
        info.spacing,
        pixel_type=pixel_type,
        allocate=allocate,
        fill_value=fill_value,
    )
    itk_set_image_origin(img, info.origin)
    itk_set_image_direction(img, info.dir)
    return img


def create_image_like_info(info, allocate=True, fill_value=0):
    img = create_3d_image(
        info.size, info.spacing, allocate=allocate, fill_value=fill_value
    )
    img.SetOrigin(info.origin)
    img.SetDirection(info.dir)
    return img


def get_info_from_image(image):
    info = Box()
    info.size = itk_get_image_size(image)
    info.spacing = itk_get_image_spacing(image)
    info.origin = itk_get_image_origin(image)
    info.dir = itk_get_image_direction(image)
    return info


def get_translation_between_images_center(img_name1, img_name2):
    """
    The two images are considered in the same physical space (coordinate system).
    This function computes the translation between their centers.
    Warning, the ITK image origin consider the center of the first voxel, we thus
    consider half a pixel shift for the center.
    """
    info1 = read_image_info(img_name1)
    info2 = read_image_info(img_name2)
    # get the center of the first image in img coordinate system
    center1 = info1.size / 2.0 * info1.spacing + info1.origin - info1.spacing / 2.0
    # get the center of the second image in img coordinate system
    center2 = info2.size / 2.0 * info2.spacing + info2.origin - info2.spacing / 2.0
    return center2 - center1


def get_origin_wrt_images_g4_position(img_info1, img_info2, translation):
    """
    The two images are considered in the same GATE physical space (coordinate system), so according to the
    centers of both images (+translation).
    This function computes the origin for the second image such as the two images will be in the same
    physical space of the first image.
    Warning, the ITK image origin considers the center of the first voxel, we thus
    consider half a pixel shift for the center.
    """
    half_size1 = img_info1.size * img_info1.spacing / 2.0
    half_size2 = img_info2.size * img_info2.spacing / 2.0
    origin = (
        img_info1.origin
        + half_size1
        - half_size2
        + translation
        - img_info1.spacing / 2.0
        + img_info2.spacing / 2
    )
    return origin


def get_image_center(image):
    info = read_image_info(image)
    center = info.size * info.spacing / 2.0  # + info.spacing / 2.0
    return center


def get_translation_from_iso_center(img_info, rot, iso_center, centered):
    if centered:
        # cf Gate GateVImageVolume.cc, function UpdatePositionWithIsoCenter
        iso_center = iso_center - img_info.origin
        center = img_info.size * img_info.spacing / 2.0
        iso_center -= center
        t = rot.apply(iso_center)
        return t
    fatal(f"not implemented yet")


def align_image_with_physical_volume(
    volume,
    image,
    initial_translation=None,
    initial_rotation=Rotation.identity(),
    copy_index=0,
):
    if initial_translation is None:
        initial_translation = [0, 0, 0]
    # FIXME rotation not implemented yet
    # get transform from world
    translation, rotation = get_transform_world_to_local(volume)
    # compute origin
    info = get_info_from_image(image)
    origin = -info.size * info.spacing / 2.0 + info.spacing / 2.0 + initial_translation
    origin = (
        Rotation.from_matrix(rotation[copy_index]).apply(origin)
        + translation[copy_index]
    )
    # set origin and direction
    itk_set_image_origin(image, origin)
    itk_set_image_direction(image, rotation[copy_index])


def create_image_with_extent(extent, spacing=(1, 1, 1), margin=0):
    # define the new size and spacing
    spacing = np.array(spacing).astype(float)
    size = np.ceil((extent[1] - extent[0]) / spacing).astype(int) + 2 * margin

    # create image
    image = create_3d_image(size, spacing)

    # The origin is considered to be at the center of first pixel.
    # It is set such that the image is at the exact extent (bounding volume).
    # The volume contour thus goes through the center of the first pixel.
    origin = extent[0] + spacing / 2.0 - margin
    itk_set_image_origin(image, origin)
    return image


def create_image_with_volume_extent(volume, spacing=(1, 1, 1), margin=0):
    if not isinstance(volume, __gate_list_objects__):
        volume = [volume]

    p_min = []
    p_max = []
    for vol in volume:
        pMin_g4vec, pMax_g4vec = vol.bounding_limits
        p_min.append(
            vec_g4_as_np(pMin_g4vec) + vol.translation_list[0]
        )  # FIXME: make this work in case if repeated volumes
        p_max.append(vec_g4_as_np(pMax_g4vec) + vol.translation_list[0])

    extent_lower = np.min(p_min, axis=0)
    extent_upper = np.max(p_max, axis=0)

    return create_image_with_extent((extent_lower, extent_upper), spacing, margin)


# FIXME: should not require a simulation engine as input
def voxelize_volume(se, image):
    """
    The voxelization do not check which volume is voxelized.
    Every voxel will be assigned an ID corresponding to the material at this position
    in the world.
    """
    # simulation engine : initialization is needed
    # because it builds the hierarchy of G4 volumes
    # that are needed by the "voxelize" function
    if not se.is_initialized:
        se.initialize()

    # start voxelization
    vox = g4.GateVolumeVoxelizer()
    update_image_py_to_cpp(image, vox.fImage, False)
    vox.Voxelize()
    image = update_image_cpp_to_py(vox.fImage)
    labels = vox.fLabels
    return labels, image


def transform_images_point(p, img1, img2):
    index = img1.TransformPhysicalPointToIndex(p)
    pbis = img2.TransformIndexToPhysicalPoint(index)
    return [i for i in pbis]


def compute_image_3D_CDF(image):
    """
    Compute the three CDF (Cumulative Density Function) for the given image
    Warning; numpy order is ZYX

    :param image: itk image
    """
    # consider image as np array
    array = itk_array_view_from_image(image)

    # normalize
    array = array / np.sum(array)

    # Sum image on a single plane along X axis
    sumx = np.sum(array, axis=2)
    # Y axis, sum plane on a single axis along Y axis
    sumxy = np.sum(sumx, axis=1)
    # X 3D CDF
    cdf_x = []
    for i in range(array.shape[0]):  # Z
        cdf_x.append([])
        for j in range(array.shape[1]):  # Y
            # cumulated sum along X axis
            t = np.cumsum(array[i][j])
            # normalise if last value (sum) is not zero
            if t[-1] != 0:
                t = t / t[-1]
            cdf_x[i].append(t)

    # Y 2D CDF
    cdf_y = []
    for i in range(len(sumx)):  # Z
        t = np.cumsum(sumx[i])
        if t[-1] != 0:
            t = t / t[-1]
        cdf_y.append(t)

    # Z 1D CDF
    cdf_z = np.cumsum(sumxy) / np.sum(sumxy)

    # return
    return cdf_x, cdf_y, cdf_z


def scale_itk_image(img, scale):
    imgarr = np.asarray(img)
    imgarr = imgarr * scale
    img2 = itk_image_from_array(imgarr)
    img2.CopyInformation(img)
    return img2


def divide_itk_images(
    img1_numerator, img2_denominator, filterVal=0, replaceFilteredVal=0
):
    imgarr1 = itk_array_view_from_image(img1_numerator)
    imgarr2 = itk_array_view_from_image(img2_denominator)
    if imgarr1.shape != imgarr2.shape:
        fatal(
            f"Cannot divide images of different shape. Found {imgarr1.shape} vs. {imgarr2.shape}."
        )
    imgarrOut = imgarr1.copy()
    L_filterInv = imgarr2 != filterVal
    imgarrOut[L_filterInv] = np.divide(imgarr1[L_filterInv], imgarr2[L_filterInv])

    imgarrOut[np.invert(L_filterInv)] = replaceFilteredVal
    imgarrOut = itk_image_from_array(imgarrOut)
    imgarrOut.CopyInformation(img1_numerator)
    return imgarrOut


def split_spect_projections(input_filenames, nb_ene):
    """
    The inputs are filenames of several images containing projections for a given spect head
    Each image is composed of nb_ene energy windows and XX angles.
    The number of angles is found by looking at the number of slices.

    The function computes nb_ene itk image with all angles and all heads merged into a list of
    projections stored as a 3D image, to make it easy to reconstruct with RTK.

    """
    nb_heads = len(input_filenames)

    # read the first image to get information
    img = itk_imread(str(input_filenames[0]))
    info = get_info_from_image(img)
    imga = itk_array_view_from_image(img)

    nb_runs = imga.shape[0] // nb_ene
    nb_angles = nb_heads * nb_runs
    # print('Number of heads', nb_heads)
    # print('Number of E windows', nb_ene)
    # print('Number of run', nb_runs)
    # print('Number of angles', nb_angles)

    # create and allocate final images
    outputs_img = []
    outputs_arr = []
    size = [imga.shape[1], imga.shape[2], nb_angles]
    spacing = info.spacing
    for e in range(nb_ene):
        image = create_3d_image(size, spacing)
        image.SetOrigin(img.GetOrigin())
        outputs_img.append(image)
        outputs_arr.append(itk_array_view_from_image(image))

    # loop on heads and create images
    s2 = 0
    for head in range(nb_heads):
        img = itk_imread(str(input_filenames[head]))
        imga = itk_array_view_from_image(img)
        e = 0
        for s in range(imga.shape[0]):
            outputs_arr[e][s2] = imga[s]
            e += 1
            if e >= nb_ene:
                e = 0
                s2 += 1

    # end
    return outputs_img


def compare_itk_image_info(image1, image2):
    are_origins_equal = np.allclose(image1.GetOrigin(), image2.GetOrigin())
    are_spacings_equal = np.allclose(image1.GetSpacing(), image2.GetSpacing())
    are_directions_equal = np.allclose(image1.GetDirection(), image2.GetDirection())
    return are_spacings_equal and are_directions_equal and are_origins_equal


def compare_itk_image_content(image1, image2):
    arr1 = itk_array_from_image(image1)
    arr2 = itk_array_from_image(image2)
    return np.array_equal(arr1, arr2)


def compare_itk_image(filename1, filename2):
    im1 = itk_imread(filename1)
    im2 = itk_imread(filename2)
    return compare_itk_image_info(im1, im2) and compare_itk_image_content(im1, im2)


def write_itk_image(img, file_path):
    # TODO: check if filepath exists
    # TODO: add metadata to file header
    itk_imwrite(img, str(file_path))
