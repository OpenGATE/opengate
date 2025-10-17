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

    # Prepare a dictionary to hold processed volume data with world coordinates
    processed_volumes = serialize_volume_data(vol_info_raw)

    # save as json
    with open(json_filename, "w") as f:
        json.dump(processed_volumes, f, indent=4)


def store_expanded_volumes_info(sim, json_filename):
    """
    Main function to be called.
    Expands the entire geometry tree to find every single instance of every
    volume, calculates their world coordinates, and saves the complete,
    expanded geometry to a JSON file. This is the correct method for
    geometries with nested replications.
    """
    # 1. Get the initial prototype volumes from the G4 store
    vol_info_raw = get_g4_volumes_pointers(sim)

    # 2. Serialize the prototype volumes to get their basic properties (like local bounds)
    #    This now uses the correct GetMother() method.
    prototype_volumes = serialize_volume_data(vol_info_raw)

    # 3. Expand the geometry to create a dictionary of all unique instances
    expanded_volumes = expand_all_geometry_instances(prototype_volumes)

    # 4. Save the final, expanded data to JSON
    with open(json_filename, "w") as f:
        # Use a custom encoder to handle numpy arrays if they exist
        json.dump(expanded_volumes, f, indent=4, cls=NumpyEncoder)


class NumpyEncoder(json.JSONEncoder):
    """Custom encoder for numpy data types"""

    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return json.JSONEncoder.default(self, obj)


def expand_all_geometry_instances(prototype_volumes: dict) -> dict:
    """
    Takes the dictionary of prototype volumes and expands it to create a new
    dictionary containing every unique instance of every volume.
    """
    root_pv_name = None
    for pv_name, pv_data in prototype_volumes.items():
        if pv_data.get("mother") is None:
            root_pv_name = pv_name
            break
    if not root_pv_name:
        raise ValueError("Could not find a root volume (a volume with no mother).")

    expanded_volumes = {}

    # The recursive function will populate the expanded_volumes dictionary
    _expand_and_store_recursively(
        parent_pv_name=root_pv_name,
        parent_world_transform=np.identity(4),
        prototype_volumes=prototype_volumes,
        expanded_volumes=expanded_volumes,
        instance_counts={},
    )
    return expanded_volumes


def _expand_and_store_recursively(
    parent_pv_name,
    parent_world_transform,
    prototype_volumes,
    expanded_volumes,
    instance_counts,
):
    """
    Recursive helper function to traverse the geometry, calculate world transforms,
    and store unique instances in the 'expanded_volumes' dictionary.
    """
    parent_prototype = prototype_volumes.get(parent_pv_name, {})

    for daughter_pv_name_prototype in parent_prototype.get("daughters", []):
        daughter_prototype = prototype_volumes.get(daughter_pv_name_prototype)
        if not daughter_prototype:
            continue

        # 1. Calculate the daughter's world transform
        local_transform = _create_transform_matrix(
            daughter_prototype.get("object_rotation"),
            daughter_prototype.get("object_translation"),
        )
        daughter_world_transform = parent_world_transform @ local_transform

        # 2. Get the local bounding box corners of the prototype
        local_corners = _get_bbox_corners(*daughter_prototype.bounding_limits_local)

        # 3. Transform corners to world coordinates
        # This expression is mathematically equivalent to (local_corners @ daughter_world_transform.T)
        # and now works because local_corners is the correct 8x4 shape.
        transformed_corners = (daughter_world_transform @ local_corners.T).T
        world_min = np.min(transformed_corners[:, :3], axis=0)
        world_max = np.max(transformed_corners[:, :3], axis=0)
        world_bounds = world_min.tolist() + world_max.tolist()

        # 4. Create a unique name for this instance and store it
        base_name = daughter_prototype.lv_name
        instance_num = instance_counts.get(base_name, 0)
        unique_name = f"{base_name}_#{instance_num}"
        instance_counts[base_name] = instance_num + 1

        new_volume_instance = {
            "pv_name": unique_name,
            "lv_name": base_name,
            "mother": parent_prototype.get("lv_name"),
            "world_bounding_limits": world_bounds,
        }
        expanded_volumes[unique_name] = new_volume_instance

        # 5. Recurse into the grandchildren
        _expand_and_store_recursively(
            parent_pv_name=daughter_pv_name_prototype,
            parent_world_transform=daughter_world_transform,
            prototype_volumes=prototype_volumes,
            expanded_volumes=expanded_volumes,
            instance_counts=instance_counts,
        )


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

    return v


