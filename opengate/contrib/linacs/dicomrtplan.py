from opengate.utility import g4_units
import numpy as np
import pydicom


def liste_CP(file, beam_sequence_ID):
    ds = pydicom.dcmread(file)[0x300A, 0x00B0].value[beam_sequence_ID][0x300A, 0x0111]
    return len(ds.value)


def list_of_beam_sequence_ID(file):
    patient_info = pydicom.dcmread(file)[0x300A, 0x0070]
    nb_of_beam_seq = len(patient_info.value[0][("0x300C", "0x0004")].value)
    id_of_beam_sequence = []
    for i in range(nb_of_beam_seq):
        number_of_mu = retrieve_value_in_DICOM_RTPlan(
            patient_info.value[0],
            [[("0x300C", "0x0004"), i], [("0x300A", "0x0086"), None]],
        )
        if number_of_mu is not None:
            id_of_beam_sequence.append(i)
    return id_of_beam_sequence


def read(file, cp_id="all_cp", arc_id=None):
    mm = g4_units.mm
    jaws_1 = 0
    jaws_2 = 1
    angle = 2
    dir_angle = 3
    isocenter = 4
    dose_weights = 5
    collimation_angle = 6
    leaves = 7
    Mu_number = 8

    jaw_1_array = []
    jaw_2_array = []
    rot_angle_array = []
    isocenter_array = []
    dose_weight_array = []
    collimation_angle_array = []
    leaf_array = []
    if arc_id is None:
        id_of_beam_sequence = list_of_beam_sequence_ID(file)
    else:
        arc_id = int(arc_id)
        id_of_beam_sequence = [arc_id]

    for beam_seq_id in id_of_beam_sequence:
        l_jaws_1 = []
        l_jaws_2 = []
        l_angle = []
        l_dir_angle = []
        l_isocenter = []
        x_leaf = []
        l_dose_weights = []
        l_collimation_angle = []
        data_set = extract_dataset(file, beam_seq_id)
        number_of_MU = data_set[Mu_number]["MU number"]
        key_list = [
            "jaws_1",
            "jaws_2",
            "rot_angle",
            "dir_angle",
            "isocenter",
            "cumulative weight",
            "collimation angle",
        ]
        l_parameters = [
            l_jaws_1,
            l_jaws_2,
            l_angle,
            l_dir_angle,
            l_isocenter,
            l_dose_weights,
            l_collimation_angle,
        ]
        if cp_id == "all_cp":
            nb_cp_id = len(data_set[jaws_1]["jaws_1"])
            l_cp_id = np.arange(0, nb_cp_id, 1)
        for id in l_cp_id:
            for i, key in enumerate(key_list):
                if data_set[i][key][id] is not None:
                    if key == "isocenter":
                        l_parameters[i].append(np.array(data_set[i][key][id]) * mm)
                    elif (
                        key != "rot_angle"
                        and key != "dir_angle"
                        and key != "collimation angle"
                    ):
                        l_parameters[i].append(float(data_set[i][key][id]) * mm)
                    else:
                        l_parameters[i].append(data_set[i][key][id])
                else:
                    if id != 0:
                        if data_set[i][key][id] is None:
                            if l_parameters[i][id - 1] is not None:
                                l_parameters[i].append(l_parameters[i][id - 1])
                        else:
                            l_parameters[i].append(data_set[i][key][id])
                    else:
                        l_parameters[i].append(data_set[i][key][id])

        tmp_dir_angle = []
        for i in range(len(l_dir_angle)):

            if l_dir_angle[i] == "CW":
                tmp_dir_angle.append(1)
            elif l_dir_angle[i] == "CC":
                tmp_dir_angle.append(-1)
            else:
                tmp_dir_angle.append(1)

        l_dir_angle = np.array(tmp_dir_angle)

        for id in l_cp_id:
            leaf_block_1 = []
            leaf_block_2 = []
            leaf_blocks = [leaf_block_1, leaf_block_2]
            for i in range(len(data_set[leaves][0])):
                for side_ID in range(2):
                    if data_set[leaves][0][i]["leaves"][id] is not None:
                        leaf_blocks[side_ID].append(
                            data_set[leaves][side_ID][i]["leaves"][id]
                        )
                    else:
                        if id != 0:
                            if data_set[leaves][0][i]["leaves"][id - 1] is not None:
                                leaf_blocks[side_ID].append(
                                    data_set[leaves][side_ID][i]["leaves"][id - 1]
                                )
                            else:
                                leaf_blocks[side_ID].append(None)
                        else:
                            leaf_blocks[side_ID].append(None)
            if None not in leaf_block_1 and None not in leaf_block_2:
                leaf_block_tmp = np.array(leaf_block_1 + leaf_block_2, dtype=float) * mm
                x_leaf.append(leaf_block_tmp)
            else:
                x_leaf.append([None])

        if None in l_dose_weights:
            diff_dose_weights = None
        else:
            l_dose_weights = np.array(l_dose_weights)
            diff_dose_weights = np.diff(l_dose_weights) * number_of_MU
            dose_weight_array += diff_dose_weights.tolist()
            # diff_dose_weights = diff_dose_weights / np.median(diff_dose_weights)
        if None in l_angle:
            l_angle = None
        else:
            l_angle = np.array(l_angle) * l_dir_angle
            l_angle[l_angle < 0] = -l_angle[l_angle < 0]
            diff_angle = np.diff(l_angle)
            diff_angle[diff_angle > 300] = diff_angle[diff_angle > 300] - 360
            diff_angle[diff_angle < -300] = diff_angle[diff_angle < -300] + 360
            l_angle = l_angle[0:-1] + diff_angle / 2
            l_angle[l_angle > 360] -= 360
            l_angle[l_angle < 0] += 360
            rot_angle_array += l_angle.tolist()
        if None in x_leaf[0]:
            x_leaf = None
        else:
            x_leaf = np.array(x_leaf)
            x_leaf = x_leaf[0:-1] + np.diff(x_leaf, axis=0) / 2
            leaf_array += x_leaf.tolist()

        if None in l_jaws_1:
            l_jaws_1 = None
        else:
            l_jaws_1 = np.array(l_jaws_1)
            l_jaws_1 = l_jaws_1[0:-1] + np.diff(l_jaws_1) / 2
            jaw_1_array += l_jaws_1.tolist()

        if None in l_jaws_2:
            l_jaws_2 = None
        else:
            l_jaws_2 = np.array(l_jaws_2)
            l_jaws_2 = l_jaws_2[0:-1] + np.diff(l_jaws_2) / 2
            jaw_2_array += l_jaws_2.tolist()

        if None in l_collimation_angle:
            l_collimation_angle = None
        else:
            l_collimation_angle = np.array(l_collimation_angle, dtype=float)
            l_collimation_angle = (
                l_collimation_angle[0:-1] + np.diff(l_collimation_angle) / 2
            )
            collimation_angle_array += l_collimation_angle.tolist()

        isocenter_array += l_isocenter

    jaw_1_array = np.array(jaw_1_array)
    jaw_2_array = np.array(jaw_2_array)
    leaf_array = np.array(leaf_array)
    rot_angle_array = np.array(rot_angle_array)
    dose_weight_array = np.array(dose_weight_array)
    dose_weight_array = dose_weight_array / np.median(dose_weight_array)
    isocenter_array = np.array(isocenter_array)
    collimation_angle_array = np.array(collimation_angle_array)

    rt_plan_parameters = {
        "jaws 1": jaw_1_array,
        "weight": dose_weight_array,
        "jaws 2": jaw_2_array,
        "leaves": leaf_array,
        "gantry angle": rot_angle_array,
        "isocenter": isocenter_array,
        "collimation angle": collimation_angle_array,
    }
    return rt_plan_parameters


