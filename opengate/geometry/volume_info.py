import matplotlib.pyplot as plt
import numpy as np
import matplotlib.patches as patches
import matplotlib.cm as cm
from box import Box
import opengate_core as g4
from opengate.geometry.utility import vec_g4_as_np, rot_g4_as_np
import json


def store_volumes_info(sim, json_filename):
    # get the pointers to the Geant4 volumes
    vol_info_raw = get_g4_volumes_pointers(sim)

    for k, vol in vol_info_raw.items():
        print(k, vol)

    # Prepare a dictionary to hold processed volume data with world coordinates
    processed_volumes = serialize_volume_data(vol_info_raw)

    # save as json
    with open(json_filename, "w") as f:
        json.dump(processed_volumes, f, indent=4)


# Helper function to get the 8 corners of a bounding box
def _get_bbox_corners(xmin, ymin, zmin, xmax, ymax, zmax):
    """Returns the 8 corners of a bounding box."""
    corners = np.array(
        [
            [xmin, ymin, zmin, 1],
            [xmax, ymin, zmin, 1],
            [xmin, ymax, zmin, 1],
            [xmin, ymin, zmax, 1],
            [xmax, ymax, zmin, 1],
            [xmin, ymax, zmax, 1],
            [xmax, ymin, zmax, 1],
            [xmax, ymax, zmax, 1],
        ]
    )
    return corners


# Helper function to create a 4x4 homogeneous transformation matrix
def _create_transform_matrix(rotation_list, translation_list):
    """
    Creates a 4x4 homogeneous transformation matrix from a 3x3 rotation matrix
    and a 3-element translation vector.
    """
    transform_matrix = np.identity(4)
    if rotation_list is not None:
        transform_matrix[:3, :3] = np.array(rotation_list)
    if translation_list is not None:
        transform_matrix[:3, 3] = np.array(translation_list)
    return transform_matrix


# Recursive function to get the transformation matrix from a volume's local frame to the world frame
def _get_world_transform_matrix(volume_name, all_volume_data, memo={}):
    """
    Recursively calculates the cumulative transformation matrix from a volume's
    local coordinate system to the world coordinate system.
    Uses memoization to avoid redundant calculations.
    """
    if volume_name in memo:
        return memo[volume_name]

    if volume_name not in all_volume_data:
        # This case should ideally not happen if data is consistent, but handle defensively
        print(
            f"Warning: Volume '{volume_name}' not found in provided data. Assuming identity transform."
        )
        return np.identity(4)

    vol_info = all_volume_data[volume_name]

    # Get the transformation of the current volume relative to its mother
    local_rotation = vol_info.get("object_rotation")
    local_translation = vol_info.get("object_translation")

    # If object_translation/rotation is None, it means identity for placement
    if local_rotation is None:
        local_rotation = np.identity(3).tolist()
    if local_translation is None:
        local_translation = [0.0, 0.0, 0.0]

    current_transform = _create_transform_matrix(local_rotation, local_translation)

    mother_name = vol_info.get("mother")

    if mother_name is None:  # This is a top-level volume (like 'world' or 'arf_world')
        world_transform = current_transform
    else:
        # Recursively get the mother's transform to the world
        mother_world_transform = _get_world_transform_matrix(
            mother_name, all_volume_data, memo
        )
        # Combine current transform with mother's world transform
        world_transform = np.dot(mother_world_transform, current_transform)

    memo[volume_name] = world_transform
    return world_transform


def get_g4_volumes_pointers(sim):
    store = g4.G4PhysicalVolumeStore.GetInstance()
    map = store.GetMap()
    volumes = Box()
    for volume_name, volume_list in map.items():
        v = Box()
        v.physical_volume = volume_list[0]
        v.logical_volume = v.physical_volume.GetLogicalVolume()
        v.solid = v.logical_volume.GetSolid()
        volumes[str(volume_name)] = v

    return volumes


