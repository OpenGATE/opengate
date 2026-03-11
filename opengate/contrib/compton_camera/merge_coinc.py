#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from pathlib import Path
import pandas as pd
import uproot

from opengate.contrib.root_helpers import (
    root_tree_get_branch_data,
    root_tree_get_branch_types,
    root_write_tree,
)

REQUIRED_BRANCHES = (
    "EventID",
    "GlobalTime",
    "PreStepUniqueVolumeID",
    "TotalEnergyDeposit",
    "PostPosition_X",
    "PostPosition_Y",
    "PostPosition_Z",
)


def _first_tree(f: uproot.ReadOnlyFile):
    key = f.keys()[0]
    name = key.split(";")[0]
    return f[name]


def _get_tree(f: uproot.ReadOnlyFile, preferred: str | None):
    if preferred and preferred in f:
        return f[preferred]
    return _first_tree(f)


def merge_singles_root(
    scatt_root: Path,
    abs_root: Path,
    out_root: Path,  # new merged ROOT file we will create.
    *,
    scatt_tree: str | None = None,
    abs_tree: str | None = None,
    out_tree: str = "Singles",
    overwrite: bool = True,
    save_branches: list[str] | None = None
) -> Path:
    scatt_root = Path(scatt_root)
    abs_root = Path(abs_root)
    out_root = Path(out_root)
    out_root.parent.mkdir(parents=True, exist_ok=True)

    if out_root.exists():
        if overwrite:
            out_root.unlink()
        else:
            return out_root

    with uproot.open(scatt_root) as f_sc, uproot.open(abs_root) as f_ab:
        t_sc = _get_tree(f_sc, scatt_tree)
        t_ab = _get_tree(f_ab, abs_tree)

        branches_sc = set(t_sc.keys())
        branches_ab = set(t_ab.keys())

        # check that all needed columns exist
        miss_sc = set(REQUIRED_BRANCHES) - branches_sc
        miss_ab = set(REQUIRED_BRANCHES) - branches_ab
        if miss_sc:
            raise ValueError(f"Scatterer singles missing branches: {sorted(miss_sc)}")
        if miss_ab:
            raise ValueError(f"Absorber singles missing branches: {sorted(miss_ab)}")
        # check that both trees have the same branches
        if branches_sc != branches_ab:
            only_sc = branches_sc - branches_ab
            only_ab = branches_ab - branches_sc

            if only_sc:
                raise ValueError(f"Branches only in scatterer: {sorted(only_sc)}")
            if only_ab:
                raise ValueError(f"Branches only in absorber: {sorted(only_ab)}")

        # Load all branches from each tree into pandas
        sc_df = t_sc.arrays(library="pd")
        ab_df = t_ab.arrays(library="pd")

        merged = pd.concat([sc_df, ab_df], ignore_index=True)
        # Optionally filter branches before writing
        if save_branches is not None:
            missing = set(save_branches) - set(merged.columns)
            if missing:
                raise ValueError(f"Branches not found in merged data: {sorted(missing)}")

            merged = merged[save_branches]


        # cc_coincidences_sorter expects time-ordered singles
        merged = merged.sort_values(
            ["EventID", "GlobalTime"], kind="mergesort"
        ).reset_index(drop=True)

        # Write merged tree as a TTree
        for col in merged.columns:
            if merged[col].dtype == object:
                merged[col] = pd.Categorical(merged[col])
        data = merged.to_dict(orient="list")
        data = root_tree_get_branch_data(data)
        types = root_tree_get_branch_types(data)
        with uproot.recreate(out_root) as f_out:
            root_write_tree(f_out, out_tree, types, data)

        # Validate exact branch set
        with uproot.open(out_root) as f_chk:
            if out_tree not in f_chk:
                raise ValueError("Merged singles tree is empty; no data to write.")
            out_keys = set(f_chk[out_tree].keys())

        # Warn if "required branches" for sorting are not included in the merged file
        missing_required = set(REQUIRED_BRANCHES) - out_keys
        if missing_required:
            print(
                "WARNING: The merged tree does not include all required branches for sorting.\n"
                f"Missing required branches: {sorted(missing_required)}\n"
                f"Required branches are: {sorted(REQUIRED_BRANCHES)}"
         )

    return out_root
