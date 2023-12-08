#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import os, sys
from scipy.spatial.transform import Rotation
import numpy as np
import itk
from opengate.tests import utility

sys.path.append("./data")
import opengate.contrib.linacs.elektasynergy as gate_linac
from opengate.geometry.volumes import unite_volumes, subtract_volumes, intersect_volumes
import pydicom
import gatetools as gt
from box import Box
import scipy
import pydicom


def readDicomRTPlan(file, fileNumber):
    # Set variables

    y1Diaphragm = 0
    y2Diaphragm = 1
    leaves = 2
    angle = 3
    dir_angle = 4
    isocenter = 5
    dose_weights = 6

    ds = pydicom.dcmread(file)[0x300A, 0x00B0].value[0][0x300A, 0x0111]
    nbLeaf = int(len(ds[0][0x300A, 0x011A].value[1][0x300A, 0x011C].value) / 2)
    # print(nbLeaf)

    dataSet = [None] * len(file)
    for i in range(len(file)):
        dataSet[i] = [None] * 7
        dataSet[i][y1Diaphragm] = {"Jaws_1": []}
        dataSet[i][y2Diaphragm] = {"Jaws_2": []}
        dataSet[i][leaves] = [[{"Leaves": []} for i in range(nbLeaf)] for j in range(2)]
        dataSet[i][angle] = {"Rot_angle": []}
        dataSet[i][dir_angle] = {"Dir_angle": []}
        dataSet[i][isocenter] = {"Isocenter": []}
        dataSet[i][dose_weights] = {"Cumulative weight": []}

    for cp in ds.value:
        dataSet[fileNumber][y1Diaphragm]["Jaws_1"].append(
            cp[0x300A, 0x011A].value[0][0x300A, 0x011C].value[0]
        )
        dataSet[fileNumber][y2Diaphragm]["Jaws_2"].append(
            cp[0x300A, 0x011A].value[0][0x300A, 0x011C].value[1]
        )
        dataSet[fileNumber][angle]["Rot_angle"].append(cp[0x300A, 0x011E].value)
        dataSet[fileNumber][dir_angle]["Dir_angle"].append(cp[0x300A, 0x011F].value)
        dataSet[fileNumber][dose_weights]["Cumulative weight"].append(
            cp[0x300C, 0x0050].value[0][0x300A, 0x010C].value
        )
        dataSet[fileNumber][isocenter]["Isocenter"].append(
            ds.value[0][0x300A, 0x012C].value
        )
        for SideID in range(2):
            for i in range(nbLeaf):
                dataSet[fileNumber][leaves][SideID][i]["Leaves"].append(
                    cp[0x300A, 0x011A].value[1][0x300A, 0x011C].value[80 * SideID + i]
                )

    return dataSet


def liste_CP(file, fileNumber=0):
    ds = pydicom.dcmread(file)[0x300A, 0x00B0].value[0][0x300A, 0x0111]
    return len(ds.value)


def information_img_patient(path_img=None, open_img=True, img=None):
    if open_img:
        image = itk.imread(path_img)
        offset = np.array(image.GetOrigin())
        dim = np.array(image.GetLargestPossibleRegion().GetSize())
        spacing = np.array(image.GetSpacing())
    else:
        offset = np.array(img.GetOrigin())
        dim = np.array(img.GetLargestPossibleRegion().GetSize())
        spacing = np.array(img.GetSpacing())

    return (offset, dim, spacing)


def Dataset_DICOM_MLC_jaws(file, liste_ID_cp, fileNumber=0):
    mm = gate.g4_units.mm
    y1Diaphragm = 0
    y2Diaphragm = 1
    leaves = 2
    angle = 3
    dir_angle = 4
    isocenter = 5
    dose_weights = 6

    Y_jaws_1 = []
    Y_jaws_2 = []
    l_angle = []
    l_dir_angle = []
    iso_center = []
    x_leaf = []
    l_dose_weights = []

    dataSet = readDicomRTPlan(file, fileNumber)
    for ID in liste_ID_cp:
        Y_jaws_1.append(float(dataSet[fileNumber][y1Diaphragm]["Jaws_1"][ID]) * mm)
        Y_jaws_2.append(float(dataSet[fileNumber][y2Diaphragm]["Jaws_2"][ID]) * mm)
        l_angle.append(float(dataSet[fileNumber][angle]["Rot_angle"][ID]))
        l_dir_angle.append(dataSet[fileNumber][dir_angle]["Dir_angle"][ID])
        iso_center.append(
            np.array(dataSet[fileNumber][isocenter]["Isocenter"][ID], dtype=float) * mm
        )
        l_dose_weights.append(
            float(dataSet[fileNumber][dose_weights]["Cumulative weight"][ID])
        )

    tmp_dir_angle = []
    for i in range(len(l_dir_angle)):
        if l_dir_angle[i] == "CW":
            tmp_dir_angle.append(1)
        elif l_dir_angle[i] == "CC":
            tmp_dir_angle.append(-1)
        else:
            tmp_dir_angle.append(1)

    l_dir_angle = np.array(tmp_dir_angle)
    count = 0
    for ID in liste_ID_cp:
        Leaf_block_1 = []
        Leaf_block_2 = []
        for i in range(len(dataSet[fileNumber][leaves][0])):
            Leaf_block_1.append(dataSet[fileNumber][leaves][0][i]["Leaves"][ID])
            Leaf_block_2.append(dataSet[fileNumber][leaves][1][i]["Leaves"][ID])
        leaf_block_tmp = np.array(Leaf_block_1 + Leaf_block_2, dtype=float) * mm
        for i in range(int(len(leaf_block_tmp) / 2)):
            if leaf_block_tmp[i] == -leaf_block_tmp[i + int(len(leaf_block_tmp) / 2)]:
                leaf_block_tmp[i] = -0 * mm
                leaf_block_tmp[i + int(len(leaf_block_tmp) / 2)] = 0 * mm
        x_leaf.append(leaf_block_tmp)

    l_dose_weights = np.array(l_dose_weights)
    l_angle = np.array(l_angle) * l_dir_angle
    l_angle[l_angle < 0] = -l_angle[l_angle < 0]
    x_leaf = np.array(x_leaf)
    Y_jaws_1 = np.array(Y_jaws_1)
    cp_param = {
        "Y_jaws_1": Y_jaws_1,
        "weight": l_dose_weights,
        "Y_jaws_2": Y_jaws_2,
        "Leaves": x_leaf,
        "Gantry angle": l_angle,
        "Isocenter": iso_center,
    }

    return cp_param


