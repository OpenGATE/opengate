import awkward as ak

# import itertools
# import collections
import opengate as gate
from tqdm import tqdm
from ..exception import fatal
import numpy as np
from collections import Counter
import sys


def coincidences_sorter(
    singles_tree,
    time_window,
    policy,
    min_transaxial_distance,
    transaxial_plane,
    max_axial_distance,
    chunk_size=10000,
):
    """
    Consider the singles and sort them according to coincidences
    :param singles_tree: input tree of singles (root format)
    :param time_window: time windows in G4 units (ns)
    :param chunk_size: events are managed by this chunk size
    :return: the coincidences as a dict of events

    Chunk size is important for very large root file to avoid loading everything in memory

    DEV NOTES:
    1) potential bug while having several chunks: couple of coincidecnes too much
    2) potential acceleration is possible
    3) TODO: add option allDigiOpenCoincGate=false, so far only for allDigiOpenCoincGate=true
    4) TODO: parallelisation

    """
    # Get the available branch names
    required_branches = {
        "EventID",
        "GlobalTime",
        "PreStepUniqueVolumeID",
        "TotalEnergyDeposit",
        "PostPosition_X",
        "PostPosition_Y",
        "PostPosition_Z",
    }

    # Find missing branches
    missing_branches = required_branches - set(singles_tree.keys())

    # Check if any branches are missing
    if missing_branches:
        print(
            f"Coincidence Sorter Error: Missing required branches: {missing_branches} in Singles Tree"
        )
        sys.exit(1)  # Immediately stops execution

    # prepare the "coincidences" tree (dict)
    # with the same branches as the singles
    # Prepare the "coincidences" tree (dict) with the same branches as the singles
    coincidences = {}
    for k in singles_tree.keys():
        coincidences[f"{k}1"] = []
        coincidences[f"{k}2"] = []

    # Iterate over chunks of the ROOT file
    previous_chunk_tail = None

    for chunk in singles_tree.iterate(step_size=chunk_size):
        # Combine the tail of the previous chunk with the current chunk
        if previous_chunk_tail is not None:
            chunk = ak.concatenate([previous_chunk_tail, chunk], axis=0)

        # Process the current combined chunk
        current_chunk_tail = process_chunk(
            singles_tree.keys(),
            chunk,
            coincidences,
            time_window,
            min_transaxial_distance,
            transaxial_plane,
            max_axial_distance,
            policy,
        )

        # Store the tail of the current chunk for the next iteration
        previous_chunk_tail = current_chunk_tail

    return coincidences


def process_chunk(
    keys,
    chunk,
    coincidences,
    time_window,
    min_transaxial_distance,
    transaxial_plane,
    max_axial_distance,
    policy,
):
    singles = chunk
    nsingles = len(singles)

    # Define policy functions
    policy_functions = {
        "removeMultiples": remove_multiples,
        "takeAllGoods": take_all_goods,
        "takeWinnerOfGoods": take_winner_of_goods,
        "takeIfOnlyOneGood": take_if_only_one_good,
        "takeWinnerIfIsGood": take_winner_if_is_good,
        "takeWinnerIfAllAreGoods": take_winner_if_all_are_goods,
    }

    print("-----Sorting------")

    coincidences_tmp = {}
    for k in coincidences.keys():
        coincidences_tmp[f"{k}"] = []
    # Loop over singles
    for i in tqdm(range(nsingles - 1)):
        time_window_open = singles[i]["GlobalTime"]

        for j in range(i + 1, nsingles):
            time = singles[j]["GlobalTime"]

            if abs(time - time_window_open) <= time_window:
                # Remove if in the same volume
                if (
                    singles[i]["PreStepUniqueVolumeID"]
                    == singles[j]["PreStepUniqueVolumeID"]
                ):
                    continue

                for k in keys:
                    coincidences_tmp[f"{k}1"].append(singles[i][k])
                    coincidences_tmp[f"{k}2"].append(singles[j][k])

            else:
                # filter coincidences in the same window

                # skip if no coincidecnes in this window
                if len(coincidences_tmp["EventID1"]) == 0:
                    break
                if policy in policy_functions:
                    coincidences_filtered = policy_functions[policy](
                        coincidences_tmp,
                        min_transaxial_distance,
                        transaxial_plane,
                        max_axial_distance,
                    )
                else:
                    fatal(f"Error in Coincidence Sorter: {policy} is unknown")
                # save the filtered coincidences
                if coincidences_filtered:
                    for key in coincidences:
                        for j in range(len(coincidences_filtered[key])):
                            coincidences[key].append(coincidences_filtered[key][j])
                # clean temp containers
                for key in coincidences_tmp.keys():
                    coincidences_tmp[key].clear()

                break  # if the time difference exceeds the time window, break the loop

    return coincidences


