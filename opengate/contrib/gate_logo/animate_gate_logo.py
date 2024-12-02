#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from scipy.spatial.transform import Rotation
import opengate as gate
import itk
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from matplotlib.animation import FuncAnimation, PillowWriter
from PIL import Image
from sklearn.mixture import GaussianMixture
from scipy.stats import multivariate_normal


def main():
    read_pb_positions_and_weights_from_file = True
    default_dir = Path("__file__").parent  # Path.cwd()
    if read_pb_positions_and_weights_from_file:
        file_path_spot_weights = default_dir / "gate_logo_gmm_results.txt"
    else:
        image_path = default_dir / "GATE_logo.png"  # Replace with your image path
        output_file = default_dir / "gate_logo_gmm_results_newlyoptimized.txt"
        n_gaussians_to_represent_img = 150
        convert_img_to_gaussian_mixture(
            image_path, output_file, n_components=n_gaussians_to_represent_img
        )
        file_path_spot_weights = output_file

    expt_fpath = default_dir / Path("Gate_logo_simulated.png")

    run_simulation_create_gif(file_path_spot_weights, expt_fpath)


def run_simulation_create_gif(
    file_path_spot_weights,
    expt_fpath,
    number_of_gif_frames=20,
    activity=5e7,
    sigma_smearing_factor=1.05,
):
    multiple_runs = True
    weight_source_activity = True  # if False use about 1e6 [Bq]

    # create the simulation
    sim = gate.Simulation()
    # main options
    sim.g4_verbose = False
    sim.g4_verbose_level = 1
    sim.visu = False
    sim.random_seed = 1234567891
    sim.number_of_threads = 1
    sim.output_dir = expt_fpath.parent / "temp"
    if not multiple_runs:
        numPartSimTest = 4e5 / sim.number_of_threads

    # units
    m = gate.g4_units.m
    cm = gate.g4_units.cm
    mm = gate.g4_units.mm
    MeV = gate.g4_units.MeV
    Bq = gate.g4_units.Bq
    kBq = 1000 * Bq

    s = gate.g4_units.s

    #  change world size
    world = sim.world
    world.size = [60 * cm, 50 * cm, 50 * cm]
    # world.material = "Vacuum"

    # waterbox
    phantom = sim.add_volume("Box", "phantom")
    phantom.size = [10 * cm, 40 * cm, 20 * cm]
    phantom.translation = [-5 * cm, 0, 0]
    phantom.material = "G4_WATER"
    phantom.color = [0, 0, 1, 1]

    # physics
    sim.physics_manager.physics_list_name = "QGSP_BIC_EMV"

    M_spots = np.genfromtxt(file_path_spot_weights, delimiter="\t")

    w_sum = np.sum(M_spots[:, 2])
    ## normalize weights in case is not normalized
    M_spots[:, 2] = M_spots[:, 2] / w_sum

    m = np.amax(M_spots, axis=0)

    sorted_indices = np.lexsort((M_spots[:, 0], M_spots[:, 1]))
    M_spots = M_spots[sorted_indices]
    # print(f'{w_sum = }')
    # print(M_sum)
    # print(f'{m=}')
    # print(f'{M_spots.shape = }')
    n_sources = M_spots.shape[0]
    id_interv = n_sources // number_of_gif_frames
    # print(f'{id_interv = }')

    meterset_weight_sum = 0.0
    run_time_intervals = []
    for i, row in enumerate(M_spots):
        x_pos = float(row[0]) - m[0] / 2
        y_pos = float(row[1]) - m[1] / 2
        w = float(row[2])

        sigma = float(row[3]) * sigma_smearing_factor
        source = sim.add_source("GenericSource", f"mysource_{i}")
        source.energy.mono = 1 * MeV
        source.particle = "proton"
        source.position.type = "disc"
        # print(dir(source.position))
        source.position.rotation = Rotation.from_euler(
            "y", 90, degrees=True
        ).as_matrix()
        # sigma = 8
        source.position.sigma_x = sigma * mm
        source.position.sigma_y = sigma * mm
        source.direction.type = "momentum"
        source.direction.momentum = [-1, 0, 0]
        source.position.translation = [0 * mm, y_pos * mm, x_pos * mm]

        # print(dir(source.energy))
        if multiple_runs:
            """There is two ways of setting the weight of the sources correctly (both work)"""

            if weight_source_activity:
                source.activity = w * activity * Bq
                source.start_time = (i) / n_sources * s
                source.end_time = (i + 1) / n_sources * s
            else:
                source.activity = activity * Bq
                source.start_time = meterset_weight_sum * s
                meterset_weight_sum += w
                source.end_time = meterset_weight_sum * s

            if (i % id_interv) == 0 or (i == (n_sources - 1)):
                if i == 0:
                    start_time = 0 * s
                else:
                    start_time = run_time_intervals[-1][1]
                run_time_intervals.append([start_time, source.end_time])

        else:
            source.n = np.ceil(numPartSimTest * w)

    size = [1, 400, 200]
    spacing = [100 * mm, 1.0 * mm, 1.0 * mm]

    doseActorName = "gate_logo"
    doseActor = sim.add_actor("DoseActor", doseActorName)
    doseActor.output_filename = "test0-" + doseActorName + ".mhd"
    doseActor.attached_to = phantom
    doseActor.size = size
    doseActor.spacing = spacing
    doseActor.hit_type = "random"
    doseActor.dose.active = False
    if multiple_runs:
        doseActor.keep_data_per_run = True
        sim.run_timing_intervals = run_time_intervals
        print(run_time_intervals)

    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "stats")
    stats.track_types_flag = True

    sim.run()

    fname1 = str(doseActor.edep.get_output_path())
    total_dose_all_runs = itk.imread(fname1)

    data_array_all_runs = np.squeeze(itk.GetArrayViewFromImage(total_dose_all_runs))
    max_value_data_arr = np.amax(data_array_all_runs[:])
    plt.imshow(data_array_all_runs)
    plt.imsave(
        expt_fpath.with_stem(f"{expt_fpath.stem}_static").with_suffix(".png"),
        data_array_all_runs,
    )
    plt.show()

    if multiple_runs:
        fpath_full_img = Path(doseActor.edep.get_output_path())
        frames = []
        data_array_sum = np.zeros_like(
            data_array_all_runs, dtype=data_array_all_runs.dtype
        )
        for i in range(len(run_time_intervals)):
            f_path_i = fpath_full_img.with_stem(f"{fpath_full_img.stem}-run{i}")
            img_i = itk.imread(str(f_path_i))
            data_array_sum += np.squeeze(itk.GetArrayViewFromImage(img_i))
            # we normalize the data to their cumulative max value, so data range from 0 to 1
            frames.append(data_array_sum.copy() / max_value_data_arr)
        # Create the figure and axis
        fig, ax = plt.subplots()
        im = ax.imshow(frames[0], cmap="viridis", aspect="auto", vmin=-0, vmax=1)
        ax.set_title("Frame 0")

        # Update function for each frame
        def update(frame):
            im.set_data(frames[frame])
            ax.set_title(f"Frame {frame}")
            return im, ax

        # Create the animation
        ani = FuncAnimation(
            fig, update, frames=len(frames), interval=100, repeat_delay=1000
        )

        # Save the animation as a GIF
        writer = PillowWriter(fps=5)  # 5 frames per second
        ani.save(
            expt_fpath.with_stem(f"{expt_fpath.stem}_animated").with_suffix(".gif"),
            writer=writer,
        )


