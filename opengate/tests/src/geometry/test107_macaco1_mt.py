#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
import pandas as pd
import uproot
import matplotlib
import matplotlib.pyplot as plt
from pathlib import Path
import time
import sys

import opengate as gate
from opengate.tests import utility
from opengate.utility import g4_units
from opengate.contrib.compton_camera.macaco import (
    add_macaco1_camera,
    add_macaco1_camera_digitizer,
    macaco1_merge_and_compute_coincidences,
    load_exp_histograms,
    compare_peak_gaussian,
)
from opengate.actors.coincidences import cc_coincidences_sorter
from opengate.contrib.root_helpers import (
    root_tree_get_branch_data,
    root_tree_get_branch_types,
    root_write_tree,
)
from opengate.actors.coincidences import kill_multiple_coinc, kill_same_volume_pairs

try:
    from scipy.optimize import curve_fit
except Exception:
    curve_fit = None

# -----------------------------
# Configuration
# -----------------------------
ME_C2_KEV = 511.0
ARM_UNITS = "rad"
ARM_RANGE = (-2.0, 2.0)
SOURCE_POS_MM = np.array([0.0, 0.0, 0.0], dtype=float)
ESUM_BIN_WIDTH_KEV = 5.0
ESUM_MAX_KEV = 2000.0
E_BIN_WIDTH_KEV = 5.0
E_MAX_KEV = 1500.0
ARM_REBIN_FACTOR = 2
FWHM_PASS_THRESHOLD_PCT = 40.0
COINC_TIME_WINDOW_NS = 50.0


# -----------------------------
# Helper functions (from working local test)
# -----------------------------
def load_root_as_dataframe(
    root_path: Path, *, out_dir: Path, retries: int = 5, delay_s: float = 0.5
) -> pd.DataFrame:
    root_path = root_path if root_path.exists() else out_dir / root_path.name
    for attempt in range(1, retries + 1):
        if not root_path.exists():
            time.sleep(delay_s)
            continue
        try:
            with uproot.open(root_path) as f:
                keys = list(f.keys())
                if keys:
                    tname = keys[0].split(";")[0]
                    return f[tname].arrays(library="pd")
        except Exception:
            pass
        time.sleep(delay_s)
    raise RuntimeError(
        f"ROOT file has no trees or could not be read after {retries} attempts: {root_path} "
        f"(size={root_path.stat().st_size if root_path.exists() else 'missing'})"
    )


def load_digitizer_singles(
    scatt_file: Path, abs_file: Path, *, out_dir: Path
) -> tuple[pd.DataFrame, pd.DataFrame]:
    return (
        load_root_as_dataframe(scatt_file, out_dir=out_dir),
        load_root_as_dataframe(abs_file, out_dir=out_dir),
    )


def prepare_layered_singles(
    scatter_df: pd.DataFrame, absorber_df: pd.DataFrame
) -> pd.DataFrame:
    def _tag_layer(df: pd.DataFrame, label: str) -> pd.DataFrame:
        tagged = df.copy()
        tagged["PreStepUniqueVolumeID"] = label
        return tagged

    combined = pd.concat(
        [_tag_layer(scatter_df, "scatterer"), _tag_layer(absorber_df, "absorber")],
        ignore_index=True,
    )
    return combined.sort_values(["GlobalTime", "EventID"]).reset_index(drop=True)


def build_singles_dataframe(layered: pd.DataFrame) -> pd.DataFrame:
    required = [
        "EventID",
        "GlobalTime",
        "PreStepUniqueVolumeID",
        "TotalEnergyDeposit",
        "PostPosition_X",
        "PostPosition_Y",
        "PostPosition_Z",
    ]
    missing = [col for col in required if col not in layered.columns]
    if missing:
        raise ValueError(f"Missing required singles columns: {missing}")
    return layered[required]


def write_singles_root(path: Path, df: pd.DataFrame) -> Path:
    df_to_write = df.copy()
    for col in df_to_write.columns:
        if df_to_write[col].dtype == object:
            df_to_write[col] = pd.Categorical(df_to_write[col])
    data = df_to_write.to_dict(orient="list")
    data = root_tree_get_branch_data(data)
    types = root_tree_get_branch_types(data)
    with uproot.recreate(path) as f:
        root_write_tree(f, "Singles", types, data)
    return path


