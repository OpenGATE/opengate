from collections import deque
from itertools import chain

import awkward as ak
import numpy as np
import pandas as pd
import os
import time
import logging
import uproot
import sys
from opengate.contrib.root_helpers import *

logger = logging.getLogger(__name__)


class ChunkSizeTooSmallError(Exception):
    pass


class CoincidenceOutputFile:
    def __init__(self, file_path, file_format):
        assert file_format in ["root", "hdf5"]
        self.file_path = file_path
        self.format = file_format
        self.empty = True

        if self.format == "root":
            # recreate() deletes the file that may already exist with the same name.
            self.file = uproot.recreate(self.file_path)
        elif self.format == "hdf5":
            if os.path.exists(self.file_path):
                os.remove(self.file_path)

    def add(self, coincidences):
        if len(coincidences) == 0:
            return
        # dtype "object" (used for strings) is not accepted by extend() function in uproot,
        # need to convert to categorical.
        for col in coincidences.columns:
            if coincidences[col].dtype == "object":
                coincidences[col] = pd.Categorical(coincidences[col])
        table_name = "Coincidences"
        if self.format == "root":
            coincidences_to_write = coincidences.to_dict(orient="list")
            coincidences_to_write_data = root_tree_get_branch_data(
                coincidences_to_write
            )
            if self.empty:
                coincidences_to_write_types = root_tree_get_branch_types(
                    coincidences_to_write_data
                )
                root_write_tree(
                    self.file,
                    table_name,
                    coincidences_to_write_types,
                    coincidences_to_write_data,
                )
            else:
                coincidences_tree = self.file[table_name]
                coincidences_data = root_tree_get_branch_data(coincidences_tree)
                coincidences_types = root_tree_get_branch_types(coincidences_data)
                root_write_tree(
                    self.file,
                    table_name,
                    coincidences_types,
                    coincidences_data + coincidences_to_write_data,
                )
        elif self.format == "hdf5":
            coincidences.to_hdf(
                self.file_path,
                key=table_name,
                mode="a",
                format="table",
                append=True,
                index=False,
            )
        self.empty = False

    def close(self):
        if self.format == "root":
            self.file.close()


