#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import opengate.contrib.spect.ge_discovery_nm670 as nm670
from opengate.contrib.spect.spect_helpers import *
from opengate.contrib.spect.spect_freeflight_helpers import *
import opengate.contrib.phantoms.nemaiec as nemaiec
from opengate.image import get_translation_to_isocenter
from opengate.sources.utility import set_source_energy_spectrum
from pathlib import Path
import numpy as np
import opengate_core as g4
import matplotlib.pyplot as plt
import SimpleITK as sitk
import os


def check_process_user_hook(simulation_engine):
    p_name = "gamma"
    g4_particle_table = g4.G4ParticleTable.GetParticleTable()
    particle = g4_particle_table.FindParticle(particle_name=p_name)
    if particle is None:
        raise Exception(f"Something went wrong. Could not find particle {p_name}.")
    pm = particle.GetProcessManager()
    process_list = pm.GetProcessList()
    for i in range(process_list.size()):
        processName = str(process_list[i].GetProcessName())
        print("Checking process", processName)


def create_simulation_test085(
    sim,
    paths,
    simu_name,
    ac=1e5,
    use_spect_head=False,
    use_spect_arf=False,
    use_phsp=False,
):
    # main options
    sim.visu_type = "qt"
    # sim.visu_type = "vrml"
    sim.random_seed = "auto"
    sim.progress_bar = True
    sim.output_dir = paths.output
    sim.store_json_archive = True
    sim.store_input_files = False
    sim.json_archive_filename = f"simu_{simu_name}.json"
    sim.random_seed = 654789
    data_folder = Path(paths.data) / "test085"

    # units
    mm = gate.g4_units.mm
    cm = gate.g4_units.cm
    m = gate.g4_units.m
    Bq = gate.g4_units.Bq
    cm3 = gate.g4_units.cm3
    BqmL = Bq / cm3
    deg = gate.g4_units.deg

    # options
    activity = ac * BqmL / sim.number_of_threads
    radius = 28 * cm

    # visu
    if sim.visu:
        sim.number_of_threads = 1
        activity = 50 * BqmL / sim.number_of_threads

    # world
    world = sim.world
    world.size = [2 * m, 2 * m, 2 * m]
    world.material = "G4_Galactic"

    # GeneralProcess must *NOT* be true (it is by default)
    s = f"/process/em/UseGeneralProcess false"
    sim.g4_commands_before_init.append(s)

    # check option
    if use_spect_head and use_spect_arf:
        raise Exception("Cannot use both spect heads and ARFs.")

    # set the two spect heads
    spacing = [2.21 * mm * 2, 2.21 * mm * 2]
    size = [128, 128]
    heads = []
    actors = []
    if use_spect_arf:
        actors, heads = add_spect_arf(
            sim, data_folder, simu_name, radius, size, spacing
        )
    if use_spect_head:
        actors, heads = add_spect_heads(sim, simu_name, radius)

    # add phsp to check E spectra
    if use_phsp:
        actors, heads = add_phsp(
            sim, simu_name, radius, size, spacing, use_parallel_world=use_spect_head
        )
        # IEC voxelization
        # voxelize_iec_phantom -o data/iec_1mm.mhd --spacing 1 --output_source data/iec_1mm_activity.mhd -a 1 1 1 1 1 1
        # voxelize_iec_phantom -o data/iec_4.42mm.mhd --spacing 4.42 --output_source data/iec_4.42mm_activity.mhd -a 1 1 1 1 1 1
        # voxelize_iec_phantom -o data/iec_4mm.mhd --spacing 4 --output_source data/iec_4mm_activity.mhd -a 1 1 1 1 1 1

    # phantom
    if not sim.visu:
        iec_vox_filename = data_folder / "iec_4mm.mhd"
        iec_label_filename = data_folder / "iec_4mm_labels.json"
        db_filename = data_folder / "iec_4mm.db"
        vox = sim.add_volume("ImageVolume", "phantom")
        vox.image = iec_vox_filename
        vox.read_label_to_material(iec_label_filename)
        vox.translation = get_translation_to_isocenter(vox.image)
        sim.volume_manager.add_material_database(str(db_filename))
    else:
        phantom = nemaiec.add_iec_phantom(sim, name="phantom")

    # physics
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option3"
    sim.physics_manager.set_production_cut("world", "all", 100 * m)
    sim.physics_manager.set_production_cut("phantom", "all", 1 * mm)
    # sim.physics_manager.set_production_cut("phantom", "gamma", 0.01 * mm)
    sim.user_hook_after_init = check_process_user_hook

    # add iec voxelized source
    iec_source_filename = data_folder / "iec_4mm_activity.mhd"
    source = sim.add_source("VoxelSource", "src")
    source.image = iec_source_filename
    source.position.translation = [0, 35 * mm, 0]
    set_source_energy_spectrum(source, "tc99m", "radar")
    source.particle = "gamma"
    _, volumes = nemaiec.get_default_sphere_centers_and_volumes()
    source.activity = activity * np.array(volumes).sum()
    print(f"Total activity is {source.activity / Bq}")

    # add a stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "stats")
    stats.track_types_flag = True
    stats.output_filename = f"stats_{simu_name}.txt"

    # set the gantry orientation
    starting_angle_deg = 10
    if len(heads) == 2:
        nm670.set_default_orientation(heads[0], "lehr")
        nm670.set_default_orientation(heads[1], "lehr")
        nm670.rotate_gantry(heads[0], radius, starting_angle_deg, 0, 1)
        nm670.rotate_gantry(heads[1], radius, starting_angle_deg + 180, 0, 1)

    return source, actors


