import awkward as ak
from tqdm import tqdm
from ..exception import fatal


def coincidences_sorter(
    singles_tree, time_window, minSecDiff, policy, chunk_size=10000
):
    """
    Consider the singles and sort them according to coincidences
    :param singles_tree: input tree of singles (root format)
    :param time_window: time windows in G4 units (ns)
    :param chunk_size: events are managed by this chunk size
    :return: the coincidences as a dict of events

    Chunk size is important for very large root file to avoid loading everything in memory

    DEV NOTES:
    1) potential bug while having several chunks: couple of coincidences too much
    2) filtering during sorting or after? so far done after but maybe better do during for execution speed
    3) removeMultiples policy is applied on EventID maybe should be done differently: checking while time window is open


    """
    # prepare the "coincidences" tree (dict)
    # with the same branches as the singles
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
            singles_tree.keys(), chunk, coincidences, time_window, policy
        )

        # Store the tail of the current chunk for the next iteration
        previous_chunk_tail = current_chunk_tail

    # prepare coincidences_filtered
    coincidences_filtered = {}
    for k in coincidences.keys():
        coincidences_filtered[f"{k}"] = []

    if policy == "removeMultiples":
        ids_to_keep = remove_multiples(coincidences)
    # TODO add other filters

    elif policy == "keepAll":
        return coincidences
    else:
        fatal(f"Error in Coincidence Sorter" f" {policy} is unknown")

    print("-----Filtering------")
    for i in tqdm(range(len(coincidences["EventID1"]))):
        for j in ids_to_keep:
            if coincidences["EventID1"][i] == j:
                for k in coincidences.keys():
                    coincidences_filtered[f"{k}"].append(coincidences[f"{k}"][i])

    return coincidences_filtered


def process_chunk(keys, chunk, coincidences, time_window, policy):
    singles = chunk
    coinc_events = []
    nsingles = len(singles)

    print("-----Sorting------")
    for i in tqdm(range(nsingles - 1)):
        time_window_open = singles[i]["GlobalTime"]
        for j in range(i + 1, nsingles):

            time = singles[j]["GlobalTime"]
            coinc_events = []

            if abs(time - time_window_open) <= time_window:

                # remove if in the same volume
                if (
                    singles[i]["PreStepUniqueVolumeID"]
                    == singles[j]["PreStepUniqueVolumeID"]
                ):
                    break

                # TODO: apply minRingDiff
                # if distance<defined_distance:
                #    break

                coinc_events.append(singles[i])
                coinc_events.append(singles[j])
                for k in keys:
                    coincidences[f"{k}1"].append(coinc_events[0][k])
                    coincidences[f"{k}2"].append(coinc_events[1][k])

            else:
                break  # if the time difference exceeds the time window, break the inner loop

    return coinc_events


def copy_tree_for_dump(input_tree):
    branches = {}
    for key in input_tree.keys():
        branches[key] = input_tree.arrays([key], library="np")[key]
    return branches


def remove_multiples(coincidences):
    # return EventID1 to keep
    ids = coincidences["EventID1"]
    ids = [i for i in ids if ids.count(i) == 1]
    return ids