def coincidences_sorter(
    singles_tree,
    time_window,
    policy,
    min_transaxial_distance,
    transaxial_plane,
    max_axial_distance,
    chunk_size=100000,
    return_type="dict",
    output_file_path=None,
    output_file_format="root",
):
    """
    Sort singles and detect coincidences.
    :param singles_tree: input tree of singles (root format)
    :param time_window: time windows in G4 units (ns)
    :param policy: coincidence detection policy, one of:
            "removeMultiples"
            "takeAllGoods"
            "takeWinnerOfGoods"
            "takeIfOnlyOneGood"
            "takeWinnerIfIsGood"
            "takeWinnerIfAllAreGoods"
    :param min_transaxial_distance: minimum transaxial distance between the two singles of a coincidence
    :param transaxial_plane: "xy", "yz", or "xz"
    :param max_axial_distance: maximum axial distance between the two singles of a coincidence
    :param chunk_size: singles are processed by this chunk size
    :param return_type: "dict" or "pd"
    :param output_file_path: if provided, the coincidences will be saved to the given file path
    :param output_file_format: "root" or "hdf5"
    :return: if output_file_path is given, the return value is None, otherwise the coincidences are returned
             as a dict of events (return_type "dict") or a pandas DataFrame (return_type "pd")

    Chunk size is important for very large root file to avoid loading everything in memory at once

    DEV NOTES:
    1) TODO: add option allDigiOpenCoincGate=false, so far only for allDigiOpenCoincGate=true
    """

    # Check the availability of the necessary branches in the root file
    required_branches = {
        "EventID",
        "GlobalTime",
        "PreStepUniqueVolumeID",
        "TotalEnergyDeposit",
        "PostPosition_X",
        "PostPosition_Y",
        "PostPosition_Z",
    }
    missing_branches = required_branches - set(singles_tree.keys())
    if missing_branches:
        if len(missing_branches) == 1:
            raise ValueError(
                f"Required branch {missing_branches.pop()} is missing in singles tree"
            )
        else:
            raise ValueError(
                f"Required branches {missing_branches} are missing in singles tree"
            )

    # Check validity of policy parameter
    policy_functions = {
        "removeMultiples": remove_multiples,
        "takeAllGoods": take_all_goods,
        "takeWinnerOfGoods": take_winner_of_goods,
        "takeIfOnlyOneGood": take_if_only_one_good,
        "takeWinnerIfIsGood": take_winner_if_is_good,
        "takeWinnerIfAllAreGoods": take_winner_if_all_are_goods,
    }
    if policy not in policy_functions:
        raise ValueError(
            f"Unknown policy '{policy}', must be one of {policy_functions.keys()}"
        )

    # Check the validity of return_type or output_file_format and output_file_path.
    if output_file_path is None:
        known_return_types = ["dict", "pd"]
        if return_type not in known_return_types:
            raise ValueError(
                f"Unknown return type '{return_type}', must be one of {known_return_types}"
            )
    else:
        known_output_formats = ["root", "hdf5"]
        if output_file_format not in known_output_formats:
            raise ValueError(
                f"Unknown output file format '{output_file_format}', must be one of {known_output_formats}"
            )
        # Saving to a HDF5 file in append mode requires pytables>=3.10 if numpy>=2.0 is used,
        # but that version of pytables is only supported from Python 3.10 onwards
        if output_file_format == "hdf5" and sys.version_info[1] < 10:
            raise NotImplementedError(
                "HDF5 output is only supported in Python 3.10 or newer"
            )
        if not output_file_path:
            raise ValueError(f"Output file path has not been provided")

    # Since singles in the root file are not guaranteed to be sorted by GlobalTime
    # (especially in the case of multithreaded simulation), singles in one chunk
    # may be more recent than the singles in the next chunk.
    # If that's the case, the chunk size must be increased for successful coincidence sorting.
    original_chunk_size = chunk_size
    max_num_chunk_size_increases = 10
    num_chunk_size_increases = 0
    processing_finished = False
    start = time.time()
    time_lost = 0
    while (
        not processing_finished
        and num_chunk_size_increases < max_num_chunk_size_increases
    ):
        try:
            if output_file_path:
                output_file = CoincidenceOutputFile(
                    output_file_path, output_file_format
                )

            # A double-ended queue is used as a FIFO to store the current and the next chunk of singles
            queue = deque()
            num_singles = 0
            coincidences_to_transfer = None
            coincidences_to_return = []
            for chunk in singles_tree.iterate(step_size=chunk_size):
                num_singles_in_chunk = len(chunk)
                # Convert chunk to pandas DataFrame
                chunk_pd = ak.to_dataframe(chunk)
                # Add a temporary column to assist in applying the various policies
                chunk_pd["SingleIndex"] = range(
                    num_singles, num_singles + num_singles_in_chunk
                )
                # Add chunk to the right of the queue
                queue.append(chunk_pd)
                # Process a chunk, unless only one has been read so far
                if len(queue) > 1:
                    coincidences = process_chunk(queue, time_window)
                    # Before filtering coincidences, we want to make sure that we have all
                    # coincidences that belong to the same time window (same SingleIndex1 value).
                    # When processing the next chunk of singles, we may still find one or more
                    # coincidences that belong to the same time window as the last coincidence so far.
                    #
                    # All coincidences that have a SingleIndex1 value different from the last one
                    # can already be filtered, the others will be transferred to be filtered in
                    # the next iteration.
                    coincidences_to_filter = coincidences.loc[
                        coincidences["SingleIndex1"]
                        != coincidences["SingleIndex1"].iloc[-1]
                    ].reset_index(drop=True)
                    if coincidences_to_transfer is not None:
                        coincidences_to_filter = pd.concat(
                            [coincidences_to_transfer, coincidences_to_filter],
                            axis=0,
                            ignore_index=True,
                        )
                    coincidences_to_transfer = coincidences.loc[
                        coincidences["SingleIndex1"]
                        == coincidences["SingleIndex1"].iloc[-1]
                    ].reset_index(drop=True)
                    # Apply policy
                    filtered_coincidences = policy_functions[policy](
                        coincidences_to_filter,
                        min_transaxial_distance,
                        transaxial_plane,
                        max_axial_distance,
                    )
                    # Remove the temporary SingleIndex columns
                    filtered_coincidences = filtered_coincidences.drop(
                        columns=["SingleIndex1", "SingleIndex2"]
                    )
                    if output_file_path:
                        output_file.add(filtered_coincidences)
                    else:
                        coincidences_to_return.append(filtered_coincidences)
                    # Remove processed chunk from the left of the queue
                    queue.popleft()
                num_singles += num_singles_in_chunk

            # At this point, all chunks have been read. Now process the last chunk.
            coincidences_to_filter = process_chunk(queue, time_window)
            if coincidences_to_transfer is not None:
                coincidences_to_filter = pd.concat(
                    [coincidences_to_transfer, coincidences_to_filter],
                    axis=0,
                    ignore_index=True,
                )
            filtered_coincidences = policy_functions[policy](
                coincidences_to_filter,
                min_transaxial_distance,
                transaxial_plane,
                max_axial_distance,
            )
            # Remove the temporary SingleIndex columns
            filtered_coincidences = filtered_coincidences.drop(
                columns=["SingleIndex1", "SingleIndex2"]
            )
            if output_file_path:
                output_file.add(filtered_coincidences)
            else:
                coincidences_to_return.append(filtered_coincidences)

            processing_finished = True

        except ChunkSizeTooSmallError:
            # Double chunk size and start all over again
            chunk_size *= 2
            num_chunk_size_increases += 1
            time_lost = time.time() - start

        finally:
            if output_file_path:
                output_file.close()

    if not processing_finished:
        # Coincidence sorting has failed, even after repeated increases of the chunk size
        raise ChunkSizeTooSmallError

    if num_chunk_size_increases > 0:
        time_reduction = time_lost / (time.time() - start)
        if time_reduction >= 0.01:
            logger.warning(
                f"Coincidence sorting execution time can be reduced by {time_reduction*100:.02f}% by using chunk_size {chunk_size} instead of {original_chunk_size}"
            )

    if output_file_path is None:
        # Combine all coincidences from all chunks into a single pandas DataFrame
        coincidences_to_return = pd.concat(
            coincidences_to_return, axis=0, ignore_index=True
        )
        if return_type == "dict":
            return coincidences_to_return.to_dict(orient="list")
        elif return_type == "pd":
            return coincidences_to_return


