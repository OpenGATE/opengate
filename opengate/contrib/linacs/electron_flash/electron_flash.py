import logging
import os
import sys

import numpy as np
import SimpleITK as sitk
from scipy.spatial.transform import Rotation as R

import opengate as gate

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

material_colors = {
    "Titanium": [0.2, 0.2, 0.2, 0.6],
    "Tecapeek": [1.0, 0.6, 0.2, 0.6],
    "Air": [1.0, 0.6, 0.2, 0.6],
    "AluminiumEGS": [0.8, 0.8, 0.8, 0.6],
    "Tungsten": [0.8, 0.8, 0.8, 0.6],
    "PMMA": [0.0, 0.6, 0.0, 0.5],
    "Water": [0.0, 0.0, 0.5, 0.5],
}


def add_tubs(
    sim, name, mother, rmin, rmax, height, material, translation, material_colors=None
):
    """
    This function creates and adds a cylindrical (Tubs) volume to the geometry.

    Args:
        sim: The simulation object where the volume will be added.
        name (str): Name of the volume.
        mother (str): The name of the mother volume.
        rmin (float): Inner radius of the tube in millimeters.
        rmax (float): Outer radius of the tube in millimeters.
        height (float): Full height of the tube in millimeters.
        material (str): Material assigned to the volume.
        translation (tuple): A 3-element tuple representing the (x, y, z) translation of the volume.
        material_colors (dict): A dictionary mapping material names to RGB color strings or tuples.

    Returns:
        The created volume object.

    """
    mm = gate.g4_units.mm
    vol = sim.add_volume("Tubs", name)
    vol.mother = mother
    vol.rmin = rmin * mm
    vol.rmax = rmax * mm
    vol.dz = height * mm / 2
    vol.material = material
    vol.translation = translation
    if material_colors and material in material_colors:
        vol.color = material_colors[material]
    return vol


def add_cons(
    sim,
    name,
    mother,
    rmin1,
    rmax1,
    rmin2,
    rmax2,
    height,
    material,
    translation,
    material_colors=None,
):
    """
    This function creates and adds a conical (Cons) volume to the geometry.

    Args:
        sim: The simulation object where the volume will be added.
        name (str): Name of the volume.
        mother (str): The name of the mother volume.
        rmin1 (float): Inner radius at the -Z end in millimeters.
        rmax1 (float): Outer radius at the -Z end in millimeters.
        rmin2 (float): Inner radius at the +Z end in millimeters.
        rmax2 (float): Outer radius at the +Z end in millimeters.
        height (float): Full height of the cone in millimeters.
        material (str): Material assigned to the volume.
        translation (tuple): A 3-element tuple representing the (x, y, z) translation of the volume.
        material_colors (dict, optional): A dictionary mapping material names to RGB color strings or tuples.

    Returns:
        The created volume object.
    """
    mm = gate.g4_units.mm
    deg = gate.g4_units.deg
    vol = sim.add_volume("Cons", name)
    vol.mother = mother
    vol.rmin1 = rmin1 * mm
    vol.rmax1 = rmax1 * mm
    vol.rmin2 = rmin2 * mm
    vol.rmax2 = rmax2 * mm
    vol.dz = height / 2
    vol.material = material
    vol.translation = translation
    vol.sphi = 0 * deg
    vol.dphi = 360 * deg
    if material_colors and material in material_colors:
        vol.color = material_colors[material]
    return vol


def add_box(sim, name, mother, lx, ly, lz, material, translation, material_colors=None):
    """
    This function creates and adds a rectangular (Box) volume to the geometry.

    Args:
        sim: The simulation object where the volume will be added.
        name (str): Name of the volume.
        mother (str): The name of the mother volume.
        lx (float): Length of the box along the X-axis in millimeters.
        ly (float): Length of the box along the Y-axis in millimeters.
        lz (float): Length of the box along the Z-axis in millimeters.
        material (str): Material assigned to the volume.
        translation (tuple): A 3-element tuple representing the (x, y, z) translation of the volume.
        material_colors (dict, optional): A dictionary mapping material names to RGB color strings or tuples.

    Returns:
        The created volume object.
    """
    vol = sim.add_volume("Box", name)
    vol.mother = mother
    vol.size = [lx, ly, lz]
    vol.material = material
    vol.translation = translation
    if material_colors and material in material_colors:
        vol.color = material_colors[material]
    return vol


