from opengate.utility import g4_units
import numpy as np
import pydicom


def extract_dataset(file):
    jaws_1 = 0
    jaws_2 = 1
    leaves = 2
    angle = 3
    dir_angle = 4
    isocenter = 5
    dose_weights = 6

    ds = pydicom.dcmread(file)[0x300A, 0x00B0].value[0][0x300A, 0x0111]
    nb_leaf = int(len(ds[0][0x300A, 0x011A].value[1][0x300A, 0x011C].value) / 2)

    data_set = [None] * 7
    data_set[jaws_1] = {"jaws_1": []}
    data_set[jaws_2] = {"jaws_2": []}
    data_set[leaves] = [[{"leaves": []} for i in range(nb_leaf)] for j in range(2)]
    data_set[angle] = {"rot_angle": []}
    data_set[dir_angle] = {"dir_angle": []}
    data_set[isocenter] = {"isocenter": []}
    data_set[dose_weights] = {"cumulative weight": []}

    for cp in ds.value:
        data_set[jaws_1]["jaws_1"].append(
            cp[0x300A, 0x011A].value[0][0x300A, 0x011C].value[0]
        )
        data_set[jaws_2]["jaws_2"].append(
            cp[0x300A, 0x011A].value[0][0x300A, 0x011C].value[1]
        )
        data_set[angle]["rot_angle"].append(cp[0x300A, 0x011E].value)
        data_set[dir_angle]["dir_angle"].append(cp[0x300A, 0x011F].value)
        data_set[dose_weights]["cumulative weight"].append(
            cp[0x300C, 0x0050].value[0][0x300A, 0x010C].value
        )
        data_set[isocenter]["isocenter"].append(ds.value[0][0x300A, 0x012C].value)
        for Sideid in range(2):
            for i in range(nb_leaf):
                data_set[leaves][Sideid][i]["leaves"].append(
                    cp[0x300A, 0x011A].value[1][0x300A, 0x011C].value[80 * Sideid + i]
                )

    return data_set


def read(file, cp_id="all_cp"):
    mm = g4_units.mm
    jaws_1 = 0
    jaws_2 = 1
    leaves = 2
    angle = 3
    dir_angle = 4
    isocenter = 5
    dose_weights = 6

    l_jaws_1 = []
    l_jaws_2 = []
    l_angle = []
    l_dir_angle = []
    l_isocenter = []
    x_leaf = []
    l_dose_weights = []

    data_set = extract_dataset(file)

    if cp_id == "all_cp":
        nb_cp_id = len(data_set[jaws_1]["jaws_1"])
        cp_id = np.arange(0, nb_cp_id, 1)
    for id in cp_id:
        l_jaws_1.append(float(data_set[jaws_1]["jaws_1"][id]) * mm)
        l_jaws_2.append(float(data_set[jaws_2]["jaws_2"][id]) * mm)
        l_angle.append(float(data_set[angle]["rot_angle"][id]))
        l_dir_angle.append(data_set[dir_angle]["dir_angle"][id])
        l_isocenter.append(
            np.array(data_set[isocenter]["isocenter"][id], dtype=float) * mm
        )
        l_dose_weights.append(float(data_set[dose_weights]["cumulative weight"][id]))

    tmp_dir_angle = []
    for i in range(len(l_dir_angle)):
        if l_dir_angle[i] == "CW":
            tmp_dir_angle.append(1)
        elif l_dir_angle[i] == "CC":
            tmp_dir_angle.append(-1)
        else:
            tmp_dir_angle.append(1)

    l_dir_angle = np.array(tmp_dir_angle)
    for id in cp_id:
        leaf_block_1 = []
        leaf_block_2 = []
        for i in range(len(data_set[leaves][0])):
            leaf_block_1.append(data_set[leaves][0][i]["leaves"][id])
            leaf_block_2.append(data_set[leaves][1][i]["leaves"][id])
        leaf_block_tmp = np.array(leaf_block_1 + leaf_block_2, dtype=float) * mm
        for i in range(int(len(leaf_block_tmp) / 2)):
            if leaf_block_tmp[i] == -leaf_block_tmp[i + int(len(leaf_block_tmp) / 2)]:
                leaf_block_tmp[i] = -0 * mm
                leaf_block_tmp[i + int(len(leaf_block_tmp) / 2)] = 0 * mm
        x_leaf.append(leaf_block_tmp)

    l_dose_weights = np.array(l_dose_weights)
    diff_dose_weights = np.diff(l_dose_weights)
    l_angle = np.array(l_angle) * l_dir_angle
    l_angle[l_angle < 0] = -l_angle[l_angle < 0]
    diff_angle = np.diff(l_angle)
    diff_angle[diff_angle > 300] = diff_angle[diff_angle > 300] - 360
    diff_angle[diff_angle < -300] = diff_angle[diff_angle < -300] + 360
    l_angle = l_angle[0:-1] + diff_angle / 2
    l_angle[l_angle > 360] -= 360
    l_angle[l_angle < 0] += 360
    x_leaf = np.array(x_leaf)
    l_jaws_1 = np.array(l_jaws_1)
    l_jaws_1 = l_jaws_1[0:-1] + np.diff(l_jaws_1) / 2
    l_jaws_2 = np.array(l_jaws_2)
    l_jaws_2 = l_jaws_2[0:-1] + np.diff(l_jaws_2) / 2
    x_leaf = x_leaf[0:-1] + np.diff(x_leaf, axis=0) / 2

    diff_dose_weights = diff_dose_weights / np.median(diff_dose_weights)
    rt_plan_parameters = {
        "jaws 1": l_jaws_1,
        "weight": diff_dose_weights,
        "jaws 2": l_jaws_2,
        "leaves": x_leaf,
        "gantry angle": l_angle,
        "isocenter": l_isocenter,
    }

    return rt_plan_parameters