def process_chunk(queue, time_window):
    """
    Processes singles in the chunk queue[0],
    possibly transferring some of those singles to the next chunk queue[1].
    """
    chunk = queue[0]
    next_chunk = queue[1] if len(queue) > 1 else None

    t1 = chunk["GlobalTime"]
    t1_min = np.min(t1)
    t1_max = np.max(t1)

    if next_chunk is not None:
        t2 = next_chunk["GlobalTime"]
        t2_min = np.min(t2)
        t2_max = np.max(t2)
        # Require that the next chunk's time interval is later than
        # the current chunk's time interval (overlap (t2_min < t1_max) is allowed).
        if not (t2_min > t1_min and t2_max > t1_max):
            raise ChunkSizeTooSmallError

    # Find coincidences in the current chunk
    coincidences = run_coincidence_detection_in_chunk(chunk, time_window)

    if next_chunk is not None:
        # If there are singles in the current chunk that are beyond t_min
        # of the next chunk minus time_window, then we want to process them
        # in the next chunk as well.

        # Remove any coincidences for which those singles have opened the time window
        # in the current chunk.
        coincidences = coincidences.loc[
            coincidences["GlobalTime1"] < t2_min - time_window
        ].reset_index(drop=True)
        # Find and add singles to be treated in the next chunk
        singles_to_transfer = chunk.loc[
            chunk["GlobalTime"] >= t2_min - time_window
        ].reset_index(drop=True)
        queue[1] = pd.concat([singles_to_transfer, next_chunk], axis=0)

    return coincidences


