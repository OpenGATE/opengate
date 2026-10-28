from pathlib import Path
import uproot
from opengate.utility import g4_units
from opengate.actors.coincidences import *
import numpy as np
import matplotlib.pyplot as plt


def add_macaco1_materials(sim):
    """
    Adds the Macaco materials database to the simulation if not already present.
    """
    db_folder = Path(__file__).parent.resolve()
    db_filename = db_folder / "macaco_materials.db"
    if not db_filename in sim.volume_manager.material_database.filenames:
        sim.volume_manager.add_material_database(db_filename)


def add_macaco1_camera(sim, name="macaco1"):
    """
    Adds a MACACO1 camera to the simulation.
    - Bounding box (BB_box)
    - Plane 1 (scatterer side): holder, crystal carcass, PCB, SiPM, LaBr3_VLC crystal
    - Plane 2 (absorber side): holder, crystal carcass, PCB, SiPM, LaBr3_VLC crystal
    """

    # units
    mm = g4_units.mm
    cm = g4_units.cm

    # material
    add_macaco1_materials(sim)

    # BB box (acts as camera envelope)
    camera = sim.add_volume("Box", f"{name}_BB_box")
    camera.mother = sim.world
    camera.material = "G4_AIR"
    camera.size = [16 * cm, 40 * cm, 7.6 * cm]
    camera.color = [0.1, 0.1, 0.1, 0.1]

    # Scatterer
    holder1 = sim.add_volume("Box", f"{name}_Holder1")
    holder1.mother = camera.name
    holder1.material = "Plastic"
    holder1.size = [6.2 * cm, 6.2 * cm, 0.56 * cm]
    holder1.translation = [0, 0, -2.74 * cm]
    holder1.color = [0.1, 0.1, 0.1, 0.9]

    crys_carcase_scatt = sim.add_volume("Box", f"{name}_crysCarcaseScatt")
    crys_carcase_scatt.mother = holder1.name
    crys_carcase_scatt.material = "G4_Al"
    crys_carcase_scatt.size = [2.72 * cm, 2.68 * cm, 0.01 * cm]
    crys_carcase_scatt.translation = [0, 0, -0.265 * cm]

    pcb_scatt = sim.add_volume("Box", f"{name}_PCBScatt")
    pcb_scatt.mother = camera.name
    pcb_scatt.material = "PCB"
    pcb_scatt.size = [10.89 * cm, 20.7 * cm, 0.4 * cm]
    # pcb_scatt.translation = [0, 6.25 * cm, -2.46 * cm]
    pcb_scatt.translation = [0, 6.25 * cm, -2.26 * cm]
    pcb_scatt.color = [0.0, 0.5, 0.0, 0.9]

    sipm_scatt = sim.add_volume("Box", f"{name}_SiPMScatt")
    sipm_scatt.mother = holder1.name
    sipm_scatt.material = "G4_Si"
    sipm_scatt.size = [2.72 * cm, 2.68 * cm, 0.04 * cm]
    sipm_scatt.translation = [0, 0, 0.26 * cm]
    sipm_scatt.color = [1.0, 0.5, 0.0, 0.9]

    scatterer = sim.add_volume("Box", f"{name}_scatterer")
    scatterer.mother = holder1.name
    scatterer.material = "LaBr3_VLC"
    scatterer.size = [2.72 * cm, 2.68 * cm, 0.50 * cm]
    scatterer.translation = [0, 0, -0.01 * cm]
    scatterer.color = [0.4, 0.7, 1.0, 1.0]

    # Absorber
    holder2 = sim.add_volume("Box", f"{name}_Holder2")
    holder2.mother = camera.name
    holder2.material = "Plastic"
    holder2.size = [8.0 * cm, 8.0 * cm, 1.06 * cm]
    holder2.translation = [0, 0, 2.51 * cm]
    holder2.color = [0.1, 0.1, 0.1, 0.9]

    crys_carcase_abs = sim.add_volume("Box", f"{name}_crysCarcaseAbs")
    crys_carcase_abs.mother = holder2.name
    crys_carcase_abs.material = "G4_Al"
    crys_carcase_abs.size = [3.24 * cm, 3.60 * cm, 0.01 * cm]
    crys_carcase_abs.translation = [0, 0, -0.515 * cm]

    absorber = sim.add_volume("Box", f"{name}_absorber")
    absorber.mother = holder2.name
    absorber.material = "LaBr3_VLC"
    absorber.size = [3.24 * cm, 3.60 * cm, 1.00 * cm]
    absorber.translation = [0, 0, -0.01 * cm]
    absorber.color = [0.4, 0.7, 1.0, 1.0]

    sipm_abs = sim.add_volume("Box", f"{name}_SiPMAbs")
    sipm_abs.mother = holder2.name
    sipm_abs.material = "G4_Si"
    sipm_abs.size = [3.24 * cm, 3.60 * cm, 0.04 * cm]
    sipm_abs.translation = [0, 0, 0.51 * cm]
    sipm_abs.color = [1.0, 0.5, 0.0, 0.9]

    pcb_abs = sim.add_volume("Box", f"{name}_PCBAbs")
    pcb_abs.mother = camera.name
    pcb_abs.material = "PCB"
    pcb_abs.size = [9.54 * cm, 16.0 * cm, 0.4 * cm]
    pcb_abs.translation = [0, 4.50 * cm, 3.24 * cm]
    pcb_abs.color = [0.0, 0.5, 0.0, 0.9]

    return {
        "camera": camera,
        "scatterer": scatterer,
        "absorber": absorber,
        "holder1": holder1,
        "holder2": holder2,
    }


