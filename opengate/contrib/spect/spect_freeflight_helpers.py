from pathlib import Path
from opengate.contrib.spect.spect_helpers import *
import json


def history_ff_combined_rel_uncertainty(
    vprim, vprim_squared, vscatter, vscatter_squared, n_prim, n_scatter
):
    """
    Combines primary and scatter simulation results, scaling them to the number of primary histories (n_prim).
    """
    if vprim is None and vscatter is None:
        raise ValueError("At least one of the primary or scattering values must be set")

    # Initialize total mean and variance, scaled to n_prim events
    mean_total = np.zeros_like(vprim if vprim is not None else vscatter)
    variance_total = np.zeros_like(mean_total)

    # --- Process Primary Component ---
    if vprim is not None:
        # The total contribution from primaries is just vprim itself
        mean_total += vprim

        # Calculate the variance of the total primary contribution
        # Var(total) = n^2 * Var(mean) = n^2 * (E[x^2] - E[x]^2)/(n-1)
        mean_prim_per_event = vprim / n_prim
        mean_prim_sq_per_event = vprim_squared / n_prim
        variance_of_mean_prim = (
            mean_prim_sq_per_event - np.power(mean_prim_per_event, 2)
        ) / (n_prim - 1)
        variance_total += variance_of_mean_prim * (n_prim**2)

    # --- Process and Scale Scatter Component ---
    if vscatter is not None:
        # Scale the scatter counts to be equivalent to n_prim histories
        scaling_factor = n_prim / n_scatter
        mean_scatter_scaled = vscatter * scaling_factor
        mean_total += mean_scatter_scaled

        # Calculate the variance of the scaled scatter contribution
        # Var(s*X) = s^2 * Var(X)
        mean_scatter_per_event = vscatter / n_scatter
        mean_scatter_sq_per_event = vscatter_squared / n_scatter
        variance_of_mean_scatter = (
            mean_scatter_sq_per_event - np.power(mean_scatter_per_event, 2)
        ) / (n_scatter - 1)
        variance_total += (
            variance_of_mean_scatter * (n_scatter**2) * (scaling_factor**2)
        )

    # --- Calculate Final Relative Uncertainty ---
    # Based on the total scaled mean and total combined variance
    uncert = np.divide(
        np.sqrt(variance_total),
        mean_total,
        out=np.zeros_like(variance_total),
        where=mean_total != 0,
    )

    return uncert, mean_total


def batch_ff_combined_rel_uncertainty(
    prim_mean, prim_uncert, scatter_mean, scatter_uncert, n_prim, n_scatter
):
    # combine mean
    r = n_prim / n_scatter
    mean = prim_mean + scatter_mean * r

    # combine uncertainties
    prim_var = np.power(prim_uncert * prim_mean, 2)
    sc_var = np.power(scatter_uncert * scatter_mean, 2) * np.power(r, 2)
    uncert = np.sqrt(prim_var + sc_var)
    uncert = np.divide(
        uncert,
        mean,
        out=np.zeros_like(uncert),
        where=mean != 0,
    )

    return uncert, mean