def plot_volume_boundaries(
    volume_data: dict, axis: str = "X", show_labels: bool = True
):
    """
    Plots the bounding box boundaries of Geant4 volumes along a specified axis.
    """
    axis = axis.upper()
    if axis not in ["X", "Y", "Z"]:
        print(f"Error: Invalid axis '{axis}'. Please choose 'X', 'Y', or 'Z'.")
        return

    axis_map = {"X": (0, 3), "Y": (1, 4), "Z": (2, 5)}
    min_idx, max_idx = axis_map[axis]

    fig, ax = plt.subplots(figsize=(12, 8))

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

    plot_data.sort(key=lambda x: x["min"])
    y_pos = np.arange(len(plot_data))

    for i, vol in enumerate(plot_data):
        ax.plot(
            [vol["min"], vol["max"]],
            [y_pos[i], y_pos[i]],
            marker="o",
            linestyle="-",
            markersize=8,
            label=vol["name"],
        )
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
    ax=None,
):
    """
    Plots the 2D bounding boxes of Geant4 volumes on a specified plane.
    Can plot on a given matplotlib axis `ax` or create a new figure.
    """
    is_standalone = ax is None
    if is_standalone:
        fig, ax = plt.subplots(figsize=(12, 10))

    plane = plane.upper()
    if plane not in ["XY", "XZ", "YZ"]:
        print(f"Error: Invalid plane '{plane}'. Please choose 'XY', 'XZ', or 'YZ'.")
        return

    highlight_volumes = highlight_volumes or []

    plane_map = {
        "XY": ((0, 1), (3, 4), "X-axis", "Y-axis"),
        "XZ": ((0, 2), (3, 5), "X-axis", "Z-axis"),
        "YZ": ((1, 2), (4, 5), "Y-axis", "Z-axis"),
    }
    (min1_idx, min2_idx), (max1_idx, max2_idx), xlabel, ylabel = plane_map[plane]

    def _get_volume_depth(volume_name, data, current_depth=0, memo={}):
        if volume_name in memo:
            return memo[volume_name]
        if volume_name not in data or data[volume_name].get("mother") is None:
            memo[volume_name] = current_depth
            return current_depth
        else:
            mother_name = data[volume_name]["mother"]
            depth = _get_volume_depth(mother_name, data, current_depth + 1, memo)
            memo[volume_name] = depth
            return depth

    processed_volumes = []
    for name, info in volume_data.items():
        if (
            "world_bounding_limits" in info
            and info["world_bounding_limits"]
            and len(info["world_bounding_limits"]) == 6
        ):
            depth = _get_volume_depth(name, volume_data)
            processed_volumes.append({"name": name, "info": info, "depth": depth})
        else:
            print(
                f"Warning: Volume '{name}' missing 'world_bounding_limits' or invalid format. Skipping for 2D plot."
            )

    processed_volumes.sort(key=lambda x: (x["depth"], x["name"]))

    volumes_to_plot_normal = [
        v for v in processed_volumes if v["name"] not in highlight_volumes
    ]
    volumes_to_plot_highlight = [
        v for v in processed_volumes if v["name"] in highlight_volumes
    ]
    plotting_order = volumes_to_plot_normal + volumes_to_plot_highlight

    num_volumes_to_plot = len(plotting_order)
    colors_cmap = cm.get_cmap(
        "tab20" if num_volumes_to_plot <= 20 else "viridis", num_volumes_to_plot
    )
    color_idx = 0
    all_x_coords, all_y_coords = [], []

    for vol_entry in plotting_order:
        name, info = vol_entry["name"], vol_entry["info"]
        limits = info["world_bounding_limits"]
        x_min, y_min = limits[min1_idx], limits[min2_idx]
        x_max, y_max = limits[max1_idx], limits[max2_idx]
        width, height = x_max - x_min, y_max - y_min
        color = colors_cmap(color_idx)
        color_idx += 1
        linewidth, edgecolor = (
            (3.0, "black") if name in highlight_volumes else (1.5, color)
        )

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

        # Add text labels for min and max values on the axes
        if width > 0 and height > 0:
            ax.text(
                x_min,
                y_min - height * 0.03,
                f"{x_min:.1f}",
                ha="center",
                va="top",
                fontsize=7,
                color=edgecolor,
            )
            ax.text(
                x_max,
                y_min - height * 0.03,
                f"{x_max:.1f}",
                ha="center",
                va="top",
                fontsize=7,
                color=edgecolor,
            )
            ax.text(
                x_min - width * 0.03,
                y_min,
                f"{y_min:.1f}",
                ha="right",
                va="center",
                fontsize=7,
                color=edgecolor,
            )
            ax.text(
                x_min - width * 0.03,
                y_max,
                f"{y_max:.1f}",
                ha="right",
                va="center",
                fontsize=7,
                color=edgecolor,
            )

        if show_labels:
            ax.text(
                x_max + width * 0.02,
                y_min + height / 2,
                name,
                ha="left",
                va="center",
                fontsize=8,
                color=color,
                bbox=dict(
                    facecolor="white",
                    alpha=0.7,
                    edgecolor="none",
                    boxstyle="round,pad=0.2",
                ),
            )

        if "world" not in name.lower():
            all_x_coords.extend([x_min, x_max])
            all_y_coords.extend([y_min, y_max])

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(f"Volume Boundaries in {plane}-plane")
    ax.grid(True, linestyle="--", alpha=0.7)
    ax.set_aspect("equal", adjustable="box")

    if all_x_coords and all_y_coords:
        x_min_plot, x_max_plot = min(all_x_coords), max(all_x_coords)
        y_min_plot, y_max_plot = min(all_y_coords), max(all_y_coords)
        x_buffer = (x_max_plot - x_min_plot) * 0.1
        y_buffer = (y_max_plot - y_min_plot) * 0.1
        ax.set_xlim(x_min_plot - x_buffer, x_max_plot + x_buffer)
        ax.set_ylim(y_min_plot - y_buffer, y_max_plot + y_buffer)
    else:
        ax.autoscale_view()

    if is_standalone:
        handles, labels = ax.get_legend_handles_labels()
        by_label = dict(zip(labels, handles))
        if by_label:
            ax.legend(
                by_label.values(),
                by_label.keys(),
                loc="center left",
                bbox_to_anchor=(1.02, 0.5),
                fontsize=8,
            )
        # plt.tight_layout(rect=[0, 0, 0.85, 1])
        plt.show()