def interpolation_CP(cp_param, seg_cp):
    Y_jaws_1 = cp_param["Y_jaws_1"]
    Y_jaws_2 = cp_param["Y_jaws_2"]
    weights = cp_param["weight"]
    x_leaf = cp_param["Leaves"]
    angle = cp_param["Gantry angle"]
    f_angle_jaws_1 = []
    f_angle_jaws_2 = []
    f_angle_weights = []
    l_f_angle_leaves = []
    for i in range(len(angle) - 1):
        l_angle = np.array([angle[i], angle[i + 1]])
        if np.abs(np.diff(l_angle)) > 300:
            l_angle[np.argmin(l_angle)] += 360
        jaws_1 = np.array([Y_jaws_1[i], Y_jaws_1[i + 1]])
        jaws_2 = np.array([Y_jaws_2[i], Y_jaws_2[i + 1]])
        weight_tmp = np.array([weights[i], weights[i + 1]])
        f_angle_jaws_1.append(scipy.interpolate.interp1d(l_angle, jaws_1))
        f_angle_jaws_2.append(scipy.interpolate.interp1d(l_angle, jaws_2))
        f_angle_weights.append(scipy.interpolate.interp1d(l_angle, weight_tmp))
        l_l_f_angle_leaves = []
        for j in range(len(x_leaf[0])):
            x_leaf_tmp = np.array([x_leaf[i, j], x_leaf[i + 1, j]])
            l_l_f_angle_leaves.append(scipy.interpolate.interp1d(l_angle, x_leaf_tmp))
        # if i == 0:
        l_f_angle_leaves.append(l_l_f_angle_leaves)
    jaws_1_interp = []
    jaws_2_interp = []
    weights_interp = []
    angle_interp = []
    for i in range(len(angle) - 1):
        l_angle = np.array([angle[i], angle[i + 1]])
        if np.abs(np.diff(l_angle)) < 300:
            new_angle = np.linspace(angle[i], angle[i + 1], seg_cp)[:-1]
        else:
            l_angle[np.argmin(l_angle)] += 360
            new_angle = np.linspace(l_angle[0], l_angle[1], seg_cp)[:-1]
        jaws_1_interp += f_angle_jaws_1[i](new_angle).tolist()
        angle_interp += new_angle.tolist()
        jaws_2_interp += f_angle_jaws_2[i](new_angle).tolist()
        weights_interp += f_angle_weights[i](new_angle).tolist()
        leaf_interp_tmp = []
        for j in range(len(x_leaf[0])):
            leaf_interp_tmp.append(l_f_angle_leaves[i][j](new_angle).tolist())
        if i == 0:
            leaf_interp = []
            for j in range(len(x_leaf[0])):
                leaf_interp.append([])
        for j in range(len(x_leaf[0])):
            leaf_interp[j] += leaf_interp_tmp[j]
    for j in range(len(x_leaf[0])):
        leaf_interp[j] += [x_leaf[-1, j]]

    jaws_1_interp = np.asarray(jaws_1_interp + [Y_jaws_1[-1]])
    jaws_2_interp = np.asarray(jaws_2_interp + [Y_jaws_2[-1]])
    weights_interp = np.asarray(weights_interp + [weights[-1]])
    angle_interp = np.asarray(angle_interp + [angle[-1]])
    angle_interp[angle_interp > 360] -= 360
    leaf_interp = np.asarray(leaf_interp)

    nouvel_ordre = [1, 0]
    leaf_interp = np.transpose(leaf_interp, nouvel_ordre)
    diff_dose_weights = np.diff(weights_interp)
    diff_angle = np.diff(angle_interp)
    diff_angle[diff_angle > 300] = diff_angle[diff_angle > 300] - 360
    diff_angle[diff_angle < -300] = diff_angle[diff_angle < -300] + 360
    angle_interp = angle_interp[0:-1] + diff_angle / 2
    angle_interp[angle_interp > 360] -= 360
    angle_interp[angle_interp < 0] += 360
    jaws_1_interp = jaws_1_interp[0:-1] + np.diff(jaws_1_interp) / 2
    jaws_2_interp = jaws_2_interp[0:-1] + np.diff(jaws_2_interp) / 2
    leaf_interp = leaf_interp[0:-1] + np.diff(leaf_interp, axis=0) / 2

    diff_dose_weights = diff_dose_weights / np.median(diff_dose_weights)

    cp_param_interp = {
        "Y_jaws_1": jaws_1_interp,
        "weight": diff_dose_weights,
        "Y_jaws_2": jaws_2_interp,
        "Leaves": leaf_interp,
        "Gantry angle": angle_interp,
        "Isocenter": cp_param["Isocenter"],
    }
    return cp_param_interp


def add_patient_image(sim, name, path_image, img, cp_param):
    # OPEN IMAGE AND ASSOCIATION OF DENSITY TO EACH VOXELS
    creation_rot_img = False
    creation_rot_dose = False
    creation_rot_mask = False
    isocenter = cp_param["Isocenter"][0]
    gcm3 = gate.g4_units.g / gate.g4_units.cm3
    mm = gate.g4_units.mm

    # IMAGE ROTATION ACCORDING TO IEC 61217

    offset, dim, spacing = information_img_patient(path_image + img)
    size = (dim - 1) * spacing
    center = offset + size / 2
    rot = Rotation.from_euler("X", -90, degrees=True).as_matrix()
    rotation = (90, 0, 0)
    image = itk.imread(path_image + img)
    spacing_itk = itk.Vector[itk.D, 3]()
    spacing_rotation = np.abs(np.dot(rot, spacing))
    spacing_itk[0] = spacing_rotation[0]
    spacing_itk[1] = spacing_rotation[1]
    spacing_itk[2] = spacing_rotation[2]
    image2 = gt.applyTransformation(
        input=image,
        newspacing=spacing_itk,
        adaptive=True,
        force_resample=True,
        rotation=rotation,
        rotation_center=center,
        pad=-1024,
    )
    offset, dim, spacing = information_img_patient(open_img=False, img=image2)
    size = (dim - 1) * spacing
    new_center = offset + size / 2
    translation = center - new_center
    image2 = gt.applyTransformation(
        input=image,
        newspacing=spacing_itk,
        adaptive=True,
        force_resample=True,
        rotation=rotation,
        rotation_center=center,
        neworigin=offset + translation,
        pad=-1024,
    )
    vec_isocenter = isocenter - center
    rot_vec = np.dot(rot, vec_isocenter)

    if creation_rot_img:
        itk.imwrite(image2, path_image + img[:-4] + "_rot.mhd")
    if creation_rot_dose:
        image_dose = itk.imread(path_image + img[:-4] + "_dose.mhd")
        image_dose_2 = gt.applyTransformation(
            input=image_dose,
            force_resample=True,
            rotation=rotation,
            rotation_center=center,
            pad=-1024,
        )
        image_dose_2 = gt.applyTransformation(
            input=image_dose_2, like=image2, force_resample=True, pad=-1024
        )
        itk.imwrite(image_dose_2, path_image + img[:-4] + "_rot_dose.mhd")
    if creation_rot_mask:
        image_mask = itk.imread(path_image + img[:-4] + "_mask.mhd")
        image_mask_2 = gt.applyTransformation(
            input=image_mask,
            force_resample=True,
            rotation=rotation,
            rotation_center=center,
            interpolation_mode="NN",
        )
        image_mask_2 = gt.applyTransformation(
            input=image_mask_2,
            like=image2,
            force_resample=True,
            interpolation_mode="NN",
        )
        itk.imwrite(image_mask_2, path_image + img[:-4] + "_rot_mask.mhd")
    offset, dim, spacing = information_img_patient(path_image + img[:-4] + "_rot.mhd")
    size = (dim - 1) * spacing
    center_rot_img = offset + size / 2
    isocenter_rot_img = center + rot_vec
    t_patient = center_rot_img - isocenter_rot_img
    # print(isocenter_rot_img)

    patient = sim.add_volume("Image", "patient")
    patient.image = path_image + img[:-4] + "_rot.mhd"
    patient.mother = name
    patient.material = "G4_AIR"  # material used by default
    f1 = "../data/Schneider2000MaterialsTable.txt"
    f2 = "../data/Schneider2000DensitiesTable.txt"
    tol = 0.05 * gcm3
    (
        patient.voxel_materials,
        materials,
    ) = gate.geometry.materials.HounsfieldUnit_to_material(sim, tol, f1, f2)
    patient.color = [1, 0, 1, 1]
    patient.translation = t_patient

    # ADD DOSE ACTOR
    dose = sim.add_actor("DoseActor", "dose")
    dose.mother = patient.name
    dose.size = np.array(np.round(dim), dtype=int)
    dose.spacing = np.array(spacing, dtype=float)
    # print(np.array(dim_rotation,dtype = int).tolist(),np.array(spacing_rotation,dtype = float).tolist())
    dose.img_coord_system = True
    dose.uncertainty = True
    dose.square = False
    dose.translation = [0, 0, 0]
    dose.hit_type = "random"
    dose.gray = True