def extract_sorted_coincidences(
    coincidences: pd.DataFrame,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    labels1 = coincidences["PreStepUniqueVolumeID1"].astype(str).str.lower()
    is_scatt1 = labels1.str.contains("scatt")
    scatt_pos = np.column_stack(
        [
            np.where(
                is_scatt1,
                coincidences[f"PostPosition_{ax}1"],
                coincidences[f"PostPosition_{ax}2"],
            )
            for ax in "XYZ"
        ]
    ).astype(float)
    abs_pos = np.column_stack(
        [
            np.where(
                is_scatt1,
                coincidences[f"PostPosition_{ax}2"],
                coincidences[f"PostPosition_{ax}1"],
            )
            for ax in "XYZ"
        ]
    ).astype(float)
    e_scatt = np.where(
        is_scatt1,
        coincidences["TotalEnergyDeposit1"],
        coincidences["TotalEnergyDeposit2"],
    ).astype(float)
    e_abs = np.where(
        is_scatt1,
        coincidences["TotalEnergyDeposit2"],
        coincidences["TotalEnergyDeposit1"],
    ).astype(float)
    return scatt_pos, abs_pos, e_scatt, e_abs, is_scatt1.to_numpy(dtype=bool)


def pairs_from_coincident_singles(df: pd.DataFrame) -> pd.DataFrame:
    if "CoincID" not in df.columns:
        raise ValueError("Missing CoincID in coincident singles.")
    rows = []
    for _, group in df.groupby("CoincID"):
        if len(group) < 2:
            continue
        s1, s2 = group.iloc[0], group.iloc[1]
        rows.append(
            {
                "PreStepUniqueVolumeID1": s1["PreStepUniqueVolumeID"],
                "PreStepUniqueVolumeID2": s2["PreStepUniqueVolumeID"],
                **{f"PostPosition_{ax}1": s1[f"PostPosition_{ax}"] for ax in "XYZ"},
                **{f"PostPosition_{ax}2": s2[f"PostPosition_{ax}"] for ax in "XYZ"},
                "TotalEnergyDeposit1": s1["TotalEnergyDeposit"],
                "TotalEnergyDeposit2": s2["TotalEnergyDeposit"],
            }
        )
    return pd.DataFrame(rows)


def compute_theta_c(e_scatt: np.ndarray, e0: np.ndarray) -> np.ndarray:
    e_scattered = e0 - e_scatt
    valid = (e0 > 0.0) & (e_scattered > 0.0)
    cos_theta = np.full_like(e0, np.nan, dtype=float)
    cos_theta[valid] = 1.0 - (
        ME_C2_KEV * e_scatt[valid] / (e_scattered[valid] * e0[valid])
    )
    in_range = (cos_theta >= -1.0) & (cos_theta <= 1.0)
    cos_theta = np.where(in_range, cos_theta, np.nan)
    return np.arccos(cos_theta)


def compute_theta_g(
    scatter_pos: np.ndarray, absorber_pos: np.ndarray, source_pos: np.ndarray
) -> np.ndarray:
    incoming = scatter_pos - source_pos
    outgoing = absorber_pos - scatter_pos
    incoming_norm = np.linalg.norm(incoming, axis=1)
    outgoing_norm = np.linalg.norm(outgoing, axis=1)
    valid = (incoming_norm > 0.0) & (outgoing_norm > 0.0)
    cos_theta = np.full(incoming_norm.shape, np.nan, dtype=float)
    dot = np.einsum("ij,ij->i", incoming, outgoing)
    cos_theta[valid] = dot[valid] / (incoming_norm[valid] * outgoing_norm[valid])
    in_range = (cos_theta >= -1.0) & (cos_theta <= 1.0)
    cos_theta = np.where(in_range, cos_theta, np.nan)
    return np.arccos(cos_theta)


def compute_arm(
    scatter_pos: np.ndarray,
    absorber_pos: np.ndarray,
    e_scatt: np.ndarray,
    e_abs: np.ndarray,
    source_pos: np.ndarray,
) -> np.ndarray:
    e0 = np.where(e_scatt + e_abs < 600.0, 511.0, 1275.0)
    theta_c = compute_theta_c(e_scatt, e0)
    theta_g = compute_theta_g(scatter_pos, absorber_pos, source_pos)
    valid = ~np.isnan(theta_c) & ~np.isnan(theta_g)
    return (theta_g - theta_c)[valid]


def normalize_hist_counts(counts: np.ndarray, edges: np.ndarray) -> np.ndarray:
    total = float(np.sum(counts))
    if total <= 0:
        return np.zeros_like(counts, dtype=float)
    bin_width = float(np.diff(edges)[0])
    return counts.astype(float) / (total * bin_width)


def rebin_hist(
    counts: np.ndarray, edges: np.ndarray, factor: int
) -> tuple[np.ndarray, np.ndarray]:
    if factor <= 1:
        return counts, edges
    n = (len(counts) // factor) * factor
    if n == 0:
        return counts, edges
    return counts[:n].reshape(-1, factor).sum(axis=1), edges[: n + 1 : factor]


def lorentzian(
    x: np.ndarray, amp: float, x0: float, gamma: float, offset: float
) -> np.ndarray:
    half_gamma = 0.5 * gamma
    return amp * half_gamma**2 / ((x - x0) ** 2 + half_gamma**2) + offset


def fit_lorentzian(
    x: np.ndarray, y: np.ndarray
) -> tuple[np.ndarray, np.ndarray] | tuple[None, None]:
    if curve_fit is None or np.count_nonzero(y) < 2:
        return None, None
    amp0 = float(np.max(y))
    x0 = float(x[np.argmax(y)])
    above_half = x[y >= amp0 / 2.0]
    gamma0 = (
        float(above_half[-1] - above_half[0])
        if len(above_half) >= 2
        else float((x[-1] - x[0]) / 10.0)
    )
    gamma0 = max(gamma0, float(np.diff(x).mean()))
    offset0 = float(np.min(y))
    p0 = [amp0, x0, gamma0, offset0]
    bin_w = float(np.diff(x).mean()) if len(x) > 1 else 1e-3
    amp_max = float(np.max(y))
    try:
        popt, pcov = curve_fit(
            lorentzian,
            x,
            y,
            p0=p0,
            bounds=(
                [0, x.min(), bin_w, -np.inf],
                [amp_max, x.max(), np.ptp(x), np.inf],
            ),
            maxfev=10000,
        )
    except RuntimeError:
        return None, None
    return popt, pcov


def load_experimental_arm_histograms(
    path: Path,
) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Experimental ROOT file not found: {path}")
    mapping = {
        "all": "AngularUncertaintyReal",
        "511": "AngularUncertaintyReal511",
        "1275": "AngularUncertaintyReal1275",
    }
    histograms: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    with uproot.open(path) as f:
        for key, name in mapping.items():
            if name not in f:
                continue
            counts, edges = f[name].to_numpy()
            centers = 0.5 * (edges[:-1] + edges[1:])
            histograms[key] = (
                np.asarray(centers, dtype=float),
                np.asarray(counts, dtype=float),
            )
    if not histograms:
        raise ValueError(f"No AngularUncertainty* histograms found in {path}")
    return histograms


def plot_arm_overlay(
    label: str,
    exp_centers: np.ndarray,
    exp_counts: np.ndarray,
    sim_arm: np.ndarray,
    out_dir: Path,
    *,
    sim_bin_factor: int = 1,
) -> tuple | None:
    if exp_centers.size < 2:
        print(f"Skipping {label} ARM (empty exp histogram).")
        return None
    bin_width = float(np.median(np.diff(exp_centers)))
    edges = np.concatenate(
        [exp_centers - bin_width / 2.0, [exp_centers[-1] + bin_width / 2.0]]
    )
    exp_counts_rb, edges_rb = rebin_hist(exp_counts, edges, ARM_REBIN_FACTOR)
    exp_hist = normalize_hist_counts(exp_counts_rb, edges_rb)
    sim_edges = edges_rb[::sim_bin_factor]
    if sim_edges[-1] != edges_rb[-1]:
        sim_edges = np.append(sim_edges, edges_rb[-1])
    sim_counts_rb, _ = np.histogram(sim_arm, bins=sim_edges)
    sim_hist = normalize_hist_counts(sim_counts_rb, sim_edges)
    exp_centers_rb = 0.5 * (edges_rb[:-1] + edges_rb[1:])
    sim_centers = 0.5 * (sim_edges[:-1] + sim_edges[1:])

    fit_mask_exp = np.abs(exp_centers_rb) <= 0.2
    fit_mask_sim = np.abs(sim_centers) <= 0.2
    exp_fit, _ = fit_lorentzian(exp_centers_rb[fit_mask_exp], exp_hist[fit_mask_exp])
    sim_fit, _ = fit_lorentzian(sim_centers[fit_mask_sim], sim_hist[fit_mask_sim])

    exp_mu = float(exp_fit[1]) if exp_fit is not None else None
    exp_fwhm = float(abs(exp_fit[2])) if exp_fit is not None else None
    sim_mu = float(sim_fit[1]) if sim_fit is not None else None
    sim_fwhm = float(abs(sim_fit[2])) if sim_fit is not None else None

    exp_label = (
        f"Experimental (μ={exp_mu:.3f}, FWHM={exp_fwhm:.3f} {ARM_UNITS})"
        if exp_fit is not None
        else "Experimental"
    )
    sim_label = (
        f"Simulated (μ={sim_mu:.3f}, FWHM={sim_fwhm:.3f} {ARM_UNITS})"
        if sim_fit is not None
        else "Simulated"
    )

    matplotlib.use("Agg")
    fig, ax = plt.subplots(figsize=(7.0, 5.5))
    ax.plot(exp_centers_rb, exp_hist, color="tab:red", linewidth=1.2, label=exp_label)
    ax.fill_between(
        exp_centers_rb, exp_hist, 0.0, color="tab:red", alpha=0.25, linewidth=0
    )
    ax.plot(
        sim_centers,
        sim_hist,
        color="black",
        linestyle="--",
        linewidth=1.1,
        label=sim_label,
    )
    ax.fill_between(sim_centers, sim_hist, 0.0, color="0.6", alpha=0.2, linewidth=0)
    if exp_fit is not None:
        xfit = np.linspace(exp_centers_rb.min(), exp_centers_rb.max(), 600)
        ax.plot(
            xfit, lorentzian(xfit, *exp_fit), color="tab:red", linewidth=1.4, alpha=0.9
        )
    if sim_fit is not None:
        xfit = np.linspace(sim_centers.min(), sim_centers.max(), 600)
        ax.plot(
            xfit,
            lorentzian(xfit, *sim_fit),
            color="black",
            linewidth=1.2,
            alpha=0.9,
            linestyle=":",
        )
    ax.set_xlabel(r"$\theta_G - \theta_C$ ({})".format(ARM_UNITS))
    ax.set_ylabel("Normalised counts")
    ax.set_title(f"ARM overlay ({label})")
    ax.set_xlim(ARM_RANGE)
    ax.set_ylim(bottom=0)
    ax.grid(True, linestyle="--", alpha=0.2)
    ax.legend(frameon=False)
    fig.tight_layout()
    out_path = out_dir / f"arm_overlay_{label.replace(' ', '_')}.png"
    fig.savefig(out_path, dpi=200)
    plt.close(fig)
    print(f"Saved ARM overlay: {out_path}")

    return exp_centers_rb, exp_hist, sim_mu, sim_fwhm, exp_fwhm


# -----------------------------
# Main
# -----------------------------
def main():
    paths = utility.get_default_test_paths(
        __file__, gate_folder="", output_folder="test107_macaco1"
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
    sim.number_of_threads = 4
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
    camera.translation = [0, 0, 83 * mm]

    # ======================================================
    # 3) Source
    # ======================================================
    src_holder = sim.add_volume("Sphere", "test_source_holder")
    src_holder.mother = sim.world
    src_holder.material = "Plastic"
    src_holder.rmax = 0.25 * mm

    src = sim.add_source("GenericSource", "Na22_decay")
    src.particle = "ion 11 22"
    src.attached_to = src_holder
    src.activity = 847e3 * Bq
    src.position.type = "point"
    src.direction.type = "iso"
    src.user_particle_life_time = 0

    sim.physics_manager.enable_decay = True

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
    with uproot.open(scatt_file) as f:
        scatt = f[f.keys()[0]]
        E_scatt = np.asarray(scatt["TotalEnergyDeposit"].array()) / keV

    with uproot.open(abs_file) as f:
        absr = f[f.keys()[0]]
        E_abs = np.asarray(absr["TotalEnergyDeposit"].array()) / keV

    scatt_name = "E_ly1"
    abs_name = "E_ly2"
    exp_hists = load_exp_histograms(exp_singles_file, scatt_name, abs_name)
    exp_abs_counts, exp_abs_edges = exp_hists[abs_name]
    exp_scatt_counts, exp_scatt_edges = exp_hists[scatt_name]

    is_ok = True
    print()
    b = compare_peak_gaussian(
        E_abs,
        exp_abs_counts,
        exp_abs_edges,
        expected_energy=1274.5,
        label="Absorber 1274.5 keV",
        output_plot_path=output_folder / "test107_abs_peak_1274.5keV.png",
    )
    is_ok = is_ok and b
    print()
    b = compare_peak_gaussian(
        E_scatt,
        exp_scatt_counts,
        exp_scatt_edges,
        expected_energy=1274.5,
        label="Scatterer 1274.5 keV",
        output_plot_path=output_folder / "test107_scatt_peak_1274.5keV.png",
    )
    is_ok = is_ok and b
    print()
    b = compare_peak_gaussian(
        E_abs,
        exp_abs_counts,
        exp_abs_edges,
        expected_energy=511.0,
        label="Absorber 511 keV",
        output_plot_path=output_folder / "test107_abs_peak_511keV.png",
    )
    is_ok = is_ok and b
    print()
    b = compare_peak_gaussian(
        E_scatt,
        exp_scatt_counts,
        exp_scatt_edges,
        expected_energy=511.0,
        label="Scatterer 511 keV",
        output_plot_path=output_folder / "test107_scatt_peak_511keV.png",
    )
    is_ok = is_ok and b
    print("✓ MACACO1 singles energy test completed")

    # ======================================================
    # 8) VALIDATION : COINCIDENCES
    # ======================================================
    coinc_file = output_folder / "coincidences.root"
    coincidences = macaco1_merge_and_compute_coincidences(
        scatt_file,
        abs_file,
        time_windows=12 * ns,
        output_root_filename=coinc_file,
        scatt_tree_name="ThrScatt",
        abs_tree_name="ThrAbs",
        merged_tree_name="Singles",
    )

    # ======================================================
    # 8b) VALIDATION : COINCIDENCES ARM
    # ======================================================
    exp_coinc_root = output_ref / "new_coinc_exp_data.root"

    if not exp_coinc_root.exists():
        print(
            f"Experimental coincidence ROOT not found: {exp_coinc_root}, skipping ARM validation."
        )
    else:
        scatt_df, abs_df = load_digitizer_singles(
            scatt_file, abs_file, out_dir=output_folder
        )
        layered = prepare_layered_singles(scatt_df, abs_df)
        singles_path = write_singles_root(
            output_folder / "singles_sim.root", build_singles_dataframe(layered)
        )

        time_window = COINC_TIME_WINDOW_NS * ns
        with uproot.open(singles_path) as f:
            coinc_singles = cc_coincidences_sorter(f["Singles"], time_window)

        if coinc_singles is None or coinc_singles.empty:
            raise AssertionError("No coincidences after sorter")

        coinc_singles = kill_multiple_coinc(coinc_singles, group_col="CoincID")
        coinc_singles = kill_same_volume_pairs(
            coinc_singles, group_col="CoincID", volume_col="PreStepUniqueVolumeID"
        )
        coinc_pairs = pairs_from_coincident_singles(coinc_singles)

        scatt_pos, abs_pos, e_scatt, e_abs, _ = extract_sorted_coincidences(coinc_pairs)
        e_scatt /= keV
        e_abs /= keV
        mask_1275 = (e_scatt + e_abs) >= 600.0

        exp_arm_hists = load_experimental_arm_histograms(exp_coinc_root)
        sim_arm = compute_arm(
            scatt_pos[mask_1275],
            abs_pos[mask_1275],
            e_scatt[mask_1275],
            e_abs[mask_1275],
            SOURCE_POS_MM,
        )
        centers, counts = exp_arm_hists["1275"]

        fit_stats = plot_arm_overlay(
            "1275", centers, counts, sim_arm, output_folder, sim_bin_factor=2
        )

        if fit_stats is None:
            print("✗ ARM plot failed")
            is_ok = False
        else:
            _, _, sim_mu, sim_fwhm, exp_fwhm = fit_stats
            if sim_fwhm is not None and exp_fwhm is not None:
                diff_pct = abs(sim_fwhm - exp_fwhm) / exp_fwhm * 100.0
                print(
                    f"1275 FWHM: sim={sim_fwhm:.3f} {ARM_UNITS}, "
                    f"exp={exp_fwhm:.3f} {ARM_UNITS}, diff={diff_pct:.1f}% "
                    f"(threshold={FWHM_PASS_THRESHOLD_PCT:.1f}%)"
                )
                b = diff_pct < FWHM_PASS_THRESHOLD_PCT
                print(
                    f"{'✓' if b else '✗'} 1275 FWHM {'within' if b else 'exceeds'} tolerance"
                )
                is_ok = is_ok and b
            else:
                print("ARM FWHM fit unavailable — FAIL")
                is_ok = False

    utility.test_ok(is_ok)


if __name__ == "__main__":
    main()
