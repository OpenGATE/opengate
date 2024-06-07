import awkward as ak
#import itertools
#import collections
import opengate as gate
from tqdm import tqdm
from ..exception import fatal
import numpy as np

def coincidences_sorter(singles_tree, time_window, policy, minDistanceXY, maxDistanceZ, chunk_size=10000):
    """
    Consider the singles and sort them according to coincidences
    :param singles_tree: input tree of singles (root format)
    :param time_window: time windows in G4 units (ns)
    :param chunk_size: events are managed by this chunk size
    :return: the coincidences as a dict of events

    Chunk size is important for very large root file to avoid loading everything in memory

    DEV NOTES: 
    1) potential bug while having several chunks: couple of coincidecnes too much

    """
    
    # prepare the "coincidences" tree (dict)
    # with the same branches as the singles  
    # Prepare the "coincidences" tree (dict) with the same branches as the singles
    
    coincidences = {}
    for k in singles_tree.keys():
        coincidences[f"{k}1"] = []
        coincidences[f"{k}2"] = []

    # Define policy functions
    policy_functions = {
        "removeMultiples": remove_multiples,
        "takeAllGoods": take_all_goods,
        "takeWinnerOfGoods": take_winner_of_goods,
        "keepIfOnlyOneGood": keep_if_only_one_good,
        "takeWinnerIfIsGood": take_winner_if_is_good
    }

         
    # Iterate over chunks of the ROOT file
    previous_chunk_tail = None
    
    for chunk in singles_tree.iterate(step_size=chunk_size):
        # Combine the tail of the previous chunk with the current chunk
        if previous_chunk_tail is not None:
            chunk = ak.concatenate([previous_chunk_tail, chunk], axis=0)

        # Process the current combined chunk
        current_chunk_tail = process_chunk(
            singles_tree.keys(), chunk, coincidences, time_window, minDistanceXY, maxDistanceZ,policy
        )

        # Store the tail of the current chunk for the next iteration
        previous_chunk_tail = current_chunk_tail

    # Apply the policy
    if policy in policy_functions:
        coincidences_filtered = policy_functions[policy](coincidences, time_window, minDistanceXY, maxDistanceZ)
    else:
        fatal(f"Error in Coincidence Sorter: {policy} is unknown")
    
    return coincidences_filtered

    

def process_chunk(keys, chunk, coincidences, time_window, minDistanceXY, maxDistanceZ,policy):
    singles = chunk 
    coinc_events = []
    nsingles=len(singles)
    #print("2 ",policy)
    #print(keys)
  
    print("-----Sorting------")
    
    for i in tqdm(range(nsingles - 1)):
        time_window_open = singles[i]["GlobalTime"]

        for j in range(i + 1, nsingles):
            time = singles[j]["GlobalTime"]

            if abs(time - time_window_open) <= time_window:
                # Remove if in the same volume
                if singles[i]["PreStepUniqueVolumeID"] == singles[j]["PreStepUniqueVolumeID"]:
                    break

                
                coinc_events.append((singles[i], singles[j]))
                for k in keys:
                    coincidences[f"{k}1"].append(singles[i][k])
                    coincidences[f"{k}2"].append(singles[j][k])
            else:
                break  # if the time difference exceeds the time window, break the inner loop

    return coinc_events

def calculate_sector_difference(coincidence,i):
    # Calculate Euclidean distance based on coordinates separately for transaxial and axial planes
    #print(coincidence.keys())
    
    x1, y1, z1 = coincidence["PostPosition_X1"][i], coincidence["PostPosition_Y1"][i], coincidence["PostPosition_Z1"][i]
    x2, y2, z2 = coincidence["PostPosition_X2"][i], coincidence["PostPosition_Y2"][i], coincidence["PostPosition_Z2"][i]
    
    XY_distance = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
    Z_distance = abs(z2 - z1)
    
    return XY_distance, Z_distance  


def filter_coincidences(coincidences, ids_to_keep):
    coincidences_filtered = {k: [] for k in coincidences.keys()}
    print("-----Filtering------")
    for i in tqdm(range(len(coincidences["EventID1"]))):
        if i in ids_to_keep:
            for k in coincidences.keys():
                coincidences_filtered[k].append(coincidences[k][i])
    return coincidences_filtered