def add_target(sim, name, z_linac):
    # unit
    mm = gate.g4_units.mm

    # colors
    red = [1, 0.2, 0.2, 0.8]
    green = [0, 1, 0, 0.2]

    # material
    target_material = f"target_tungsten"
    copper = f"target_copper"

    # target
    target_support = sim.add_volume("Tubs", "target_support")
    target_support.mother = name
    target_support.material = "G4_AIR"
    target_support.rmin = 0
    target_support.rmax = 15 * mm
    target_support.dz = 11 * mm / 2.0
    target_support.translation = [0, 0, z_linac / 2 - 5 * mm]
    target_support.color = [0, 0, 0, 0]  # invisible

    target = sim.add_volume("Tubs", "target")
    target.mother = target_support.name
    target.material = target_material
    target.rmin = 0
    target.rmax = 2.7 * mm
    target.dz = 1 * mm / 2.0
    target.translation = [0, 0, 5 * mm]
    target.color = red

    target_support_top = sim.add_volume("Tubs", "target_support_top")
    target_support_top.mother = target_support.name
    target_support_top.material = copper
    target_support_top.rmin = 2.7 * mm
    target_support_top.rmax = 15 * mm
    target_support_top.dz = 1 * mm / 2.0
    target_support_top.translation = [0, 0, 5 * mm]
    target_support_top.color = green

    target_support_bottom = sim.add_volume("Tubs", "target_support_bottom")
    target_support_bottom.mother = target_support.name
    target_support_bottom.material = copper
    target_support_bottom.rmin = 0
    target_support_bottom.rmax = 15 * mm
    target_support_bottom.dz = 10 * mm / 2.0
    target_support_bottom.translation = [0, 0, -0.5 * mm]
    target_support_bottom.color = green


def add_flattening_filter(sim, name, z_linac):
    # unit
    mm = gate.g4_units.mm
    deg = gate.g4_units.deg

    # colors
    red = [1, 0.7, 0.7, 0.8]
    green = [0.5, 1, 0.5, 0.8]
    yellow = [0, 0.7, 0.7, 0.8]

    # bounding cylinder
    flattening_filter = sim.add_volume("Tubs", "flattening_filter")
    flattening_filter.mother = name
    flattening_filter.material = "G4_AIR"
    flattening_filter.rmin = 0
    flattening_filter.rmax = 40 * mm
    flattening_filter.dz = 24.1 * mm / 2
    flattening_filter.translation = [0, 0, z_linac / 2 - 146.05 * mm]
    flattening_filter.color = [1, 0, 0, 0]  # invisible

    # create all cones
    def add_cone(sim, p):
        c = sim.add_volume("Cons", f"flattening_filter_cone_{p.name}")
        c.mother = "flattening_filter"
        c.material = "flattening_filter_material"
        c.rmin1 = 0
        c.rmax1 = p.rmax1
        c.rmin2 = 0
        c.rmax2 = p.rmax2
        c.dz = p.dz
        c.sphi = 0
        c.dphi = 360 * deg
        c.translation = [0, 0, p.tr]
        c.color = yellow

    cones = [
        [0.001, 5.45, 3.40, 10.35],
        [5.45, 9, 2.7, 7.3],
        [9, 14.5, 4.9, 3.5],
        [14.5, 22.5, 5.5, -1.7],
        [22.5, 32.5, 5.6, -7.25],
        [38.5, 38.5, 2, -11.05],
    ]  ## FIXME check 32.5 ?
    i = 0
    for c in cones:
        cone = Box()
        cone.name = i
        cone.rmax2 = c[0] * mm
        cone.rmax1 = c[1] * mm
        cone.dz = c[2] * mm / 2  # /2 to keep same values than Gate (where dz was /2)
        cone.tr = c[3] * mm
        add_cone(sim, cone)
        i = i + 1


def add_ionizing_chamber(sim, name, z_linac):
    # unit
    mm = gate.g4_units.mm

    # main cylinder
    ionizing_chamber = sim.add_volume("Tubs", "ionizing_chamber")
    ionizing_chamber.mother = name
    ionizing_chamber.material = "G4_AIR"
    ionizing_chamber.rmin = 0
    ionizing_chamber.rmax = 45 * mm
    ionizing_chamber.dz = 9.28 * mm / 2
    ionizing_chamber.translation = [0, 0, z_linac / 2 - 169 * mm]
    ionizing_chamber.color = [0, 0, 0, 0]

    # layers
    def add_layer(sim, p):
        l = sim.add_volume("Tubs", f"ionizing_chamber_mylar_layer_{p.i}")
        l.mother = "ionizing_chamber"
        l.material = "linac_mylar"
        l.rmin = 0
        l.rmax = 45 * mm
        l.dz = 0.012 * mm / 2
        l.translation = [0, 0, p.tr1]

        l = sim.add_volume("Tubs", f"ionizing_chamber_carbon_layer_{p.i}")
        l.mother = "ionizing_chamber"
        l.material = "linac_carbon"
        l.rmin = 0
        l.rmax = 45 * mm
        l.dz = 0.000150 * mm / 2
        l.translation = [0, 0, p.tr2]

    layers = [
        [-2.634, -2.627925],
        [-0.434, -0.427925],
        [0.566, 0.572075],
        [1.566, 1.572075],
        [2.566, 2.572075],
        [3.566, 3.572075],
    ]
    i = 1
    for l in layers:
        ll = Box()
        ll.i = i
        ll.tr1 = l[0] * mm
        ll.tr2 = l[1] * mm
        add_layer(sim, ll)
        i = i + 1


def add_mirror(sim, name, z_linac):
    # unit
    mm = gate.g4_units.mm
    blue = [0, 0, 1, 0.8]

    # main box
    m = sim.add_volume("Box", "mirror")
    m.mother = name
    m.material = "G4_AIR"
    m.size = [137 * mm, 137 * mm, 1.5 * mm]
    m.translation = [0, 0, z_linac / 2 - 225 * mm]
    rot = Rotation.from_euler("x", 37.5, degrees=True)
    m.rotation = rot.as_matrix()

    # mylar
    l = sim.add_volume("Box", "mirror_mylar_layer")
    l.mother = m.name
    l.material = "linac_mylar"
    l.size = [110 * mm, 110 * mm, 0.0012 * mm]
    l.translation = [0, 0, 0.15 * mm]
    l.color = blue

    # alu
    l = sim.add_volume("Box", "mirror_alu_layer")
    l.mother = m.name
    l.material = "linac_aluminium"
    l.size = [110 * mm, 110 * mm, 0.0003 * mm]
    l.translation = [0, 0, -0.6 * mm]
    l.color = blue


