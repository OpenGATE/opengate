from pathlib import Path
import json
import random
import string
import itk
import numpy as np

import opengate_core as g4
from .engines import SimulationEngine
from .exception import fatal
from .geometry.volumes import VolumeBase
from .image import (
    write_itk_image,
    create_image_with_volume_extent,
    create_image_with_extent,
    update_image_py_to_cpp,
    get_py_image_from_cpp_image,
    get_info_from_image,
)
from .processing import dispatch_to_subprocess
from .serialization import dump_json
from .utility import ensure_filename_is_str
from .definitions import __gate_list_objects__
from . import logger


def generate_random_string(length=10):
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


def voxelize_geometry(
    sim,
    extent="auto",
    spacing=(3, 3, 3),
    margin=0,
    filename=None,
    return_path=False,
):
    """Create a voxelized three-dimensional representation of the simulation geometry.

    The user can specify the sub-portion (a rectangular box) of the simulation which is to be extracted.

    Args:
        extent : By default ('auto'), GATE automatically determines the sub-portion
            to contain all volumes of the simulation.
            Alternatively, extent can be either a tuple of 3-vectors indicating the two diagonally
            opposite corners of the box-shaped
            sub-portion of the geometry to be extracted, or a volume or list volumes.
            In the latter case, the box is automatically determined to contain the volume(s).
        spacing (tuple): The voxel spacing in x-, y-, z-direction.
        margin : Width (in voxels) of the additional margin around the extracted box-shaped sub-portion
            indicated by `extent`.
        filename (str, optional): The filename/path to which the voxelized image and labels are written.
            Suffix added automatically. Path can be relative to the global output directory of the simulation.
        return_path (bool): Return the absolute path where the voxelized image was written?

    Returns:
        dict, itk image, (path): A dictionary containing the label to volume LUT; the voxelized geometry;
            optionally: the absolute path where the image was written, if applicable.
    """
    # collect volumes which are directly underneath the world/parallel worlds
    if extent in ("auto", "Auto"):
        sim.volume_manager.update_volume_tree_if_needed()
        extent = list(sim.volume_manager.world_volume.children)
        for pw in sim.volume_manager.parallel_world_volumes.values():
            extent.extend(list(pw.children))

    labels, image = dispatch_to_subprocess(
        compute_voxelized_geometry, sim, extent, spacing, margin
    )

    if filename is not None:
        outpath = sim.get_output_path(filename)
        outpath_json = outpath.parent / (outpath.stem + "_labels.json")
        outpath_mhd = outpath.parent / (outpath.stem + "_image.mhd")

        # write labels
        with open(outpath_json, "w") as outfile:
            dump_json(labels, outfile, indent=4)

        # write image
        write_itk_image(image, ensure_filename_is_str(outpath_mhd))
    else:
        outpath_mhd = "not_applicable"

    if return_path is True:
        return labels, image, outpath_mhd
    else:
        return labels, image


def write_voxelized_geometry(
    self,
    labels,
    image,
    base_filename,
    vol_filename=None,
    image_filename=None,
    label_filename=None,
    db_filename=None,
):
    # write labels
    if vol_filename is None:
        vol_filename = Path(base_filename).with_suffix(".json")
        vol_filename = str(vol_filename).replace(".json", "_volumes.json")
    with open(vol_filename, "w") as outfile:
        json.dump(labels, outfile, indent=4)

    # write image
    if image_filename is None:
        image_filename = Path(base_filename).with_suffix(".mhd")
    itk.imwrite(image, image_filename)

    # create the label to material
    vm = [[m["label"], m["label"] + 1, m["material"]] for m in labels.values()]
    image_volume = self.add_volume("Image", generate_random_string(12))
    image_volume.voxel_materials = vm
    if label_filename is None:
        label_filename = Path(base_filename).with_suffix(".json")
        label_filename = str(label_filename).replace(".json", "_labels.json")
    image_volume.write_label_to_material(label_filename)

    # write the database of material
    # gate_iec.create_material(sim)
    if db_filename is None:
        db_filename = Path(base_filename).with_suffix(".db")
    image_volume.write_material_database(db_filename)

    self.volume_manager.remove_volume(image_volume.name)
    return {
        "volumes": vol_filename,
        "image": image_filename,
        "labels": label_filename,
        "materials": db_filename,
    }


def compute_voxelized_geometry(sim, extent, spacing, margin):
    """Method which returns a voxelized image of the simulation geometry
    given the extent, spacing and margin.
    The voxelization does not check which volume is voxelized.
    Every voxel will be assigned an ID corresponding to the material at this position
    in the world.
    """

    if isinstance(extent, VolumeBase):
        image = create_image_with_volume_extent(extent, spacing, margin)
    elif isinstance(extent, __gate_list_objects__) and all(
        [isinstance(e, VolumeBase) for e in extent]
    ):
        image = create_image_with_volume_extent(extent, spacing, margin)
    elif isinstance(extent, __gate_list_objects__) and all(
        [isinstance(e, __gate_list_objects__) and len(e) == 3 for e in extent]
    ):
        image = create_image_with_extent(extent, spacing, margin)
    else:
        fatal(
            f"The input variable `extent` needs to be a tuple of 3-vectors, or a volume, "
            f"or a list of volumes. Found: {extent}."
        )

    vl = sim.verbose_level
    sim.verbose_level = logger.NONE
    with SimulationEngine(sim) as se:
        se.initialize()
        vox = g4.GateVolumeVoxelizer()
        update_image_py_to_cpp(image, vox.fImage, False)
        vox.Voxelize()
        image = get_py_image_from_cpp_image(vox.fImage)
        labels = vox.fLabels
        for key in labels.keys():
            vol = se.simulation.volume_manager.get_volume(key)
            labels[key] = {"label": labels[key], "material": vol.material}

    sim.verbose_level = vl
    return labels, image


def voxelized_source(itk_image, volumes_labels, activities):
    img_label = itk.GetArrayViewFromImage(itk_image)
    img_arr = itk.GetArrayFromImage(itk_image).astype(np.float32)
    img_arr[:, :, :] = 0.0
    for label in volumes_labels:
        l = volumes_labels[label]["label"]
        if label in activities:
            img_arr[img_label == l] = activities[label]
    itk_source = itk.GetImageFromArray(img_arr)
    itk_source.CopyInformation(itk_image)
    return itk_source