def load_and_discretize_image(image_path, sigma_blurr=0, levels=5):
    img = Image.open(image_path).convert("L")
    image_array = np.array(img)
    # Apply Gaussian filter (blur)
    # image_array = gaussian_filter(image_array, sigma=sigma_blurr)
    # Normalize the image and scale it to the desired levels
    max_val = 255  # Maximum grayscale value
    step = max_val // levels
    # Discretize and preserve the original contrast
    discretized = (max_val - image_array) // step
    return discretized


# Perform Gaussian Mixture analysis
def analyze_with_gmm_discretized(image_array, n_components=10):
    # Get coordinates and intensity values
    coords = np.column_stack(np.where(image_array > 0))
    intensities = image_array[coords[:, 0], coords[:, 1]]

    # Repeat coordinates based on discretized intensity values
    repeated_coords = np.repeat(coords, intensities // (1), axis=0)

    # Fit the GMM without sample_weight
    gmm = GaussianMixture(
        n_components=n_components, random_state=42, covariance_type="spherical"
    )
    # gmm = BayesianGaussianMixture(n_components=n_components,tol = 1e-4, covariance_type = 'spherical', random_state=42)
    gmm.fit(repeated_coords)
    return gmm


# Custom GMM fitting with fixed sigma
def fixed_sigma_gmm(X, n_components, sigma):
    n_samples, n_features = X.shape
    gmm = GaussianMixture(
        n_components=n_components, covariance_type="spherical", random_state=42
    )
    gmm.fit(X)

    # Override the covariances with the fixed sigma squared
    gmm.covariances_ = np.full(n_components, sigma**2)  # Variance = sigma^2
    gmm.precisions_cholesky_ = np.sqrt(
        1 / gmm.covariances_
    )  # Precomputed for faster predictions

    # Predict cluster assignments
    labels = gmm.predict(X)
    return gmm, labels


# Calculate the cumulative Gaussian map
def calculate_cumulative_gaussian_map(image_shape, gmm):
    x = np.arange(image_shape[1])
    y = np.arange(image_shape[0])
    xx, yy = np.meshgrid(x, y)
    grid_coords = np.column_stack([yy.ravel(), xx.ravel()])
    cumulative_map = np.zeros(image_shape)

    for mean, covar, weight in zip(gmm.means_, gmm.covariances_, gmm.weights_):
        gaussian = multivariate_normal(mean=mean, cov=covar)
        cumulative_map += weight * gaussian.pdf(grid_coords).reshape(image_shape)

    return cumulative_map


# Plot results
def plot_results(image_array, gmm, cumulative_map):
    fig, axes = plt.subplots(1, 2, figsize=(15, 7))

    # Plot discretized grayscale image
    axes[0].imshow(image_array, cmap="gray", origin="upper")
    centers = gmm.means_
    weights = gmm.weights_
    axes[0].scatter(
        centers[:, 1],
        centers[:, 0],
        c="red",
        s=weights * 1000,
        alpha=0.7,
        label="GMM Centers",
    )
    axes[0].set_title("GMM Analysis on Discretized Grayscale Image")
    axes[0].legend()

    # Plot cumulative Gaussian map
    axes[1].imshow(cumulative_map, cmap="hot", origin="upper")
    axes[1].set_title("Cumulative Gaussian Map")
    plt.show()


# Save results to a text file
def save_results_to_file(gmm, output_file):
    centers = gmm.means_
    weights = gmm.weights_
    sigmas = np.sqrt(gmm.covariances_)
    with open(output_file, "w") as f:
        for i, (x, y) in enumerate(centers):
            f.write(f"{x:.2f}\t{y:.2f}\t{weights[i]:.4e}\t{sigmas[i]:.4e}\n")


# Main workflow
def convert_img_to_gaussian_mixture(image_path, output_file, n_components=10, levels=5):
    image_array = load_and_discretize_image(image_path, levels)
    gmm = analyze_with_gmm_discretized(image_array, n_components)
    cumulative_map = calculate_cumulative_gaussian_map(image_array.shape, gmm)
    plot_results(image_array, gmm, cumulative_map)
    save_results_to_file(gmm, output_file)
    print(f"Results saved to {output_file}")


if __name__ == "__main__":
    main()