def serialize_volume_data(vol_info_raw):
    # Prepare a dictionary to hold processed volume data with world coordinates
    processed_volumes = Box()

    # To calculate world coordinates, serialize_volume_data needs access to
    # the object_translation and object_rotation of all volumes, including mothers.
    # We create a simplified dictionary for the recursive world transform calculation.
    simplified_all_data_for_transform = {
        name: {
            "mother": (
                str(data.physical_volume.GetMotherLogical().GetName())
                if data.physical_volume.GetMotherLogical()
                else None
            ),
            "object_translation": (
                vec_g4_as_np(data.physical_volume.GetObjectTranslation()).tolist()
                if data.physical_volume.GetObjectTranslation()
                else None
            ),
            "object_rotation": (
                rot_g4_as_np(data.physical_volume.GetObjectRotation()).tolist()
                if data.physical_volume.GetObjectRotation()
                else None
            ),
        }
        for name, data in vol_info_raw.items()
    }

    # Iterate through each volume and serialize its data, including world limits
    for k, v_raw in vol_info_raw.items():
        # Pass the raw volume info object and the simplified all_volume_data for recursion
        serialized_data = serialize_one_volume_data(
            v_raw, all_volume_data=simplified_all_data_for_transform
        )
        processed_volumes[k] = serialized_data

    return processed_volumes


def serialize_one_volume_data(vol_info, all_volume_data=None):
    """
    Serializes volume information, including local and world coordinate system
    bounding limits.

    Args:
        vol_info (Box): A Box object containing physical_volume, logical_volume, and solid.
        all_volume_data (dict, optional): The complete dictionary of all volumes,
                                          needed for world coordinate transformation.
                                          If None, world_bounding_limits will not be calculated.
    """
    v = Box()
    # PL
    pl = vol_info.physical_volume
    v.pv_name = str(pl.GetName())
    v.is_replicated = pl.IsReplicated()
    v.is_parameterised = pl.IsParameterised()
    m = pl.GetMotherLogical()
    if m:
        v.mother = str(pl.GetMotherLogical().GetName())
    else:
        v.mother = None
    v.copy_no = pl.GetCopyNo()
    v.object_translation = None
    v.object_rotation = None
    v.frame_translation = None
    v.frame_rotation = None
    if pl.GetObjectTranslation() is not None:
        v.object_translation = vec_g4_as_np(pl.GetObjectTranslation()).tolist()
    if pl.GetObjectRotation() is not None:
        v.object_rotation = rot_g4_as_np(pl.GetObjectRotation()).tolist()
    if pl.GetFrameTranslation() is not None:
        v.frame_translation = vec_g4_as_np(pl.GetFrameTranslation()).tolist()
    if pl.GetFrameRotation() is not None:
        v.frame_rotation = rot_g4_as_np(pl.GetFrameRotation()).tolist()

    # LV
    lv = vol_info.logical_volume
    v.lv_name = str(lv.GetName())
    v.n_daughters = lv.GetNoDaughters()
    v.total_volume_entities = lv.TotalVolumeEntities()
    if lv.GetMaterial() is not None:
        v.material = str(lv.GetMaterial().GetName())
    else:
        v.material = None
    v.daughters = [str(lv.GetDaughter(i).GetName()) for i in range(lv.GetNoDaughters())]
    try:
        if v.material:
            v.mass = lv.GetMass(False, True, None)
    except:
        v.mass = None
    v.instance_id = lv.GetInstanceID()

    # Solid
    solid = vol_info.solid
    v.solid_name = str(solid.GetName())
    pMin_local = g4.G4ThreeVector()
    pMax_local = g4.G4ThreeVector()
    solid.BoundingLimits(pMin_local, pMax_local)

    # Store local bounding limits
    v.bounding_limits_local = [
        pMin_local.x,
        pMin_local.y,
        pMin_local.z,
        pMax_local.x,
        pMax_local.y,
        pMax_local.z,
    ]

    # Calculate world bounding limits if all_volume_data is provided
    v.world_bounding_limits = None
    if all_volume_data is not None:
        local_corners = _get_bbox_corners(*v.bounding_limits_local)
        world_transform_matrix = _get_world_transform_matrix(v.pv_name, all_volume_data)

        transformed_corners = np.dot(
            local_corners, world_transform_matrix.T
        )  # Apply transform

        # Extract min/max from transformed corners
        world_xmin, world_ymin, world_zmin = np.min(transformed_corners[:, :3], axis=0)
        world_xmax, world_ymax, world_zmax = np.max(transformed_corners[:, :3], axis=0)

        v.world_bounding_limits = [
            world_xmin,
            world_ymin,
            world_zmin,
            world_xmax,
            world_ymax,
            world_zmax,
        ]

    v.cubic_volume = solid.GetCubicVolume()
    v.surface_area = solid.GetSurfaceArea()
    v.entity_type = str(solid.GetEntityType())
    v.is_faceted = solid.IsFaceted()
    v.num_of_constituents = solid.GetNumOfConstituents()
    # print(solid.GetConstituentSolid(0))
    # v.constituents_solid = [ str(solid.GetConstituentSolid(i).GetName()) for i in range(solid.GetNumOfConstituents()) ]
    # StreamInfo

    return v


