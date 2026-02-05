import pandas as pd
import uproot
import numpy as np

from enum import Enum, auto


class TimeWindowPolicy(Enum):
    NonParalyzable = auto()
    Paralyzable = auto()
    EnergyWinnerParalyzable = auto()


class PositionAttributePolicy(Enum):
    EnergyWinner = auto()
    EnergyWeightedCentroid = auto()


class AttributePolicy(Enum):
    First = auto()
    EnergyWinner = auto()
    Last = auto()


def pileup(
    singles_before_pileup: pd.DataFrame,
    time_window: float,
    time_window_policy: TimeWindowPolicy = TimeWindowPolicy.NonParalyzable,
    position_attribute_policy: PositionAttributePolicy = PositionAttributePolicy.EnergyWeightedCentroid,
    attribute_policy: AttributePolicy = AttributePolicy.First,
) -> dict:
    """
    This function simulates pile-up with the given time window in ns.
    The singles_before_pileup are in a pandas DataFrame.
    It returns a dict in which the keys are volume IDs, and the values are a pandas DataFrame
    representing the singles for that volume ID after pile-up.
    Each single after pile-up has:
    - TotalEnergyDeposit equal to the sum of TotalEnergyDeposit ofall singles in the same time window.
    - PostPosition according to the position_attribute_policy.
    - All other attribute values according to the attribute_policy.
    """
    df = singles_before_pileup  # df for DataFrame
    grouped = df.groupby("PreStepUniqueVolumeID")

    singles_after_pileup = {}
    for volume_id, group in grouped:
        # For each volume, start with a sorted list of singles time values in ns.
        group = group.sort_values("GlobalTime")
        times = group["GlobalTime"].values

        current = 0  # index of a single that opens the current time window
        next_single = 1
        while next_single < len(times):
            window_begin = times[current]
            # Increment next until it points to the single that opens the next time window.
            while (
                next_single < len(times)
                and times[next_single] <= window_begin + time_window
            ):
                if time_window_policy == TimeWindowPolicy.Paralyzable:
                    window_begin = times[next_single]
                elif time_window_policy == TimeWindowPolicy.EnergyWinnerParalyzable:
                    # In EnergyWinnerParalyzable mode, we extend the time window only if
                    # the next single has higher energy than the current highest-energy single.
                    current_slice = group.iloc[current:next_single]
                    max_energy = current_slice["TotalEnergyDeposit"].max()
                    if group.iloc[next_single]["TotalEnergyDeposit"] > max_energy:
                        window_begin = times[next_single]
                next_single += 1

            if next_single > current + 1:
                # We have found a group of at least two singles in the same time window.
                group_slice = group.iloc[current:next_single]

                # Find the single with the highest TotalEnergyDeposit in the time window.
                max_energy_idx = group_slice["TotalEnergyDeposit"].idxmax()

                # Create a single with the attribute values according to attribute_policy.
                if attribute_policy == AttributePolicy.First:
                    pileup_row = group_slice.iloc[0].copy()
                elif attribute_policy == AttributePolicy.EnergyWinner:
                    pileup_row = group.loc[max_energy_idx].copy()
                elif attribute_policy == AttributePolicy.Last:
                    pileup_row = group_slice.iloc[-1].copy()

                # Energy is the sum of energies of all contributing singles.
                pileup_row["TotalEnergyDeposit"] = group_slice[
                    "TotalEnergyDeposit"
                ].sum()

                # PostPosition is according to the position_attribute_policy.
                if position_attribute_policy == PositionAttributePolicy.EnergyWinner:
                    pileup_row["PostPosition_X"] = group.loc[max_energy_idx][
                        "PostPosition_X"
                    ]
                    pileup_row["PostPosition_Y"] = group.loc[max_energy_idx][
                        "PostPosition_Y"
                    ]
                    pileup_row["PostPosition_Z"] = group.loc[max_energy_idx][
                        "PostPosition_Z"
                    ]
                elif (
                    position_attribute_policy
                    == PositionAttributePolicy.EnergyWeightedCentroid
                ):
                    total_energy = group_slice["TotalEnergyDeposit"].sum()
                    pileup_row["PostPosition_X"] = (
                        group_slice["PostPosition_X"]
                        * group_slice["TotalEnergyDeposit"]
                    ).sum() / total_energy
                    pileup_row["PostPosition_Y"] = (
                        group_slice["PostPosition_Y"]
                        * group_slice["TotalEnergyDeposit"]
                    ).sum() / total_energy
                    pileup_row["PostPosition_Z"] = (
                        group_slice["PostPosition_Z"]
                        * group_slice["TotalEnergyDeposit"]
                    ).sum() / total_energy

                # Add the combined single to the output.
                singles_after_pileup.setdefault(volume_id, []).append(pileup_row)

                # Update current and next for the next time window.
                current = next_single
                next_single = current + 1

            else:
                # The time window opened by current contains only contains one single.
                # Add that single to the output unchanged.
                singles_after_pileup.setdefault(volume_id, []).append(
                    group.iloc[current]
                )

                # Update current and next for the next time window.
                current += 1
                next_single += 1

            # If there is only one single left, add it to the output unchanged.
            if current == len(times) - 1:
                singles_after_pileup.setdefault(volume_id, []).append(
                    group.iloc[current]
                )

    return singles_after_pileup


