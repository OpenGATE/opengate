import SimpleITK as sitk
from opengate.contrib.spect.spect_config import SPECTConfig
from opengate import g4_units
import opengate.contrib.phantoms.nemaiec as nemaiec
from opengate.tests import utility


def define_spect_config(data_path, visu, n_primary):
    number_of_threads = 8

    # units
    sec = g4_units.s
    mm = g4_units.mm
    Bq = g4_units.Bq

    # Init SPECT simulation (no phantom)
    sc = SPECTConfig()
    sc.output_folder = data_path / f"tomo_4.8mm_2e7"
    sc.number_of_threads = number_of_threads
    sc.detector_config.model = "intevo"
    sc.detector_config.collimator = "melp"
    sc.detector_config.number_of_heads = 2
    sc.detector_config.size = [128, 128]
    sc.detector_config.spacing = [4.8 * mm, 4.8 * mm]

    sc.phantom_config.image = data_path / f"iec_4.8mm.mhd"
    sc.phantom_config.labels = data_path / f"iec_4.8mm_labels.json"
    sc.phantom_config.material_db = data_path / f"iec_4.8mm.db"

    sc.source_config.image = data_path / f"iec_activity_1mm.mhd"
    sc.source_config.radionuclide = "177lu"
    sc.source_config.total_activity = n_primary * Bq

    sc.acquisition_config.duration = 15 * sec
    sc.acquisition_config.radius = 250 * mm
    sc.acquisition_config.number_of_angles = 60  # per head, so 120 in total

    # special case for visualization to avoid overwriting previous results
    if visu:
        sc.output_folder = data_path / "visu"

    return sc


def setup_primary_simulation(sc, sim, visu):
    deg = g4_units.deg
    sc.free_flight_config.mode = "primary"
    sc.free_flight_config.angular_acceptance.policy = "ForceDirection"
    sc.free_flight_config.angular_acceptance.angle_tolerance_max = 8 * deg
    sc.free_flight_config.angular_acceptance.angle_tolerance_min = 0
    sc.free_flight_config.angular_acceptance.enable_angle_check = True
    sc.free_flight_config.angular_acceptance.enable_intersection_check = True

    sc.setup_simulation(sim, visu=visu)


def setup_scatter_simulation(sc, sim, visu):
    deg = g4_units.deg
    cm = g4_units.cm
    sc.free_flight_config.mode = "scatter"
    sc.free_flight_config.angular_acceptance.policy = "Rejection"
    sc.free_flight_config.angular_acceptance.skip_policy = "SkipEvents"
    sc.free_flight_config.angular_acceptance.angle_check_proximity_distance = 6 * cm
    sc.free_flight_config.angular_acceptance.angle_tolerance_proximal = 90 * deg
    sc.free_flight_config.angular_acceptance.angle_tolerance_max = 8 * deg
    sc.free_flight_config.angular_acceptance.angle_tolerance_min = 0
    sc.free_flight_config.angular_acceptance.enable_angle_check = True
    sc.free_flight_config.angular_acceptance.enable_intersection_check = True
    sc.free_flight_config.compton_splitting_factor = 300
    sc.free_flight_config.rayleigh_splitting_factor = 300
    sc.free_flight_config.max_compton_level = 5

    sc.setup_simulation(sim, visu=visu)


def analyse_test094(ref_mask_img, ref_activity, recon_img_path, output_path):
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

    recon_img = sitk.ReadImage(recon_img_path)
    m = nemaiec.check_centroid_alignment(labeled_mask, recon_img, dilate_mm=0)
    b = m < 0.4
    utility.print_test(b, f"Compare centroid distance is {m}")
    if not b:
        nemaiec.plot_sphere_panels(labeled_mask, recon_img, recon_img, margin_mm=20)

    metrics = nemaiec.compute_iec_nema_metrics(
        ref_activity, labeled_mask, bg_mask_obj, recon_img
    )

    fn = output_path / f"rc.pdf"
    nemaiec.plot_iec_rc_curves(labeled_mask, [metrics], labels=["Recon"], fig_path=fn)
    print(f"\nSaved NEMA RC curves to {fn}")

    return b
