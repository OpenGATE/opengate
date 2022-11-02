import numpy as np
import os
import opengate as gate
from box import Box
import gatetools.phsp as phsp
import uproot
import matplotlib.pyplot as plt


def root_compare_param_tree(filename, tree_name, keys):
    p = Box()
    p.root_file = filename
    p.tree_name = tree_name
    p.the_keys = keys
    p.scaling = [1.0] * len(keys)
    p.mins = [None] * len(keys)
    p.maxs = [None] * len(keys)
    return p


def root_compare_param(keys, fig):
    p = Box()
    p.tols = [1.0] * len(keys)
    p.fig = fig
    p.hits_tol = 6
    p.nb_bins = 300
    return p


def root_compare4(p1, p2, param):
    """
    Compare two root trees.

    p1 and p2 contain = the root filename, the tree name, a list of branch names
    (see root_compare_param_tree)
    Also, each branch can be scaled and clip to a min/max range.

    param contains: the tolerance values (for all branches), the fig name,
    the nb of bins of the histograms, the tolerance for the nb of hits
    (see root_compare_param)
    """

    # read reference tree
    hits1 = uproot.open(p1.root_file)[p1.tree_name]
    hits1_n = hits1.num_entries
    hits1 = hits1.arrays(library="numpy")

    # read tree
    hits2 = uproot.open(p2.root_file)[p2.tree_name]
    hits2_n = hits2.num_entries
    hits2 = hits2.arrays(library="numpy")

    print(f"Reference tree: {os.path.basename(p1.root_file)} n={hits1_n}")
    print(f"Current tree:   {os.path.basename(p2.root_file)} n={hits2_n}")
    diff = gate.rel_diff(float(hits2_n), float(hits1_n))
    b = np.fabs(diff) < param.hits_tol
    is_ok = gate.print_test(b, f"Difference: {hits1_n} {hits2_n} {diff:+.2f}%")
    print(f"Reference tree: {hits1.keys()}")
    print(f"Current tree:   {hits2.keys()}")

    # compare the given tree
    p1.tree = hits1
    p2.tree = hits2
    is_ok = compare_trees4(p1, p2, param) and is_ok

    # figure
    plt.suptitle(
        f"Values: ref {os.path.basename(p1.root_file)} {os.path.basename(p2.root_file)} "
        f"-> {hits1_n} vs {hits2_n}"
    )
    plt.savefig(param.fig)
    print(f"Figure in {param.fig}")

    return is_ok


def compare_trees4(p1, p2, param):
    nb_fig = 0
    ax = None
    if param.fig:
        nb_fig = len(p1.the_keys)
        nrow, ncol = phsp.fig_get_nb_row_col(nb_fig)
        f, ax = plt.subplots(nrow, ncol, figsize=(25, 10))
    is_ok = True
    n = 0
    print("Compare branches with Wasserstein distance")
    for i in range(len(p2.the_keys)):
        if param.fig:
            a = phsp.fig_get_sub_fig(ax, i)
            n += 1
        else:
            a = False
        b1 = p1.tree[p1.the_keys[i]] * p1.scaling[i]
        b2 = p2.tree[p2.the_keys[i]] * p2.scaling[i]
        if p1.mins[i] is not None:
            b1 = b1[b1 > p1.mins[i]]
        if p1.maxs[i] is not None:
            b1 = b1[b1 < p1.maxs[i]]
        if p2.mins[i] is not None:
            b2 = b2[b2 > p2.mins[i]]
        if p2.maxs[i] is not None:
            b2 = b2[b2 < p2.maxs[i]]
        is_ok = (
            gate.compare_branches_values(
                b1, b2, p1.the_keys[i], p2.the_keys[i], param.tols[i], a, param.nb_bins
            )
            and is_ok
        )

    if param.fig:
        phsp.fig_rm_empty_plot(nb_fig, n, ax)
    return is_ok
