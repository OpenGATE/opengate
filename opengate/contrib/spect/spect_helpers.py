import pathlib
from opengate.geometry.utility import (
    translate_point_to_volume,
    vec_g4_as_np,
)
from opengate.actors.digitizers import *
import itk


def add_fake_table(sim, name="table"):
    """
    Add a patient table (fake)
    """

    # unit
    mm = g4_units.mm
    cm = g4_units.cm
    cm3 = g4_units.cm3
    deg = g4_units.deg
    gcm3 = g4_units.g / cm3

    # colors
    red = [1, 0.7, 0.7, 0.8]
    white = [1, 1, 1, 1]

    sim.volume_manager.material_database.add_material_weights(
        f"CarbonFiber", ["C"], [1], 1.78 * gcm3
    )

    # main bed
    table = sim.add_volume("Tubs", f"{name}_table")
    table.mother = "world"
    table.rmax = 439 * mm
    table.rmin = 406 * mm
    table.dz = 200 * cm / 2.0
    table.sphi = 0 * deg
    table.dphi = 70 * deg
    table.translation = [0, 25 * cm, 0]
    table.rotation = Rotation.from_euler("z", -125, degrees=True).as_matrix()
    table.material = "CarbonFiber"
    table.color = white

    # interior of the table
    tablein = sim.add_volume("Tubs", f"{name}_tablein")
    tablein.mother = table.name
    tablein.rmax = 436.5 * mm
    tablein.rmin = 408.5 * mm
    tablein.dz = 200 * cm / 2.0
    tablein.sphi = 0 * deg
    tablein.dphi = 69 * deg
    tablein.translation = [0, 0, 0]
    tablein.rotation = Rotation.from_euler("z", 0.5, degrees=True).as_matrix()
    tablein.material = "G4_AIR"
    tablein.color = red

    return table


def get_volume_position_in_head(sim, spect_name, vol_name, pos="max", axis=2):
    vol = sim.volume_manager.volumes[f"{spect_name}_{vol_name}"]
    pMin, pMax = vol.bounding_limits
    x = pMax
    if pos == "min":
        x = pMin
    if pos == "center":
        x = pMin + (pMax - pMin) / 2.0
    x = vec_g4_as_np(x)
    x = translate_point_to_volume(sim, vol, spect_name, x)
    return x[axis]


def extract_energy_window_itk(
    image: itk.Image,
    energy_window: int = "all",
    nb_of_energy_windows: int = 3,
    nb_of_gantries: int = 60,
) -> itk.Image:
    """
    Extracts a given energy window from a 3D image and returns a reshaped image.

    3rd dim is number_of_energy_window x number_of_gantries

    Args:
        image (itk.Image): The input 3D image of shape (e.g. 128 x 128 x 3 x 60).
        energy_window : which energy windows to extract (int or 'all').
        nb_of_energy_windows (int): the number of energy windows
        nb_of_gantries (int): The number of gantry positions (default: 60).

    Returns:
        itk.Image: The extracted and reshaped image of shape (128 x 128 x 60).
    """

    # Validate input dimensions
    width, height, depth = image.GetSize()
    if depth != nb_of_gantries * nb_of_energy_windows:
        raise ValueError(
            f"Input image depth {depth} does not match expected "
            f"dimensions = {nb_of_gantries} x {nb_of_energy_windows}."
        )

    # Extract the relevant slices
    # (warning numpy is z,x,y, while itk is x,y,z)
    arr = itk.GetArrayViewFromImage(image)
    sub_image_array = arr[energy_window::nb_of_energy_windows, :, :]

    # Convert the numpy array back to a SimpleITK image
    sub_image = itk.GetImageFromArray(sub_image_array)

    # Preserve the original image metadata
    sub_image.SetSpacing(image.GetSpacing())
    sub_image.SetOrigin(image.GetOrigin())
    sub_image.SetDirection(image.GetDirection())

    return sub_image


def extract_energy_window_from_projection_actors(
    projections,
    energy_window: int = "all",
    nb_of_energy_windows: int = 3,
    nb_of_gantries: int = 60,
    output_filenames=None,
):
    auto_output_filenames = output_filenames is None
    if auto_output_filenames:
        output_filenames = []
    i = 0
    for proj in projections:
        filename = proj.get_output_path()
        img = itk.imread(filename)
        out = extract_energy_window_itk(
            img,
            energy_window=energy_window,
            nb_of_energy_windows=nb_of_energy_windows,
            nb_of_gantries=nb_of_gantries,
        )
        if auto_output_filenames:
            extension = pathlib.Path(filename).suffix
            output_filename = str(filename).replace(
                extension, f"_ene_{energy_window}{extension}"
            )
            output_filenames.append(output_filename)
        else:
            output_filename = output_filenames[i]
        itk.imwrite(out, output_filename)
        i += 1
    return output_filenames


def merge_several_heads_projections(filenames):
    output_arr = None
    img = None
    for filename in filenames:
        img = itk.imread(filename)
        arr = itk.GetArrayFromImage(img)
        if output_arr is None:
            output_arr = arr
        else:
            output_arr = np.concatenate((output_arr, arr), axis=0)

    output_img = itk.GetImageFromArray(output_arr)
    output_img.CopyInformation(img)
    return output_img