def get_object_zdimension(components, center_z):
    """
    Computes the Z-dimension range (start and end Z coordinates) of the whole structure (made up of components).

    Args:
        components (list): A list of component tuples.
        center_z (float): Global Z-axis offset to apply to all components.

    Returns:
        tuple: (start_z, end_z) in millimeters, representing the total Z-extent.
    """
    get_z_bounds = lambda comp: (
        comp[-1][2] - comp[-3] / 2 + center_z,
        comp[-1][2] + comp[-3] / 2 + center_z,
    )

    start_z, _ = get_z_bounds(components[0])
    _, end_z = get_z_bounds(components[-1])
    return start_z, end_z


def build_ElectronFlash(sim, center_x=0, center_y=0, center_z=0, material_colors=None):
    """
    This function builds the full ElectronFlash linear accelerator (linac) geometry, starting from the titanium window up to the beginning of the BLD.

    Args:
        sim: The simulation object where volumes will be added.
        center_x (float): Offset in millimeters along the X-axis for the titanium window.
        center_y (float): Offset in millimeters along the Y-axis for the titanium window.
        center_z (float): Offset in millimeters along the Z-axis for the titanium window.
        material_colors (dict, optional): A dictionary mapping material names to RGB color strings or tuples.

    Returns:
        float: The Z-coordinate (in mm) of the end of the linac structure, useful when other components has to be added.
    """
    mm = gate.g4_units.mm
    if material_colors is None:
        material_colors = {}

    def offset(mother, pos):
        if mother == "world":
            return [pos[0] + center_x, pos[1] + center_y, pos[2] + center_z]
        return pos

    logger.info(
        f"Building ElectronFlash linac structure with center offset: X={center_x} mm, Y={center_y} mm, Z={center_z} mm"
    )

    components = [
        # (func, name, mother, args..., material, translation)
        (
            add_tubs,
            sim,
            "tit_window",
            "world",
            0,
            18.2,
            0.055,
            "Titanium",
            [0, 0, 0.0275 * mm],
        ),
        (add_tubs, sim, "cyl1", "world", 0, 34.6, 12.8, "Tecapeek", [0, 0, 6.455 * mm]),
        (add_cons, sim, "hollow_cone", "cyl1", 0, 7, 0, 19, 12.8, "Air", [0, 0, 0]),
        (add_tubs, sim, "st_0", "world", 15, 34.6, 5, "Tecapeek", [0, 0, 15.355 * mm]),
        (add_tubs, sim, "st_1", "world", 15, 22, 14, "Tecapeek", [0, 0, 24.855 * mm]),
        (add_tubs, sim, "st_2", "world", 20, 24, 132, "Tecapeek", [0, 0, 97.855 * mm]),
        (add_tubs, sim, "st_3", "world", 31, 37, 35, "Tecapeek", [0, 0, 156.755 * mm]),
        (
            add_tubs,
            sim,
            "st_4",
            "world",
            22.5,
            37,
            73.5,
            "Tecapeek",
            [0, 0, 211.005 * mm],
        ),
        (
            add_tubs,
            sim,
            "st_5",
            "world",
            37,
            130.8,
            20,
            "AluminiumEGS",
            [0, 0, 211.005 * mm],
        ),
        (add_tubs, sim, "cyl6", "world", 0, 48, 69, "Tecapeek", [0, 0, 282.255 * mm]),
        (add_cons, sim, "hollow_cone1", "cyl6", 0, 22.5, 0, 31.5, 69, "Air", [0, 0, 0]),
        (add_tubs, sim, "st_6", "world", 48, 72, 16, "Tecapeek", [0, 0, 255.755 * mm]),
        (add_tubs, sim, "st_7", "world", 48, 72, 29, "Tecapeek", [0, 0, 302.255 * mm]),
    ]

    for comp in components:
        func = comp[0]
        sim = comp[1]
        name = comp[2]
        mother = comp[3]
        *args, material, translation = comp[4:]

        func(
            sim,
            name,
            mother,
            *args,
            material,
            offset(mother, translation),
            material_colors=material_colors,
        )
    start_z, end_z = get_object_zdimension(components, center_z)

    logger.info(
        f"Linac structure range: start at {start_z:.3f} mm, end at {end_z:.3f} mm"
    )
    return end_z