def add_spect_arf(sim, data_folder, simu_name, radius, size, spacing):
    pth = data_folder / "arf_034_nm670_tc99m_v2.pth"
    det_plane1, arf1 = nm670.add_arf_detector_OLD(
        sim, radius, 0, size, spacing, "lehr", "spect", 1, pth
    )
    det_plane2, arf2 = nm670.add_arf_detector_OLD(
        sim, radius, 180, size, spacing, "lehr", "spect", 2, pth
    )
    det_planes = [det_plane1, det_plane2]

    arf1.output_filename = f"projection_1_{simu_name}.mhd"
    arf2.output_filename = f"projection_2_{simu_name}.mhd"
    arfs = [arf1, arf2]
    return arfs, det_planes


def add_spect_heads(sim, simu_name, radius):
    mm = gate.g4_units.mm
    heads, crystals = nm670.add_spect_two_heads(
        sim, "spect", "lehr", debug=sim.visu, radius=radius
    )
    channels = get_default_energy_windows("tc99m")
    digit1 = nm670.add_digitizer(sim, crystals[0].name, "digit1", channels=channels)
    digit2 = nm670.add_digitizer(sim, crystals[1].name, "digit2", channels=channels)

    # we need the weights for the digitizer
    hits1 = digit1.find_module("hits")
    hits1.attributes.append("Weight")
    hits1.attributes.append("TrackID")

    hits2 = digit2.find_module("hits")
    hits2.attributes.append("Weight")
    hits2.attributes.append("TrackID")

    proj1 = digit1.find_module("projection")
    proj1.output_filename = f"projection_1_{simu_name}.mhd"
    proj2 = digit2.find_module("projection")
    proj2.output_filename = f"projection_2_{simu_name}.mhd"
    proj1.squared_counts.active = True
    proj2.squared_counts.active = True
    projs = [proj1, proj2]

    # sim.physics_manager.set_production_cut(crystals[0].name, "all", 2 * mm)
    # sim.physics_manager.set_production_cut(crystals[1].name, "all", 2 * mm)
    sim.physics_manager.set_production_cut("spect_1", "all", 2 * mm)
    sim.physics_manager.set_production_cut("spect_2", "all", 2 * mm)

    return projs, heads


def add_phsp(sim, simu_name, radius, size, spacing, use_parallel_world, sph_rad=None):

    phsp_sphere = sim.add_volume("Sphere", "phsp_sphere")
    if sph_rad is None:
        phsp_sphere.rmax = 30 * gate.g4_units.cm
    else:
        phsp_sphere.rmax = sph_rad
    phsp_sphere.rmin = phsp_sphere.rmax - 2 * gate.g4_units.mm
    phsp_sphere.color = [1, 0, 0, 1]

    phsp1 = sim.add_actor("PhaseSpaceActor", "phsp_sphere")
    phsp1.attached_to = phsp_sphere
    phsp1.attributes = ["KineticEnergy", "PrePositionLocal", "Weight"]
    phsp1.output_filename = f"phsp_sphere_{simu_name}.root"

    # gamma only
    fe = sim.add_filter("ParticleFilter", "fe")
    fe.particle = "gamma"
    fe.policy = "accept"
    phsp1.filters.append(fe)

    phsps = [phsp1]
    planes = [phsp_sphere]

    return phsps, planes


def compute_zscore_per_pixel(ref, ff, squared_ff, n_ref, n_ff):
    # compute reference uncertainty (Poisson)
    # sigma_ref = poisson_rel_uncertainty(ref)

    # compute scatter uncertainty
    if squared_ff is None:
        sigma_ff = compute_poisson_relative_uncertainty(ff)
    else:
        sigma_ff = compute_history_by_history_relative_uncertainty(ff, squared_ff, n_ff)
    ff = ff * (n_ref / n_ff)

    # compute zscore per pixel
    mask = (ref > 0) & (ff > 0)
    z_score = np.divide(
        ff - ref,
        np.sqrt(ref + (sigma_ff * ff) ** 2),
        out=np.zeros_like(ref),
        where=mask,
    )

    z_score = z_score.astype(np.float64)
    return z_score