def run_coincidence_detection_in_chunk(chunk, time_window):
    """
    Detects coincidences between singles in the given chunk, excluding coincidences
    between singles in the same volume.
    """
    # Add a temporary column containing hash values of the strings identifying the volumes,
    # to assist in excluding coincidences between singles in the same volume
    # (calculating and comparing hash values is much faster than comparing strings).
    chunk["VolumeIDHash"] = pd.util.hash_pandas_object(
        chunk["PreStepUniqueVolumeID"], index=False
    )
    time_np = chunk["GlobalTime"].to_numpy()
    # Sort the time values chronologically (singles in the chunk may not be in chronological order).
    time_np_sorted_indices = np.argsort(time_np)
    time_np = time_np[time_np_sorted_indices]
    # Create NumPy arrays for the indices of the first and second single in each coincidence.
    indices1 = np.zeros((0,), dtype=np.int32)
    indices2 = np.zeros((0,), dtype=np.int32)
    # Repeatedly consider single pairs that are 1, 2, etc. positions apart in the sorted list,
    # until no more coincidences can be found.
    offset = 1
    while True:
        delta_time = time_np[offset:] - time_np[:-offset]
        indices = np.nonzero(delta_time <= time_window)[0]
        if len(indices) == 0:
            break
        indices1 = np.concatenate((indices1, indices))
        indices2 = np.concatenate((indices2, indices + offset))
        offset += 1
    # Combine indices1 and indices2 in a two-column NumPy array.
    indices12 = np.vstack((indices1, indices2)).T
    # Sort rows such that index1 is increasing, and for rows with the same
    # index1 value, index2 is increasing.
    indices12 = indices12[np.lexsort((indices12[:, 1], indices12[:, 0]))]
    # Create dictionaries to create the names of the columns in the coincidences pandas DataFrame.
    rename_dict1 = {name: name + "1" for name in chunk.columns.tolist()}
    rename_dict2 = {name: name + "2" for name in chunk.columns.tolist()}
    # Create pandas DataFrames with the sorted singles that are part of the coincidences.
    coincidence_singles1 = (
        chunk.iloc[time_np_sorted_indices[indices12[:, 0]]]
        .rename(columns=rename_dict1)
        .reset_index(drop=True)
    )
    coincidence_singles2 = (
        chunk.iloc[time_np_sorted_indices[indices12[:, 1]]]
        .rename(columns=rename_dict2)
        .reset_index(drop=True)
    )
    # Combine both DataFrames into one, interleaving the columns.
    interleaved_columns = list(
        chain(*zip(coincidence_singles1.columns, coincidence_singles2.columns))
    )
    coincidences = pd.concat([coincidence_singles1, coincidence_singles2], axis=1)[
        interleaved_columns
    ]
    # Remove coincidences between singles in the same volume.
    coincidences = coincidences.loc[
        coincidences["VolumeIDHash1"] != coincidences["VolumeIDHash2"]
    ].reset_index(drop=True)
    # Remove the temporary volume ID hash columns.
    coincidences = coincidences.drop(columns=["VolumeIDHash1", "VolumeIDHash2"])

    return coincidences


