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


def create_image_like(like_image, allocate=True):
    info = get_info_from_image(like_image)
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
    This function computes the origin for the second image such as the the two images will be in the same
    physical space of the first image.
    Warning, the ITK image origin consider the center of the first voxel, we thus
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
    image = itk.image_from_array(arr)
    image.SetOrigin(cpp_image.origin())
    image.SetSpacing(cpp_image.spacing())
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


def get_physical_volume(sim, vol_name, physical_volume_index):
    vol = sim.volume_manager.get_volume(vol_name)
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


def voxelize_volume(sim, vol_name, image):
    # get physical volume
    vol = sim.volume_manager.get_volume(vol_name).g4_physical_volume
    if vol.GetMultiplicity() != 1:
        gate.warning(
            f"Warning the volume {vol_name} is multiple: "
            f"{vol.GetMultiplicity()}. Only first is considered"
        )

    # world volume
    world = sim.volume_manager.get_volume("world").g4_physical_volume

    # navigator
    nav = g4.G4Navigator()
    nav.SetWorldVolume(world)

    # list of volume label
    labels = {}
    vox = g4.GateVolumeVoxelizer()
    gate.update_image_py_to_cpp(image, vox.fImage, False)
    vox.Voxelize(vol_name)

    image = gate.get_cpp_image(vox.fImage)
    labels = vox.fLabels
    return labels, image


def transform_images_point(p, img1, img2):
    index = img1.TransformPhysicalPointToIndex(p)
    return img2.TransformIndexToPhysicalPoint(index)


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