def build_passive_collimation(
    sim, string_name, center_x=0, center_y=0, center_z=0, material_colors=None
):
    """
    Builds a passive collimation structure.

    Args:
        sim: The simulation object where volumes are added.
        string_name (str): Identifier for the collimator type. Allowed values are:
            - 'app100'
            - 'app40'
            - 'app70'
            - 'shaper40'
            - 'mb_40_holes_11'
            - 'mb_40_slit_11'
        center_x (float, optional): X-axis offset (in mm) applied to all components. Defaults to 0.
        center_y (float, optional): Y-axis offset (in mm) applied to all components. Defaults to 0.
        center_z (float, optional): Z-axis offset (in mm) applied to all components. Defaults to 0.
        material_colors (dict, optional): Dictionary mapping material names to colors.

    Raises:
        ValueError: If `string_name` is not one of the allowed applicator types.

    Returns:
        float: The Z-coordinate (in mm) of the end position of the constructed collimator structure.
    """
    mm = gate.g4_units.mm
    if material_colors is None:
        material_colors = {}

    allowed_names = [
        "app100",
        "app40",
        "app70",
        "shaper40",
        "mb_40_holes_11",
        "mb_40_slit_11",
    ]
    if string_name not in allowed_names:
        raise ValueError(
            f"[ERROR] Unsupported applicator type: '{string_name}'. Allowed applicators are: {allowed_names}"
        )

    def offset(mother, pos):
        if mother == "world":
            return [pos[0] + center_x, pos[1] + center_y, pos[2] + center_z]
        return pos

    if string_name == "app100":
        components = [
            (add_tubs, sim, "cyl7", "world", 0, 72, 42.8, "PMMA", [0, 0, 21.4]),
            (
                add_tubs,
                sim,
                "hollow_cyl",
                "cyl7",
                0,
                31.5,
                10,
                "Air",
                [0, 0, -16.4 * mm],
            ),
            (
                add_cons,
                sim,
                "hollow_cone2",
                "cyl7",
                0,
                31.5,
                0,
                50,
                32.8,
                "Air",
                [0, 0, 5 * mm],
            ),
            (add_tubs, sim, "st_8", "world", 55, 72, 14.8, "PMMA", [0, 0, 50.2 * mm]),
            (add_tubs, sim, "app100", "world", 50, 55, 742, "PMMA", [0, 0, 413.8 * mm]),
        ]
    elif string_name == "app40":
        components = [
            (add_tubs, sim, "cyl7", "world", 0, 72, 42.8, "PMMA", [0, 0, 21.4]),
            (
                add_cons,
                sim,
                "hollow_cone2",
                "cyl7",
                0,
                31.5,
                0,
                20,
                42.8,
                "Air",
                [0, 0, 0],
            ),
            (add_tubs, sim, "st_8", "world", 25, 72, 10, "PMMA", [0, 0, 47.8 * mm]),
            (add_tubs, sim, "app40", "world", 20, 25, 357, "PMMA", [0, 0, 231.3 * mm]),
        ]
    elif string_name == "shaper40":
        components = [
            (add_tubs, sim, "cyl_s", "world", 25.2, 26, 50, "PMMA", [0, 0, -28]),
            (add_tubs, sim, "cyl_p", "world", 25.2, 75, 5, "PMMA", [0, 0, -0.5]),
        ]
        leaf_defs = [
            ("leaf1", [12.5, 0, 3.5]),
            ("leaf2", [-12.5, 0, 3.5]),
            ("leaf3", [0, 12.5, 8.5]),
            ("leaf4", [0, -12.5, 8.5]),
        ]
        leaf_components = [
            (
                add_box,
                sim,
                name,
                "world",
                25 if name in ["leaf1", "leaf2"] else 50,
                50 if name in ["leaf1", "leaf2"] else 25,
                3,
                "Tungsten",
                pos,
            )
            for name, pos in leaf_defs
        ]
        final_components = components + leaf_components
    elif string_name == "mb_40_holes_11":
        positions = [[x, y, 0] for x in [-4, -2, 0, 2, 4] for y in [-4, -2, 0, 2, 4]]

        components = [
            (
                add_tubs,
                sim,
                "cyl_mb1",
                "world",
                25.2,
                40,
                25,
                "Tecapeek",
                [0, 0, -12.5],
            ),  # 338.155
            (add_box, sim, "slab1", "world", 5, 50, 2.5, "Tecapeek", [22.5, 0, 3.75]),
            (add_box, sim, "slab2", "world", 5, 50, 2.5, "Tecapeek", [-22.5, 0, 3.75]),
            (add_box, sim, "slab3", "world", 40, 5, 2.5, "Tecapeek", [0, -22.5, 3.75]),
        ]
    elif string_name == "mb_40_slit_11":
        positions = [[x, 0, 0] for x in [-4, -2, 0, 2, 4]]

        components = [
            (
                add_tubs,
                sim,
                "cyl_mb1",
                "world",
                25.2,
                40,
                25,
                "Tecapeek",
                [0, 0, -12.5],
            ),  # 338.155
            # (add_box , sim, "plate1", "world", 50  , 50,  2.5,  "Tungsten",   [0, 0, 1.25]),
            # (add_box , sim, "plate2", "world", 40  , 40,  2.5,  "Tungsten",   [0, 0, 3.75]),
            (add_box, sim, "slab1", "world", 5, 50, 2.5, "Tecapeek", [22.5, 0, 3.75]),
            (add_box, sim, "slab2", "world", 5, 50, 2.5, "Tecapeek", [-22.5, 0, 3.75]),
            (add_box, sim, "slab3", "world", 40, 5, 2.5, "Tecapeek", [0, -22.5, 3.75]),
        ]

    for comp in components:
        func = comp[0]
        sim = comp[1]
        name = comp[2]
        mother = comp[3]
        *args, material, translation = comp[4:]

        func(
            sim,
            name,
            mother,
            *args,
            material,
            offset(mother, translation),
            material_colors=material_colors,
        )

    if string_name == "shaper40":
        leaf_objects = []
        for name, pos in leaf_defs:
            obj = add_box(
                sim,
                name,
                "world",
                25 if "leaf1" in name or "leaf2" in name else 50,
                50 if "leaf1" in name or "leaf2" in name else 25,
                3,
                "Tungsten",
                offset("world", pos),
                material_colors=material_colors,
            )
            leaf_objects.append(obj)

    if string_name == "mb_40_holes_11":
        plate_1 = add_box(
            sim,
            "plate1",
            "world",
            50,
            50,
            2.5,
            "Tungsten",
            offset("world", [0, 0, 1.25]),
        )
        plate_2 = add_box(
            sim,
            "plate2",
            "world",
            40,
            40,
            2.5,
            "Tungsten",
            offset("world", [0, 0, 3.75]),
        )

        hole1_1 = add_box(
            sim, "hole1_1", plate_1, 1 * mm, 1 * mm, 2.5 * mm, "Air", positions[0]
        )
        hole1_2 = add_box(
            sim, "hole1_2", plate_1, 1 * mm, 1 * mm, 2.5 * mm, "Air", positions[1]
        )
        hole1_3 = add_box(
            sim, "hole1_3", plate_1, 1 * mm, 1 * mm, 2.5 * mm, "Air", positions[2]
        )
        hole1_4 = add_box(
            sim, "hole1_4", plate_1, 1 * mm, 1 * mm, 2.5 * mm, "Air", positions[3]
        )
        hole1_5 = add_box(
            sim, "hole1_5", plate_1, 1 * mm, 1 * mm, 2.5 * mm, "Air", positions[4]
        )
        hole1_6 = add_box(
            sim, "hole1_6", plate_1, 1 * mm, 1 * mm, 2.5 * mm, "Air", positions[5]
        )
        hole1_7 = add_box(
            sim, "hole1_7", plate_1, 1 * mm, 1 * mm, 2.5 * mm, "Air", positions[6]
        )
        hole1_8 = add_box(
            sim, "hole1_8", plate_1, 1 * mm, 1 * mm, 2.5 * mm, "Air", positions[7]
        )
        hole1_9 = add_box(
            sim, "hole1_9", plate_1, 1 * mm, 1 * mm, 2.5 * mm, "Air", positions[8]
        )
        hole1_10 = add_box(
            sim, "hole1_10", plate_1, 1 * mm, 1 * mm, 2.5 * mm, "Air", positions[9]
        )
        hole1_11 = add_box(
            sim, "hole1_11", plate_1, 1 * mm, 1 * mm, 2.5 * mm, "Air", positions[10]
        )
        hole1_12 = add_box(
            sim, "hole1_12", plate_1, 1 * mm, 1 * mm, 2.5 * mm, "Air", positions[11]
        )
        hole1_13 = add_box(
            sim, "hole1_13", plate_1, 1 * mm, 1 * mm, 2.5 * mm, "Air", positions[12]
        )
        hole1_14 = add_box(
            sim, "hole1_14", plate_1, 1 * mm, 1 * mm, 2.5 * mm, "Air", positions[13]
        )
        hole1_15 = add_box(
            sim, "hole1_15", plate_1, 1 * mm, 1 * mm, 2.5 * mm, "Air", positions[14]
        )
        hole1_16 = add_box(
            sim, "hole1_16", plate_1, 1 * mm, 1 * mm, 2.5 * mm, "Air", positions[15]
        )
        hole1_17 = add_box(
            sim, "hole1_17", plate_1, 1 * mm, 1 * mm, 2.5 * mm, "Air", positions[16]
        )
        hole1_18 = add_box(
            sim, "hole1_18", plate_1, 1 * mm, 1 * mm, 2.5 * mm, "Air", positions[17]
        )
        hole1_19 = add_box(
            sim, "hole1_19", plate_1, 1 * mm, 1 * mm, 2.5 * mm, "Air", positions[18]
        )
        hole1_20 = add_box(
            sim, "hole1_20", plate_1, 1 * mm, 1 * mm, 2.5 * mm, "Air", positions[19]
        )
        hole1_21 = add_box(
            sim, "hole1_21", plate_1, 1 * mm, 1 * mm, 2.5 * mm, "Air", positions[20]
        )
        hole1_22 = add_box(
            sim, "hole1_22", plate_1, 1 * mm, 1 * mm, 2.5 * mm, "Air", positions[21]
        )
        hole1_23 = add_box(
            sim, "hole1_23", plate_1, 1 * mm, 1 * mm, 2.5 * mm, "Air", positions[22]
        )
        hole1_24 = add_box(
            sim, "hole1_24", plate_1, 1 * mm, 1 * mm, 2.5 * mm, "Air", positions[23]
        )
        hole1_25 = add_box(
            sim, "hole1_25", plate_1, 1 * mm, 1 * mm, 2.5 * mm, "Air", positions[24]
        )
        hole2_1 = add_box(
            sim, "hole2_1", plate_2, 1 * mm, 1 * mm, 2.5 * mm, "Air", positions[0]
        )
        hole2_2 = add_box(
            sim, "hole2_2", plate_2, 1 * mm, 1 * mm, 2.5 * mm, "Air", positions[1]
        )
        hole2_3 = add_box(
            sim, "hole2_3", plate_2, 1 * mm, 1 * mm, 2.5 * mm, "Air", positions[2]
        )
        hole2_4 = add_box(
            sim, "hole2_4", plate_2, 1 * mm, 1 * mm, 2.5 * mm, "Air", positions[3]
        )
        hole2_5 = add_box(
            sim, "hole2_5", plate_2, 1 * mm, 1 * mm, 2.5 * mm, "Air", positions[4]
        )
        hole2_6 = add_box(
            sim, "hole2_6", plate_2, 1 * mm, 1 * mm, 2.5 * mm, "Air", positions[5]
        )
        hole2_7 = add_box(
            sim, "hole2_7", plate_2, 1 * mm, 1 * mm, 2.5 * mm, "Air", positions[6]
        )
        hole2_8 = add_box(
            sim, "hole2_8", plate_2, 1 * mm, 1 * mm, 2.5 * mm, "Air", positions[7]
        )
        hole2_9 = add_box(
            sim, "hole2_9", plate_2, 1 * mm, 1 * mm, 2.5 * mm, "Air", positions[8]
        )
        hole2_10 = add_box(
            sim, "hole2_10", plate_2, 1 * mm, 1 * mm, 2.5 * mm, "Air", positions[9]
        )
        hole2_11 = add_box(
            sim, "hole2_11", plate_2, 1 * mm, 1 * mm, 2.5 * mm, "Air", positions[10]
        )
        hole2_12 = add_box(
            sim, "hole2_12", plate_2, 1 * mm, 1 * mm, 2.5 * mm, "Air", positions[11]
        )
        hole2_13 = add_box(
            sim, "hole2_13", plate_2, 1 * mm, 1 * mm, 2.5 * mm, "Air", positions[12]
        )
        hole2_14 = add_box(
            sim, "hole2_14", plate_2, 1 * mm, 1 * mm, 2.5 * mm, "Air", positions[13]
        )
        hole2_15 = add_box(
            sim, "hole2_15", plate_2, 1 * mm, 1 * mm, 2.5 * mm, "Air", positions[14]
        )
        hole2_16 = add_box(
            sim, "hole2_16", plate_2, 1 * mm, 1 * mm, 2.5 * mm, "Air", positions[15]
        )
        hole2_17 = add_box(
            sim, "hole2_17", plate_2, 1 * mm, 1 * mm, 2.5 * mm, "Air", positions[16]
        )
        hole2_18 = add_box(
            sim, "hole2_18", plate_2, 1 * mm, 1 * mm, 2.5 * mm, "Air", positions[17]
        )
        hole2_19 = add_box(
            sim, "hole2_19", plate_2, 1 * mm, 1 * mm, 2.5 * mm, "Air", positions[18]
        )
        hole2_20 = add_box(
            sim, "hole2_20", plate_2, 1 * mm, 1 * mm, 2.5 * mm, "Air", positions[19]
        )
        hole2_21 = add_box(
            sim, "hole2_21", plate_2, 1 * mm, 1 * mm, 2.5 * mm, "Air", positions[20]
        )
        hole2_22 = add_box(
            sim, "hole2_22", plate_2, 1 * mm, 1 * mm, 2.5 * mm, "Air", positions[21]
        )
        hole2_23 = add_box(
            sim, "hole2_23", plate_2, 1 * mm, 1 * mm, 2.5 * mm, "Air", positions[22]
        )
        hole2_24 = add_box(
            sim, "hole2_24", plate_2, 1 * mm, 1 * mm, 2.5 * mm, "Air", positions[23]
        )
        hole2_25 = add_box(
            sim, "hole2_25", plate_2, 1 * mm, 1 * mm, 2.5 * mm, "Air", positions[24]
        )

    elif string_name == "mb_40_slit_11":
        plate_1 = add_box(
            sim,
            "plate1",
            "world",
            50,
            50,
            2.5,
            "Tungsten",
            offset("world", [0, 0, 1.25]),
        )
        plate_2 = add_box(
            sim,
            "plate2",
            "world",
            40,
            40,
            2.5,
            "Tungsten",
            offset("world", [0, 0, 3.75]),
        )
        hole1_1 = add_box(
            sim, "hole1_1", plate_1, 1 * mm, 10 * mm, 2.5 * mm, "Air", positions[0]
        )
        hole1_2 = add_box(
            sim, "hole1_2", plate_1, 1 * mm, 10 * mm, 2.5 * mm, "Air", positions[1]
        )
        hole1_3 = add_box(
            sim, "hole1_3", plate_1, 1 * mm, 10 * mm, 2.5 * mm, "Air", positions[2]
        )
        hole1_4 = add_box(
            sim, "hole1_4", plate_1, 1 * mm, 10 * mm, 2.5 * mm, "Air", positions[3]
        )
        hole1_5 = add_box(
            sim, "hole1_5", plate_1, 1 * mm, 10 * mm, 2.5 * mm, "Air", positions[4]
        )
        hole2_1 = add_box(
            sim, "hole2_1", plate_2, 1 * mm, 10 * mm, 2.5 * mm, "Air", positions[0]
        )
        hole2_2 = add_box(
            sim, "hole2_2", plate_2, 1 * mm, 10 * mm, 2.5 * mm, "Air", positions[1]
        )
        hole2_3 = add_box(
            sim, "hole2_3", plate_2, 1 * mm, 10 * mm, 2.5 * mm, "Air", positions[2]
        )
        hole2_4 = add_box(
            sim, "hole2_4", plate_2, 1 * mm, 10 * mm, 2.5 * mm, "Air", positions[3]
        )
        hole2_5 = add_box(
            sim, "hole2_5", plate_2, 1 * mm, 10 * mm, 2.5 * mm, "Air", positions[4]
        )

    if string_name == "shaper40":
        start_z, end_z = get_object_zdimension(final_components, center_z)
        logger.info(
            f"Passive collimator - '{string_name}' - range: start at {start_z:.3f} mm, end at {end_z:.3f} mm"
        )
        return end_z, leaf_objects

    elif string_name == ("mb_40_holes_11" or "mb_40_slit_11"):
        start_z, end_z = get_object_zdimension(components, center_z)
        logger.info(
            f"Passive collimator - '{string_name}' - range: start at {start_z:.3f} mm, end at {end_z:.3f} mm"
        )
        return end_z

    else:
        start_z, end_z = get_object_zdimension(components, center_z)
        logger.info(
            f"Passive collimator - '{string_name}' - range: start at {start_z:.3f} mm, end at {end_z:.3f} mm"
        )
        return end_z