def filter_goods(
    coincidences, min_transaxial_distance, transaxial_plane, max_axial_distance
):

    indices_to_keep = []

    for i in range(len(coincidences["EventID1"])):
        # XY_diff, Z_diff = calculate_distance(coincidences)
        x1, y1, z1 = (
            coincidences["PostPosition_X1"][i],
            coincidences["PostPosition_Y1"][i],
            coincidences["PostPosition_Z1"][i],
        )
        x2, y2, z2 = (
            coincidences["PostPosition_X2"][i],
            coincidences["PostPosition_Y2"][i],
            coincidences["PostPosition_Z2"][i],
        )

        if transaxial_plane == "xy":
            trans_diff = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
            axial_diff = abs(z2 - z1)
        elif transaxial_plane == "yz":
            trans_diff = np.sqrt((y2 - y1) ** 2 + (z2 - z1) ** 2)
            axial_diff = abs(x2 - x1)
        elif transaxial_plane == "xz":
            trans_diff = np.sqrt((x2 - x1) ** 2 + (z2 - z1) ** 2)
            axial_diff = abs(y2 - y1)
        else:
            raise ValueError(
                f"Invalid transaxial_plane: '{transaxial_plane}'. Expected one of 'xy', 'yz' or 'xz'."
            )

        # print(trans_diff, " vs. ", min_transaxial_distance, trans_diff > min_transaxial_distance)

        if trans_diff > min_transaxial_distance and axial_diff < max_axial_distance:
            indices_to_keep.append(i)

    coincidences_filtered = {
        key: [value[i] for i in indices_to_keep] for key, value in coincidences.items()
    }

    return coincidences_filtered


def filter_multi(coincidences):
    coincidences_output = {}
    if len(coincidences["EventID1"]) < 2:
        coincidences_output = coincidences
        return coincidences_output
    else:
        return {}


def filter_max_energy(coincidences):

    energy_sums = [
        coincidences["TotalEnergyDeposit1"][i] + coincidences["TotalEnergyDeposit2"][i]
        for i in range(len(coincidences["TotalEnergyDeposit1"]))
    ]
    # Find the index of the maximum energy sum

    if energy_sums:
        max_index = energy_sums.index(max(energy_sums))
        # Filter the dictionary to include only the element at the max energy sum index
        coincidences_filtered = {
            key: [value[max_index]] for key, value in coincidences.items()
        }

        return coincidences_filtered
    else:
        return {}


def remove_multiples(
    coincidences, min_transaxial_distance, transaxial_plane, max_axial_distance
):
    # Remove all multiple coincidences
    # 1) check if good
    # 2) take only ones where one coincidence in a time window

    coincidences_output = filter_multi(coincidences)
    return coincidences_output


def take_all_goods(
    coincidences, min_transaxial_distance, transaxial_plane, max_axial_distance
):
    # Return all good coincidences
    return filter_goods(
        coincidences, min_transaxial_distance, transaxial_plane, max_axial_distance
    )


def take_winner_of_goods(
    coincidences, min_transaxial_distance, transaxial_plane, max_axial_distance
):
    # Take winner of goods
    # 1) check if good
    # 2) take only one with the highest energy (energy1+energy2)

    coincidences_goods = filter_goods(
        coincidences, min_transaxial_distance, transaxial_plane, max_axial_distance
    )
    coincidences_output = filter_max_energy(coincidences_goods)

    return coincidences_output


def take_if_only_one_good(
    coincidences, min_transaxial_distance, transaxial_plane, max_axial_distance
):
    # Take winner if only one good
    # 1) check how many goods
    # 2) if one --> keep

    coincidences_goods = filter_goods(
        coincidences, min_transaxial_distance, transaxial_plane, max_axial_distance
    )

    coincidences_output = filter_multi(coincidences_goods)

    return coincidences_output


def take_winner_if_is_good(
    coincidences, min_transaxial_distance, transaxial_plane, max_axial_distance
):
    # Take winner if it is good one
    # 1) find the winner with Emax
    # 2) if good --> keep

    coincidences_winner = filter_max_energy(coincidences)
    coincidences_output = filter_goods(
        coincidences_winner,
        min_transaxial_distance,
        transaxial_plane,
        max_axial_distance,
    )
    return coincidences_output


def take_winner_if_all_are_goods(
    coincidences, min_transaxial_distance, transaxial_plane, max_axial_distance
):
    # Take winner if all are goods
    # 1) check if all are goods, if not -> skip
    # 2) keep winner with Emax
    coincidences_goods = filter_goods(
        coincidences, min_transaxial_distance, transaxial_plane, max_axial_distance
    )

    if len(coincidences_goods["EventID1"]) != len(coincidences["EventID1"]):
        coincidences_output = {}
    else:
        coincidences_output = filter_max_energy(coincidences_goods)

    return coincidences_output


def copy_tree_for_dump(input_tree):
    branches = {}
    for key in input_tree.keys():
        branches[key] = input_tree.arrays([key], library="np")[key]
    return branches