def add_macaco1_camera_digitizer(sim, scatterer, absorber):
    # Units
    keV = g4_units.keV
    MeV = g4_units.MeV
    mm = g4_units.mm
    ns = g4_units.ns

    # 1) Collect step-level hits for both scatterer and absorber
    hits_scatt = sim.add_actor("DigitizerHitsCollectionActor", "HitsScatt")
    hits_scatt.attached_to = scatterer.name
    hits_scatt.attributes = [
        "EventID",
        "TrackID",
        "TotalEnergyDeposit",
        "GlobalTime",
        "PrePosition",
        "PostPosition",
        "PreStepUniqueVolumeID",
    ]

    hits_abs = sim.add_actor("DigitizerHitsCollectionActor", "HitsAbs")
    hits_abs.attached_to = absorber.name
    hits_abs.attributes = hits_scatt.attributes
    scatt_collection = hits_scatt.name
    abs_collection = hits_abs.name

    # 2) Process Hits into Singles
    sing_scatt = sim.add_actor("DigitizerAdderActor", "SinglesScatt")
    sing_scatt.input_digi_collection = scatt_collection
    sing_scatt.policy = "EnergyWeightedCentroidPosition"
    sing_scatt.attributes = [
        "EventID",
        "GlobalTime",
        "TotalEnergyDeposit",
        "PostPosition",
    ]
    scatt_collection = sing_scatt.name

    sing_abs = sim.add_actor("DigitizerAdderActor", "SinglesAbs")
    sing_abs.input_digi_collection = abs_collection
    sing_abs.policy = "EnergyWeightedCentroidPosition"
    sing_abs.attributes = sing_scatt.attributes
    abs_collection = sing_abs.name

    # Spatial blurring
    spat_scatt = sim.add_actor("DigitizerSpatialBlurringActor", "SpatScatt")
    spat_scatt.attached_to = scatterer.name
    spat_scatt.input_digi_collection = scatt_collection
    spat_scatt.blur_attribute = "PostPosition"
    spat_scatt.blur_fwhm = [2 * mm, 2 * mm, 2 * mm]
    scatt_collection = spat_scatt.name

    spat_abs = sim.add_actor("DigitizerSpatialBlurringActor", "SpatAbs")
    spat_abs.attached_to = absorber.name
    spat_abs.input_digi_collection = abs_collection
    spat_abs.blur_attribute = "PostPosition"
    spat_abs.blur_fwhm = [2 * mm, 2 * mm, 2 * mm]
    abs_collection = spat_abs.name

    # Energy blurring
    reference_energy = 511 * keV
    scatt_resolution = 0.085  # FWHM/E at 511 keV
    abs_resolution = 0.125  # FWHM/E at 511 keV

    blur_scatt = sim.add_actor("DigitizerBlurringActor", "BlurScatt")
    blur_scatt.attached_to = scatterer.name
    blur_scatt.input_digi_collection = scatt_collection
    blur_scatt.blur_attribute = "TotalEnergyDeposit"
    blur_scatt.blur_method = "InverseSquare"
    blur_scatt.blur_reference_value = reference_energy
    blur_scatt.blur_resolution = scatt_resolution
    scatt_collection = blur_scatt.name

    blur_abs = sim.add_actor("DigitizerBlurringActor", "BlurAbs")
    blur_abs.attached_to = absorber.name
    blur_abs.input_digi_collection = abs_collection
    blur_abs.blur_attribute = "TotalEnergyDeposit"
    blur_abs.blur_method = "InverseSquare"
    blur_abs.blur_reference_value = reference_energy
    blur_abs.blur_resolution = abs_resolution
    abs_collection = blur_abs.name

    # Time blurring
    time_fwhm = 10 * ns
    time_sigma = time_fwhm / 2.355
    time_scatt = sim.add_actor("DigitizerBlurringActor", "TimeBlurScatt")
    time_scatt.attached_to = scatterer.name
    time_scatt.input_digi_collection = scatt_collection
    time_scatt.blur_attribute = "GlobalTime"
    time_scatt.blur_method = "Gaussian"
    time_scatt.blur_sigma = time_sigma
    scatt_collection = time_scatt.name

    time_abs = sim.add_actor("DigitizerBlurringActor", "TimeBlurAbs")
    time_abs.attached_to = absorber.name
    time_abs.input_digi_collection = abs_collection
    time_abs.blur_attribute = "GlobalTime"
    time_abs.blur_method = "Gaussian"
    time_abs.blur_sigma = time_sigma
    abs_collection = time_abs.name

    # Energy windows (thresholds)
    threshold_min_scatt = 70 * keV
    threshold_min_abs = 70 * keV
    threshold_max = 2.0 * MeV
    thr_scatt = sim.add_actor("DigitizerEnergyWindowsActor", "ThrScatt")
    thr_scatt.attached_to = scatterer.name
    thr_scatt.input_digi_collection = scatt_collection
    thr_scatt.channels = [
        {"name": thr_scatt.name, "min": threshold_min_scatt, "max": threshold_max}
    ]
    scatt_collection = thr_scatt.name

    thr_abs = sim.add_actor("DigitizerEnergyWindowsActor", "ThrAbs")
    thr_abs.attached_to = absorber.name
    thr_abs.input_digi_collection = abs_collection
    thr_abs.channels = [
        {"name": thr_abs.name, "min": threshold_min_abs, "max": threshold_max}
    ]

    # Saving root files
    thr_scatt.output_filename = f"{thr_scatt.name}.root"
    thr_abs.output_filename = f"{thr_abs.name}.root"
    scatt_file = thr_scatt.get_output_path()
    abs_file = thr_abs.get_output_path()

    return scatt_file, abs_file


