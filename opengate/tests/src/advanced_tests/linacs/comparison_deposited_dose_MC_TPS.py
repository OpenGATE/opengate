import numpy as np
import os, glob
from scipy import ndimage
from pathlib import Path
import pydicom
from opengate.contrib.linacs import dicomrtplan as rtplan
from opengate.tests import utility
import itk
from box import Box
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import json
import pymedphys
import click


class voxelised_dose:

    def __init__(self, img, **kwargs):
        x, y, z, arrayD, voxel_size, nb_voxel, offset_voxel = self.open_itk_dose_image(
            img
        )
        img_dose = itk.imread(img)
        self.x = x
        self.y = y
        self.z = z
        self.dose = arrayD
        self.information = Box(
            {
                "spacing": voxel_size,
                "number_of_voxels": nb_voxel,
                "offset": offset_voxel,
                "errors": False,
                "img": img_dose,
            }
        )
        self.information["label"] = img.split("./")[-1]
        for key in kwargs.keys():
            if key == "label":
                self.information["label"] = kwargs[key]
            if key == "field":
                self.information["field"] = kwargs[key]

        l_err_img = [img[:-4] + "-uncertainty.mhd", img[:-4] + "_uncertainty.mhd"]
        for err_img in l_err_img:
            if os.path.exists(err_img):
                x, y, z, err_arrayD, voxel_size, nb_voxel, offset_voxel = (
                    self.open_itk_dose_image(err_img)
                )
                self.err_dose_on_dose = err_arrayD
                self.err_dose = err_arrayD * self.dose
                self.information["errors"] = True
                break

    def __str__(self):
        return self.information.label

    def open_itk_dose_image(self, img):
        img_dose = itk.imread(img)
        voxel_size = np.array(img_dose.GetSpacing())
        nb_voxel = np.array(img_dose.GetLargestPossibleRegion().GetSize())
        offset_voxel = np.array(img_dose.GetOrigin())

        arrayD = itk.GetArrayFromImage(img_dose)
        numpy_column_order = [2, 1, 0]
        arrayD = np.transpose(arrayD, numpy_column_order)
        arrayD = arrayD[:, :, ::-1]

        x = np.arange(0, nb_voxel[0] * voxel_size[0], voxel_size[0])
        x = x + offset_voxel[0]

        y = np.arange(0, nb_voxel[1] * voxel_size[1], voxel_size[1])
        y = y + offset_voxel[1]

        z = np.arange(0, nb_voxel[2] * voxel_size[2], voxel_size[2])
        z = z + offset_voxel[2]

        return (x, y, z, arrayD, voxel_size, nb_voxel, offset_voxel)


def vec_equal(a, b, tol=0.01) -> bool:
    return all(abs(x - y) <= tol for x, y in zip(a, b))


def get_single_isocenter(rtplan_path: Path, tol: float = 0.01) -> np.ndarray:
    ds = pydicom.dcmread(str(rtplan_path), force=True)

    if not hasattr(ds, "BeamSequence"):
        raise ValueError("RT Plan sans BeamSequence — impossible de lire l'isocentre.")

    iso_ref = None
    for i, beam in enumerate(ds.BeamSequence):
        if not hasattr(beam, "ControlPointSequence"):
            raise ValueError(f"Le faisceau #{i+1} n'a pas de ControlPointSequence.")

        iso = None
        # lecture du CP0 en priorité
        cp0 = beam.ControlPointSequence[0]
        if hasattr(cp0, "IsocenterPosition"):
            iso = np.array(cp0.IsocenterPosition, dtype=float)
        else:
            for cp in beam.ControlPointSequence:
                if hasattr(cp, "IsocenterPosition"):
                    iso = np.array(cp.IsocenterPosition, dtype=float)
                    break

        if iso is None:
            raise ValueError(f"Aucun IsocenterPosition trouvé pour le faisceau #{i+1}.")

        if iso_ref is None:
            iso_ref = iso
        elif not vec_equal(iso_ref, iso, tol):
            raise ValueError(
                f"Plus d'un isocentre détecté (écart > {tol} mm).\n"
                f"Référence: {iso_ref} vs Faisceau #{i+1}: {iso}"
            )

    if iso_ref is None:
        raise ValueError("Aucun isocentre trouvé dans le RT Plan.")

    return iso_ref  # numpy.ndarray [x, y, z] en mm


def estimate_nb_of_event(dicom_file, median_nb_part):
    rt_plan_parameters = rtplan.read(dicom_file, "all_cp")
    cp_weight = rt_plan_parameters["weight"]
    cp_weight = cp_weight / np.median(cp_weight)
    total_nb_event = np.sum(cp_weight) * median_nb_part
    return total_nb_event


CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option(
    "--path", default="./data_advanced_test_linac/", help="path to the patient folder"
)
@click.option("--path_output", default="./output/", help="path to the patient folder")
def gamma_index_comparison(path, path_output):
    # ############# path and file name to modify ##############
    tle = True
    CT_name = "CT.mhd"
    TPS_name = "TPS.mhd"
    RTplan_name = "rt_plan.dcm"
    CT_mask_name = "mask.mhd"

    if tle:
        MC_dose_name = "MC-tle-norm-dose.mhd"
    else:
        MC_dose_name = "MC-norm-dose.mhd"
    isocenter = get_single_isocenter(f"{path}/{RTplan_name}", 0.01)
    CT_mask_path = f"{path}/{CT_mask_name}"
    CT_mask = voxelised_dose(CT_mask_path)
    structuring_element = np.ones((3, 3, 3))

    CT_mask.dose = ndimage.binary_erosion(CT_mask.dose, structure=structuring_element)

    CT_path = f"{path}/{CT_name}"
    CT = voxelised_dose(CT_path)
    CT.dose = CT.dose * CT_mask.dose
    CT.dose[CT.dose == 0] -= 1024

    TPS_path = f"{path}/{TPS_name}"
    TPS = voxelised_dose(TPS_path)
    TPS.dose = TPS.dose * CT_mask.dose
    spacing = TPS.information.spacing

    MC_dose_path = f"{path_output}/{MC_dose_name}"
    MC_dose = voxelised_dose(MC_dose_path)
    MC_dose.dose = MC_dose.dose * CT_mask.dose

    MC_dose.z = MC_dose.z[::-1]
    x = MC_dose.x - isocenter[0]
    z = -(MC_dose.z - isocenter[2])
    idx = 40

    axes_reference = (MC_dose.x, MC_dose.y, MC_dose.z)
    axes_evaluation = (MC_dose.x, MC_dose.y, MC_dose.z)

    dose_reference = TPS.dose
    dose_evaluation = MC_dose.dose

    gamma_options = {
        "dose_percent_threshold": 2,
        "distance_mm_threshold": 2,
        "lower_percent_dose_cutoff": 50,
        "interp_fraction": 10,  # Should be 10 or more for more accurate results
        "max_gamma": 1.5,
        "random_subset": None,
        "local_gamma": True,
        "ram_available": 40 * 2**29,  # 40 * 1/2 GB
    }

    gamma = pymedphys.gamma(
        axes_reference,
        dose_reference,
        axes_evaluation,
        dose_evaluation,
        **gamma_options,
    )
    valid_gamma = gamma[~np.isnan(gamma)]
    pass_ratio = np.sum(valid_gamma <= 1) / len(valid_gamma)

    height = 20
    width = height / 2
    fig1, ax1 = plt.subplots(2, 1)
    fig1.set_size_inches(width, height)
    fig1.subplots_adjust(
        left=0.15, bottom=0.086, right=0.99, top=0.986, wspace=0.2, hspace=0.193
    )
    norm = mcolors.LogNorm(vmin=0.03, vmax=70)

    cax = ax1[0].imshow(
        np.rot90(CT.dose[:, idx, :]),
        extent=[x.min(), x.max(), z.max(), z.min()],
        origin="lower",
        cmap="gist_gray",
        aspect="equal",
    )
    cax2 = ax1[0].imshow(
        np.rot90(MC_dose.dose[:, idx, :]),
        extent=[x.min(), x.max(), z.max(), z.min()],
        origin="lower",
        cmap="jet",
        norm=norm,
        aspect="equal",
        alpha=0.6,
    )
    cbar = fig1.colorbar(cax2, ax=ax1[0])
    cbar.set_label(label="Dose[%]", fontsize=16)

    #
    cax = ax1[1].imshow(
        np.rot90(CT.dose[:, idx, :]),
        extent=[x.min(), x.max(), z.max(), z.min()],
        origin="lower",
        cmap="gist_gray",
        aspect="equal",
    )
    cax2 = ax1[1].imshow(
        np.rot90(TPS.dose[:, idx, :]),
        extent=[x.min(), x.max(), z.max(), z.min()],
        origin="lower",
        cmap="jet",
        norm=norm,
        aspect="equal",
        alpha=0.6,
    )
    cbar = fig1.colorbar(cax2, ax=ax1[1], pad=0.04)
    cbar.set_label(label="Dose[%]", fontsize=16)

    ax1[0].set(ylabel="Y position [mm]")
    ax1[1].set(ylabel="Y position [mm]", xlabel="X position [mm]")
    ax1[0].axes.get_xaxis().set_visible(False)
    fig1.savefig(f"{path_output}/MC_vs_TPS_dose.pdf")
    is_ok = pass_ratio > 0.6
    utility.test_ok(is_ok)


if __name__ == "__main__":
    gamma_index_comparison()