def remove_multiples(coincidences, time_window, minDistanceXY, maxDistanceZ):
    event_times = []
    # Filter out multiples within the time window and return coincidences
    for i in range(len(coincidences["EventID1"])):
        if is_good_pair(coincidences, i, minDistanceXY, maxDistanceZ):
            event_times.append(coincidences["GlobalTime1"][i])


    #event_times = coincidences["GlobalTime1"]
    ids_to_keep = []
    time_buckets = {}

    for i, time in enumerate(event_times):
        bucket = int(time // time_window)
        if bucket not in time_buckets:
            time_buckets[bucket] = []
        time_buckets[bucket].append(i)

    for bucket, indices in time_buckets.items():
        if len(indices) == 1:
            ids_to_keep.append(indices[0])
    
    return filter_coincidences(coincidences, ids_to_keep)


def take_all_goods(coincidences, time_window,minDistanceXY, maxDistanceZ):
    # Return all good coincidences
    good_ids = []
    for i in range(len(coincidences["EventID1"])):
        if is_good_pair(coincidences, i, minDistanceXY, maxDistanceZ):
            good_ids.append(i)

    return filter_coincidences(coincidences, good_ids)



def take_winner_of_goods(coincidences, time_window, minDistanceXY, maxDistanceZ):
    event_times = []
    ids_to_keep = []
    time_buckets = {}
    # Filter out multiples within the time window and return coincidences
    for i in range(len(coincidences["EventID1"])):
        if is_good_pair(coincidences, i, minDistanceXY, maxDistanceZ):
            event_times.append(coincidences["GlobalTime1"][i])
   
   

    for i, time in enumerate(event_times):
        bucket = int(time // time_window)
        if bucket not in time_buckets:
            time_buckets[bucket] = []
        time_buckets[bucket].append(i)

    for bucket, indices in time_buckets.items():
        
        if len(indices) > 0:
            highest_energy_index = max(indices, key=lambda idx: coincidences["TotalEnergyDeposit1"][idx] + coincidences["TotalEnergyDeposit2"][idx])
            ids_to_keep.append(highest_energy_index)

    return filter_coincidences(coincidences, ids_to_keep)
  

def keep_if_only_one_good(coincidences, time_window, minDistanceXY, maxDistanceZ):
    event_times = coincidences["GlobalTime1"]
    ids_to_keep = []
    time_buckets = {}

    # Create buckets of indices grouped by their time window
    for i, time in enumerate(event_times):
        bucket = int(time // time_window)
        if bucket not in time_buckets:
            time_buckets[bucket] = []
        time_buckets[bucket].append(i)

    # Check each bucket for at least one "good" coincidence
    for bucket, indices in time_buckets.items():
        good_found = False
        for idx in indices:
            if is_good_pair(coincidences, idx, minDistanceXY, maxDistanceZ):
                good_found = True
                break
        if good_found:
            ids_to_keep.extend(indices)  # If one good pair is found, add all indices in this bucket
    return filter_coincidences(coincidences, ids_to_keep)

def take_winner_if_is_good(coincidences, time_window, minDistanceXY, maxDistanceZ):

    event_times =coincidences["GlobalTime1"]  
    ids_to_keep = []
    time_buckets = {}

    # Populate event_times with all times
    #for i in range(len(coincidences["EventID1"])):
    #    event_times.append(coincidences["GlobalTime1"][i])

    # Create buckets of indices grouped by their time window
    for i, time in enumerate(event_times):
        bucket = int(time // time_window)
        if bucket not in time_buckets:
            time_buckets[bucket] = []
        time_buckets[bucket].append(i)

    # Process each bucket to find the highest energy pair and check if it is good
    for bucket, indices in time_buckets.items():
        if len(indices) > 0:
            highest_energy_index = max(indices, key=lambda idx: coincidences["TotalEnergyDeposit1"][idx] + coincidences["TotalEnergyDeposit2"][idx])
            if is_good_pair(coincidences, highest_energy_index, minDistanceXY, maxDistanceZ):
                ids_to_keep.append(highest_energy_index)

    return filter_coincidences(coincidences, ids_to_keep)




def is_good_pair(coincidences,i, minDistanceXY, maxDistanceZ):
    XY_diff, Z_diff = calculate_sector_difference(coincidences,i)
    if XY_diff < minDistanceXY or Z_diff > maxDistanceZ:
        return False
    else:
        return True




def copy_tree_for_dump(input_tree):
    branches = {}
    for key in input_tree.keys():
        branches[key] = input_tree.arrays([key], library="np")[key]
    return branches