def macaco1_merge_and_compute_coincidences(
    scatt_root_filename,
    abs_root_filename,
    output_root_filename,
    time_windows,
    scatt_tree_name,
    abs_tree_name,
    merged_tree_name,
):
    """
    Merge scatterer/absorber singles, run the Gate coincidence sorter,
    then filter good coincidences.
    """

    ccmod_merge_several_singles_root_into_one(
        scatt_root_filename,
        abs_root_filename,
        output_root_filename,
        scatt_tree_name=scatt_tree_name,
        abs_tree_name=abs_tree_name,
        output_tree_name=merged_tree_name,
        overwrite=True,
    )

    with uproot.open(output_root_filename) as f:
        singles_tree = f[merged_tree_name]
        coincidences = cc_coincidences_sorter(singles_tree, time_windows)

    if coincidences is None or coincidences.empty:
        return coincidences

    coincidences = kill_multiple_coinc(coincidences)
    coincidences = kill_same_volume_pairs(coincidences)
    return coincidences


def load_exp_histograms(
    path: Path, scatter_name, abs_name
) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    if not path.exists():
        raise FileNotFoundError(f"Experimental data file not found: {path}")
    histograms: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    with uproot.open(path) as f:
        for name in (scatter_name, abs_name):
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
    output_plot_path: Path = None,  # New parameter
):
    centers = 0.5 * (exp_edges[:-1] + exp_edges[1:])
    win_lo, win_hi = peak_window_from_exp(
        centers, exp_counts, expected_energy=expected_energy
    )
    exp_mask = (centers >= win_lo) & (centers <= win_hi)
    exp_counts_win = exp_counts[exp_mask]
    exp_centers_win = centers[exp_mask]

    if exp_counts_win.sum() <= 0.0:
        print(f"✗ {label}: no experimental counts in window", flush=True)
        return False

    sim_counts, _ = np.histogram(sim_energies, bins=exp_edges)
    sim_counts_win = sim_counts[exp_mask]

    mu_exp, sigma_exp = gaussian_fit_hist(exp_centers_win, exp_counts_win)
    mu_sim, sigma_sim = gaussian_fit_hist(exp_centers_win, sim_counts_win)

    # --- Plotting Logic ---
    if output_plot_path:
        plt.figure(figsize=(8, 6))

        # Plot Data
        plt.step(
            exp_centers_win,
            exp_counts_win,
            where="mid",
            label="Exp Data",
            color="black",
            alpha=0.6,
        )
        plt.step(
            exp_centers_win,
            sim_counts_win,
            where="mid",
            label="Sim Data",
            color="blue",
            alpha=0.6,
        )

        # Plot Fits
        x_fit = np.linspace(win_lo, win_hi, 100)
        if not np.isnan(mu_exp):
            y_exp = np.max(exp_counts_win) * np.exp(
                -((x_fit - mu_exp) ** 2) / (2 * sigma_exp**2)
            )
            plt.plot(x_fit, y_exp, "k--", label=f"Exp Fit ($\mu$={mu_exp:.1f})")

        if not np.isnan(mu_sim):
            y_sim = np.max(sim_counts_win) * np.exp(
                -((x_fit - mu_sim) ** 2) / (2 * sigma_sim**2)
            )
            plt.plot(x_fit, y_sim, "b--", label=f"Sim Fit ($\mu$={mu_sim:.1f})")

        plt.title(f"Gaussian Fit Comparison: {label}")
        plt.xlabel("Energy (keV)")
        plt.ylabel("Counts")
        plt.legend()
        plt.grid(True, linestyle=":", alpha=0.7)
        plt.savefig(output_plot_path)
        plt.close()
        print("Figure saved in: ", output_plot_path)
    # ----------------------

    if (
        np.isnan(mu_exp)
        or np.isnan(sigma_exp)
        or np.isnan(mu_sim)
        or np.isnan(sigma_sim)
    ):
        print(f"✗ {label}: Gaussian fit failed", flush=True)
        return False

    # (Keep the rest of your existing logic for validation...)
    mean_pct = 100.0 * abs(mu_sim - mu_exp) / abs(mu_exp)
    sigma_pct = 100.0 * abs(sigma_sim - sigma_exp) / abs(sigma_exp)
    fwhm_pct = (
        100.0 * abs((2.355 * sigma_sim) - (2.355 * sigma_exp)) / abs(2.355 * sigma_exp)
    )
    tol_pct = tol_frac * 100.0

    max_diff = max(mean_pct, sigma_pct, fwhm_pct)
    if mean_pct < tol_pct and sigma_pct < tol_pct and fwhm_pct < tol_pct:
        print(f"✓ {label} pass (max diff={max_diff:.1f}%)", flush=True)
        return True

    print(f"✗ {label} fail (max diff={max_diff:.1f}%)", flush=True)
    return False


# builds the energy window around the expected peak in the experimental histogram.
def peak_window_from_exp(
    centers: np.ndarray,
    counts: np.ndarray,
    expected_energy: float,
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
