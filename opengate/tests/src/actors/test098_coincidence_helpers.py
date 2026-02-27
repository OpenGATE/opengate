#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import uproot
import pandas as pd
import numpy as np


def compare_coincidences(
    expected_coincidences: pd.DataFrame, root_filename: str, tolerance: float = 1e-6
) -> bool:
    """
    This function checks that the coincidences in the given pandas Dataframe and
    in the given root file are identical.
    """
    actual_coincidences = uproot.open(root_filename)["coincidences"].arrays(
        library="pd"
    )

    if len(actual_coincidences) != len(expected_coincidences):
        print(
            f"Number of coincidences does not match: expected {len(expected_coincidences)}, got {len(actual_coincidences)}"
        )
        return False

    print(f"{len(actual_coincidences)} coincidences")

    expected_coincidences.sort_values(by=["GlobalTime1"], inplace=True)
    actual_coincidences.sort_values(by=["GlobalTime1"], inplace=True)

    # Columns corresponding with attributes of type "3", e.g. PostPosition, are named differently
    # in the CoincidenceSorterActor and the Python function coincidences_sorter():
    # e.g. PostPosition1_X vs. PostPosition_X1
    # Rename those columns before starting the comparison.
    column_mapping = {}
    for attr in actual_coincidences.columns:
        if attr.endswith("_X") or attr.endswith("_Y") or attr.endswith("_Z"):
            axis = attr[-1]
            num = attr[-3]
            column_mapping[attr] = attr[:-3] + f"_{axis}{num}"
        else:
            column_mapping[attr] = attr
    actual_coincidences = actual_coincidences.rename(columns=column_mapping)

    # Check that all column names match.
    if not set(actual_coincidences.columns) == set(expected_coincidences.columns):
        print("Column names do not match")
        return False

    all_match = True
    for attr in expected_coincidences.columns:
        print(attr)
        expected_values = np.asarray(expected_coincidences[attr].values)
        actual_values = np.asarray(actual_coincidences[attr].values)
        if np.issubdtype(expected_values.dtype, np.floating):
            if not np.allclose(expected_values, actual_values, rtol=1e-9):
                print(f"Attribute {attr} does not match")
                all_match = False
                break
        else:
            if not all(expected_values == actual_values):
                print(f"Attribute {attr} does not match")
                all_match = False
                break

    return all_match