def plot_volume_boundaries(
    volume_data: dict, axis: str = "X", show_labels: bool = True
):
    """
    Plots the bounding box boundaries of Geant4 volumes along a specified axis.

    Args:
        volume_data (dict): A dictionary containing volume information, typically
                            loaded from a JSON file like 'spect_info.json'.
                            Each key is a volume name, and its value is a dict
                            containing 'bounding_limits' (list of [xmin, ymin, zmin, xmax, ymax, zmax]).
        axis (str): The axis along which to plot the boundaries. Can be 'X', 'Y', or 'Z'.
                    Case-insensitive.
        show_labels (bool): If True, display the volume names next to their boundaries.
    """
    # Validate the input axis
    axis = axis.upper()
    if axis not in ["X", "Y", "Z"]:
        print(f"Error: Invalid axis '{axis}'. Please choose 'X', 'Y', or 'Z'.")
        return

    # Determine the indices for the chosen axis
    axis_map = {"X": (0, 3), "Y": (1, 4), "Z": (2, 5)}
    min_idx, max_idx = axis_map[axis]

    fig, ax = plt.subplots(figsize=(12, 8))

    # Prepare data for plotting
    plot_data = []
    for name, info in volume_data.items():
        if "bounding_limits" in info and len(info["bounding_limits"]) == 6:
            limits = info["bounding_limits"]
            min_val = limits[min_idx]
            max_val = limits[max_idx]
            plot_data.append({"name": name, "min": min_val, "max": max_val})
        else:
            print(
                f"Warning: Volume '{name}' missing 'bounding_limits' or invalid format. Skipping."
            )

    # Sort volumes by their minimum boundary along the chosen axis for better visualization
    plot_data.sort(key=lambda x: x["min"])

    y_pos = np.arange(len(plot_data))

    # Plot each volume's boundaries
    for i, vol in enumerate(plot_data):
        # Plot the line representing the extent of the volume along the axis
        ax.plot(
            [vol["min"], vol["max"]],
            [y_pos[i], y_pos[i]],
            marker="o",
            linestyle="-",
            markersize=8,
            label=vol["name"],
        )

        # Add text labels for min and max values
        ax.text(
            vol["min"],
            y_pos[i],
            f'{vol["min"]:.2f}',
            va="center",
            ha="right",
            fontsize=8,
            color="blue",
        )
        ax.text(
            vol["max"],
            y_pos[i],
            f'{vol["max"]:.2f}',
            va="center",
            ha="left",
            fontsize=8,
            color="red",
        )

        # Optionally add volume name label
        if show_labels:
            ax.text(
                vol["max"] + (vol["max"] - vol["min"]) * 0.05,
                y_pos[i],
                vol["name"],
                va="center",
                fontsize=9,
                color="black",
            )

    ax.set_yticks(y_pos)
    ax.set_yticklabels([vol["name"] for vol in plot_data])
    ax.set_xlabel(f"Position along {axis}-axis")
    ax.set_ylabel("Volume Name")
    ax.set_title(f"Geant4 Volume Boundaries along {axis}-axis")
    ax.grid(True, linestyle="--", alpha=0.7)
    plt.tight_layout()
    plt.show()


