import logging
import os
from pathlib import Path

import awkward as ak
import matplotlib.pyplot as plt
import numpy as np
import uproot
from scipy.stats import chi2_contingency

from opengate.exception import raise_except

# Get a logger for this specific module. This is the standard practice for libraries.
logger = logging.getLogger(__name__)


def _root_open_trees_safely(paths, tree_name):
    """Opens one or more ROOT files and yields the TTree objects safely."""
    files = [uproot.open(path) for path in paths]
    try:
        trees = [f[tree_name] for f in files]
        yield trees
    except KeyError:
        raise KeyError(f"Tree '{tree_name}' not found in one of the files.")
    finally:
        for f in files:
            f.close()


def _is_branch_numeric(branch):
    """Checks if a TBranch contains a simple, plottable numeric type."""
    # ... (content is unchanged)
    return branch.interpretation.typename in (
        "bool",
        "int8",
        "int16",
        "int32",
        "int64",
        "uint8",
        "uint16",
        "uint32",
        "uint64",
        "float32",
        "float64",
        "double",
    )


def _get_common_numeric_branches(trees, ignore_branches=None):
    """Finds common numeric branches between a list of TTrees."""
    # ... (content is unchanged)
    if not trees:
        return []

    ignore_branches = set(ignore_branches) if ignore_branches else set()

    branch_sets = [set(trees[0].keys())]
    for tree in trees[1:]:
        branch_sets.append(set(tree.keys()))
    common_branches = sorted(list(set.intersection(*branch_sets)))

    numeric_branches = [
        b
        for b in common_branches
        if b not in ignore_branches and _is_branch_numeric(trees[0][b])
    ]
    return numeric_branches


def _get_scaled_weights(branches_data, weight_branch, scaling_factor):
    """Extracts weights, applies a scaling factor, and creates weights if they don't exist."""
    # Get the number of events directly from the length of the awkward array.
    num_events = len(branches_data)

    # Check for field existence using the '.fields' attribute of the awkward array.
    if weight_branch in branches_data.fields:
        weights = branches_data[weight_branch] * scaling_factor
    else:
        weights = np.full(num_events, scaling_factor, dtype=np.float32)

    return weights


def is_uproot_tree(tree):
    # Check if the object has the key methods/attributes that uproot trees have
    return hasattr(tree, "arrays") and hasattr(tree, "keys") and hasattr(tree, "items")


def get_array_dtype(series):
    if isinstance(series, np.ndarray):
        sdtype = series.dtype
        if sdtype == "object":
            return "string"
        if np.issubdtype(sdtype, np.number):
            # Get the type string (e.g., 'i4', 'f8') from the final NumPy array.
            return sdtype.str.replace("<", "")
        if sdtype.kind == "U":
            return "string"
        return sdtype.str
    elif isinstance(series, ak.Array):
        return series.type.content
    else:
        return type(series)


def root_tree_get_branch_data(tree, library="np"):
    branch_data = {}
    for branch_name, series in tree.items():
        if not is_uproot_tree(tree):
            if library == "np":
                series = np.array(tree[branch_name])
            if library == "ak":
                series = ak.Array(tree[branch_name])
        else:
            series = tree.arrays([branch_name], library=library)[branch_name]
        branch_data[branch_name] = series
    return branch_data


def root_tree_get_branch_types(tree, verbose=False):
    branch_types = {}
    for branch_name, series in tree.items():
        dtype = get_array_dtype(series)
        branch_types[branch_name] = dtype
        if verbose:
            print(f"Branch '{branch_name}': {branch_types[branch_name]}")
    return branch_types


def root_tree_get_branch(tree, branch_name, library="np"):
    """
    This version is with numpy arrays, not awkward arrays.
    Use only when the root file is small (for tests)
    """
    if branch_name not in tree:
        # check if a branch with "_X" exists?
        b = f"{branch_name}_X"
        if b not in tree:
            raise_except(f"Error: Branch '{branch_name}' not found in tree.")
        return np.column_stack(
            [
                tree[f"{branch_name}_X"].array(library=library),
                tree[f"{branch_name}_Y"].array(library=library),
                tree[f"{branch_name}_Z"].array(library=library),
            ]
        )
    return tree[branch_name].array(library=library)