def check_gate_pileup(
    root_file_path: str,
    name_before_pileup: str,
    name_after_pileup: str,
    time_window: float,
    time_window_policy: TimeWindowPolicy,
    position_attribute_policy: PositionAttributePolicy,
    attribute_policy: AttributePolicy,
):
    """
    This function checks that the singles generated by GateDigitizerPileupActor are identical
    to the ones generated by the Python pile-up implementation in the pileup() function above.
    """
    with uproot.open(root_file_path) as root_file:
        singles_before_pileup = root_file[name_before_pileup].arrays(library="pd")
        actual_singles_after_pileup = root_file[name_after_pileup].arrays(library="pd")

    expected_singles_after_pileup = pileup(
        singles_before_pileup,
        time_window,
        time_window_policy,
        position_attribute_policy,
        attribute_policy,
    )
    num_expected_singles = sum(
        len(entries) for entries in expected_singles_after_pileup.values()
    )

    print(f"Singles before pile-up: {len(singles_before_pileup)}")
    print(
        f"Expected singles after pile-up: {num_expected_singles} ({num_expected_singles / len(singles_before_pileup) * 100:.01f}%)"
    )
    print(f"Actual singles after pile-up: {len(actual_singles_after_pileup)}")

    all_match = True
    for volume_id in expected_singles_after_pileup.keys():

        # Get the expected singles (Python) and actual singles (GateDigitizerPileupActor) for the current volume.
        expected_singles = pd.DataFrame(expected_singles_after_pileup[volume_id])
        actual_singles = actual_singles_after_pileup[
            actual_singles_after_pileup["PreStepUniqueVolumeID"] == volume_id
        ].reset_index(drop=True)

        # Compare the number of singles
        if len(expected_singles) != len(actual_singles):
            print(
                f"Volume {volume_id}: Expected {len(expected_singles)} singles, got {len(actual_singles)}"
            )
            all_match = False
            continue

        # Compare all attributes, except the volume ID
        for attr in expected_singles.columns:
            if attr == "PreStepUniqueVolumeID":
                continue
            expected_values = expected_singles[attr].values
            actual_values = actual_singles[attr].values
            if np.issubdtype(expected_values.dtype, np.floating):
                if not np.allclose(expected_values, actual_values, rtol=1e-9):
                    print(f"Volume {volume_id}: Attribute {attr} does not match")
                    all_match = False
                    break
            else:
                if not all(expected_values == actual_values):
                    print(f"Volume {volume_id}: Attribute {attr} does not match")
                    all_match = False
                    break

    return all_match