def build_dosephantombox(
    sim,
    _string_name,
    material,
    center_x=0,
    center_y=0,
    center_z=0,
    dimension_x=None,
    dimension_y=None,
    dimension_z=None,
    material_colors=None,
):
    """
    Creates and adds a box-shaped volume to the simulation representing a typical dose phantom.

    Args:
        sim: The simulation object where volumes are added.
        _string_name (str): Unique identifier name for the box volume.
        material (str): The material name assigned to the box volume.
        center_x (float, optional): X-coordinate (in mm) of the box center. Defaults to 0.
        center_y (float, optional): Y-coordinate (in mm) of the box center. Defaults to 0.
        center_z (float, optional): Z-coordinate (in mm) of the box center. Defaults to 0.
        dimension_x (float): Size of the box along the X-axis (in mm). Must be specified.
        dimension_y (float): Size of the box along the Y-axis (in mm). Must be specified.
        dimension_z (float): Size of the box along the Z-axis (in mm). Must be specified.
        material_colors (dict, optional): Dictionary mapping material names to color values.

    Raises:
        ValueError: If any of the dimensions (dimension_x, dimension_y, dimension_z) are None.

    Returns:
        Volume: The created box volume object added to the simulation.
    """
    if None in (dimension_x, dimension_y, dimension_z):
        raise ValueError(
            "[ERROR] All dimensions (dimension_x, dimension_y, dimension_z) must be specified."
        )

    if material_colors is None:
        material_colors = {}

    box = sim.add_volume("Box", _string_name)
    box.mother = "world"
    box.size = [dimension_x, dimension_y, dimension_z]
    box.material = material
    box.translation = [center_x, center_y, center_z]

    if material in material_colors:
        box.color = material_colors[material]

    logger.info(
        f"Box - '{_string_name}' - of material '{material}' built at: "
        f"({center_x:.3f}, {center_y:.3f}, {center_z:.3f}) mm with size: "
        f"{dimension_x:.3f} x {dimension_y:.3f} x {dimension_z:.3f} mm."
    )

    return box