def root_read_tree(root_file_path, tree_name="phsp"):
    # if not exists, raise_except
    if not Path(root_file_path).exists():
        raise_except(f"Error: File '{root_file_path}' not found.")
    # open the root file
    with uproot.open(root_file_path) as file:
        if tree_name not in file:
            raise_except(f"Error: TTree '{tree_name}' not found in {root_file_path}.")
        tree = file[tree_name]
    return tree


def root_write_tree(output_file, tree_name, branch_types, branch_data):
    """
    Must be used like :
    with uproot.recreate(output_filename) as output_file:
        root_write_tree(output_file, "hits", hits_types, hits_data)
        root_write_tree(output_file, "singles", singles_types, singles_data)
    """

    # Step 1: Create the empty tree using the dictionary of type strings.
    tree = output_file.mktree(tree_name, branch_types)

    # Step 2: Fill the tree using the dictionary of prepared data arrays.
    tree.extend(branch_data)


def root_write_trees(output_filename, trees_names, trees_data):
    with uproot.recreate(output_filename) as output_file:
        for tree_name, tree_data in zip(trees_names, trees_data):
            t_data = root_tree_get_branch_data(tree_data)
            t_types = root_tree_get_branch_types(t_data)
            root_write_tree(output_file, tree_name, t_types, t_data)


def root_split_tree_by_branch(
    input_path,
    high_val_path,
    low_val_path,
    tree_name,
    branch_name,
    threshold,
    verbose=False,
):
    """
    Splits a TTree into two files based on a threshold value in a specified branch.
    """
    if verbose:
        logger.info(f"Splitting tree '{tree_name}' from '{input_path}'...")
        logger.info(f"Condition: '{branch_name}' > {threshold}")

    try:
        with uproot.open(input_path) as file:
            tree = file[tree_name]
            if branch_name not in tree.keys():
                raise KeyError(
                    f"Branch '{branch_name}' not found in tree '{tree_name}'."
                )

            all_branches = tree.arrays()

            mask = all_branches[branch_name] > threshold
            high_val_events = all_branches[mask]
            low_val_events = all_branches[~mask]

            if verbose:
                logger.info(f"Read {len(all_branches)} total events.")
                logger.info(
                    f"Found {len(high_val_events)} events matching condition (high)."
                )
                logger.info(
                    f"Found {len(low_val_events)} events not matching condition (low)."
                )

            with uproot.recreate(high_val_path) as high_file:
                # high_file.mktree(tree_name, high_val_events)
                high_file[tree_name] = high_val_events
            with uproot.recreate(low_val_path) as low_file:
                # low_file.mktree(tree_name, low_val_events)
                low_file[tree_name] = low_val_events

        if verbose:
            logger.info(f"Successfully wrote high-value events to '{high_val_path}'.")
            logger.info(f"Successfully wrote low-value events to '{low_val_path}'.")

    except FileNotFoundError:
        logger.error(f"Input file not found: '{input_path}'")
        raise
    except Exception as e:
        logger.error(f"An unexpected error occurred during splitting: {e}")
        raise


