#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
from opengate.contrib.compton_camera.macaco import *


def main():
    # get tests paths
    paths = utility.get_default_test_paths(
        __file__, gate_folder="", output_folder="test099_macaco1"
    )
    output_folder = paths.output
    output_ref = paths.output_ref

    exp_singles_file = output_ref / "singles_experimental.root"
    print(exp_singles_file)

    # ======================================================
    # 1) Create simulation
    # ======================================================
    sim = gate.Simulation()
    sim.visu = False
    sim.number_of_threads = 2
    sim.check_volumes_overlap = False
    sim.progress_bar = True
    sim.output_dir = output_folder
    sim.random_seed = 123456789

    m = g4_units.m
    mm = g4_units.mm
    keV = g4_units.keV
    Bq = g4_units.Bq
    sec = g4_units.s
    ns = g4_units.ns

    # ======================================================
    # 2) Geometry
    # ======================================================
    sim.world.size = [1 * m, 1 * m, 1 * m]
    cam = add_macaco1_camera(sim)
    scatterer = cam["scatterer"]
    absorber = cam["absorber"]
    camera = cam["camera"]
    # 53 mm from the first plane
    camera.translation = [0, 0, 83 * mm]

    # ======================================================
    # 3) Source
    # ======================================================
    src_holder = sim.add_volume("Sphere", "test_source_holder")
    src_holder.mother = sim.world
    src_holder.material = "Plastic"
    src_holder.rmax = 0.25 * mm

    src = sim.add_source("GenericSource", "test_gammas")
    src.particle = "gamma"
    src.attached_to = src_holder
    src.activity = 847e3 * Bq
    src.position.type = "sphere"
    src.position.radius = 0.25 * mm
    src.direction.type = "iso"

    # Na-22-like spectrum
    src.energy.type = "spectrum_discrete"
    src.energy.spectrum_energies = [1274.5 * keV, 511 * keV]
    src.energy.spectrum_weights = [0.9994, 1.807]

    # ======================================================
    # 4) Timing
    # ======================================================
    if sim.visu:
        sim.run_timing_intervals = [[0, 0.000003 * sec]]
    else:
        sim.run_timing_intervals = [[0, 1 * sec]]

    # ======================================================
    # 5) Digitizer
    # ======================================================
    scatt_file, abs_file = add_macaco1_camera_digitizer(sim, scatterer, absorber)
    print(f"Scatt file: {scatt_file}")
    print(f"Abs file: {abs_file}")

    # ======================================================
    # 6) Run simulation
    # ======================================================
    sim.run()

    # ======================================================
    # 7) VALIDATION : SINGLES
    # ======================================================
    #  Load data
    with uproot.open(scatt_file) as f:
        scatt = f[f.keys()[0]]
        E_scatt = np.asarray(scatt["TotalEnergyDeposit"].array()) / keV

    with uproot.open(abs_file) as f:
        absr = f[f.keys()[0]]
        E_abs = np.asarray(absr["TotalEnergyDeposit"].array()) / keV

    # Energy-only tests (Gaussian peaks)
    scatt_name = "E_ly1"  # Scatterer histogram name
    abs_name = "E_ly2"  # Absorber histogram name
    exp_hists = load_exp_histograms(exp_singles_file, scatt_name, abs_name)
    exp_abs_counts, exp_abs_edges = exp_hists[abs_name]
    exp_scatt_counts, exp_scatt_edges = exp_hists[scatt_name]

    is_ok = True
    b = compare_peak_gaussian(
        E_abs,
        exp_abs_counts,
        exp_abs_edges,
        expected_energy=1274.5,
        label="Absorber 1274.5 keV",
        output_plot_path=output_folder / "test099_abs_peak_1274.5keV.png",
    )
    is_ok = is_ok and b
    b = compare_peak_gaussian(
        E_scatt,
        exp_scatt_counts,
        exp_scatt_edges,
        expected_energy=1274.5,
        label="Scatterer 1274.5 keV",
        output_plot_path=output_folder / "test099_scatt_peak_1274.5keV.png",
    )
    is_ok = is_ok and b
    compare_peak_gaussian(
        E_abs,
        exp_abs_counts,
        exp_abs_edges,
        expected_energy=511.0,
        label="Absorber 511 keV",
        output_plot_path=output_folder / "test099_abs_peak_511keV.png",
    )
    is_ok = is_ok and b
    compare_peak_gaussian(
        E_scatt,
        exp_scatt_counts,
        exp_scatt_edges,
        expected_energy=511.0,
        label="Scatterer 511 keV",
        output_plot_path=output_folder / "test099_scatt_peak_511keV.png",
    )
    is_ok = is_ok and b
    print("✓ MACACO1 singles energy test completed")

    # ======================================================
    # 8) VALIDATION : COINCIDENCES
    # ======================================================

    coinc_file = output_folder / "coincidences.root"
    coincidences = macaco1_compute_coincidences(
        scatt_file,
        abs_file,
        time_windows=12 * ns,
        output_root_filename=coinc_file,
        scatt_tree_name="ThrScatt",
        abs_tree_name="ThrAbs",
        merged_tree_name="Singles",
    )
    print()
    print(
        f"Coincidences file: {coinc_file} : FIXME to be compared with experimental data"
    )

    # FIXME => here add the comparison with the experimental data

    # print("\n✓ MACACO1 coincidence test completed")

    utility.test_ok(is_ok)


if __name__ == "__main__":
    main()
