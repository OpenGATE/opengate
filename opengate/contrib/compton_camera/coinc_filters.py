#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd


def kill_multiple_coinc(df: pd.DataFrame, group_col: str = "CoincID") -> pd.DataFrame:
    """
    Remove coincidences that contain more than 2 singles.
    """
    singles_per_coinc = df.groupby(group_col, sort=False).size()
    valid_ids = singles_per_coinc[singles_per_coinc == 2].index
    return df[df[group_col].isin(valid_ids)].copy()


def kill_same_volume_pairs(
    df: pd.DataFrame,
    group_col: str = "CoincID",
    volume_col: str = "PreStepUniqueVolumeID",
) -> pd.DataFrame:
    """
    Remove 2‑single coincidences where both singles occur in the same volume.

    Assumes:
    - Each CoincID has exactly 2 singles (e.g. after kill_multiple_coinc).
    """
    unique_volumes_per_coinc = df.groupby(group_col, sort=False)[volume_col].nunique()
    good_ids = unique_volumes_per_coinc[unique_volumes_per_coinc >= 2].index
    return df[df[group_col].isin(good_ids)].copy()