def add_source(sim, number_of_events):
    """
    Adds an electron source to the simulation with a discrete energy spectrum loaded from a file.

    Args:
        sim: The simulation object to which the source is added.
        number_of_events (int): Number of events to simulate from the source.

    Returns:
        source: The created source object.
    """
    mm = gate.g4_units.mm
    spectrum_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "utils", "spectra", "9Mev.txt"
    )
    source = sim.add_source("GenericSource", "source")
    source.particle = "e-"
    source.energy.type = "spectrum_discrete"
    source.energy.spectrum_energies, source.energy.spectrum_weights = np.loadtxt(
        spectrum_path, unpack=True
    )
    source.position.type = "disc"
    source.position.radius = 3 * mm

    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]

    source.n = number_of_events

    logger.info(
        f"Added source with spectrum from '{spectrum_path}', "
        f"number of events: {number_of_events}, "
        f"position radius: {source.position.radius} mm."
    )

    return source


def set_shaper_aperture(leaf1, leaf2, leaf3, leaf4, aperture_x_mm, aperture_y_mm):
    """
    Adjusts leaf positions to create a square/rectangular aperture.

    Args:
        leaf1, leaf2: Leaves that define the X direction.
        leaf3, leaf4: Leaves that define the Y direction.
        aperture_x_mm (float): Desired aperture in X direction (must be <= 40 mm).
        aperture_y_mm (float): Desired aperture in Y direction (must be <= 40 mm).

    Raises:
        ValueError: If aperture_x_mm or aperture_y_mm exceeds 40 mm.
    """
    if aperture_x_mm > 40 or aperture_y_mm > 40:
        raise ValueError(
            f"[ERROR] Requested aperture exceeds maximum of 40 mm: "
            f"X = {aperture_x_mm:.2f}, Y = {aperture_y_mm:.2f}"
        )

    half_x = aperture_x_mm / 2
    half_y = aperture_y_mm / 2

    # Update X leaves (left/right)
    leaf1.translation[0] = half_x + leaf1.size[0] / 2  # right
    leaf2.translation[0] = -half_x - leaf2.size[0] / 2  # left

    # Update Y leaves (top/bottom)
    leaf3.translation[1] = half_y + leaf3.size[1] / 2  # top
    leaf4.translation[1] = -half_y - leaf4.size[1] / 2  # bottom


