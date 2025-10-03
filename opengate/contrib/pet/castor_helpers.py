import json
import opengate_core as g4
from opengate.geometry.utility import vec_g4_as_np, rot_g4_as_np
import numpy as np


def set_hook_castor_config(sim, crystal_name, filename):
    """
    Prepare everything to create the castor config file at the init of the simulation.
    The param structure allows to retrieve the castor config at the end of the simulation.
    """
    # create the param structure
    param = {
        "volume_name": crystal_name,
        "output_filename": filename,
        "castor_config": None,
    }
    sim.user_hook_after_init = create_castor_config
    sim.user_hook_after_init_arg = param
    return param


def create_castor_config(simulation_engine, param):
    castor_config = {
        "rotation": [],
        "size": [],
        "translation": [],
        "unique_volume_id": [],
    }

    volume_name = param["volume_name"]
    touchables = g4.FindAllTouchables(volume_name)
    m = g4.GateUniqueVolumeIDManager.GetInstance()

    # update the unique volume id and other parameters
    for touchable in touchables:
        unique_vol = m.GetVolumeID(touchable)
        # suid = unique_vol.fID
        uid = unique_vol.fNumericID
        translation = vec_g4_as_np(touchable.GetTranslation(0))
        rotation = rot_g4_as_np(touchable.GetRotation(0).inverse())
        solid = touchable.GetSolid(0)
        pMin_local = g4.G4ThreeVector()
        pMax_local = g4.G4ThreeVector()
        solid.BoundingLimits(pMin_local, pMax_local)
        size = [
            pMax_local.x - pMin_local.x,
            pMax_local.y - pMin_local.y,
            pMax_local.z - pMin_local.z,
        ]
        r = [rotation[i].tolist() for i in range(3)]
        castor_config["rotation"].append(r)
        castor_config["translation"].append(translation.tolist())
        # castor_config["unique_volume_id"].append(suid)
        castor_config["unique_volume_id"].append(uid)
        castor_config["size"].append(size)

    # write the dict as json
    filename = param["output_filename"]
    if filename is not None:
        with open(filename, "w") as f:
            json.dump(castor_config, f, indent=4)

    for key in ["translation", "rotation", "size"]:
        castor_config[key] = np.array(castor_config[key])

    # Convert to numpy arrays for calculations
    param["castor_config"] = castor_config
    return castor_config


def build_castor_config_volume_index(castor_config):
    """
    Create a dictionary mapping unique_volume_id to its index for fast lookup.
    """
    volume_index = {vid: i for i, vid in enumerate(castor_config["unique_volume_id"])}
    return volume_index


def rotation_matrix_to_axis_angle(matrix: np.ndarray):
    """
    Converts a 3x3 rotation matrix to the axis-angle representation required by VRML.

    Args:
        matrix: A 3x3 NumPy array representing the rotation matrix.

    Returns:
        A tuple containing the axis (3-element NumPy array) and the angle in radians.
    """
    R = np.array(matrix, dtype=np.float64)

    # The trace of a rotation matrix is 1 + 2*cos(theta)
    # We clip the value to the valid range of acos to handle potential floating point inaccuracies
    trace_val = np.trace(R)
    cos_theta = np.clip((trace_val - 1.0) / 2.0, -1.0, 1.0)
    theta = np.arccos(cos_theta)

    # If the angle is very close to 0, it's an identity rotation. The axis is arbitrary.
    if np.isclose(theta, 0.0):
        return np.array([0, 1, 0]), 0.0

    # If the angle is very close to pi, the axis calculation requires a special case
    # to avoid division by zero and maintain numerical stability.
    if np.isclose(theta, np.pi):
        # Find the axis vector from the matrix elements
        xx, yy, zz = (R[0, 0] + 1) / 2, (R[1, 1] + 1) / 2, (R[2, 2] + 1) / 2
        xy, xz, yz = (
            (R[0, 1] + R[1, 0]) / 4,
            (R[0, 2] + R[2, 0]) / 4,
            (R[1, 2] + R[2, 1]) / 4,
        )
        if xx > yy and xx > zz:
            x = np.sqrt(xx)
            y = xy / x
            z = xz / x
        elif yy > zz:
            y = np.sqrt(yy)
            x = xy / y
            z = yz / y
        else:
            z = np.sqrt(zz)
            x = xz / z
            y = yz / z
        axis = np.array([x, y, z])
        return axis / np.linalg.norm(axis), theta

    # The general case for finding the axis
    sin_theta = np.sin(theta)
    axis_x = (R[2, 1] - R[1, 2]) / (2 * sin_theta)
    axis_y = (R[0, 2] - R[2, 0]) / (2 * sin_theta)
    axis_z = (R[1, 0] - R[0, 1]) / (2 * sin_theta)

    axis = np.array([axis_x, axis_y, axis_z])
    return axis / np.linalg.norm(axis), theta


