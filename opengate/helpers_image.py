import itk
import numpy as np
from box import Box
import opengate as gate
import opengate_core as g4
from scipy.spatial.transform import Rotation


def update_image_py_to_cpp(py_img, cpp_img, copy_data=False):
    cpp_img.set_size(py_img.GetLargestPossibleRegion().GetSize())
    cpp_img.set_spacing(py_img.GetSpacing())
    cpp_img.set_origin(py_img.GetOrigin())
    # this is needed !
    cpp_img.set_region(
        py_img.GetLargestPossibleRegion().GetIndex(),
        py_img.GetLargestPossibleRegion().GetSize(),
    )
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


def create_image_like(like_image, allocate=True, pixel_type=""):
    # TODO fix pixel_type -> copy from image rather than argument
    info = get_info_from_image(like_image)

    if pixel_type:
        img = create_3d_image(
            info.size, info.spacing, pixel_type=pixel_type, allocate=allocate
        )
    else:
        img = create_3d_image(info.size, info.spacing, allocate=allocate)
    img.SetOrigin(info.origin)
    img.SetDirection(info.dir)
    return img


def create_image_like_info(info, allocate=True):
    img = create_3d_image(info.size, info.spacing, allocate=allocate)
    img.SetOrigin(info.origin)
    img.SetDirection(info.dir)
    return img


def get_info_from_image(image):
    info = Box()
    info.size = np.array(itk.size(image)).astype(int)
    info.spacing = np.array(image.GetSpacing())
    info.origin = np.array(image.GetOrigin())
    info.dir = image.GetDirection()
    return info


def read_image_info(filename):
    filename = str(filename)
    image_IO = itk.ImageIOFactory.CreateImageIO(
        filename, itk.CommonEnums.IOFileMode_ReadMode
    )
    if not image_IO:
        gate.fatal(f"Cannot read the header of this image file (itk): {filename}")
    image_IO.SetFileName(filename)
    image_IO.ReadImageInformation()
    info = Box()
    info.filename = filename
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


def get_cpp_image(cpp_image):
    arr = cpp_image.to_pyarray()
    image = itk_image_view_from_array(arr)
    image.SetOrigin(cpp_image.origin())
    image.SetSpacing(cpp_image.spacing())
    return image


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
    gate.fatal(f"not implemented yet")


def get_physical_volume(volume_engine, vol_name, physical_volume_index):
    vol = volume_engine.get_volume(vol_name)
    vols = vol.g4_physical_volumes
    if len(vols) == 0:
        gate.fatal(
            f'The function "attach_image_to_volume" can only be used after initialization'
        )
    if physical_volume_index is None and len(vols) > 1:
        gate.fatal(
            f"There are {len(vols)} physical volumes attached to the {vol_name}, "
            f'"physical_volume_index" must be set explicitly.'
        )
    if physical_volume_index is not None and len(vols) <= physical_volume_index:
        gate.fatal(
            f"Cannot find phys vol {physical_volume_index}, in the list of physical "
            f"volumes of {vol_name} ({len(vols)})"
        )
    if physical_volume_index is None:
        return vols[0]
    return vols[physical_volume_index]


def attach_image_to_physical_volume(
    phys_vol_name, image, initial_translation=None, initial_rotation=Rotation.identity()
):
    if initial_translation is None:
        initial_translation = [0, 0, 0]
    # FIXME rotation not implemented yet
    # get transform from world
    translation, rotation = gate.get_transform_world_to_local(phys_vol_name)
    # compute origin
    info = get_info_from_image(image)
    origin = -info.size * info.spacing / 2.0 + info.spacing / 2.0 + initial_translation
    origin = Rotation.from_matrix(rotation).apply(origin) + translation
    # set origin and direction
    image.SetOrigin(origin)
    image.SetDirection(rotation)


def create_image_with_volume_extent(sim, vol_name, spacing=[1, 1, 1], margin=0):
    pMin, pMax = gate.get_volume_bounding_limits(sim, vol_name)
    pMin = gate.vec_g4_as_np(pMin)
    pMax = gate.vec_g4_as_np(pMax)

    # define the new size and spacing
    spacing = np.array(spacing).astype(float)
    size = np.ceil((pMax - pMin) / spacing).astype(int)
    size = size + margin * 2

    # create image
    image = gate.create_3d_image(size, spacing)

    # the origin is considered at the center of first pixel
    # is it set such as the image is at the exact extent (bounding volume)
    # (the volume contour thus goes through the center of the first pixel)
    origin = pMin + spacing / 2.0 - margin
    image.SetOrigin(origin)
    return image


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
    gate.update_image_py_to_cpp(image, vox.fImage, False)
    vox.Voxelize()
    image = gate.get_cpp_image(vox.fImage)
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
    array = itk.array_view_from_image(image)

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
    imgarr = itk.array_view_from_image(img)
    imgarr = imgarr * scale
    img2 = itk.image_from_array(imgarr)
    img2.CopyInformation(img)
    return img2


def divide_itk_images(
    img1_numerator, img2_denominator, filterVal=0, replaceFilteredVal=0
):
    imgarr1 = itk.array_view_from_image(img1_numerator)
    imgarr2 = itk.array_view_from_image(img2_denominator)
    imgarrOut = imgarr1.copy()
    L_filterInv = imgarr2 != filterVal
    imgarrOut[L_filterInv] = np.divide(imgarr1[L_filterInv], imgarr2[L_filterInv])

    imgarrOut[np.invert(L_filterInv)] = replaceFilteredVal
    imgarrOut = itk.image_from_array(imgarrOut)
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
    img = itk.imread(str(input_filenames[0]))
    info = gate.get_info_from_image(img)
    imga = itk.array_view_from_image(img)

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
        image = gate.create_3d_image(size, spacing)
        image.SetOrigin(img.GetOrigin())
        outputs_img.append(image)
        outputs_arr.append(itk.array_view_from_image(image))

    # loop on heads and create images
    s2 = 0
    for head in range(nb_heads):
        img = itk.imread(str(input_filenames[head]))
        imga = itk.array_view_from_image(img)
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
    arr1 = itk.array_from_image(image1)
    arr2 = itk.array_from_image(image2)
    return np.array_equal(arr1, arr2)


def compare_itk_image(filename1, filename2):
    im1 = itk.imread(filename1)
    im2 = itk.imread(filename2)
    return compare_itk_image_info(im1, im2) and compare_itk_image_content(im1, im2)
