import uproot
from opengate.exception import raise_except
from pathlib import Path
import numpy as np


def read_root_tree(root_file_path, tree_name="phsp"):
    # if not exists, raise_except
    if not Path(root_file_path).exists():
        raise_except(f"Error: File '{root_file_path}' not found.")
    # open the root file
    with uproot.open(root_file_path) as file:
        if tree_name not in file:
            raise_except(f"Error: TTree '{tree_name}' not found in {root_file_path}.")
        tree = file[tree_name]
    return tree


def tree_get_branch(tree, branch_name):
    """
    This version is with numpy arrays, not awkward arrays.
    Use only when the root file is small (for tests)
    """
    if branch_name not in tree:
        # check if a branch with "_X" exists?
        b = f"{branch_name}_X"
        if b not in tree:
            raise_except(f"Error: Branch '{branch_name}' not found in tree.")
        """vec = {
            "x": tree[f"{branch_name}_X"].array(library="np"),
            "y": tree[f"{branch_name}_Y"].array(library="np"),
            "z": tree[f"{branch_name}_Z"].array(library="np"),
        }"""
        return np.column_stack(
            [
                tree[f"{branch_name}_X"].array(library="np"),
                tree[f"{branch_name}_Y"].array(library="np"),
                tree[f"{branch_name}_Z"].array(library="np"),
            ]
        )
    return tree[branch_name].array(library="np")