def plot_all_views_2d(
    volume_data: dict, show_labels: bool = True, highlight_volumes: list = None
):
    """
    Plots the 2D bounding boxes of Geant4 volumes from three different views (XY, XZ, YZ)
    on a single figure with three subplots.
    """
    fig, axes = plt.subplots(1, 3, figsize=(30, 9))

    # Plot on each subplot
    plot_volume_boundaries_2d(
        volume_data,
        plane="XY",
        show_labels=show_labels,
        highlight_volumes=highlight_volumes,
        ax=axes[0],
    )
    plot_volume_boundaries_2d(
        volume_data,
        plane="XZ",
        show_labels=show_labels,
        highlight_volumes=highlight_volumes,
        ax=axes[1],
    )
    plot_volume_boundaries_2d(
        volume_data,
        plane="YZ",
        show_labels=show_labels,
        highlight_volumes=highlight_volumes,
        ax=axes[2],
    )

    # Create a single, combined legend for the entire figure
    handles, labels = axes[0].get_legend_handles_labels()
    by_label = dict(zip(labels, handles))  # To remove duplicate labels
    if by_label:
        fig.legend(
            by_label.values(),
            by_label.keys(),
            loc="center right",
            bbox_to_anchor=(0.98, 0.5),
            fontsize=9,
        )

    fig.suptitle("Geant4 Volume Boundaries - All Views", fontsize=16)
    # plt.tight_layout(rect=[0, 0, 0.9, 0.95])  # Adjust for suptitle and legend
    plt.show()


def _expand_geometry_recursively(
    parent_pv_name: str, parent_world_transform: np.ndarray, all_volume_data: dict
):
    """
    Recursively traverses the geometry tree top-down, calculating the world
    transform for every combinatorial instance of every volume.

    Returns:
        A dictionary where keys are LV names and values are lists of
        all calculated world transformation matrices for that LV.
    """
    # This dictionary will store all transforms found under this parent
    all_found_transforms = {}

    parent_data = all_volume_data.get(parent_pv_name, {})

    # Iterate through the physical daughters of the current parent
    for daughter_pv_name in parent_data.get("daughters", []):
        daughter_data = all_volume_data.get(daughter_pv_name)
        if not daughter_data:
            continue

        # 1. Calculate the daughter's world transform
        local_transform = _create_transform_matrix(
            daughter_data.get("object_rotation"),
            daughter_data.get("object_translation"),
        )
        daughter_world_transform = parent_world_transform @ local_transform

        # 2. Store this daughter's transform
        daughter_lv_name = daughter_data.get("lv_name")
        if daughter_lv_name:
            if daughter_lv_name not in all_found_transforms:
                all_found_transforms[daughter_lv_name] = []
            all_found_transforms[daughter_lv_name].append(daughter_world_transform)

        # 3. Recurse into the grandchildren
        child_transforms = _expand_geometry_recursively(
            daughter_pv_name, daughter_world_transform, all_volume_data
        )

        # 4. Merge the results from the recursive call
        for lv_name, transform_list in child_transforms.items():
            if lv_name not in all_found_transforms:
                all_found_transforms[lv_name] = []
            all_found_transforms[lv_name].extend(transform_list)

    return all_found_transforms


def get_all_instances_transforms(volume_data: dict, target_lv_name: str) -> list:
    """
    Finds ALL combinatorial instances of a given logical volume (LV) by
    performing a full, top-down expansion of the geometry tree.
    """
    # 1. Find the root of the geometry tree (the volume with no mother)
    root_pv_name = None
    for pv_name, pv_data in volume_data.items():
        if pv_data.get("mother") is None:
            root_pv_name = pv_name
            break

    if not root_pv_name:
        raise ValueError("Could not find a root volume (a volume with no mother).")

    # 2. Start the recursive expansion from the root volume
    root_transform = np.identity(4)  # World's transform is identity
    all_transforms_by_lv = _expand_geometry_recursively(
        root_pv_name, root_transform, volume_data
    )

    # 3. Extract and format the results for the target LV
    final_results = []
    target_transforms = all_transforms_by_lv.get(target_lv_name, [])

    for transform_matrix in target_transforms:
        final_results.append(
            {
                "logical_volume_name": target_lv_name,
                "world_translation": transform_matrix[:3, 3].tolist(),
                "world_rotation": transform_matrix[:3, :3].tolist(),
            }
        )

    return final_results
