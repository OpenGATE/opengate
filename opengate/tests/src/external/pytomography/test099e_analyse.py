#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from opengate.tests import utility
from opengate.contrib.spect.pytomography_helpers import *
import opengate.contrib.phantoms.nemaiec as nemaiec


def go():
    paths = utility.get_default_test_paths(__file__, output_folder="test099_pytomo")
    data_path = paths.data / "test099_pytomo" / "data"
    recon_img_path = paths.output / "reconstructed_i4s6.mha"
    recon_img_rm_path = paths.output / "reconstructed_i4s6_rm.mha"
    recon_img_rm_ac_path = paths.output / "reconstructed_i4s6_rm_ac.mha"
    recon_img_rm_ac_sc_path = paths.output / "reconstructed_i4s6_rm_ac_sc.mha"
    recon_img_paths = [
        recon_img_path,
        recon_img_rm_path,
        recon_img_rm_ac_path,
        recon_img_rm_ac_sc_path,
    ]
    ref_mask_img = data_path / "iec_activity_1mm.mhd"
    ref_activity = data_path / "iec_activity_1mm.mhd"
    is_ok = True

    # test
    mask_obj = sitk.ReadImage(ref_mask_img)
    labeled_mask = nemaiec.individualize_spheres(mask_obj)

    # We place a 25mm sphere exactly in the physical center of the IEC phantom
    # to measure Background Variability (Noise) uniformly without hitting the 6 hot spheres.
    img_size = mask_obj.GetSize()
    img_spacing = mask_obj.GetSpacing()
    img_origin = mask_obj.GetOrigin()
    center_pos = [
        img_origin[i] + (img_size[i] * img_spacing[i]) / 2.0 for i in range(3)
    ]
    print(f"\nCreating Background ROI at Physical Center: {center_pos}")
    bg_mask_obj = nemaiec.create_sphere(mask_obj, center_pos, radius=25, intensity=1)

    metrics = []
    for recon_img_path in recon_img_paths:
        recon_img = sitk.ReadImage(recon_img_path)
        m = nemaiec.check_centroid_alignment(labeled_mask, recon_img, dilate_mm=0)
        b = m < 0.4
        utility.print_test(b, f"Compare centroid distance is {m}")
        if not b:
            nemaiec.plot_sphere_panels(labeled_mask, recon_img, recon_img, margin_mm=20)
        is_ok = b and is_ok

        m = nemaiec.compute_iec_nema_metrics(
            ref_activity, labeled_mask, bg_mask_obj, recon_img
        )
        metrics.append(m)

    fn = paths.output / f"rc.pdf"
    nemaiec.plot_iec_rc_curves(
        labeled_mask, metrics["spheres"], None, label1="noRM", label2="RM", fig_path=fn
    )
    print(f"\nSaved NEMA RC curves to {fn}")

    # end
    utility.test_ok(is_ok)


if __name__ == "__main__":
    go()
