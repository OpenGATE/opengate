import uproot
from opengate.exception import raise_except
from pathlib import Path
import numpy as np
import awkward as ak


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


def root_tree_get_branch_types(tree, verbose=False):
    branch_types = {}
    for branch_name, series in tree.items():
        dtype = get_array_dtype(series)
        branch_types[branch_name] = dtype
        if verbose:
            print(f"Branch '{branch_name}': {branch_types[branch_name]}")
    return branch_types


def is_uproot_tree(tree):
    # Check if the object has the key methods/attributes that uproot trees have
    return hasattr(tree, "arrays") and hasattr(tree, "keys") and hasattr(tree, "items")


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