def spect_freeflight_merge_all_heads(
    folder,
    n_prim,
    n_scatter,
    n_target,
    prim_folder="primary",
    scatter_folder="scatter",
    nb_of_heads=2,
    counts_filename_pattern="projection_$I_counts.mhd",
    sq_counts_filename_pattern="projection_$I_squared_counts.mhd",
    merge_filename="projection_$I_counts.mhd",
    rel_uncert_suffix="relative_uncertainty",
    spr_filename="projection_$I_spr.mhd",
    verbose=True,
):
    for d in range(nb_of_heads):
        spect_freeflight_merge(
            folder,
            n_prim,
            n_scatter,
            n_target,
            prim_folder=prim_folder,
            scatter_folder=scatter_folder,
            counts_filename=counts_filename_pattern.replace("$I", str(d)),
            sq_counts_filename=sq_counts_filename_pattern.replace("$I", str(d)),
            merge_filename=merge_filename.replace("$I", str(d)),
            rel_uncert_suffix=rel_uncert_suffix.replace("$I", str(d)),
            spr_filename=spr_filename.replace("$I", str(d)),
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
    img.CopyInformation(template_image)  # Use the saved template
    sitk.WriteImage(img, str(folder / counts_filename))

    img = sitk.GetImageFromArray(uncertainty)
    img.CopyInformation(template_image)  # Use the saved template
    sitk.WriteImage(img, str(folder / output_filename))


def merge_freeflight_old(
    folder,
    ref_n,
    subfolders,  # primary, scatter, septal_penetration (or some of them)
    num_events,
    counts_filename="projection_0_counts.mhd",
    squared_counts_filename="projection_0_squared_counts.mhd",
    output_filename="relative_uncertainty_0_counts.mhd",
):
    # check
    if len(subfolders) != len(num_events):
        fatal(
            f"merge_freeflight: subfolders and num_events must have the same length \n {subfolders} {num_events}"
        )

    # merge all counts and squared counts
    # normalized for 1 event
    # compute squared sum of variances
    total_counts = None
    total_squared_counts = None
    total_variance = None
    img_counts = None
    for subfolder, n in zip(subfolders, num_events):
        if n == 0:
            continue
        f = folder / subfolder
        counts_path = f / counts_filename
        squared_counts_path = f / squared_counts_filename
        print(f"Reading {subfolder} with {n} events")
        if not counts_path.exists():
            fatal(f"merge_freeflight: {counts_path} does not exist")
        if not squared_counts_path.exists():
            fatal(f"merge_freeflight: {squared_counts_path} does not exist")
        img_counts = sitk.GetArrayFromImage(sitk.ReadImage(counts_path)) / n
        img_squared_counts = (
            sitk.GetArrayFromImage(sitk.ReadImage(squared_counts_path)) / n
        )
        if total_counts is None:
            total_counts = img_counts
            total_squared_counts = img_squared_counts
        else:
            total_counts += img_counts
            total_squared_counts += img_squared_counts
        # current variance
        v = (img_squared_counts - np.power(img_counts, 2)) / (n - 1) * (n**2)
        if total_variance is None:
            total_variance = v
        else:
            total_variance += v

    # compute uncertainty
    uncertainty = np.divide(
        np.sqrt(total_variance),
        total_counts,
        out=np.zeros_like(total_variance),
        where=total_counts != 0,
    )

    # scale and write images
    total_counts *= ref_n
    img = sitk.GetImageFromArray(total_counts)
    img.CopyInformation(img_counts)
    sitk.WriteImage(img, folder / counts_filename)
    img = sitk.GetImageFromArray(uncertainty)
    img.CopyInformation(img_counts)
    sitk.WriteImage(img, folder / output_filename)


def spect_freeflight_merge(
    folder,
    n_prim,
    n_scatter,
    n_target,
    prim_folder="primary",
    scatter_folder="scatter",
    counts_filename="projection_0_counts.mhd",
    sq_counts_filename="projection_0_squared_counts.mhd",
    merge_filename="projection_0_counts.mhd",
    rel_uncert_suffix="relative_uncertainty",
    spr_filename="projection_0_spr.mhd",
    verbose=True,
):
    # make the paths
    prim_folder = Path(prim_folder)
    scatter_folder = Path(scatter_folder)

    # primary
    if n_prim > 0:
        img = folder / prim_folder / counts_filename
        sq_img = folder / prim_folder / sq_counts_filename
        out = folder / prim_folder / f"{img.stem}_{rel_uncert_suffix}.mhd"
        _, prim, prim_squared = history_rel_uncertainty_from_files(
            img, sq_img, n_prim, out
        )
    else:
        prim = None
        prim_squared = None

    # scatter
    if n_scatter > 0:
        img = folder / scatter_folder / counts_filename
        sq_img = folder / scatter_folder / sq_counts_filename
        out = folder / scatter_folder / f"{img.stem}_{rel_uncert_suffix}.mhd"
        _, scatter, scatter_squared = history_rel_uncertainty_from_files(
            img, sq_img, n_scatter, out
        )
    else:
        scatter = None
        scatter_squared = None

    # combined (combined prim/scatter is scaled to n_primary)
    uncert, mean = history_ff_combined_rel_uncertainty(
        prim, prim_squared, scatter, scatter_squared, n_prim, n_scatter
    )

    # combined image
    scaling = n_target / n_prim
    mean = mean * scaling
    if verbose:
        print(f"Primary n = {n_prim}  Scatter n = {n_scatter}  Target n = {n_target}")
        if n_scatter > 0:
            print(f"Primary to scatter ratio = {n_prim / n_scatter}")
        print(f"Scaling to target        = {scaling}")

    # Scatter-to-Primary Ratio (SPR)
    if n_scatter > 0:
        vprim = (prim / n_prim) * n_target
        vscatter = (scatter / n_scatter) * n_target
        spr = np.divide(vscatter, vprim, out=np.zeros_like(vscatter), where=vprim != 0)

    # write combined image
    prim_img = sitk.ReadImage(img)
    img = sitk.GetImageFromArray(mean)
    img.CopyInformation(prim_img)
    fn = folder / merge_filename
    sitk.WriteImage(img, fn)
    if verbose:
        print(fn)

    # write combined relative uncertainty
    img = sitk.GetImageFromArray(uncert)
    img.CopyInformation(prim_img)
    fn = folder / f"{fn.stem}_{rel_uncert_suffix}.mhd"
    sitk.WriteImage(img, fn)
    if verbose:
        print(fn)

    # write SPR
    if n_scatter > 0:
        img = sitk.GetImageFromArray(spr)
        img.CopyInformation(prim_img)
        fn = folder / spr_filename
        sitk.WriteImage(img, fn)
        if verbose:
            print(fn)

    # open info if the file exists
    prim_info = {}
    if n_prim > 0:
        prim_info_fn = folder / prim_folder / "ff_info.json"
        if prim_info_fn.is_file():
            with open(prim_info_fn, "r") as f:
                prim_info = json.load(f)

    # open info if the file exists
    scatter_info = {}
    scatter_info_fn = folder / scatter_folder / "ff_info.json"
    if scatter_info_fn.is_file():
        with open(scatter_info_fn, "r") as f:
            scatter_info = json.load(f)
    else:
        scatter_info = {
            "scatter_activity": 0,
            "max_compton_level": 10,
            "angle_tolerance": 10.0,
            "compton_splitting_factor": 300,
            "rayleigh_splitting_factor": 300,
        }

    # write combined information
    info = prim_info
    info.update(scatter_info)
    info_fn = folder / "ff_info.json"
    with open(info_fn, "w") as f:
        json.dump(info, f, indent=4)
