from opengate.contrib.spect.spect_config import SPECTConfig
from opengate import g4_units


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