def root_merge_trees(
    file_paths,
    output_path,
    tree_name,
    scaling_factors=None,
    weight_branch="Weight",
    verbose=False,
):
    """
    Merges TTrees from multiple ROOT files into a single file, applying scaling factors.
    """
    if scaling_factors and len(file_paths) != len(scaling_factors):
        raise ValueError(
            "The number of scaling factors must match the number of file paths."
        )
    if not scaling_factors:
        scaling_factors = [1.0] * len(file_paths)

    if verbose:
        logger.info(f"Merging {len(file_paths)} files into '{output_path}'...")

    try:
        all_data_to_merge = []
        for trees in _root_open_trees_safely(file_paths, tree_name):
            first_branches = set(trees[0].keys())
            for i, tree in enumerate(trees[1:], 1):
                if set(tree.keys()) != first_branches:
                    raise ValueError(
                        f"Branch mismatch between '{file_paths[0]}' and '{file_paths[i]}'."
                    )

            for i, tree in enumerate(trees):
                branches = tree.arrays()
                weights = _get_scaled_weights(
                    branches, weight_branch, scaling_factors[i]
                )

                data_with_weights = ak.with_field(
                    branches, weights, where=weight_branch
                )
                all_data_to_merge.append(data_with_weights)
                if verbose:
                    logger.info(
                        f"Processed '{file_paths[i]}' with scaling factor {scaling_factors[i]}."
                    )

        merged_data = ak.concatenate(all_data_to_merge)

        with uproot.recreate(output_path) as output_file:
            # output_file.mktree(tree_name, merged_data)
            output_file[tree_name] = merged_data

        if verbose:
            logger.info(
                f"Merge complete. Wrote {len(merged_data)} total events to '{output_path}'."
            )

    except Exception as e:
        logger.error(f"An unexpected error occurred during merging: {e}")
        raise


def root_compare_branches_chi2(
    file1_path,
    file2_path,
    tree_name,
    bins=100,
    weight_branch="Weight",
    scaling_factor1=1.0,
    scaling_factor2=1.0,
    significance_level=0.05,
    verbose=False,
):
    """
    Performs a chi-squared test on common branches of two ROOT files.

    This function compares distributions using a chi-squared test on their
    histograms, which can be scaled using factors. This is suitable for
    both weighted and unweighted data.

    Returns:
        tuple: A tuple containing:
            - list: A list of dictionaries with detailed results for each branch.
            - bool: True if no significant differences were found, otherwise False.
    """
    if verbose:
        logger.info(
            f"Starting Chi-Squared comparison between '{os.path.basename(file1_path)}' and '{os.path.basename(file2_path)}'."
        )
        print(f"Significance level (alpha): {significance_level}\n")

    results = []
    all_ok = True
    try:
        for trees in _root_open_trees_safely([file1_path, file2_path], tree_name):
            tree1, tree2 = trees
            branches1, branches2 = tree1.arrays(), tree2.arrays()

            # Get base weights and apply scaling factors
            weights1 = (
                branches1[weight_branch] * scaling_factor1
                if weight_branch in branches1.fields
                else np.full(len(branches1), scaling_factor1)
            )
            weights2 = (
                branches2[weight_branch] * scaling_factor2
                if weight_branch in branches2.fields
                else np.full(len(branches2), scaling_factor2)
            )

            numeric_branches = _get_common_numeric_branches(
                [tree1, tree2], ignore_branches=[weight_branch]
            )
            if not numeric_branches and verbose:
                logger.warning("No common numeric branches found to test.")

            if verbose:
                print(
                    f"{'Branch':<20} | {'Chi2-Statistic':<18} | {'P-Value':<12} | {'Result'}"
                )
                print("-" * 75)

            for branch in numeric_branches:
                data1, data2 = branches1[branch], branches2[branch]
                if len(data1) == 0 or len(data2) == 0:
                    continue

                min_val = min(ak.min(data1), ak.min(data2))
                max_val = max(ak.max(data1), ak.max(data2))
                if (
                    not np.isfinite(min_val)
                    or not np.isfinite(max_val)
                    or min_val == max_val
                ):
                    continue

                hist1, bin_edges = np.histogram(
                    data1, bins=bins, range=(min_val, max_val), weights=weights1
                )
                hist2, _ = np.histogram(
                    data2, bins=bins, range=(min_val, max_val), weights=weights2
                )

                # Add a small epsilon to avoid issues with bins that have zero counts.
                contingency_table = np.array([hist1, hist2]) + 1e-9

                significant = False
                try:
                    chi2, p_value, _, _ = chi2_contingency(contingency_table)
                    if p_value < significance_level:
                        significant = True
                        all_ok = False

                    results.append(
                        {
                            "branch": branch,
                            "chi2": chi2,
                            "p_value": p_value,
                            "significant": significant,
                        }
                    )

                    if verbose:
                        result_str = (
                            f"Significant (p < {significance_level})"
                            if significant
                            else "Not significant"
                        )
                        print(
                            f"{branch:<20} | {chi2:<18.4f} | {p_value:<12.4e} | {result_str}"
                        )

                except ValueError as e:
                    if verbose:
                        print(f"{branch:<20} | {'Error':<18} | {'Error':<12} | {e}")

    except Exception as e:
        logger.error(f"An unexpected error occurred during chi-squared comparison: {e}")
        raise

    if verbose:
        status = "PASSED" if all_ok else "FAILED"
        print(f"\nOverall Chi-Squared Test Status: {status}")

    return results, all_ok


