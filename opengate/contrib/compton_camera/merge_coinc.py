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

        # check that all needed columns exist
        miss_sc = set(REQUIRED_BRANCHES) - set(t_sc.keys())
        miss_ab = set(REQUIRED_BRANCHES) - set(t_ab.keys())
        if miss_sc:
            raise ValueError(f"Scatterer singles missing branches: {sorted(miss_sc)}")
        if miss_ab:
            raise ValueError(f"Absorber singles missing branches: {sorted(miss_ab)}")

        # read singles from a ROOT tree and tag them with their detector layer.
        def _load_and_tag(tree: uproot.ReadOnlyTree, label: str) -> pd.DataFrame:
            cols = [c for c in REQUIRED_BRANCHES if c != "PreStepUniqueVolumeID"]
            df = tree.arrays(cols, library="pd")
            df["PreStepUniqueVolumeID"] = label
            return df

        sc_df = _load_and_tag(t_sc, "scatterer")
        ab_df = _load_and_tag(t_ab, "absorber")
        merged = pd.concat([sc_df, ab_df], ignore_index=True)
        merged = merged[list(REQUIRED_BRANCHES)]

        # cc_coincidences_sorter expects time-ordered singles
        merged = merged.sort_values(
            ["GlobalTime", "EventID"], kind="mergesort"
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
        if out_keys != set(REQUIRED_BRANCHES):
            raise ValueError(
                "Merged tree does not match required branches. "
                f"Expected {sorted(REQUIRED_BRANCHES)}, got {sorted(out_keys)}"
            )

    return out_root
