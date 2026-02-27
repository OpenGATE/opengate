#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
import uproot
from pathlib import Path
import os

import opengate as gate
from opengate.utility import g4_units
from opengate.tests import utility

# Code under test
from opengate.contrib.compton_camera.macaco import (
    add_macaco1_camera,
    add_macaco1_camera_digitizer,
)

EXP_SINGLES_FILE = None  # set in main() using utility paths
EXP_SCATT_HIST = "E_ly1"  # Scatterer histogram name in EXP_SINGLES_FILE
EXP_ABS_HIST = "E_ly2"  # Absorber histogram name in EXP_SINGLES_FILE


def load_exp_histograms(path: Path) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    if not path.exists():
        raise FileNotFoundError(f"Experimental data file not found: {path}")
    histograms: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    with uproot.open(path) as f:
        for name in (EXP_SCATT_HIST, EXP_ABS_HIST):
            obj = f[name]
            counts, edges = obj.to_numpy()
            histograms[name] = (
                np.asarray(counts, dtype=float),
                np.asarray(edges, dtype=float),
            )
    return histograms


def gaussian_fit_hist(centers: np.ndarray, counts: np.ndarray) -> tuple[float, float]:
    mask = counts > 0
    if mask.sum() < 3:  # need at least 3 points to fit a quadratic
        return float("nan"), float("nan")
    x = centers[mask].astype(float)  # x values for the fit (bin centers)
    y = np.log(counts[mask].astype(float))  # log of counts to linearize Gaussian
    a, b, _ = np.polyfit(x, y, 2)  # quadratic fit: y = a x^2 + b x + c
    mu = -b / (2.0 * a)  # mean of Gaussian from quadratic coefficients
    sigma = float(np.sqrt(-1.0 / (2.0 * a)))  # sigma from curvature
    return float(mu), sigma  # return fitted mean and sigma


def compare_peak_gaussian(
    sim_energies: np.ndarray,
    exp_counts: np.ndarray,
    exp_edges: np.ndarray,
    expected_energy: float,
    label: str,
    tol_frac: float = 0.20,
) -> None:
    centers = 0.5 * (
        exp_edges[:-1] + exp_edges[1:]
    )  # bin centers from experimental edges
    win_lo, win_hi = peak_window_from_exp(  # pick window around expected peak
        centers, exp_counts, expected_energy=expected_energy
    )
    exp_mask = (centers >= win_lo) & (centers <= win_hi)  # select bins in window
    exp_counts_win = exp_counts[exp_mask]  # experimental counts in window
    exp_centers_win = centers[exp_mask]  # experimental bin centers in window
    if exp_counts_win.sum() <= 0.0:  # guard against empty experimental window
        print(
            f"✗ {label}: no experimental counts in window", flush=True
        )  # report failure
        return  # stop if no data to fit
    sim_counts, _ = np.histogram(
        sim_energies, bins=exp_edges
    )  # simulated counts on same bins
    sim_counts_win = sim_counts[exp_mask]  # simulated counts in same window

    # debug prints removed

    mu_exp, sigma_exp = gaussian_fit_hist(exp_centers_win, exp_counts_win)
    mu_sim, sigma_sim = gaussian_fit_hist(exp_centers_win, sim_counts_win)

    if (
        np.isnan(mu_exp)
        or np.isnan(sigma_exp)
        or np.isnan(mu_sim)
        or np.isnan(sigma_sim)
    ):
        print(f"✗ {label}: Gaussian fit failed", flush=True)
        return

    if mu_exp == 0.0 or sigma_exp == 0.0:
        print(f"✗ {label}: zero experimental mean/sigma", flush=True)
        return

    mean_pct = 100.0 * abs(mu_sim - mu_exp) / abs(mu_exp)  # % difference in mean
    sigma_pct = (
        100.0 * abs(sigma_sim - sigma_exp) / abs(sigma_exp)
    )  # % difference in sigma
    fwhm_exp = 2.355 * sigma_exp  # convert sigma to FWHM for experimental
    fwhm_sim = 2.355 * sigma_sim  # convert sigma to FWHM for simulated
    fwhm_pct = 100.0 * abs(fwhm_sim - fwhm_exp) / abs(fwhm_exp)  # % difference in FWHM
    tol_pct = tol_frac * 100.0  # tolerance expressed in percent

    max_diff = max(mean_pct, sigma_pct, fwhm_pct)
    if mean_pct < tol_pct and sigma_pct < tol_pct and fwhm_pct < tol_pct:
        print(f"✓ {label} pass (max diff={max_diff:.1f}%)", flush=True)
    else:
        print(f"✗ {label} fail (max diff={max_diff:.1f}%)", flush=True)


