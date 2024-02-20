import awkward as ak


def coincidences_sorter_method_1(singles_tree, time_window, chunk_size=10000):
    """
    Consider the singles and sort them according to coincidences
    :param singles_tree: input tree of singles (root format)
    :param time_window: time windows in G4 units (ns)
    :param chunk_size: events are managed by this chunk size
    :return: the coincidences as a dict of events

    Chunk size is important for very large root file to avoid loading everything in memory

    """
    # prepare the "coincidences" tree (dict)
    # with the same branches as the singles
    # only 2 events per coincidences here, all other coincidences are rejected
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
            singles_tree.keys(), chunk, coincidences, time_window
        )

        # Store the tail of the current chunk for the next iteration
        previous_chunk_tail = current_chunk_tail

    return coincidences


def process_chunk(keys, chunk, coincidences, time_window):
    coinc_events = []
    it = iter(chunk)
    event = next(it)
    try:
        # loop on all events, stop when there is no more
        while True:
            time_windows_open = event["GlobalTime"]
            coinc_events = []
            # keep all events within the time windows
            while event["GlobalTime"] < time_windows_open + time_window:
                coinc_events.append(event)
                event = next(it)
            # only keep coincidences when there are 2 events only
            if len(coinc_events) == 2:
                for k in keys:
                    coincidences[f"{k}1"].append(coinc_events[0][k])
                    coincidences[f"{k}2"].append(coinc_events[1][k])
    except StopIteration:
        pass  # End of events

    return coinc_events


def copy_tree_for_dump(input_tree):
    branches = {}
    for key in input_tree.keys():
        branches[key] = input_tree.arrays([key], library="np")[key]
    return branches