def rotate_leaves_around_z(leaf1, leaf2, leaf3, leaf4, angle_deg):
    rot = R.from_euler("z", angle_deg, degrees=True)
    rot_matrix = rot.as_matrix()  # shape (3,3)

    for leaf in [leaf1, leaf2, leaf3, leaf4]:
        x, y, z = leaf.translation
        pos_rotated = rot.apply([x, y, z])
        leaf.translation = pos_rotated.tolist()
        leaf.rotation = rot_matrix


def obtain_pdd_from_image(path, mean_size=10):
    """
    Loads a dose image and computes the normalized Percent Depth Dose (PDD)
    from a central square ROI.

    Parameters:
        path (str or Path): Path to the .mhd dose file.

    Returns:
        pdd (np.ndarray): Normalized 1D PDD profile along depth (Z-axis).
    """
    image = sitk.ReadImage(str(path))
    dose_array = sitk.GetArrayFromImage(image)

    y_center, x_center = int(dose_array.shape[1] / 2), int(dose_array.shape[2] / 2)
    half = mean_size // 2
    roi_y = slice(y_center - half, y_center + half)
    roi_x = slice(x_center - half, x_center + half)

    pdd = np.mean(dose_array[:, roi_y, roi_x], axis=(1, 2))
    pdd /= np.max(pdd)

    return pdd