def bool_leaf_X_neg(pair=True, count=1):
    mm = gate.g4_units.mm
    interleaf_gap = 0.09 * mm
    # interleaf_gap = 1* mm
    leaf_lenght = 155 * mm
    leaf_height = 90 * mm
    leaf_mean_width = 1.76 * mm
    # leaf_mean_width = 5.79 * mm
    tongues_lenght = 0.8 * mm

    cyl = gate.geometry.volumes.TubsVolume(name="cylinder_leaf_" + str(count))
    cyl.rmin = 0
    cyl.rmax = 170 * mm

    box_rot_leaf = gate.geometry.volumes.BoxVolume(name="Box_leaf_" + str(count))
    box_rot_leaf.size = [200 * mm, leaf_lenght, leaf_height]

    trap_leaf = gate.geometry.volumes.TrapVolume(name="trap_leaf_" + str(count))
    dz = leaf_height / 2
    dy1 = leaf_lenght / 2
    if pair:
        dx1 = 1.94 * mm / 2
        dx3 = 1.58 * mm / 2
        # dx1 = 10*mm / 2
        theta = np.arctan((dx3 - dx1) / (2 * dz))
    else:
        dx1 = 1.58 * mm / 2
        dx3 = 1.94 * mm / 2
        # dx3 = 10*mm / 2
        theta = np.arctan((dx1 - dx3) / (2 * dz))
    alpha1 = 0
    alpha2 = alpha1
    phi = 0
    dy2 = dy1
    dx2 = dx1
    dx4 = dx3

    trap_leaf.dx1 = dx1
    trap_leaf.dx2 = dx2
    trap_leaf.dx3 = dx3
    trap_leaf.dx4 = dx4
    trap_leaf.dy1 = dy1
    trap_leaf.dy2 = dy2
    trap_leaf.dz = dz
    trap_leaf.alp1 = alpha1
    trap_leaf.alp2 = alpha2
    trap_leaf.theta = theta
    trap_leaf.phi = phi

    rot_leaf = Rotation.from_euler("Z", -90, degrees=True).as_matrix()
    rot_cyl = Rotation.from_euler("X", 90, degrees=True).as_matrix()

    if pair:
        trap_tongue = gate.geometry.volumes.TrapVolume(
            name="trap_tongue_p_" + str(count)
        )
    else:
        trap_tongue = gate.geometry.volumes.TrapVolume(
            name="trap_tongue_o_" + str(count)
        )
    dz = tongues_lenght / 2
    dy1 = leaf_lenght / 2
    dx1 = interleaf_gap / 2
    dx3 = dx1
    alpha1 = 0
    alpha2 = alpha1
    if pair:
        theta = np.arctan((1.58 * mm - 1.94 * mm) / (leaf_height))
        # theta = np.arctan((1.58*mm - 10*mm) / (leaf_height))
    else:
        theta = 0
    phi = 0
    dy2 = dy1
    dx2 = dx1
    dx4 = dx1

    trap_tongue.dx1 = dx1
    trap_tongue.dx2 = dx2
    trap_tongue.dx3 = dx3
    trap_tongue.dx4 = dx4
    trap_tongue.dy1 = dy1
    trap_tongue.dy2 = dy2
    trap_tongue.dz = dz
    trap_tongue.alp1 = alpha1
    trap_tongue.alp2 = alpha2
    trap_tongue.theta = theta
    trap_tongue.phi = phi

    bool_leaf = intersect_volumes(box_rot_leaf, trap_leaf, [0, 0, 0], rot_leaf)
    bool_tongue = intersect_volumes(box_rot_leaf, trap_tongue, [0, 0, 0], rot_leaf)
    bool_leaf = unite_volumes(
        bool_leaf, bool_tongue, [0 * mm, (leaf_mean_width + interleaf_gap) / 2, 0 * mm]
    )
    # bool_leaf = unite_volumes(trap_leaf, trap_tongue, [(leaf_mean_width + interleaf_gap) / 2,0 * mm, 0 * mm])
    bool_leaf = intersect_volumes(bool_leaf, cyl, [-92.5 * mm, 0, 7.5 * mm], rot_cyl)

    # leaf = sim.volume_manager.add_volume(bool_leaf,'leaf')
    # # leaf.rotation = rot_leaf
    # a = sim.add_volume("Box",'test')
    # a.size = [2*mm,2*mm,2*mm]

    return bool_leaf


def bool_leaf_X_pos(pair=True, count=1):
    mm = gate.g4_units.mm
    interleaf_gap = 0.09 * mm
    # interleaf_gap = 1* mm
    leaf_lenght = 155 * mm
    leaf_height = 90 * mm
    leaf_mean_width = 1.76 * mm
    # leaf_mean_width = 5.79 * mm
    tongues_lenght = 0.8 * mm

    cyl = gate.geometry.volumes.TubsVolume(name="cylinder_leaf_" + str(count))
    cyl.rmin = 0
    cyl.rmax = 170 * mm

    box_rot_leaf = gate.geometry.volumes.BoxVolume(name="Box_leaf_" + str(count))
    box_rot_leaf.size = [200 * mm, leaf_lenght, leaf_height]

    trap_leaf = gate.geometry.volumes.TrapVolume(name="trap_leaf_" + str(count))
    dz = leaf_height / 2
    dy1 = leaf_lenght / 2
    if pair:
        dx1 = 1.94 * mm / 2
        dx3 = 1.58 * mm / 2
        # dx1 = 10*mm / 2
        theta = np.arctan((dx3 - dx1) / (2 * dz))
    else:
        dx1 = 1.58 * mm / 2
        dx3 = 1.94 * mm / 2
        # dx3 = 10*mm / 2
        theta = np.arctan((dx1 - dx3) / (2 * dz))
    alpha1 = 0
    alpha2 = alpha1
    phi = 0
    dy2 = dy1
    dx2 = dx1
    dx4 = dx3

    trap_leaf.dx1 = dx1
    trap_leaf.dx2 = dx2
    trap_leaf.dx3 = dx3
    trap_leaf.dx4 = dx4
    trap_leaf.dy1 = dy1
    trap_leaf.dy2 = dy2
    trap_leaf.dz = dz
    trap_leaf.alp1 = alpha1
    trap_leaf.alp2 = alpha2
    trap_leaf.theta = theta
    trap_leaf.phi = phi

    rot_leaf = Rotation.from_euler("Z", -90, degrees=True).as_matrix()
    rot_cyl = Rotation.from_euler("X", 90, degrees=True).as_matrix()

    if pair:
        trap_tongue = gate.geometry.volumes.TrapVolume(
            name="trap_tongue_p_" + str(count)
        )
    else:
        trap_tongue = gate.geometry.volumes.TrapVolume(
            name="trap_tongue_o_" + str(count)
        )
    dz = tongues_lenght / 2
    dy1 = leaf_lenght / 2
    dx1 = interleaf_gap / 2
    dx3 = dx1
    alpha1 = 0
    alpha2 = alpha1
    if pair:
        theta = np.arctan((1.58 * mm - 1.94 * mm) / (leaf_height))
        # theta = np.arctan((1.58*mm - 10*mm) / (leaf_height))
    else:
        theta = 0
    phi = 0
    dy2 = dy1
    dx2 = dx1
    dx4 = dx1

    trap_tongue.dx1 = dx1
    trap_tongue.dx2 = dx2
    trap_tongue.dx3 = dx3
    trap_tongue.dx4 = dx4
    trap_tongue.dy1 = dy1
    trap_tongue.dy2 = dy2
    trap_tongue.dz = dz
    trap_tongue.alp1 = alpha1
    trap_tongue.alp2 = alpha2
    trap_tongue.theta = theta
    trap_tongue.phi = phi

    bool_leaf = intersect_volumes(box_rot_leaf, trap_leaf, [0, 0, 0], rot_leaf)
    bool_tongue = intersect_volumes(box_rot_leaf, trap_tongue, [0, 0, 0], rot_leaf)
    bool_leaf = unite_volumes(
        bool_leaf, bool_tongue, [0 * mm, (leaf_mean_width + interleaf_gap) / 2, 0 * mm]
    )
    # bool_leaf = unite_volumes(trap_leaf, trap_tongue, [(leaf_mean_width + interleaf_gap) / 2,0 * mm, 0 * mm])
    bool_leaf = intersect_volumes(bool_leaf, cyl, [92.5 * mm, 0, 7.5 * mm], rot_cyl)

    # leaf = sim.volume_manager.add_volume(bool_leaf,'leaf')
    # # leaf.rotation = rot_leaf
    # a = sim.add_volume("Box",'test')
    # a.size = [2*mm,2*mm,2*mm]

    return bool_leaf


def trap_G4_param(
    obj, dx1, dx2, dx3, dx4, dy1, dy2, dz, theta=0, phi=0, alpha1=0, alpha2=0
):
    obj.dx1 = dx1
    obj.dx2 = dx2
    obj.dx3 = dx3
    obj.dx4 = dx4
    obj.dy1 = dy1
    obj.dy2 = dy2
    obj.dz = dz
    obj.alp1 = alpha1
    obj.alp2 = alpha2
    obj.theta = theta
    obj.phi = phi


