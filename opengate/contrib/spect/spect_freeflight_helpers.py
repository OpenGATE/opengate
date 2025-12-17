from opengate.contrib.spect.spect_helpers import *
from opengate.actors.simulation_stats_helpers import *
from pathlib import Path


def merge_freeflight_uncertainty_for_all_heads(
    folder, ref_n, subfolders, num_events, num_heads, verbose=False
):
    for head in range(num_heads):
        counts_filename = f"projection_{head}_counts.mhd"
        squared_counts_filename = f"projection_{head}_squared_counts.mhd"
        output_filename = f"relative_uncertainty_{head}_counts.mhd"
        merge_freeflight_uncertainty(
            folder,
            ref_n,
            subfolders,
            num_events,
            counts_filename=counts_filename,
            squared_counts_filename=squared_counts_filename,
            output_filename=output_filename,
            verbose=verbose,
        )


def merge_freeflight_uncertainty(
    folder,
    ref_n,
    subfolders,  # primary, scatter, septal_penetration (or some of them)
    num_events,
    counts_filename="projection_0_counts.mhd",
    squared_counts_filename="projection_0_squared_counts.mhd",
    output_filename="relative_uncertainty_0_counts.mhd",
    verbose=False,
):
    # check
    if len(subfolders) != len(num_events):
        fatal(
            f"merge_freeflight: subfolders and num_events must have the same length \n {subfolders} {num_events}"
        )

    # ---
    # Initialization
    # We will sum the mean counts and the variance of the mean from each independent step.
    # Let X_i be the pixel value from one event in step i.
    # Let N_i be the number of events for step i.
    # ---
    total_counts = None  # Will be Sum( E[X_i] ) = Sum( C_i / N_i )
    total_variance = None  # Will be Sum( Var( E[X_i] ) )
    template_image = None  # To store sitk metadata (origin, spacing)

    # merge all counts and squared counts
    for subfolder, n in zip(subfolders, num_events):
        if n <= 1:  # Need n > 1 to calculate variance
            verbose and print(
                f"Skipping {subfolder} with n={n} events (n > 1 required)"
            )
            continue

        f = folder / subfolder
        counts_path = f / counts_filename
        squared_counts_path = f / squared_counts_filename
        verbose and print(f"Reading {subfolder} with {n} events")

        # Check for files
        if not counts_path.exists():
            fatal(f"merge_freeflight: {counts_path} does not exist")
        if not squared_counts_path.exists():
            fatal(f"merge_freeflight: {squared_counts_path} does not exist")

        # Read images
        counts_img_sitk = sitk.ReadImage(str(counts_path))
        squared_counts_img_sitk = sitk.ReadImage(str(squared_counts_path))

        # Store the first valid image as template for metadata
        if template_image is None:
            template_image = counts_img_sitk

        # ---
        # Equations for step i:
        # C_i = sum(w) (raw counts image)
        # C2_i = sum(w^2) (raw squared-counts image)
        # N_i = n (number of primary events)
        #
        # E[X_i] = C_i / N_i  (mean count per event)
        # E[X_i^2] = C2_i / N_i (mean squared-count per event)
        # ---
        img_counts = sitk.GetArrayFromImage(counts_img_sitk) / n
        img_squared_counts = sitk.GetArrayFromImage(squared_counts_img_sitk) / n

        # Accumulate total mean counts
        # E[X_total] = E[X_primary] + E[X_scatter] + ...
        if total_counts is None:
            total_counts = img_counts
        else:
            total_counts += img_counts

        # ---
        # Variance of the mean for step i:
        # Var(E[X_i]) = (E[X_i^2] - (E[X_i])^2) / (N_i - 1)
        v = (img_squared_counts - np.power(img_counts, 2)) / (n - 1)

        # Ensure variance is non-negative (floating point precision issues)
        v[v < 0] = 0

        # Accumulate total variance
        # Var(E[X_total]) = Var(E[X_primary]) + Var(E[X_scatter]) + ...
        if total_variance is None:
            total_variance = v
        else:
            total_variance += v

    # Check if any data was processed
    if total_counts is None or template_image is None:
        fatal(
            "merge_freeflight: No valid data processed (all subfolders may have n <= 1)"
        )

    # ---
    # Final Relative Uncertainty:
    # R = sqrt( Var(E[X_total]) ) / E[X_total]
    # ---
    uncertainty = np.divide(
        np.sqrt(total_variance),
        total_counts,
        out=np.zeros_like(total_variance, dtype=float),  # Use float for output
        where=total_counts != 0,
    )

    # ---
    # Scale and write images
    # C_final = E[X_total] * N_ref
    # ---
    total_counts *= ref_n

    img = sitk.GetImageFromArray(total_counts)
    img.CopyInformation(template_image)
    sitk.WriteImage(img, str(folder / counts_filename))

    img = sitk.GetImageFromArray(uncertainty)
    img.CopyInformation(template_image)
    sitk.WriteImage(img, str(folder / output_filename))


def merge_free_flight_stats(ff_folder, subfolders, filename="stats.txt"):
    total_stats = None
    durations = []
    for subfolder in subfolders:
        ff_subfolder = ff_folder / subfolder
        stats_file = ff_subfolder / filename
        if not stats_file.exists():
            continue
        stats = read_stats_file(stats_file)
        if total_stats is None:
            total_stats = stats
        else:
            total_stats = sum_stats(total_stats, stats)
        durations.append(stats.counts.duration)

    # write final merged stats
    write_stats(total_stats, ff_folder / filename)
    stats = read_stats_file(ff_folder / filename)
    return stats, durations


def compare_stats(ref_folder: Path, ff_folder: Path):
    ref_stats_file = ref_folder / "stats.txt"
    ff_stats_file = ff_folder / "stats.txt"
    ref_data = read_stats_file(ref_stats_file)
    ff_data = read_stats_file(ff_stats_file)

    ref_duration_min = ref_data.counts.duration / g4_units.min
    ff_duration_min = ff_data.counts.duration / g4_units.min
    r = ref_duration_min / ff_duration_min
    print(
        f"Total Duration {ref_duration_min:.2f} min vs {ff_duration_min:.2f} min  raw speedup x {r:.2f}"
    )
    r = ref_data.counts.events / ff_data.counts.events
    print(
        f"Total events {ref_data.counts.events} vs {ff_data.counts.events}  ratio {r:.2f}"
    )
    r = ref_data.counts.tracks / ff_data.counts.tracks
    print(
        f"Total tracks {ref_data.counts.tracks} vs {ff_data.counts.tracks}  ratio {r:.2f}"
    )
    r = ref_data.counts.steps / ff_data.counts.steps
    print(
        f"Total steps {ref_data.counts.steps} vs {ff_data.counts.steps}  ratio {r:.2f}"
    )