def root_plot_branch_comparison(
    file1_path,
    file2_path,
    tree_name,
    bins=100,
    normalize=False,
    scaling_factor1=1.0,
    scaling_factor2=1.0,
    weight_branch="Weight",
    save_path=None,
    verbose=False,
):
    """
    Compares branches by plotting histograms and returns the figure and axes objects.
    """
    if verbose:
        logger.info(
            f"Generating comparison plots for '{os.path.basename(file1_path)}' and '{os.path.basename(file2_path)}'."
        )

    try:
        for trees in _root_open_trees_safely([file1_path, file2_path], tree_name):
            tree1, tree2 = trees
            numeric_branches = _get_common_numeric_branches(
                trees, ignore_branches=[weight_branch]
            )

            if not numeric_branches:
                if verbose:
                    logger.warning("No common numeric branches found to plot.")
                return None, None

            branches1 = tree1.arrays(
                numeric_branches
                + ([weight_branch] if weight_branch in tree1.keys() else []),
                library="ak",
            )
            branches2 = tree2.arrays(
                numeric_branches
                + ([weight_branch] if weight_branch in tree2.keys() else []),
                library="ak",
            )
            weights1 = _get_scaled_weights(branches1, weight_branch, scaling_factor1)
            weights2 = _get_scaled_weights(branches2, weight_branch, scaling_factor2)

            n_plots = len(numeric_branches)
            n_cols = int(np.ceil(np.sqrt(n_plots)))
            n_rows = int(np.ceil(n_plots / n_cols))
            fig, axes = plt.subplots(
                n_rows, n_cols, figsize=(6 * n_cols, 5 * n_rows), squeeze=False
            )
            axes = axes.flatten()

            for i, branch in enumerate(numeric_branches):
                ax = axes[i]
                data1, data2 = branches1[branch], branches2[branch]

                min_val = min(
                    ak.min(data1) if len(data1) > 0 else np.inf,
                    ak.min(data2) if len(data2) > 0 else np.inf,
                )
                max_val = max(
                    ak.max(data1) if len(data1) > 0 else -np.inf,
                    ak.max(data2) if len(data2) > 0 else -np.inf,
                )
                if (
                    not np.isfinite(min_val)
                    or not np.isfinite(max_val)
                    or min_val == max_val
                ):
                    continue

                ax.hist(
                    data1,
                    bins=bins,
                    range=(min_val, max_val),
                    weights=weights1,
                    histtype="step",
                    linewidth=1.5,
                    label=os.path.basename(file1_path),
                    density=normalize,
                )
                ax.hist(
                    data2,
                    bins=bins,
                    range=(min_val, max_val),
                    weights=weights2,
                    histtype="step",
                    linewidth=1.5,
                    label=os.path.basename(file2_path),
                    density=normalize,
                )
                ax.set_title(f"'{branch}'")
                ax.set_xlabel(branch)
                ax.legend()
                ax.grid(True, linestyle="--", alpha=0.6)

            fig.suptitle("Comparison of ROOT File Branches", fontsize=16)
            for j in range(n_plots, len(axes)):
                fig.delaxes(axes[j])
            plt.tight_layout(rect=[0, 0, 1, 0.97])

            if save_path:
                if verbose:
                    logger.info(f"Saving figure to '{save_path}'")
                fig.savefig(save_path, dpi=300)

            return fig, axes

    except Exception as e:
        logger.error(f"An unexpected error occurred during plotting: {e}")
        raise