def plot_volume_boundaries_2d(
    volume_data: dict,
    plane: str = "XY",
    show_labels: bool = True,
    highlight_volumes: list = None,
):
    """
    Plots the 2D bounding boxes of Geant4 volumes along a specified plane.

    Args:
        volume_data (dict): A dictionary containing volume information, typically
                            loaded from a JSON file like 'spect_info.json'.
                            Each key is a volume name, and its value is a dict
                            containing 'bounding_limits' (list of [xmin, ymin, zmin, xmax, ymax, zmax]).
        plane (str): The plane along which to plot the 2D boundaries. Can be 'XY', 'XZ', or 'YZ'.
                     Case-insensitive.
        show_labels (bool): If True, display the volume names near their bounding boxes.
        highlight_volumes (list): A list of volume names to highlight. These volumes will be drawn
                                  last and with a bolder outline.
    """
    plane = plane.upper()
    if plane not in ["XY", "XZ", "YZ"]:
        print(f"Error: Invalid plane '{plane}'. Please choose 'XY', 'XZ', or 'YZ'.")
        return

    if highlight_volumes is None:
        highlight_volumes = []

    # Map plane to corresponding indices in bounding_limits [xmin, ymin, zmin, xmax, ymax, zmax]
    # (x_min_idx, y_min_idx), (x_max_idx, y_max_idx) for the chosen plane's axes
    plane_map = {
        "XY": ((0, 1), (3, 4), "X-axis", "Y-axis"),
        "XZ": ((0, 2), (3, 5), "X-axis", "Z-axis"),
        "YZ": ((1, 2), (4, 5), "Y-axis", "Z-axis"),
    }
    (min1_idx, min2_idx), (max1_idx, max2_idx), xlabel, ylabel = plane_map[plane]

    fig, ax = plt.subplots(figsize=(12, 10))  # Increased figure width for legend

    # Helper to calculate depth
    def _get_volume_depth(volume_name, data, current_depth=0, memo={}):
        if volume_name in memo:
            return memo[volume_name]

        # If the volume itself is not in the provided data (e.g., a mother that's not fully described)
        # or if it's a top-level volume with no mother, consider it as a base depth.
        if volume_name not in data or data[volume_name].get("mother") is None:
            memo[volume_name] = current_depth
            return current_depth
        else:
            mother_name = data[volume_name]["mother"]
            depth = _get_volume_depth(mother_name, data, current_depth + 1, memo)
            memo[volume_name] = depth
            return depth

    # Prepare data for plotting, including depth
    processed_volumes = []
    for name, info in volume_data.items():
        if "world_bounding_limits" in info and len(info["world_bounding_limits"]) == 6:
            depth = _get_volume_depth(name, volume_data)
            processed_volumes.append({"name": name, "info": info, "depth": depth})
        else:
            print(
                f"Warning: Volume '{name}' missing 'world_bounding_limits' or invalid format. Skipping for 2D plot."
            )

    # Sort volumes by depth (ascending), then by name for consistent plotting order
    # This ensures that deeper elements are drawn on top of their parents.
    processed_volumes.sort(key=lambda x: (x["depth"], x["name"]))

    # Separate volumes into normal and highlighted lists
    volumes_to_plot_normal = [
        v for v in processed_volumes if v["name"] not in highlight_volumes
    ]
    volumes_to_plot_highlight = [
        v for v in processed_volumes if v["name"] in highlight_volumes
    ]

    # Ensure highlighted volumes are drawn last by appending them
    # This maintains their depth order relative to each other, but places them on top of all normal volumes.
    plotting_order = volumes_to_plot_normal + volumes_to_plot_highlight

    # Get a colormap for distinct colors
    num_volumes_to_plot = len(plotting_order)
    if num_volumes_to_plot <= 20:
        colors_cmap = cm.get_cmap(
            "tab20", num_volumes_to_plot
        )  # tab20 provides 20 distinct colors
    else:
        colors_cmap = cm.get_cmap(
            "viridis", num_volumes_to_plot
        )  # Viridis for more than 20 distinct colors, perceptually uniform

    color_idx = 0

    # To store min/max for auto-cropping
    all_x_coords = []
    all_y_coords = []

    for vol_entry in plotting_order:
        name = vol_entry["name"]
        info = vol_entry["info"]

        limits = info["world_bounding_limits"]

        # Extract relevant 2D coordinates
        x_min = limits[min1_idx]
        y_min = limits[min2_idx]
        x_max = limits[max1_idx]
        y_max = limits[max2_idx]

        width = x_max - x_min
        height = y_max - y_min

        # Assign a unique color from the colormap
        color = colors_cmap(color_idx)
        color_idx += 1

        # Determine styling for highlighted volumes
        linewidth = 1.5
        edgecolor = color
        if name in highlight_volumes:
            linewidth = 3.0  # Make it bolder
            edgecolor = "black"  # Distinct color for highlight border

        # Create a rectangle patch with unique color and styling
        rect = patches.Rectangle(
            (x_min, y_min),
            width,
            height,
            linewidth=linewidth,
            edgecolor=edgecolor,
            facecolor="none",
            label=name,
        )
        ax.add_patch(rect)

        # Add label to the right of the box
        if show_labels:
            ax.text(
                x_max + width * 0.02,
                y_min + height / 2,
                name,
                ha="left",
                va="center",
                fontsize=8,
                color=color,  # Label text color matches volume color
                bbox=dict(
                    facecolor="white",
                    alpha=0.7,
                    edgecolor="none",
                    boxstyle="round,pad=0.2",
                ),
            )

        # Indicate boundaries on the projected axis
        # X-axis boundaries
        ax.plot(
            [x_min, x_min],
            [y_min, y_min - height * 0.02],
            color=color,
            linestyle="--",
            linewidth=0.8,
        )
        ax.plot(
            [x_max, x_max],
            [y_min, y_min - height * 0.02],
            color=color,
            linestyle="--",
            linewidth=0.8,
        )
        ax.text(
            x_min,
            y_min - height * 0.03,
            f"{x_min:.1f}",
            ha="center",
            va="top",
            fontsize=7,
            color=color,
        )
        ax.text(
            x_max,
            y_min - height * 0.03,
            f"{x_max:.1f}",
            ha="center",
            va="top",
            fontsize=7,
            color=color,
        )

        # Y-axis boundaries
        ax.plot(
            [x_min, x_min - width * 0.02],
            [y_min, y_min],
            color=color,
            linestyle="--",
            linewidth=0.8,
        )
        ax.plot(
            [x_min, x_min - width * 0.02],
            [y_max, y_max],
            color=color,
            linestyle="--",
            linewidth=0.8,
        )
        ax.text(
            x_min - width * 0.03,
            y_min,
            f"{y_min:.1f}",
            ha="right",
            va="center",
            fontsize=7,
            color=color,
        )
        ax.text(
            x_min - width * 0.03,
            y_max,
            f"{y_max:.1f}",
            ha="right",
            va="center",
            fontsize=7,
            color=color,
        )

        # Collect coordinates for auto-cropping, excluding 'world' volumes
        if "world" not in name.lower():
            all_x_coords.extend([x_min, x_max])
            all_y_coords.extend([y_min, y_max])

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(f"Geant4 Volume Boundaries in {plane}-plane")
    ax.grid(True, linestyle="--", alpha=0.7)
    ax.set_aspect(
        "equal", adjustable="box"
    )  # Maintain aspect ratio for better visual representation

    # Auto-crop based on non-"world" volumes
    if all_x_coords and all_y_coords:
        x_min_plot = min(all_x_coords)
        x_max_plot = max(all_x_coords)
        y_min_plot = min(all_y_coords)
        y_max_plot = max(all_y_coords)

        # Add a small buffer to the limits
        x_buffer = (x_max_plot - x_min_plot) * 0.1
        y_buffer = (y_max_plot - y_min_plot) * 0.1
        ax.set_xlim(x_min_plot - x_buffer, x_max_plot + x_buffer)
        ax.set_ylim(y_min_plot - y_buffer, y_max_plot + y_buffer)
    else:
        ax.autoscale_view()  # Fallback to default autoscale if no non-world volumes found

    # Place legend outside plot to avoid cropping
    # Adjust rect parameter to leave space on the right for the legend
    ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5), fontsize=8)
    plt.tight_layout(
        rect=[0, 0, 0.85, 1]
    )  # [left, bottom, right, top] in figure coordinates
    plt.show()