def add_MLC(sim, name):
    mm = gate.g4_units.mm
    m = gate.g4_units.m
    cm = gate.g4_units.cm
    interleaf_gap = 0.09 * mm
    # interleaf_gap = 1*mm
    leaf_width = 1.76 * mm
    # leaf_width = 5.79*mm
    leaf_lenght = 155 * mm
    center_MLC = 349.3 * mm
    nb_leaf = 160
    rot_MLC = Rotation.from_euler("Z", 90, degrees=True).as_matrix()

    leaf_p_1 = bool_leaf_X_neg(True)
    leaf_o_1 = bool_leaf_X_neg(False)
    leaf_p_2 = bool_leaf_X_pos(True, count=2)
    leaf_o_2 = bool_leaf_X_pos(False, count=2)

    sim.volume_manager.add_volume(leaf_p_1, "leaf_p_1")
    leaf_p_1.material = "mat_leaf"
    leaf_p_1.mother = name
    leaf_p_1.color = [1, 0.2, 0.6, 0.7]

    sim.volume_manager.add_volume(leaf_o_1, "leaf_o_1")
    leaf_o_1.material = "mat_leaf"
    leaf_o_1.mother = name
    leaf_o_1.color = [1, 0.2, 0.6, 0.7]

    sim.volume_manager.add_volume(leaf_p_2, "leaf_p_2")
    leaf_p_2.material = "mat_leaf"
    leaf_p_2.mother = name
    leaf_p_2.color = [1, 0.2, 0.6, 0.7]

    sim.volume_manager.add_volume(leaf_o_2, "leaf_o_2")
    leaf_o_2.material = "mat_leaf"
    leaf_o_2.mother = name
    leaf_o_2.color = [1, 0.2, 0.6, 0.7]

    size = [1, int(0.25 * nb_leaf), 1]
    tr_blocks = np.array([leaf_lenght, 2 * leaf_width + 2 * interleaf_gap, 0])

    MLC_p_1 = gate.geometry.utility.get_grid_repetition(size, tr_blocks)
    leaf_p_1.translation = MLC_p_1

    MLC_o_1 = gate.geometry.utility.get_grid_repetition(size, tr_blocks)
    leaf_o_1.translation = MLC_o_1

    MLC_p_2 = gate.geometry.utility.get_grid_repetition(size, tr_blocks)
    leaf_p_2.translation = MLC_p_2

    MLC_o_2 = gate.geometry.utility.get_grid_repetition(size, tr_blocks)
    leaf_o_2.translation = MLC_o_2

    for i in range(len(MLC_p_1)):
        MLC_p_1[i] += np.array([-leaf_lenght / 2, leaf_width + interleaf_gap, 0])
        MLC_o_1[i] += np.array([-leaf_lenght / 2, 0, 0])
        MLC_p_2[i] += np.array([leaf_lenght / 2, leaf_width + interleaf_gap, 0])
        MLC_o_2[i] += np.array([leaf_lenght / 2, 0, 0])

    MLC = []

    for i in range(len(MLC_p_1)):
        MLC.append(
            {"translation": MLC_o_1[i], "name": leaf_o_1.name + "_rep_" + str(i)}
        )
        MLC.append(
            {"translation": MLC_p_1[i], "name": leaf_p_1.name + "_rep_" + str(i)}
        )
    for i in range(len(MLC_p_2)):
        MLC.append(
            {"translation": MLC_o_2[i], "name": leaf_o_2.name + "_rep_" + str(i)}
        )
        MLC.append(
            {"translation": MLC_p_2[i], "name": leaf_p_2.name + "_rep_" + str(i)}
        )
    return MLC


def move_MLC_RT_plan(sim, MLC, x_leaf, liste_cp, z_linac, SAD=1000):
    mm = gate.g4_units.mm
    center_MLC = 349.3 * mm
    center_curve_MLC = center_MLC - 7.5 * mm
    fact_iso = center_curve_MLC / SAD
    nb_leaf = 160
    motion_leaves = []
    motion_leaves_t = []
    motion_leaves_r = []
    for i in range(nb_leaf):
        motion_leaves.append(sim.add_actor("MotionVolumeActor", "Move_leaf_" + str(i)))
        motion_leaves[i].mother = MLC[i]["name"]
        motion_leaves[i].translations = []
        motion_leaves[i].rotations = []
        motion_leaves_t.append(motion_leaves[i].translations)
        motion_leaves_r.append(motion_leaves[i].rotations)

    translation_MLC = []
    for n in range(liste_cp):
        for i in range(len(MLC)):
            translation_MLC.append(np.copy(MLC[i]["translation"]))
            motion_leaves_t[i].append(
                translation_MLC[i]
                + np.array(
                    [
                        x_leaf[n, i] * fact_iso,
                        -0.88 * mm - 0.045 * mm,
                        0.5 * z_linac - center_MLC,
                    ]
                )
            )
            # if i > len(MLC)/2 -1 :
            #     rot = Rotation.from_euler("Z", 180, degrees=True).as_matrix()
            #     motion_leaves_r[i].append(rot)
            # else :
            motion_leaves_r[i].append(np.identity(3))