def _weighted_stats(values, weights):
    """Calculates weighted mean and standard deviation."""
    if weights is None:
        # If no weights, use unweighted calculations for performance.
        mean = np.mean(values)
        std_dev = np.std(values)
        return mean, std_dev

    # Use ak.values_astype for type casting, compatible with Awkward arrays.
    weights = ak.values_astype(weights, np.float64)
    values = ak.values_astype(values, np.float64)

    sum_weights = ak.sum(weights)
    mean = ak.sum(values * weights) / sum_weights
    variance = ak.sum(weights * (values - mean) ** 2) / sum_weights
    std_dev = np.sqrt(variance)
    return mean, std_dev


def compare_branches_statistics(
    file1_path,
    file2_path,
    tree_name,
    weight_branch="Weight",
    scaling_factor1=1.0,
    scaling_factor2=1.0,
    verbose=False,
):
    """
    Compares statistical moments (mean, std dev) of common numeric branches.

    This function is designed to detect small, systematic biases. It now includes
    a robust metric that compares the difference in means to the average
    standard deviation, which is reliable even for distributions centered at zero.

    Returns:
        list: A list of dictionaries, one for each branch, containing the
              calculated statistics and their differences.
    """
    if verbose:
        logger.info(
            f"Starting statistical moment comparison between '{os.path.basename(file1_path)}' and '{os.path.basename(file2_path)}'."
        )

    results = []
    try:
        for trees in _root_open_trees_safely([file1_path, file2_path], tree_name):
            tree1, tree2 = trees
            branches1, branches2 = tree1.arrays(), tree2.arrays()

            # Get base weights and apply scaling factors
            weights1 = (
                branches1[weight_branch] * scaling_factor1
                if weight_branch in branches1.fields
                else np.full(len(branches1), scaling_factor1)
            )
            weights2 = (
                branches2[weight_branch] * scaling_factor2
                if weight_branch in branches2.fields
                else np.full(len(branches2), scaling_factor2)
            )

            numeric_branches = _get_common_numeric_branches(
                [tree1, tree2], ignore_branches=[weight_branch]
            )

            if verbose:
                print(
                    f"\n{'Branch':<20} | {'File':<12} | {'Mean':<18} | {'Std Dev':<18}"
                )
                print("-" * 100)

            for branch in numeric_branches:
                data1, data2 = branches1[branch], branches2[branch]
                if len(data1) == 0 or len(data2) == 0:
                    continue

                mean1, std1 = _weighted_stats(data1, weights1)
                mean2, std2 = _weighted_stats(data2, weights2)

                mean_diff_abs = np.abs(mean1 - mean2)
                avg_std = (std1 + std2) / 2.0
                # New metric: Mean difference as a fraction of the average standard deviation
                mean_diff_vs_std = mean_diff_abs / avg_std if avg_std != 0 else 0.0
                mean_diff_vs_std *= 100

                branch_results = {
                    "branch": branch,
                    "mean1": mean1,
                    "std1": std1,
                    "mean2": mean2,
                    "std2": std2,
                    "mean_diff_abs": mean_diff_abs,
                    "mean_diff_vs_std": mean_diff_vs_std,
                }
                results.append(branch_results)

                if verbose:
                    print(
                        f"{branch:<20} | {'File 1':<20} | {mean1:<18.6g} | {std1:<18.6g}"
                    )
                    print(f"{'':<20} | {'File 2':<20} | {mean2:<18.6g} | {std2:<18.6g}")
                    # Print the new, more reliable metric
                    print(
                        f"{'':<20} | {'|Mean Diff|/AvgStd %':<20} | {mean_diff_vs_std:<18.6g}"
                    )
                    print("-" * 100)

    except Exception as e:
        logger.error(f"An unexpected error occurred during statistical comparison: {e}")
        raise

    return results