def remove_multiples(
    coincidences, min_transaxial_distance, transaxial_plane, max_axial_distance
):
    # Remove multiple coincidences.
    # Remaining coincidences are the ones that are alone in their time window.
    coincidences_multiples_removed = filter_multi(coincidences)
    # Only keep coincidences that comply with the minimum transaxial distance
    # and the maximum axial distance.
    coincidences_output = filter_goods(
        coincidences_multiples_removed,
        min_transaxial_distance,
        transaxial_plane,
        max_axial_distance,
    )
    return coincidences_output


def take_all_goods(
    coincidences, min_transaxial_distance, transaxial_plane, max_axial_distance
):
    # Only keep coincidences that comply with the minimum transaxial distance
    # and the maximum axial distance.
    return filter_goods(
        coincidences, min_transaxial_distance, transaxial_plane, max_axial_distance
    )


def take_winner_of_goods(
    coincidences, min_transaxial_distance, transaxial_plane, max_axial_distance
):
    # Of all the "good" coincidences in a window, only keep the one with highest energy.

    coincidences_goods = filter_goods(
        coincidences, min_transaxial_distance, transaxial_plane, max_axial_distance
    )
    return filter_max_energy(coincidences_goods)


def take_if_only_one_good(
    coincidences, min_transaxial_distance, transaxial_plane, max_axial_distance
):
    # Keep only the "good" coincidences, then remove multiples from the remaining coincidences.
    # As a result, the only coincidences remainining are the ones that are the only "good" one
    # in their coincidence window.

    coincidences_goods = filter_goods(
        coincidences, min_transaxial_distance, transaxial_plane, max_axial_distance
    )

    return filter_multi(coincidences_goods)


def take_winner_if_is_good(
    coincidences, min_transaxial_distance, transaxial_plane, max_axial_distance
):
    # Only keep the coincidence with max energy in each time window, then remove
    # coincidences that are not "good".
    coincidences_winner = filter_max_energy(coincidences)
    return filter_goods(
        coincidences_winner,
        min_transaxial_distance,
        transaxial_plane,
        max_axial_distance,
    )


def take_winner_if_all_are_goods(
    coincidences, min_transaxial_distance, transaxial_plane, max_axial_distance
):
    filtered_coincidences = filter_goods(
        coincidences, min_transaxial_distance, transaxial_plane, max_axial_distance
    )

    # SingleIndex1 is the index of the single that has opened the time window for a coincidence.
    # Coincidences with the same value of SingleIndex1 belong to the same time window.

    # Count the number of occurrences of all SingleIndex1 values before and after filtering the goods.
    counts = coincidences["SingleIndex1"].value_counts()
    filtered_counts = filtered_coincidences["SingleIndex1"].value_counts()

    # Find the SingleIndex1 values that appear in both count lists.
    common_index1_values = counts.index.intersection(filtered_counts.index)
    # Find the SingleIndex1 values that have the same count value before and after filtering the goods.
    index1_values_with_matching_counts = common_index1_values[
        counts[common_index1_values] == filtered_counts[common_index1_values]
    ]
    # Only keep the coincidences if the count in their time window has not changed
    # by filtering the goods ("all are good").
    filtered_coincidences = filtered_coincidences[
        filtered_coincidences["SingleIndex1"].isin(index1_values_with_matching_counts)
    ]

    # In each time window, take the "winner" with maximal sum of singles deposited energy.
    return filter_max_energy(filtered_coincidences)


def filter_multi(coincidences):

    # Coincidences with the same value of SingleIndex1 belong to the same time window.
    # Remove multiples by removing coincidences where the first single appears more than once.
    return coincidences[~coincidences["SingleIndex1"].duplicated(keep=False)]