def add_realistic_jaws(sim, name, side, visu=False):
    mm = gate.g4_units.mm
    center_jaws = 470.5 * mm
    jaws_height = 77 * mm
    jaws_lenght_X = 201.84 * mm
    jaws_lenght_tot_X = 229.58 * mm
    jaws_lenght_Y = 205.2 * mm

    # Jaws Structure

    box_jaws = gate.geometry.volumes.BoxVolume(name="box_jaws" + "_" + side)
    box_jaws.size = np.array([jaws_lenght_X, jaws_lenght_Y, jaws_height])
    box_to_remove = gate.geometry.volumes.BoxVolume(name="box_to_remove" + "_" + side)
    box_to_remove.size = np.array(
        [
            jaws_lenght_X + 1 * mm,
            jaws_lenght_Y - 17.83 * mm + 1 * mm,
            jaws_height - 21.64 * mm + 1 * mm,
        ]
    )
    bool_box_jaws = subtract_volumes(
        box_jaws,
        box_to_remove,
        [0, -(17.83) / 2 * mm - 1 / 2 * mm, (-21.64) / 2 * mm - 1 / 2 * mm],
    )

    # Jaws fine sub-structure : Box + Traps

    box_to_add = gate.geometry.volumes.BoxVolume(name="box_to_add" + "_" + side)
    box_to_add.size = np.array(
        [35.63 * mm, 104.61 * mm - 27.95 * mm, jaws_height - 21.64 * mm]
    )

    trap_jaws = gate.geometry.volumes.TrapVolume(name="trap_jaws" + "_" + side)
    trap_G4_param(
        trap_jaws,
        18.44 * mm / 2,
        18.44 * mm / 2,
        18.44 * mm / 2,
        18.44 * mm / 2,
        35.63 * mm / 2,
        jaws_lenght_tot_X / 2,
        (jaws_lenght_Y - 17.83 * mm - 104.61 * mm) / 2,
    )
    rot_trap_jaws = Rotation.from_euler("YZ", [90, 90], degrees=True).as_matrix()

    trap_jaws_2 = gate.geometry.volumes.TrapVolume(name="trap_jaws_" + "_" + side)
    trap_G4_param(
        trap_jaws_2,
        29.93 * mm / 2,
        29.93 * mm / 2,
        29.93 * mm / 2,
        29.93 * mm / 2,
        35.63 * mm / 2,
        (jaws_lenght_X + 4.91 * 2 * mm) / 2,
        (jaws_lenght_Y - 17.83 * mm - 104.61 * mm - 7.65 * mm) / 2,
    )
    box_trap_2 = gate.geometry.volumes.BoxVolume(name="box_trap_2" + "_" + side)
    box_trap_2.size = [jaws_lenght_X + 4.92 * mm * 2, 7.65 * mm, 29.93 * mm]
    trap_jaws_3 = gate.geometry.volumes.TrapVolume(name="trap_jaws_3" + "_" + side)
    trap_G4_param(
        trap_jaws_3,
        (jaws_height - 21.64 * mm - 18.44 * mm - 29.93 * mm) / 2,
        (jaws_height - 21.64 * mm - 18.44 * mm - 29.93 * mm) / 2,
        (jaws_height - 21.64 * mm - 18.44 * mm - 29.93 * mm) / 2,
        (jaws_height - 21.64 * mm - 18.44 * mm - 29.93 * mm) / 2,
        35.63 * mm / 2,
        jaws_lenght_X / 2,
        (jaws_lenght_Y - 17.83 * mm - 104.61 * mm - 11.84 * mm) / 2,
    )
    box_trap_3 = gate.geometry.volumes.BoxVolume(name="box_trap_3" + "_" + side)
    box_trap_3.size = [
        jaws_lenght_X,
        11.84 * mm,
        (jaws_height - 18.44 * mm - 29.93 * mm - 21.64 * mm),
    ]
    if not visu:
        bool_box_jaws = unite_volumes(
            bool_box_jaws,
            box_to_add,
            [
                0,
                -jaws_lenght_Y / 2 + 27.95 * mm + 0.5 * (104.61 * mm - 27.95 * mm),
                -21.64 / 2 * mm,
            ],
        )
        bool_box_jaws = unite_volumes(
            bool_box_jaws,
            trap_jaws,
            [
                0,
                -jaws_lenght_Y / 2
                + 104.61 * mm
                + (jaws_lenght_Y - 17.83 * mm - 104.61 * mm) / 2,
                -jaws_height / 2 + 18.44 * mm / 2,
            ],
            rot_trap_jaws,
        )
        bool_box_jaws = unite_volumes(
            bool_box_jaws,
            trap_jaws_2,
            [
                0,
                -jaws_lenght_Y / 2
                + 104.61 * mm
                + (jaws_lenght_Y - 17.83 * mm - 104.61 * mm - 7.65 * mm) / 2,
                -jaws_height / 2 + 18.44 * mm + 29.93 * mm / 2,
            ],
            rot_trap_jaws,
        )
        bool_box_jaws = unite_volumes(
            bool_box_jaws,
            box_trap_2,
            [
                0,
                -jaws_lenght_Y / 2
                + 104.61 * mm
                + (jaws_lenght_Y - 17.83 * mm - 104.61 * mm - 7.65 * mm)
                + 7.65 / 2 * mm,
                -jaws_height / 2 + 18.44 * mm + 29.93 * mm / 2,
            ],
        )
        bool_box_jaws = unite_volumes(
            bool_box_jaws,
            trap_jaws_3,
            [
                0,
                -jaws_lenght_Y / 2
                + 104.61 * mm
                + (jaws_lenght_Y - 17.83 * mm - 104.61 * mm - 11.84 * mm) / 2,
                -jaws_height / 2
                + 18.44 * mm
                + 29.93 * mm
                + 0.5 * (jaws_height - 18.44 * mm - 29.93 * mm - 21.64 * mm),
            ],
            rot_trap_jaws,
        )
        bool_box_jaws = unite_volumes(
            bool_box_jaws,
            box_trap_3,
            [
                0,
                -jaws_lenght_Y / 2
                + 104.61 * mm
                + (jaws_lenght_Y - 17.83 * mm - 104.61 * mm - 11.84 * mm)
                + 11.84 / 2 * mm,
                -jaws_height / 2
                + 18.44 * mm
                + 29.93 * mm
                + 0.5 * (jaws_height - 18.44 * mm - 29.93 * mm - 21.64 * mm),
            ],
        )

    # Correction of the front jaw shape

    minibox_to_add = gate.geometry.volumes.BoxVolume(name="minibox_to_add" + "_" + side)
    minibox_to_add.size = np.array(
        [0.5 * (jaws_lenght_tot_X - jaws_lenght_X), 17.83 * mm, 18.44 * mm]
    )
    minibox_to_add_2 = gate.geometry.volumes.BoxVolume(
        name="minibox_to_add_2" + "_" + side
    )
    minibox_to_add_2.size = np.array([4.91 * mm, 17.83 * mm, 29.93 * mm])

    rot_block_to_remove = gate.geometry.volumes.BoxVolume(
        name="rot_block_to_remove" + "_" + side
    )
    rot_block_to_remove.size = [
        14.55 * np.sqrt(2) * mm,
        14.55 * np.sqrt(2) * mm,
        21.64 * mm + 1 * mm,
    ]
    rot_block = Rotation.from_euler("Z", 45, degrees=True).as_matrix()
    if not visu:
        bool_box_jaws = unite_volumes(
            bool_box_jaws,
            minibox_to_add,
            [
                (-jaws_lenght_X - 0.5 * (jaws_lenght_tot_X - jaws_lenght_X)) / 2,
                (jaws_lenght_Y - 17.83 * mm) / 2,
                -jaws_height / 2 + 18.44 / 2 * mm,
            ],
        )
        bool_box_jaws = unite_volumes(
            bool_box_jaws,
            minibox_to_add,
            [
                (jaws_lenght_X + 0.5 * (jaws_lenght_tot_X - jaws_lenght_X)) / 2,
                (jaws_lenght_Y - 17.83 * mm) / 2,
                -jaws_height / 2 + 18.44 / 2 * mm,
            ],
        )
        bool_box_jaws = unite_volumes(
            bool_box_jaws,
            minibox_to_add_2,
            [
                (-jaws_lenght_X - 4.91 * mm) / 2,
                (jaws_lenght_Y - 17.83 * mm) / 2,
                -jaws_height / 2 + 18.44 * mm + 29.93 / 2 * mm,
            ],
        )
        bool_box_jaws = unite_volumes(
            bool_box_jaws,
            minibox_to_add_2,
            [
                (jaws_lenght_X + 4.91 * mm) / 2,
                (jaws_lenght_Y - 17.83 * mm) / 2,
                -jaws_height / 2 + 18.44 * mm + 29.93 / 2 * mm,
            ],
        )
        bool_box_jaws = subtract_volumes(
            bool_box_jaws,
            rot_block_to_remove,
            [-jaws_lenght_X / 2, -jaws_lenght_Y / 2, jaws_height / 2 - 21.74 / 2 * mm],
            rot_block,
        )
        bool_box_jaws = subtract_volumes(
            bool_box_jaws,
            rot_block_to_remove,
            [jaws_lenght_X / 2, -jaws_lenght_Y / 2, jaws_height / 2 - 21.74 / 2 * mm],
            rot_block,
        )

    # Jaws curve tips
    cylindre = gate.geometry.volumes.TubsVolume(name="cyl_leaf" + "_" + side)
    cylindre.rmin = 0
    cylindre.rmax = 135 * mm
    cylindre.dz = jaws_lenght_tot_X
    rot_cyl = Rotation.from_euler("Y", 90, degrees=True).as_matrix()
    jaw = intersect_volumes(
        bool_box_jaws,
        cylindre,
        [0, -(135 * mm - jaws_lenght_Y / 2), -3.5 * mm],
        rot_cyl,
    )

    # Add final jaw volume
    sim.volume_manager.add_volume(jaw, "jaws" + "_" + side)
    jaw.mother = name
    jaw.material = "mat_leaf"
    # if side == 'left' :
    #     jaw.translation = np.array([0, -jaws_lenght_Y/2, z_linac / 2 - center_jaws])
    if side == "right":
        rot_jaw = Rotation.from_euler("Z", 180, degrees=True).as_matrix()
        #     jaw.translation = np.array([0, jaws_lenght_Y/2, z_linac / 2 - center_jaws])
        jaw.rotation = rot_jaw
    # jaw.translation += np.array([0, position_jaw, 0])
    return jaw