file = "/home/mjacquet/Documents/Simulation_RT_plan/patient_data/IGR/AGORL_CLB_P1toP20/AGORL_P17/RP.1.2.752.243.1.1.20200423201445736.8300.22461.dcm"


def retrieve_value_in_DICOM_RTPlan(cp, list):
    if list[0][0] in cp:
        if list[0][1] is not None:
            value = cp[list[0][0]].value[list[0][1]]
        else:
            value = cp[list[0][0]].value
        if len(list) > 1:
            return retrieve_value_in_DICOM_RTPlan(value, list[1:])
        if len(list) == 1:
            if value == "NONE":
                return None
            return value
    return None


def extract_dataset(file, beam_sequence_ID):
    jaws_1 = 0
    jaws_2 = 1
    angle = 2
    dir_angle = 3
    isocenter = 4
    dose_weights = 5
    limiting_device_angle = 6
    leaves = 7
    MU_number = 8

    ds = pydicom.dcmread(file)[0x300A, 0x00B0].value[beam_sequence_ID][0x300A, 0x0111]
    nb_leaf = 1
    for j in range(len(ds[0][0x300A, 0x011A].value)):
        if ds[0][0x300A, 0x011A].value[j][0x300A, 0x00B8].value == "MLCX":
            nb_leaf = int(len(ds[0][0x300A, 0x011A].value[j][0x300A, 0x011C].value) / 2)

    data_set = [None] * 9
    data_set[jaws_1] = {"jaws_1": []}
    data_set[jaws_2] = {"jaws_2": []}
    data_set[angle] = {"rot_angle": []}
    data_set[dir_angle] = {"dir_angle": []}
    data_set[isocenter] = {"isocenter": []}
    data_set[dose_weights] = {"cumulative weight": []}
    data_set[leaves] = [[{"leaves": []} for _ in range(nb_leaf)] for _ in range(2)]
    data_set[MU_number] = {"MU number": 0}
    data_set[limiting_device_angle] = {"collimation angle": []}
    count = 0

    patient_info = pydicom.dcmread(file)[0x300A, 0x0070]
    number_of_mu = retrieve_value_in_DICOM_RTPlan(
        patient_info.value[0],
        [[("0x300C", "0x0004"), beam_sequence_ID], [("0x300A", "0x0086"), None]],
    )
    data_set[MU_number]["MU number"] = number_of_mu
    for cp in ds.value:
        bool_MLC = False
        bool_jaws = False
        idx_jaws = 0
        idx_MLC = 0
        if (0x300A, 0x011A) in cp:
            for j in range(len(cp[0x300A, 0x011A].value)):
                if cp[0x300A, 0x011A].value[j][0x300A, 0x00B8].value == "MLCX":
                    idx_MLC = j
                    bool_MLC = True

                if cp[0x300A, 0x011A].value[j][0x300A, 0x00B8].value == "ASYMY":
                    idx_jaws = j
                    bool_jaws = True
        if bool_jaws:
            data_set[jaws_1]["jaws_1"].append(
                retrieve_value_in_DICOM_RTPlan(
                    cp, [[("0x300A", "0x011A"), idx_jaws], [("0x300A", "0x011C"), 0]]
                )
            )
            data_set[jaws_2]["jaws_2"].append(
                retrieve_value_in_DICOM_RTPlan(
                    cp, [[("0x300A", "0x011A"), idx_jaws], [("0x300A", "0x011C"), 1]]
                )
            )
        else:
            data_set[jaws_1]["jaws_1"].append(None)
            data_set[jaws_2]["jaws_2"].append(None)

        data_set[angle]["rot_angle"].append(
            retrieve_value_in_DICOM_RTPlan(cp, [[("0x300A", "0x011E"), None]])
        )
        data_set[dir_angle]["dir_angle"].append(
            retrieve_value_in_DICOM_RTPlan(cp, [[("0x300A", "0x011F"), None]])
        )
        data_set[dose_weights]["cumulative weight"].append(
            retrieve_value_in_DICOM_RTPlan(
                cp, [[("0x300C", "0x0050"), 0], [("0x300A", "0x010C"), None]]
            )
        )
        data_set[limiting_device_angle]["collimation angle"].append(
            retrieve_value_in_DICOM_RTPlan(cp, [[("0x300A", "0x0120"), None]])
        )
        data_set[isocenter]["isocenter"].append(ds.value[0]["0x300A", "0x012C"].value)
        if bool_MLC:
            for side_ID in range(2):
                for i in range(nb_leaf):
                    data_set[leaves][side_ID][i]["leaves"].append(
                        retrieve_value_in_DICOM_RTPlan(
                            cp,
                            [
                                [("0x300A", "0x011A"), idx_MLC],
                                [("0x300A", "0x011C"), 80 * side_ID + i],
                            ],
                        )
                    )
        else:
            for side_ID in range(2):
                data_set[leaves][side_ID][0]["leaves"].append(None)

        count += 1
    return data_set