def filter_goods(
    coincidences, min_transaxial_distance, transaxial_plane, max_axial_distance
):
    # Calculate the transaxial distance between the singles in each coincidence.
    td = transaxial_distance(coincidences, transaxial_plane)
    # Remove coincidences of which the transaxial distance is below threshold.
    filtered_coincidences = coincidences.loc[td >= min_transaxial_distance].reset_index(
        drop=True
    )
    # Calculate the axial distance between the singles in each remaining coincidence.
    ad = axial_distance(filtered_coincidences, transaxial_plane)
    # Remove coincidences of which the axial distance is above the threshold.
    return filtered_coincidences.loc[ad <= max_axial_distance].reset_index(drop=True)


def filter_max_energy(coincidences):

    filtered_coincidences = coincidences.copy(deep=True)
    # Add a temporary column containing the sum of deposited energy of both singles.
    filtered_coincidences["TotalEnergyInCoincidence"] = (
        filtered_coincidences["TotalEnergyDeposit1"]
        + filtered_coincidences["TotalEnergyDeposit2"]
    )
    # Of all the coincidences with the same "SingleIndex1" value (belonging to the same time window),
    # only keep the one with the highest value in column "TotalEnergyInCoincidence".
    filtered_coincidences = filtered_coincidences.loc[
        filtered_coincidences.groupby("SingleIndex1")[
            "TotalEnergyInCoincidence"
        ].idxmax()
    ]
    # Remove the temporary column.
    return filtered_coincidences.drop(columns=["TotalEnergyInCoincidence"])


def transaxial_distance(coincidences, transaxial_plane):

    if transaxial_plane not in ("xy", "yz", "xz"):
        raise ValueError(
            f"Invalid transaxial_plane: '{transaxial_plane}'. Expected one of 'xy', 'yz' or 'xz'."
        )
    # Extract the first transaxial plane coordinate values for both singles from all coincidences.
    a1, a2 = [
        coincidences[f"PostPosition_{transaxial_plane[0].upper()}{n}"].to_numpy()
        for n in (1, 2)
    ]
    # Extract the second transaxial plane coordinate values for both singles from all coincidences.
    b1, b2 = [
        coincidences[f"PostPosition_{transaxial_plane[1].upper()}{n}"].to_numpy()
        for n in (1, 2)
    ]

    return np.sqrt((a1 - a2) ** 2 + (b1 - b2) ** 2)


def axial_distance(coincidences, transaxial_plane):

    if transaxial_plane not in ("xy", "yz", "xz"):
        raise ValueError(
            f"Invalid transaxial_plane: '{transaxial_plane}'. Expected one of 'xy', 'yz' or 'xz'."
        )
    # Determine the coordinate perpendicular to the transaxial plane.
    axial_coordinate = (set("xyz") - set(transaxial_plane)).pop().upper()
    # Extract the coordinate values for both singles from all coincidences.
    a1, a2 = [
        coincidences[f"PostPosition_{axial_coordinate}{n}"].to_numpy() for n in (1, 2)
    ]

    return np.abs(a1 - a2)


def filter_pandas_tree(df, branch_name="ParentID", value=0, accepted=True):

    if accepted == True:
        df = df[df[branch_name] == value]
        # df.drop(df[df[branch_name] != value].index, inplace=True)

    else:
        df = df[df[branch_name] != value]
        # df.drop(df[df[branch_name] == value].index, inplace=True) #to avoid copie of data frame. Is it worth it?

    # print(f"Number of entries after filtering: {len(df_filtered)}")

    return df