def move_jaws_RT_plan(sim, jaws, y_jaws, liste_cp, z_linac, side, SAD=1000):
    mm = gate.g4_units.mm
    motion_jaws = sim.add_actor("MotionVolumeActor", "Move_" + side + "_jaws")
    motion_jaws.translations = []
    motion_jaws.rotations = []
    motion_jaws.mother = jaws.name
    jaws_lenght_Y = 205.2 * mm
    jaws_height = 77 * mm
    center_jaws = 470.5 * mm
    center_curve_jaws = center_jaws - (jaws_height / 2 - 35 * mm)
    fact_iso = center_curve_jaws / SAD
    rot_jaw = Rotation.from_euler("Z", 180, degrees=True).as_matrix()
    for n in range(liste_cp):
        if side == "left":
            jaws_translation = np.array(
                [
                    0,
                    -jaws_lenght_Y / 2 + y_jaws[n] * fact_iso,
                    0.5 * z_linac - center_jaws,
                ]
            )
            motion_jaws.rotations.append(np.identity(3))
        if side == "right":
            jaws_translation = np.array(
                [
                    0,
                    jaws_lenght_Y / 2 + y_jaws[n] * fact_iso,
                    0.5 * z_linac - center_jaws,
                ]
            )
            motion_jaws.rotations.append(rot_jaw)
        motion_jaws.translations.append(jaws_translation)
    # print(motion_jaws.translations)


def add_jaws(sim, name, z_linac, position_jaws):
    # Jaws description
    mm = gate.g4_units.mm
    center_jaws = 470.5 * mm
    jaws_height = 77 * mm
    jaws_lenght_X = 180 * mm
    jaws_lenght_Y = 220 * mm

    cylindre = gate.geometry.volumes.TubsVolume(name="cyl_leaf")
    cylindre.rmin = 0
    cylindre.rmax = 135 * mm
    cylindre.dz = jaws_lenght_X

    box_jaws = gate.geometry.volumes.BoxVolume(name="box_jaws_left")
    box_jaws.size = np.array([jaws_height, jaws_lenght_Y, jaws_lenght_X])

    bool_jaws = intersect_volumes(box_jaws, cylindre, [-3.5 * mm, -25 * mm, 0])

    left_jaws = sim.volume_manager.add_volume(bool_jaws, "left_jaws")
    left_jaws.mother = name
    left_jaws.material = "mat_leaf"
    rot = Rotation.from_euler("Y", 90, degrees=True).as_matrix()
    left_jaws.rotation = rot
    left_jaws.translation = np.array([0, -jaws_lenght_Y / 2, z_linac / 2 - center_jaws])

    right_jaws = sim.volume_manager.add_volume(bool_jaws, "right_jaws")
    right_jaws.mother = name
    right_jaws.material = "mat_leaf"
    rot = Rotation.from_euler("YZ", [90, 180], degrees=True).as_matrix()
    right_jaws.rotation = rot
    right_jaws.translation = np.array(
        [0, +jaws_lenght_Y / 2, z_linac / 2 - center_jaws]
    )

    left_jaws.color = [0, 1, 0, 1]
    right_jaws.color = [0, 1, 0, 1]

    left_jaws.translation += np.array([0, position_jaws[0], 0])
    right_jaws.translation += np.array([0, position_jaws[1], 0])


def add_primary_collimator(sim, name, z_linac):
    mm = gate.g4_units.mm
    deg = gate.g4_units.deg
    primary_collimator = sim.add_volume("Cons", "primary_collimator")
    primary_collimator.mother = name
    primary_collimator.material = "mat_leaf"
    primary_collimator.rmin1 = 31.45 * mm
    primary_collimator.rmax1 = 82 * mm
    primary_collimator.rmin2 = 6.45 * mm
    primary_collimator.rmax2 = 82 * mm
    primary_collimator.dz = 101 * mm / 2.0
    primary_collimator.sphi = 0
    primary_collimator.dphi = 360 * deg
    primary_collimator.translation = [0, 0, z_linac / 2 - 65.5 * mm]
    primary_collimator.color = [0.5, 0.5, 1, 0.8]


def add_back_scatter_plate(sim, name, z_linac):
    # back_scatter_plate
    mm = gate.g4_units.mm
    bsp = sim.add_volume("Box", "_back_scatter_plate")
    bsp.mother = name
    bsp.material = "linac_aluminium"
    bsp.size = [116 * mm, 84 * mm, 3 * mm]
    bsp.translation = [0, 0, z_linac / 2 - 183 * mm]
    bsp.color = [1, 0.7, 0.7, 0.8]


def define_apertures(field_X, field_Y, SAD=1000):
    mm = gate.g4_units.mm
    center_MLC = 349.3 * mm
    center_jaws = 470.5 * mm
    jaws_height = 77 * mm
    center_curve_MLC = center_MLC - 7.5 * mm
    leaf_width = 1.76 * mm + 0.09 * mm
    center_curve_jaws = center_jaws - (jaws_height / 2 - 35 * mm)

    jaws_Y_aperture = field_Y / 2 * center_curve_jaws / SAD
    MLC_X_aperture = field_X / 2 * center_curve_MLC / SAD

    MLC_Y_aperture = field_Y * center_MLC / SAD
    nb_of_leaf_open = int(MLC_Y_aperture / leaf_width) + 1

    if nb_of_leaf_open % 2 == 1:
        nb_of_leaf_open += 1

    pos_X_leaf = np.zeros(160)
    pos_X_leaf[0:80] -= 0.5 * mm
    pos_X_leaf[80:160] += 0.5 * mm
    pos_X_leaf[
        39 - int(nb_of_leaf_open / 2) : 39 + int(nb_of_leaf_open / 2) + 1
    ] = -MLC_X_aperture
    pos_X_leaf[
        119 - int(nb_of_leaf_open / 2) : 119 + int(nb_of_leaf_open / 2) + 1
    ] = MLC_X_aperture

    pos_X_leaf = np.array(10 * pos_X_leaf, dtype=int) / 10

    pos_Y_jaws = np.array(
        [-int(10 * jaws_Y_aperture) / 10, int(10 * jaws_Y_aperture) / 10]
    )

    return (pos_X_leaf, pos_Y_jaws)


def add_linac(sim, name, cp_param, visu=False, source_flag="phsp", seg_cp=2):
    cp_param = interpolation_CP(cp_param, seg_cp)
    y_jaws_1 = cp_param["Y_jaws_1"]

    y_jaws_2 = cp_param["Y_jaws_2"]
    x_leaf = cp_param["Leaves"]
    angle = cp_param["Gantry angle"]
    len_cp_param = len(y_jaws_1)

    ui = sim.user_info
    # LINAC box mother volume
    mm = gate.g4_units.mm
    m = gate.g4_units.m
    cm = gate.g4_units.cm
    nm = gate.g4_units.nm
    Bq = gate.g4_units.Bq
    deg = gate.g4_units.deg
    linac_box = sim.add_volume("Box", "Linac_box")
    linac_box.mother = name
    linac_box.material = "G4_AIR"

    white = [1, 1, 1, 0.8]

    size_linac = [1 * m, 1 * m, 0.52 * m]
    linac_box.size = size_linac
    translation_linac_box = np.array([0 * mm, 0, +0.74 * m])
    linac_box.translation = translation_linac_box

    linac_box.color = [1, 1, 0, 1]  # red
    if source_flag == "elec":
        add_target(sim, linac_box.name, size_linac[2])
        add_primary_collimator(sim, linac_box.name, size_linac[2])
        add_flattening_filter(sim, linac_box.name, size_linac[2])
        add_ionizing_chamber(sim, linac_box.name, size_linac[2])
        add_back_scatter_plate(sim, linac_box.name, size_linac[2])
        add_mirror(sim, linac_box.name, size_linac[2])

    # x_leaf_position,position_jaws = define_apertures(field_X,field_Y)
    MLC = add_MLC(sim, linac_box.name)
    left_jaws = add_realistic_jaws(sim, linac_box.name, "left", visu)
    right_jaws = add_realistic_jaws(sim, linac_box.name, "right", visu)

    move_MLC_RT_plan(sim, MLC, x_leaf, len_cp_param, size_linac[2])
    move_jaws_RT_plan(sim, left_jaws, y_jaws_1, len_cp_param, size_linac[2], "left")
    move_jaws_RT_plan(sim, right_jaws, y_jaws_2, len_cp_param, size_linac[2], "right")

    motion_LINAC = sim.add_actor("MotionVolumeActor", "Move_LINAC")
    motion_LINAC.rotations = []
    motion_LINAC.translations = []
    motion_LINAC.mother = linac_box.name
    # print(angle)
    for n in range(len_cp_param):
        # print(angle[n])
        rot = Rotation.from_euler("y", angle[n], degrees=True)
        t = gate.geometry.utility.get_translation_from_rotation_with_center(
            rot, [0, 0, -translation_linac_box[2]]
        )
        rot = rot.as_matrix()
        motion_LINAC.rotations.append(rot)
        motion_LINAC.translations.append(np.array(t) + translation_linac_box)
    return linac_box


