#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import sys
import numpy as np
import itk
from box import Box
from opengate.contrib.dose.doserate import create_simulation
from opengate.tests import utility


def write_water_phantom(folder, size=50, spacing=4.0, source_size=5):
    """CT of a water cube (0 HU) and a small cubic source at its centre (same grid)."""
    folder.mkdir(parents=True, exist_ok=True)
    ct = np.zeros((size, size, size), dtype=np.int16)
    activity = np.zeros((size, size, size), dtype=np.float32)
    c, h = size // 2, source_size // 2
    activity[c - h : c + h + 1, c - h : c + h + 1, c - h : c + h + 1] = 1
    names = []
    for name, arr in (("ct.mhd", ct), ("activity.mhd", activity)):
        img = itk.GetImageFromArray(arr)
        img.SetSpacing([spacing] * 3)
        itk.imwrite(img, str(folder / name))
        names.append(str(folder / name))
    return names


def run_simulation(bremsstrahlung, activity=2e5, threads=None):
    """Electron run (e- mode) of Y90, a pure beta emitter: all photons are bremsstrahlung."""
    if threads is None:
        threads = 1 if sys.platform.startswith("win") else 4
    folder_name = "test035d_brems_" + ("on" if bremsstrahlung else "off")
    paths = utility.get_default_test_paths(__file__, "", output_folder=folder_name)
    dr_data = paths.data / "dose_rate_data"
    ct_image, activity_image = write_water_phantom(paths.output / "phantom")

    param = Box()
    param.ct_image = ct_image
    # table_mat and table_density: default, the Schneider 2000 tables of opengate
    param.activity_image = activity_image
    param.radionuclide = "Y90"
    param.activity_bq = activity
    param.number_of_threads = threads
    param.visu = False
    param.verbose = True
    param.density_tolerance_gcm3 = 0.05
    param.output_folder = str(paths.output)
    param.mode = "e-"
    param.bremsstrahlung = bremsstrahlung

    sim = create_simulation(param)
    sim.run(start_new_process=True)

    with open(paths.output / "stats.txt") as f:
        stats = json.load(f)
    dose = itk.GetArrayFromImage(itk.imread(str(paths.output / "output_dose.mhd")))
    activity_img = itk.GetArrayFromImage(itk.imread(param.activity_image))
    return stats, dose, activity_img > 0


if __name__ == "__main__":
    is_ok = True

    stats_off, dose_off, source = run_simulation(bremsstrahlung=False)
    stats_on, dose_on, _ = run_simulation(bremsstrahlung=True)

    # 1. Bremsstrahlung photons are created only with the option
    gammas_off = stats_off["track_types"]["value"].get("gamma", 0)
    gammas_on = stats_on["track_types"]["value"].get("gamma", 0)
    electrons = stats_on["track_types"]["value"]["e-"]
    print(
        f"Photon tracks: off = {gammas_off}, on = {gammas_on} ({electrons} electrons)"
    )
    b = gammas_on > 0.02 * electrons and gammas_off < 0.01 * electrons
    utility.print_test(b, "Bremsstrahlung photons created only with the option")
    is_ok = is_ok and b

    # 2. The total energy is about the same (the bremsstrahlung energy is deposited
    # further away, part of it escapes), the dose in the source is almost unchanged
    src_off = dose_off[source].mean()
    src_on = dose_on[source].mean()
    print(f"Mean dose in the source: off = {src_off:.4e}, on = {src_on:.4e} Gy")
    b = abs(src_on / src_off - 1) < 0.02
    utility.print_test(
        b, f"Dose in the source: on / off = {src_on / src_off:.4f} (within 2 %)"
    )
    is_ok = is_ok and b

    # 3. In water, beyond the maximum Y90 electron range (11 mm), the dose comes from
    # the bremsstrahlung only: much higher with the option
    spacing_mm = 4.0
    near = source.copy()
    for _ in range(int(np.ceil(20 / spacing_mm))):  # dilate the source by 20 mm
        grown = near.copy()
        for axis in range(3):
            grown |= np.roll(near, 1, axis) | np.roll(near, -1, axis)
        near = grown
    far = ~near
    far_off = dose_off[far].sum()
    far_on = dose_on[far].sum()
    print(f"Dose beyond 20 mm of the source: off = {far_off:.4e}, on = {far_on:.4e} Gy")
    b = far_on > 5 * far_off
    utility.print_test(
        b,
        f"Dose beyond the electron range: on / off = {far_on / max(far_off, 1e-30):.1f} (> 5)",
    )
    is_ok = is_ok and b

    utility.test_ok(is_ok)