def ccmod_ideal_singles(data):
    required_branches = {
        "EventID",
        "PostPosition_X",
        "PostPosition_Y",
        "PostPosition_Z",
        "ProcessDefinedStep",
        "PreKineticEnergy",
        "PostKineticEnergy",
        "PDGCode",  # it could be optional ?
        "ParentID",
    }
    missing_columns = set(required_branches) - set(
        data.columns
    )  # all branches in required that are not in data columns
    assert (
        not missing_columns
    ), f"Missing columns: {missing_columns}"  # Error if there are missing columns
    data["ProcessDefinedStep"] = data["ProcessDefinedStep"].astype(
        str
    )  # otherwise strange error coming from having string values in the conversion to pandas
    # Filter Hits
    df = filter_pandas_tree(
        data, branch_name="PDGCode", value=22, accepted=True
    )  # it should be the case. Just check it
    df = filter_pandas_tree(
        df, branch_name="ParentID", value=0, accepted=True
    )  # I rewrite the data but I couls save different ones
    df = filter_pandas_tree(
        df, branch_name="ProcessDefinedStep", value="Transportation", accepted=False
    )
    df = filter_pandas_tree(
        df, branch_name="ProcessDefinedStep", value="Rayl", accepted=False
    )  # Check but I think that this process did not generate a pulse

    # Create a new branch  with ideal energy info
    df["IdealTotalEnergyDeposit"] = df["PreKineticEnergy"] - df["PostKineticEnergy"]

    # rm branches (optional)# use of inplace worth it?
    df = df.drop(columns=["PreKineticEnergy"])
    # df = df.drop(columns=["PostKineticEnergy"])
    df = df.drop(columns=["ParentID"])
    df = df.drop(columns=["PDGCode"])

    return df


def ccmod_ideal_coincidences(df):
    required_branches = {"EventID"}
    missing_columns = set(required_branches) - set(
        df.columns
    )  # all branches in required that are not in data columns
    assert (
        not missing_columns
    ), f"Missing columns: {missing_columns}"  # Error if there are missing columns
    # create a new attribute CoincID that groups hits from the same coincidence. We can have more that two hits/pulses in a coincidence oe
    nSingles = df["EventID"].value_counts()
    # keep only events with more than one nSingles
    df = df[df["EventID"].isin(nSingles[nSingles > 1].index)]
    # Assign CoincIDs starting from 0, in order of first appearance).
    df["CoincID"] = pd.factorize(df["EventID"])[0]

    return df


def ccmod_make_cones(
    data,
    energy_key_name="TotalEnergyDeposit",
    posX_key_name="PostPosition_X",
    posY_key_name="PostPosition_Y",
    posZ_key_name="PostPosition_Z",
):

    required_branches = {
        "CoincID",
        posX_key_name,
        posY_key_name,
        posX_key_name,
        energy_key_name,
    }
    missing_columns = set(required_branches) - set(
        data.columns
    )  # all branches in required that are not in data columns
    assert (
        not missing_columns
    ), f"Missing columns: {missing_columns}"  # Error if there are missing columns

    # Attribute name  for energy to create the cones : either IdealTotalEnergyDeposit or TotalEnergyDeposit
    first_vals = data.groupby("CoincID").first()[
        [energy_key_name, posX_key_name, posY_key_name, posZ_key_name]
    ]
    second_vals = (
        data.groupby("CoincID")
        .nth(1)[[posX_key_name, posY_key_name, posZ_key_name]]
        .reset_index()
    )  # reset otherwise old indexes of data

    # last_vals = data.groupby("CoincID").last()[["PostKineticEnergy"]]

    total_energy = data.groupby("CoincID")[energy_key_name].sum()
    EnergyRest = total_energy - first_vals[energy_key_name]

    # it would be nice to have the info of energy and position of the sourve
    data_cones = pd.DataFrame(
        {
            # "CoincID": first_vals.index,#Not needed
            "Energy1": first_vals[energy_key_name].values,
            "EnergyRest": EnergyRest.values,
            "X1": first_vals[posX_key_name].values,
            "Y1": first_vals[posY_key_name].values,
            "Z1": first_vals[posZ_key_name].values,
            #
            "X2": second_vals[posX_key_name].values,
            "Y2": second_vals[posY_key_name].values,
            "Z2": second_vals[posZ_key_name].values,
            # "EnergyExit": last_vals["PostKineticEnergy"].values, #Added if possible
        }
    ).reset_index(
        drop=True
    )  # flatten index Do not save old index from data

    return data_cones