def add_source_elec(sim):
    ui = sim.user_info
    mm = gate.g4_units.mm
    source = sim.add_source("GenericSource", "e-_source")
    target = sim.volume_manager.volumes["target"]
    Bq = gate.g4_units.Bq
    MeV = gate.g4_units.MeV
    source.particle = "e-"
    source.mother = target.name
    source.energy.type = "gauss"
    source.energy.mono = 6.4 * MeV
    source.energy.sigma_gauss = source.energy.mono * 0.03 / 2.35
    source.position.type = "disc"
    source.position.sigma_x = 0.468 * mm
    source.position.sigma_y = 0.468 * mm
    source.position.translation = [0, 0, 0.6 * mm]
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, -1]


def add_source(sim, name, z_linac, ov=False):
    ui = sim.user_info
    mm = gate.g4_units.mm
    m = gate.g4_units.m
    nm = gate.g4_units.nm
    fake_plane = sim.add_volume("Box", "fake_phase_space_plane")
    fake_plane.material = "G4_AIR"
    fake_plane.mother = name
    fake_plane.size = [1 * m, 1 * m, 1 * nm]
    fake_plane.translation = [0 * mm, 0 * mm, +z_linac / 2]

    source = sim.add_source("PhaseSpaceSource", "phsp_source_global")
    source.mother = fake_plane.name
    source.phsp_file = "./output/data_ref.root"
    source.position_key = "PrePosition"
    source.direction_key = "PreDirection"
    source.weight_key = "Weight"
    source.global_flag = False
    source.particle = ""
    # source.PDGCode_key = "PDGcode"
    source.batch_size = 100
    source.override_position = ov
    source.position.translation = [0 * m, 0 * m, -1000 * mm]


def add_water_tank(sim, name, SSD):
    mm = gate.g4_units.mm
    cm = gate.g4_units.cm
    depth_water = 40 * cm
    SSD = SSD * mm / cm * cm

    water = sim.add_volume("Box", "water_box")
    water.material = "G4_WATER"
    water.mother = name
    water.size = [40 * cm, 40 * cm, depth_water]
    water.translation = [0 * mm, 0 * mm, (100 * cm - SSD) - depth_water / 2]
    water.color = [0, 0, 1, 1]

    voxel_size_x = 2 * mm
    voxel_size_y = 2 * mm
    voxel_size_z = 2 * mm
    dose = sim.add_actor("DoseActor", "dose")
    dose.output = "output/testilol.mhd"
    dose.mother = water.name
    dose.size = [
        int(water.size[0] / voxel_size_x),
        int(water.size[1] / voxel_size_y),
        int(water.size[2] / voxel_size_z),
    ]
    dose.spacing = [voxel_size_x, voxel_size_y, voxel_size_z]
    # dose.img_coord_system = True
    dose.uncertainty = False
    dose.square = False
    # dose.translation = [ - voxel_size_x/2, - voxel_size_y/2, - voxel_size_z/2]
    dose.hit_type = "random"


def add_phase_space(sim, name, pos, idx_phsp=None):
    nm = gate.g4_units.nm
    if idx_phsp == None:
        phsp_plan = sim.add_volume("Box", "Box")
    else:
        phsp_plan = sim.add_volume("Box", "Box_" + idx_phsp)
    phsp_plan.mother = name
    linac = sim.get_volume_user_info("Linac_box")
    phsp_plan.size = [linac.size[0], linac.size[1], 1 * nm]
    # phsp_plan.translation = [0,0,- linac.size[2]/2 + 1*nm]
    # phsp_plan.translation = [0,0, linac.size[2]/2 - 300*mm]
    phsp_plan.translation = pos
    phsp_plan.color = [0, 1, 0.5, 1]
    # PhaseSpace Actor
    if idx_phsp == None:
        phsp_actor = sim.add_actor("PhaseSpaceActor", "PhaseSpace")
    else:
        phsp_actor = sim.add_actor("PhaseSpaceActor", "PhaseSpace_" + idx_phsp)
    phsp_actor.mother = phsp_plan.name
    phsp_actor.attributes = [
        "KineticEnergy",
        "Weight",
        "PrePosition",
        "PreDirection",
        "EventPosition",
        "PDGCode",
    ]
    phsp_actor.output = ".output/data.root"
    phsp_actor.debug = False
    # phsp_actor = sim.add_filter("ParticleFilter", "f")
    # phsp_actor.particle = "gamma"
    # phsp_actor.filters.append(f)


def init_simulation(
    nt,
    cp_param,
    path_image,
    img,
    visu,
    source_flag,
    bool_phsp=False,
    seg_cp=2,
    patient=True,
):
    sim = gate.Simulation()
    mat_database_path = "../../contrib/linacs/"
    path_phsp = "/home/mjacquet/Documents"
    path_data = "./"
    paths = utility.get_default_test_paths(__file__)
    file = str(paths.data / "modified_elekta_synergy_materials.db")
    sim.volume_manager.add_material_database(str(file))
    ui = sim.user_info
    ui.g4_verbose = False
    ui.check_volumes_overlap = False
    ui.random_seed = "auto"
    ui.number_of_threads = nt

    # units
    m = gate.g4_units.m
    mm = gate.g4_units.mm
    nm = gate.g4_units.nm
    Bq = gate.g4_units.Bq
    MeV = gate.g4_units.MeV

    #  adapt world size
    world = sim.world
    world.size = [5 * m, 5 * m, 5 * m]
    linac = add_linac(sim, world.name, cp_param, visu, source_flag, seg_cp)
    if source_flag == "phsp":
        add_source(sim, linac.name, linac.size[2], ov=True)
    if source_flag == "elec":
        add_source_elec(sim)
    if bool_phsp:
        add_phase_space(sim, linac.name, [0, 0, linac.size[2] / 2 - 300 * mm], "1")
        add_phase_space(sim, linac.name, [0, 0, -linac.size[2] / 2 + 1 * mm], "2")

    if patient:
        add_patient_image(sim, world.name, path_image, img, cp_param)

    # add stat actor
    s = sim.add_actor("SimulationStatisticsActor", "Stats")
    s.track_types_flag = True
    # phys
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option3"
    sim.physics_manager.enable_decay = False

    sim.physics_manager.global_production_cuts.gamma = 1 * mm
    sim.physics_manager.global_production_cuts.electron = 1 * mm
    sim.physics_manager.global_production_cuts.positron = 1 * mm

    return sim


def run_simu(sim, source_flag, cp_param, seg_cp=2):
    old_int_MU = cp_param["weight"]
    cp_param = interpolation_CP(cp_param, seg_cp)
    MU = cp_param["weight"]
    # MU = np.zeros(len(MU)) + 1
    # print(MU)
    if source_flag == "elec":
        target = sim.volume_manager.volumes["target"]
        region_linac_target = sim.create_region(name=f"{target.name}")
        region_linac_target.associate_volume(target)
        s = f"/process/em/setSecBiasing eBrem {target.name} 100 100 MeV"
        sim.apply_g4_command(s)
    sec = gate.g4_units.s
    sim.run_timing_intervals = []
    for i in range(len(MU)):
        if i == 0:
            sim.run_timing_intervals.append([0, MU[0] * sec])
        else:
            sim.run_timing_intervals.append(
                [np.sum(MU[:i]) * sec, np.sum(MU[: i + 1]) * sec]
            )
    sim.run()
    stats = sim.output.get_actor("Stats")
    print(stats)