def obtain_profile_from_image(path, mean_size=10):
    """
    Loads a dose image and computes the normalized Percent Depth Dose (PDD)
    from a central square ROI.

    Parameters:
        path (str or Path): Path to the .mhd dose file.

    Returns:
        pdd (np.ndarray): Normalized 1D PDD profile along depth (Z-axis).
    """
    image = sitk.ReadImage(str(path))
    dose_array = sitk.GetArrayFromImage(image)

    profile = np.mean(dose_array[0:7, 120:130, :], axis=(0, 1))
    profile /= np.max(profile)

    return profile


def evaluate_pdd_similarity(reference_pdd, test_pdd, tolerance=0.03):
    """
    Compares two PDD curves using Mean Absolute Error (MAE).

    Parameters:
        reference_pdd (np.1darray): Reference PDD curve (normalized).
        test_pdd (np.1darray)     : Test PDD curve (normalized).
        tolerance (float)         : MAE tolerance threshold.

    Returns:
        passed (bool): True if MAE < tolerance.
    """
    mae = np.mean(np.abs(reference_pdd - test_pdd))
    passed = mae < tolerance

    return passed, mae


def evaluate_profile_similarity(reference_profile, test_profile, tolerance=0.2):
    """
    Compares two PDD curves using Mean Absolute Error (MAE).

    Parameters:
        reference_pdd (np.1darray): Reference PDD curve (normalized).
        test_pdd (np.1darray)     : Test PDD curve (normalized).
        tolerance (float)         : MAE tolerance threshold.

    Returns:
        passed (bool): True if MAE < tolerance.
    """
    mae = np.mean(np.abs(reference_profile - test_profile))
    passed = mae < tolerance

    return passed, mae