def create_vrml_from_config(
    config_filepath: str, output_vrml_path: str, axis_length: float = 150.0
):
    """
    Reads a castor_config.json file and generates a VRML 2.0 file
    visualizing all crystals as 3D boxes and a coordinate system at the origin.
    This version uses cylinders for the axes to ensure they are always visible.

    Args:
        config_filepath: Path to the input castor_config.json file.
        output_vrml_path: Path for the output .wrl file.
        axis_length: The length of the X, Y, Z axes to be drawn at the origin.
    """
    print(f"Reading geometry configuration from: {config_filepath}")
    with open(config_filepath, "r") as f:
        config = json.load(f)

    translations = config["translation"]
    rotations = config["rotation"]
    sizes = config["size"]
    num_crystals = len(translations)

    print(f"Generating VRML file for {num_crystals} crystals at: {output_vrml_path}")

    with open(output_vrml_path, "w") as f:
        # VRML Header
        f.write("#VRML V2.0 utf8\n")
        f.write("# Generated by OpenGATE analysis script\n\n")
        f.write("Background { skyColor [0 0 0] } # White background\n")
        f.write('NavigationInfo { type ["EXAMINE", "ANY"] }\n\n')

        # --- Add world coordinate system axes using Cylinders ---
        f.write("# --- World Coordinate System Axes ---\n")
        axis_radius = axis_length / 200.0  # Keep the cylinders thin
        half_length = axis_length / 2.0

        # X-Axis (Red)
        f.write("Transform {\n")
        f.write(f"  translation {half_length} 0 0\n")
        f.write("  rotation 0 0 1 1.5708 # 90 deg around Z\n")
        f.write("  children Shape {\n")
        f.write(
            "    appearance Appearance { material Material { diffuseColor 1 0 0 } }\n"
        )
        f.write(
            f"    geometry Cylinder {{ radius {axis_radius} height {axis_length} }}\n"
        )
        f.write("  }\n}\n")

        # Y-Axis (Green)
        f.write("Transform {\n")
        f.write(f"  translation 0 {half_length} 0\n")
        # No rotation needed as Cylinder is oriented along Y by default
        f.write("  children Shape {\n")
        f.write(
            "    appearance Appearance { material Material { diffuseColor 0 1 0 } }\n"
        )
        f.write(
            f"    geometry Cylinder {{ radius {axis_radius} height {axis_length} }}\n"
        )
        f.write("  }\n}\n")

        # Z-Axis (Blue)
        f.write("Transform {\n")
        f.write(f"  translation 0 0 {half_length}\n")
        f.write("  rotation 1 0 0 1.5708 # 90 deg around X\n")
        f.write("  children Shape {\n")
        f.write(
            "    appearance Appearance { material Material { diffuseColor 0 0 1 } }\n"
        )
        f.write(
            f"    geometry Cylinder {{ radius {axis_radius} height {axis_length} }}\n"
        )
        f.write("  }\n}\n\n")

        f.write("# --- Crystal Geometries ---\n")
        for i in range(num_crystals):
            tr = translations[i]
            rot_matrix = np.array(rotations[i])
            size = sizes[i]
            axis, angle = rotation_matrix_to_axis_angle(rot_matrix)

            f.write(f"# Crystal instance #{i}\n")
            f.write("Transform {\n")
            f.write(f"  translation {tr[0]:.4f} {tr[1]:.4f} {tr[2]:.4f}\n")
            f.write(
                f"  rotation {axis[0]:.4f} {axis[1]:.4f} {axis[2]:.4f} {angle:.4f}\n"
            )
            f.write("  children [ Shape {\n")
            f.write("    appearance Appearance {\n")
            f.write("      material Material {\n")
            f.write("        diffuseColor 0.2 0.5 0.9\n")
            f.write("        transparency 0.5\n")
            f.write("      }\n")
            f.write("    }\n")
            f.write("    geometry Box {\n")
            f.write(f"      size {size[0]:.4f} {size[1]:.4f} {size[2]:.4f}\n")
            f.write("    }\n")
            f.write("  } ]\n}\n\n")

    print("VRML file generation complete.")