def compute_zscore_and_rel_diff(
    ref_filename,
    test_filename,
    n_ref,
    n_test,
    zscore_filename,
    refdiff_filename,
    squared_filename=None,
):
    ref_img = sitk.ReadImage(ref_filename)
    test_img = sitk.ReadImage(test_filename)
    ref_arr = sitk.GetArrayFromImage(ref_img).astype(np.float32)
    test_arr = sitk.GetArrayFromImage(test_img).astype(np.float32)

    if squared_filename is not None:
        squared_test_img = sitk.ReadImage(squared_filename)
        squared_test_arr = sitk.GetArrayFromImage(squared_test_img).astype(np.float32)
    else:
        squared_test_arr = None

    # zscore
    zscore = compute_zscore_per_pixel(
        ref_arr, test_arr, squared_test_arr, n_ref, n_test
    )
    zimg = sitk.GetImageFromArray(zscore)
    zimg.CopyInformation(ref_img)
    sitk.WriteImage(zimg, zscore_filename)
    print(zscore_filename)

    # reldiff
    test_arr = test_arr * (n_ref / n_test)
    ref_diff = np.divide(
        ref_arr - test_arr,
        ref_arr,
        out=np.zeros_like(ref_arr),
        where=(ref_arr != 0) & (test_arr != 0),
    )
    ref_diff = ref_diff.astype(np.float32)
    refdiff_img = sitk.GetImageFromArray(ref_diff)
    refdiff_img.CopyInformation(ref_img)
    sitk.WriteImage(refdiff_img, refdiff_filename)
    print(refdiff_filename)


def save_slice_histograms_as_pdf(filename: str, bins: int = 100):
    """
    Reads a 2D or 3D image and plots the histogram of each slice on a single
    figure, arranged horizontally. It ignores zero-valued pixels and overlays
    the mean and median.

    The final figure is saved as a PDF with the same name as the input file.

    Args:
        filename (str): The path to the image file.
        bins (int): The number of bins to use for the histogram.
    """
    # --- 1. Read the image using SimpleITK ---
    try:
        image_sitk = sitk.ReadImage(filename)
    except Exception as e:
        print(f"Error: Could not read the file '{filename}'.")
        print(f"Details: {e}")
        return

    # --- 2. Convert to a NumPy array ([z, y, x] order) ---
    image_np = sitk.GetArrayFromImage(image_sitk)

    # --- 3. Handle both 2D and 3D images consistently ---
    if image_np.ndim == 2:
        image_np = image_np.reshape(1, *image_np.shape)

    if image_np.ndim != 3:
        print(
            f"Error: Function expects a 2D or 3D image, but got {image_np.ndim} dimensions."
        )
        return

    # --- 4. Pre-filter to find slices with actual data ---
    # This helps determine the required number of subplots.
    valid_slices_data = []
    for i, slice_2d in enumerate(image_np):
        # Flatten and filter out zeros
        non_zero_pixels = slice_2d.flatten()
        non_zero_pixels = non_zero_pixels[non_zero_pixels != 0]

        if non_zero_pixels.size > 0:
            valid_slices_data.append({"index": i, "data": non_zero_pixels})

    if not valid_slices_data:
        print("No non-zero data found in any slice. No plot will be generated.")
        return

    # --- 5. Create a single figure with multiple subplots ---
    num_plots = len(valid_slices_data)
    # Dynamically adjust figure size based on the number of plots
    fig, axes = plt.subplots(nrows=1, ncols=num_plots, figsize=(6 * num_plots, 5))

    # If there's only one plot, `subplots` returns a single Axes object, not an array.
    # We wrap it in a list to make the subsequent loop work consistently.
    if num_plots == 1:
        axes = [axes]

    # Set the main title for the entire figure
    fig.suptitle(f"Histograms for: {os.path.basename(filename)}", fontsize=16)

    # --- 6. Iterate through valid slices and plot on the corresponding subplot axis ---
    for ax, slice_info in zip(axes, valid_slices_data):
        slice_index = slice_info["index"]
        non_zero_pixels = slice_info["data"]

        mean_val = np.mean(non_zero_pixels)
        median_val = np.median(non_zero_pixels)

        # Plot the histogram on the specific subplot axis `ax`
        ax.hist(
            non_zero_pixels,
            bins=bins,
            color="deepskyblue",
            edgecolor="blue",
            alpha=0.7,
        )

        # Add vertical lines to the subplot
        ax.axvline(
            mean_val,
            color="red",
            linestyle="dashed",
            linewidth=2,
            label=f"Mean: {mean_val:.2f}",
        )
        ax.axvline(
            median_val,
            color="green",
            linestyle="solid",
            linewidth=2,
            label=f"Median: {median_val:.2f}",
        )

        # Set titles and labels for the specific subplot
        ax.set_title(f"Slice {slice_index}")
        ax.set_xlabel("Pixel Intensity")
        ax.set_ylabel("Frequency (Count)")
        ax.legend()
        ax.grid(axis="y", alpha=0.5)

    # --- 7. Save the figure to a PDF file ---
    # Adjust layout to prevent titles and labels from overlapping
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])  # rect makes space for suptitle

    # Construct the output filename
    base_filename, _ = os.path.splitext(filename)
    output_filename = f"{base_filename}.pdf"

    try:
        plt.savefig(output_filename, bbox_inches="tight")
        print(f"Histogram plot successfully saved to: {output_filename}")
    except Exception as e:
        print(f"\nError: Could not save the plot to '{output_filename}'.")
        print(f"Details: {e}")
    finally:
        # Close the figure to free up memory
        plt.close(fig)