# builds the energy window around the expected peak in the experimental histogram.
def peak_window_from_exp(
    centers: np.ndarray,
    counts: np.ndarray,
    expected_energy: float,
    *,
    rel_span: float = 0.1,
) -> tuple[float, float]:
    if expected_energy < 700.0:
        rel_span = 0.12
    else:
        rel_span = 0.075
    low = expected_energy * (1.0 - rel_span)
    high = expected_energy * (1.0 + rel_span)
    mask = (centers > low) & (centers < high)
    sel_counts = counts[mask]
    if sel_counts.sum() <= 0.0:
        raise ValueError(f"No experimental counts near {expected_energy} keV.")
    return low, high


def main():
    # get tests paths
    paths = utility.get_default_test_paths(
        __file__, gate_folder="", output_folder="test099_macaco1"
    )
    output_folder = paths.output
    output_ref = paths.output_ref

    exp_singles_file = output_ref / "singles_experimental.root"

    # ======================================================
    # 1) Create simulation
    # ======================================================
    sim = gate.Simulation()
    sim.visu = False
    sim.number_of_threads = 2
    sim.check_volumes_overlap = False

    mm = g4_units.mm
    keV = g4_units.keV
    Bq = g4_units.Bq
    sec = g4_units.s

    # ======================================================
    # 2) Geometry
    # ======================================================
    cam = add_macaco1_camera(sim)
    scatterer = cam["scatterer"]
    absorber = cam["absorber"]

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
    sim.run_timing_intervals = [[0, 3 * sec]]

    # ======================================================
    # 5) Digitizer (CODE UNDER TEST)
    # ======================================================
    prev_cwd = os.getcwd()
    os.chdir(output_folder)

    scatt_file, abs_file = add_macaco1_camera_digitizer(sim, scatterer, absorber)

    # ======================================================
    # 6) Run simulation
    # ======================================================
    sim.run()

    # ======================================================
    # 7) VALIDATIONS
    # ======================================================
    try:
        #  Load data
        with uproot.open(scatt_file) as f:
            scatt = f[f.keys()[0]]
            E_scatt = np.asarray(scatt["TotalEnergyDeposit"].array()) / keV

        with uproot.open(abs_file) as f:
            absr = f[f.keys()[0]]
            E_abs = np.asarray(absr["TotalEnergyDeposit"].array()) / keV
    finally:
        os.chdir(prev_cwd)

    # Energy-only tests (Gaussian peaks)
    exp_hists = load_exp_histograms(exp_singles_file)
    exp_abs_counts, exp_abs_edges = exp_hists[EXP_ABS_HIST]
    exp_scatt_counts, exp_scatt_edges = exp_hists[EXP_SCATT_HIST]

    compare_peak_gaussian(
        E_abs,
        exp_abs_counts,
        exp_abs_edges,
        expected_energy=1274.5,
        label="Absorber 1274.5 keV",
    )
    compare_peak_gaussian(
        E_scatt,
        exp_scatt_counts,
        exp_scatt_edges,
        expected_energy=1274.5,
        label="Scatterer 1274.5 keV",
    )
    compare_peak_gaussian(
        E_abs,
        exp_abs_counts,
        exp_abs_edges,
        expected_energy=511.0,
        label="Absorber 511 keV",
    )
    compare_peak_gaussian(
        E_scatt,
        exp_scatt_counts,
        exp_scatt_edges,
        expected_energy=511.0,
        label="Scatterer 511 keV",
    )

    print("\n✓ MACACO1 energy test completed")


if __name__ == "__main__":
    main()