def compare_branches_zscore(
    file1_path,
    file2_path,
    tree_name,
    bins=100,
    weight_branch="Weight",
    scaling_factor1=1.0,
    scaling_factor2=1.0,
    zscore_threshold=3.0,
    verbose=False,
):
    """
    Compares branches by calculating a z-score for the difference in each bin.

    This test is highly sensitive to localized differences. A z-score of N means
    the difference observed in that bin is N standard deviations away from what
    is expected if the distributions were identical.

    Returns:
        list: A list of dictionaries, one for each branch, containing the
              z-scores, bin edges, and the maximum absolute z-score found.
    """
    if verbose:
        logger.info(
            f"Starting Z-Score comparison between '{os.path.basename(file1_path)}' and '{os.path.basename(file2_path)}'."
        )

    results = []
    try:
        for trees in _root_open_trees_safely([file1_path, file2_path], tree_name):
            tree1, tree2 = trees
            branches1, branches2 = tree1.arrays(), tree2.arrays()

            # Get base weights and apply scaling factors
            weights1 = (
                branches1[weight_branch] * scaling_factor1
                if weight_branch in branches1.fields
                else np.full(len(branches1), scaling_factor1)
            )
            weights2 = (
                branches2[weight_branch] * scaling_factor2
                if weight_branch in branches2.fields
                else np.full(len(branches2), scaling_factor2)
            )

            numeric_branches = _get_common_numeric_branches(
                [tree1, tree2], ignore_branches=[weight_branch]
            )
            if not numeric_branches and verbose:
                logger.warning("No common numeric branches found to test.")

            for branch in numeric_branches:
                data1, data2 = branches1[branch], branches2[branch]
                if len(data1) == 0 or len(data2) == 0:
                    continue

                # Determine common binning
                min_val = min(ak.min(data1), ak.min(data2))
                max_val = max(ak.max(data1), ak.max(data2))
                if (
                    not np.isfinite(min_val)
                    or not np.isfinite(max_val)
                    or min_val == max_val
                ):
                    continue

                # Calculate histograms (sum of weights) and sum of weights squared
                hist1, bin_edges = np.histogram(
                    data1, bins=bins, range=(min_val, max_val), weights=weights1
                )
                sum_w2_1 = np.histogram(
                    data1, bins=bins, range=(min_val, max_val), weights=weights1**2
                )[0]

                hist2, _ = np.histogram(
                    data2, bins=bins, range=(min_val, max_val), weights=weights2
                )
                sum_w2_2 = np.histogram(
                    data2, bins=bins, range=(min_val, max_val), weights=weights2**2
                )[0]

                # Calculate z-score: (data1 - data2) / sqrt(err1^2 + err2^2)
                diff = hist1 - hist2
                # The error squared in a bin is the sum of the squares of the weights
                error = np.sqrt(sum_w2_1 + sum_w2_2)

                # Ensure arrays are NumPy for the ufunc to avoid TypeError
                diff = np.asarray(diff)
                error = np.asarray(error)

                z_scores = np.divide(
                    diff, error, out=np.zeros_like(diff), where=error != 0
                )

                max_z = np.max(np.abs(z_scores))
                r = {
                    "branch": branch,
                    "z_scores": z_scores,
                    "bin_edges": bin_edges,
                    "max_abs_zscore": max_z,
                }
                results.append(r)

                if verbose:
                    print(f"\n--- Branch: {branch} ---")
                    print(f"  Max absolute z-score: {max_z:.2f}")
                    outlier_bins = np.where(np.abs(z_scores) > zscore_threshold)[0]
                    if len(outlier_bins) > 0:
                        if "outliers" not in r:
                            r["outliers"] = {}
                        print(
                            f"  Found {len(outlier_bins)} bins with |z-score| > {zscore_threshold}:"
                        )
                        r["outliers"][branch] = outlier_bins
                        for b_idx in outlier_bins:
                            print(
                                f"    - Bin {b_idx} [{bin_edges[b_idx]:.3g}, {bin_edges[b_idx + 1]:.3g}]: z = {z_scores[b_idx]:.2f}"
                            )

    except Exception as e:
        logger.error(f"An unexpected error occurred during z-score comparison: {e}")
        raise

    return results
