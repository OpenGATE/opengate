import opengate as gate
from opengate.contrib.spect.spect_helpers import *
from opengate.actors.biasingactors import distance_dependent_angle_tolerance
from opengate.exception import fatal
from opengate import Simulation, g4_units
from box import Box
import opengate.contrib.spect.ge_discovery_nm670 as nm670
import opengate.contrib.spect.siemens_intevo as intevo
from opengate.image import read_image_info
from opengate.utility import get_basename_and_extension
from opengate.sources.utility import set_source_energy_spectrum
import numpy as np
import matplotlib.pyplot as plt


class SPECTConfig:
    """
    Represents the configuration object for a SPECT simulation.

    This class organizes and manages the configuration details required to set up
    and execute a SPECT (Single Photon Emission Computed Tomography) simulation.

    It includes settings for the simulation output, main configurable elements,
    such as detector, phantom, source, and protocol, as well as simulation
    initialization and execution methods.
    """

    def __init__(self, simu_name="spect"):
        # default
        self.output_folder = "output"
        self.output_basename = "projection.mhd"
        self.sim = None
        self.simu_name = simu_name

        # main elements
        self.detector_config = DetectorConfig(self)
        self.phantom_config = PhantomConfig(self)
        self.source_config = SourceConfig(self)
        self.acquisition_config = AcquisitionConfig(self)
        self.stats = None

    def print(self, str_only=False):
        s = f"SPECT simulation\n"
        s += f"Output folder: {self.output_folder}\n"
        s += f"Output basename: {self.output_basename}\n"
        s += self.detector_config.print(True)
        s += self.phantom_config.print(True)
        s += self.source_config.print(True)
        s += self.acquisition_config.print(True)
        if str_only:
            return s
        print(s)

    def create_simulation(self, number_of_threads=1, visu=False):
        # create a new simulation object each time
        self.sim = Simulation()
        self.initialize_simulation(number_of_threads, visu)

        # init all elements
        self.detector_config.create_simulation()
        self.phantom_config.create_simulation()
        self.source_config.create_simulation()
        self.acquisition_config.create_simulation()

        # return
        return self.sim

    def initialize_simulation(self, number_of_threads, visu):
        # main options
        sim = self.sim
        sim.random_seed = "auto"
        sim.check_volumes_overlap = True
        sim.visu = visu
        sim.visu_type = "qt"
        sim.output_dir = self.output_folder
        sim.progress_bar = True
        sim.store_json_archive = True
        sim.store_input_files = False
        sim.json_archive_filename = "simu.json"

        # thread
        if visu:
            sim.number_of_threads = 1
        else:
            sim.number_of_threads = number_of_threads

        # world
        m = gate.g4_units.m
        sim.world.size = [3 * m, 3 * m, 3 * m]
        sim.world.material = "G4_AIR"

        # physics
        sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option3"
        sim.physics_manager.global_production_cuts.all = 2 * gate.g4_units.mm

        # add stat actor
        stats = sim.add_actor("SimulationStatisticsActor", "stats")
        stats.output_filename = "stats.txt"
        self.stats = stats


class PhantomConfig:
    """
    Used in SPECTConfig. Represents a phantom configuration

    This class is used to configure and handle a phantom in a medical imaging
    simulation context. It includes properties for the phantom image,
    labels, and density tolerance, and provides methods for printing the
    phantom configuration and generating a simulation. The phantom's
    construction and materials are based on Hounsfield Unit (HU) mappings
    to materials defined in external files.

    Attributes:
        spect_config (SpectConfig): The SpectConfig object containing simulation
            setup and parameters.
        image (Optional[any]): The phantom image data used in the simulation,
            initially set to None.
        labels (Optional[any]): Labels associated with the phantom,
            initially set to None.
        density_tol (float): The density tolerance threshold in g/cm^3
            for material mapping, default set to 0.05 * g/cm^3.

    Methods:
        print(str_only: bool = False) -> Optional[str]:
            Prints or returns a string representation of the phantom configuration.
        create_simulation(visu: Optional[any]):
            Creates a voxelized simulation configuration based on the set
            phantom image and materials.
    """

    def __init__(self, spect_config):
        gcm3 = gate.g4_units.g_cm3
        self.spect_config = spect_config
        # user param
        self.image = None
        self.labels = None
        self.material_db = None
        self.density_tol = 0.05 * gcm3
        self.phantom = None

    def print(self, str_only=False):
        s = f"Phantom image: {self.image}\n"
        s += f"Phantom labels: {self.labels}\n"
        if str_only:
            return s
        print(s)

    def create_simulation(self):
        sim = self.spect_config.sim
        # can be: nothing or voxelized
        if self.image is None:
            return
        # special case for visu
        if sim.visu is True:
            return self.add_fake_phantom_for_visu()
        # insert voxelized phantom
        phantom = sim.add_volume("Image", f"{self.spect_config.simu_name}_phantom")
        phantom.image = self.image
        phantom.material = "G4_AIR"
        if self.material_db is not None:
            sim.volume_manager.add_material_database(self.material_db)
        if self.labels is not None:
            phantom.read_label_to_material(self.labels)
        else:
            f1 = gate.utility.get_data_folder() / "Schneider2000MaterialsTable.txt"
            f2 = gate.utility.get_data_folder() / "Schneider2000DensitiesTable.txt"
            vm, materials = gate.geometry.materials.HounsfieldUnit_to_material(
                sim, self.density_tol, f1, f2
            )
            phantom.voxel_materials = vm
        self.phantom = phantom

    def add_fake_phantom_for_visu(self):
        sim = self.spect_config.sim
        img_info = read_image_info(self.image)
        phantom = sim.add_volume("Box", f"{self.spect_config.simu_name}_phantom")
        phantom.material = "G4_WATER"
        phantom.size = img_info.size * img_info.spacing
        self.phantom = phantom


class DetectorConfig:
    """
    Used in SPECTConfig. Represents the configuration for a SPECT detector.

    Manage: detector models, crystals, collimators, digitizers,
    and the number of detector heads.
    """

    def __init__(self, spect_config):
        self.spect_config = spect_config
        # spect models
        self.available_models = ("intevo", "nm670")
        # built objects
        self.detectors = []
        self.digitizers = []
        self.crystals = []
        # user param
        self.model = None
        self.collimator = None
        self.digitizer = None
        self.number_of_heads = 2
        self.garf = GARFConfig(spect_config)

    def print(self, str_only=False):
        s = f"Detector model: {self.model}\n"
        s += f"Detector collimator: {self.collimator}\n"
        s += f"Detector digitizer: {self.digitizer}\n"
        s += f"Detector # of heads: {self.number_of_heads}\n"
        if str_only:
            return s
        print(s)

    def get_model_module(self):
        m = None
        if self.model == "nm670":
            m = nm670
        if self.model == "intevo":
            m = intevo
        # FIXME veriton
        return m

    def get_detector_normal(self):
        if self.model == "nm670":
            return [0, 0, -1]
        if self.model == "intevo":
            return [1, 0, 0]
        fatal(f"Unknown detector model: {self.model}")

    def get_proj_filename(self, i):
        filename, ext = get_basename_and_extension(self.spect_config.output_basename)
        f = f"{filename}_{i}{ext}"
        return f

    def create_simulation(self):
        if self.model not in self.available_models:
            fatal(
                f'The model "{self.model}" is unknown. '
                f"Known models are: {self.available_models}"
            )

        self.detectors = []
        self.crystals = []
        self.digitizers = []
        m = self.get_model_module()
        sim = self.spect_config.sim

        # GARF ?
        if self.garf.is_enabled():
            return self.garf.create_simulation(sim, m)

        # or real SPECT volumes
        for i in range(self.number_of_heads):
            det, colli, crystal = m.add_spect_head(
                sim,
                f"{self.spect_config.simu_name}_spect{i}",
                collimator_type=self.collimator,
                debug=sim.visu == True,
            )
            self.detectors.append(det)
            self.crystals.append(crystal)
            # set the digitizer
            if self.digitizer is not None:
                proj = self.digitizer(
                    sim, crystal.name, f"{self.spect_config.simu_name}_digit{i}"
                )
                proj.output_filename = self.get_proj_filename(i)
                self.digitizers.append(proj)


class GARFConfig:
    """
    Used in DetectorConfig.
    Configuration class for GARF detector.
    """

    def __init__(self, spect_config):
        self.spect_config = spect_config
        # options
        mm = gate.g4_units.mm
        self.spacing = [
            4.7951998710632 * mm / 2,
            4.7951998710632 * mm / 2,
        ]  # FIXME intevo
        self.size = [128 * 2, 128 * 2]
        self.pth_filename = None
        self.batch_size = 1e5
        self.verbose_batch = True
        self.gpu_mode = "auto"
        # built objects
        self.detectors = []
        self.garf_actors = []

    def print(self, str_only=False):
        s = f"GARF : {self.pth_filename}\n"
        s += f"GARF image size: {self.size}\n"
        s += f"GARF image spacing: {self.spacing}\n"
        s += f"GARF batch size: {self.batch_size}\n"
        if str_only:
            return s
        print(s)

    def is_enabled(self):
        return self.pth_filename is not None

    def create_simulation(self, sim, m):
        colli = self.spect_config.detector_config.collimator
        for i in range(self.spect_config.detector_config.number_of_heads):
            # create the plane
            det_plane = m.add_detection_plane_for_arf(
                sim, f"{self.spect_config.simu_name}_det{i}", colli
            )
            self.spect_config.detector_config.detectors.append(det_plane)

            # set the position in front of the collimator
            _, crystal_distance, _ = m.compute_plane_position_and_distance_to_crystal(
                colli
            )
            # rotate_gantry(det_plane, radius=0, start_angle_deg=0) # FIXME later

            # output filename
            arf = sim.add_actor(
                "ARFActor", f"{self.spect_config.simu_name}_{det_plane.name}_arf"
            )
            arf.attached_to = det_plane.name
            arf.output_filename = self.spect_config.detector_config.get_proj_filename(i)
            arf.batch_size = 1e5
            arf.image_size = self.size
            arf.image_spacing = self.spacing
            arf.verbose_batch = False
            arf.distance_to_crystal = crystal_distance  # 74.625 * mm
            arf.pth_filename = self.pth_filename
            arf.gpu_mode = "auto"

            # specific to each SPECT model
            if self.spect_config.detector_config.model == "intevo":
                arf.flip_plane = False
                arf.plane_axis = [1, 2, 0]
            if self.spect_config.detector_config.model == "nm670":
                fatal(f"TODO")


class SourceConfig:
    """
    Used in SPECTConfig. Represents a configuration for an activity source.

    This class is used to define and manage the settings of an activity source,
    such as the source image, radionuclide, and total activity.
    """

    def __init__(self, spect_config):
        self.spect_config = spect_config
        # user param
        self.image = None
        self.radionuclide = None
        self.total_activity = 0
        self.source = None
        # self.gaga = GAGAConfig(spect_config) # FIXME todo

    def print(self, str_only=False):
        s = f"Activity source image: {self.image}\n"
        s = f"Activity source radionuclide: {self.radionuclide}\n"
        s = f"Activity source: {self.total_activity/gate.g4_units.Bq} Bq\n"
        if str_only:
            return s
        print(s)

    def create_simulation(self):
        # can be: nothing / voxelized / gaga
        if self.image is None:
            return
        if self.radionuclide is None:
            fatal(f"Radionuclide is None, please set a radionuclide (eg. 'lu177')")

        # FIXME gaga tests

        sim = self.spect_config.sim
        source = sim.add_source("VoxelSource", f"{self.spect_config.simu_name}_source")
        source.image = self.image
        set_source_energy_spectrum(source, self.radionuclide)
        source.particle = "gamma"
        source.activity = self.total_activity
        if sim.visu is True:
            source.activity = 10 * gate.g4_units.Bq

        self.source = source
        return source


class AcquisitionConfig:
    """
    Used in SPECTConfig. A configuration class for acquisition settings specific to a simulation.

    This class provides configuration parameters and functionality for managing
    acquisition settings in SPECT simulations. It allows specifying parameters
    such as acquisition duration, radius, and number of angles.
    """

    def __init__(self, spect_config):
        self.spect_config = spect_config
        # user param
        self.duration = 1 * gate.g4_units.s
        self.radius = None
        # self.angles = None
        self.number_of_angles = 1
        # internal var
        self.available_starting_head_angles = {
            "1": [0.0],
            "2": [0.0, 180.0],
            "3": [0.0, 120.0, 240.0],
            "4": [0.0, 90.0, 180.0, 270.0],
            # FIXME later for Veriton
        }

    def print(self, str_only=False):
        s = f"Acquisition duration: {self.duration/g4_units.s} sec\n"
        s += f"Acquisition radius: {self.radius/g4_units.mm} mm\n"
        s += f"Acquisition # angles: {self.number_of_angles}\n"
        if str_only:
            return s
        print(s)

    def create_simulation(self):
        # get number of heads and starting angles
        nb = str(self.spect_config.detector_config.number_of_heads)
        if nb not in self.available_starting_head_angles:
            fatal(f"The number of heads must be 1 to 4")
        head_angles = self.available_starting_head_angles[nb]

        # get the rotation angles
        # if self.number_of_angles is None and self.angles is None:
        #    fatal(f"You should provide either number_of_angles or angles")

        # set the rotation angles (runs)
        step_time = self.duration / self.number_of_angles
        sim = self.spect_config.sim
        sim.run_timing_intervals = [
            [i * step_time, (i + 1) * step_time] for i in range(self.number_of_angles)
        ]

        # compute the gantry rotations
        step_angle = head_angles[1] / self.number_of_angles
        d = self.spect_config.detector_config
        m = d.get_model_module()
        i = 0
        for sa in head_angles:
            m.rotate_gantry(
                d.detectors[i], self.radius, sa, step_angle, self.number_of_angles
            )
            i += 1


def spect_freeflight_run(sc, options):

    # prepare output dict
    output = Box()
    out = sc.output_folder.resolve()
    output.options = options

    # run 1 = primary
    sim = sc.create_simulation(number_of_threads=options.number_of_threads, visu=False)
    source = sc.source_config.source
    sim.output_dir = f"{sim.output_dir}/freeflight_primary"
    spect_freeflight_initialize_primary(sim, sc, options)
    sim.run(start_new_process=True)

    # store some output information
    output.nb_detectors = len(sc.detector_config.detectors)
    output.prim = Box()
    output.prim.stats = sc.stats.stats.merged_data
    output.prim.activity = source.activity / g4_units.Bq * sim.number_of_threads
    output.prim.proj_paths = [
        str(d.get_output_path("counts").relative_to(out))
        for d in sc.detector_config.digitizers
    ]
    output.prim.squared_proj_paths = [
        str(d.get_output_path("squared_counts").relative_to(out))
        for d in sc.detector_config.digitizers
    ]
    print(sc.stats)

    # run 2 = scatter
    print()
    print()
    print()
    sim = sc.create_simulation(number_of_threads=options.number_of_threads, visu=False)
    source = sc.source_config.source
    sim.output_dir = f"{sim.output_dir}/freeflight_scatter"
    ff = spect_freeflight_initialize_scatter(sim, sc, options)
    sim.run(start_new_process=True)

    # store some output information
    output.scatter = Box()
    output.scatter.stats = sc.stats.stats.merged_data
    output.scatter.activity = source.activity / g4_units.Bq * sim.number_of_threads
    output.scatter.proj_paths = [
        str(d.get_output_path("counts").relative_to(out))
        for d in sc.detector_config.digitizers
    ]
    output.scatter.squared_proj_paths = [
        str(d.get_output_path("squared_counts").relative_to(out))
        for d in sc.detector_config.digitizers
    ]
    print(sc.stats)
    print(ff)

    return output


def spect_freeflight_initialize(sim):
    # Weights MUST be in the digitizer
    hits_actors = sim.actor_manager.find_actors("hits")
    for ha in hits_actors:
        if "Weight" not in ha.attributes:
            ha.attributes.append("Weight")

    # GeneralProcess must *NOT* be used
    s = f"/process/em/UseGeneralProcess false"
    sim.g4_commands_before_init.append(s)


def spect_freeflight_initialize_primary(sim, sc, options):
    spect_freeflight_initialize(sim)
    options = Box(options)

    # get some information from spect config
    source = sc.source_config.source
    digitizers = sc.detector_config.digitizers
    crystal_names = [c.name for c in sc.detector_config.crystals]

    # add the ff actor
    n = sc.detector_config.get_detector_normal()
    ff = sim.add_actor("GammaFreeFlightActor", f"{sc.simu_name}_ff")
    ff.attached_to = "world"
    ff.ignored_volumes = crystal_names
    source.direction.acceptance_angle.intersection_flag = True
    source.direction.acceptance_angle.volumes = crystal_names
    source.direction.acceptance_angle.normal_flag = True
    source.direction.acceptance_angle.normal_vector = n
    source.direction.acceptance_angle.normal_tolerance = options.angle_tolerance
    source.direction.acceptance_angle.distance_dependent_normal_tolerance = False
    source.direction.acceptance_angle.normal_tolerance_min_distance = (
        options.angle_tolerance_min_distance
    )

    for d in digitizers:
        d.squared_counts.active = True
    source.activity = options.primary_activity

    return ff


def spect_freeflight_initialize_scatter(sim, sc, options):
    spect_freeflight_initialize(sim)
    options = Box(options)

    # get some information from spect config
    source = sc.source_config.source
    digitizers = sc.detector_config.digitizers
    crystal_names = [c.name for c in sc.detector_config.crystals]
    source.direction.acceptance_angle.intersection_flag = False
    source.direction.acceptance_angle.normal_flag = False

    # run 1 = primary
    n = sc.detector_config.get_detector_normal()
    ff = sim.add_actor("ScatterSplittingFreeFlightActor", f"{sc.simu_name}_ff")
    ff.attached_to = "world"
    ff.ignored_volumes = crystal_names
    ff.compton_splitting_factor = options.compton_splitting_factor
    ff.rayleigh_splitting_factor = options.rayleigh_splitting_factor
    ff.max_compton_level = options.max_compton_level
    ff.acceptance_angle.intersection_flag = True
    ff.acceptance_angle.volumes = crystal_names
    ff.acceptance_angle.normal_flag = True
    ff.acceptance_angle.normal_vector = n
    source.direction.acceptance_angle.normal_tolerance = options.angle_tolerance
    source.direction.acceptance_angle.normal_tolerance_min_distance = (
        options.angle_tolerance_min_distance
    )
    """ REMOVED because too slow
    ff.acceptance_angle.distance_dependent_normal_tolerance = True
    tol = options.scatter_angle_tolerance
    ff.acceptance_angle.distance1 = tol[0]
    ff.acceptance_angle.angle1 = tol[1]
    ff.acceptance_angle.distance2 = tol[2]
    ff.acceptance_angle.angle2 = tol[3]
    """

    for d in digitizers:
        d.squared_counts.active = True
    source.activity = options.scatter_activity

    return ff


def spect_freeflight_merge(output_data, output_folder, n_target):
    output_data = Box(output_data)
    nd = output_data.nb_detectors
    n_prim = output_data.prim.activity
    n_scatter = output_data.scatter.activity

    for i in range(nd):
        # primary
        img = output_folder / output_data["prim"]["proj_paths"][i]
        sq_img = output_folder / output_data["prim"]["squared_proj_paths"][i]
        out = img.parent / f"relative_uncertainty_primary_{i}.mhd"
        print(img, out)
        _, prim, prim_squared = history_rel_uncertainty_from_files(
            img, sq_img, n_prim, out
        )
        # scatter
        img = output_folder / output_data["scatter"]["proj_paths"][i]
        sq_img = output_folder / output_data["scatter"]["squared_proj_paths"][i]
        out = img.parent / f"relative_uncertainty_scatter_{i}.mhd"
        print(img, out)
        _, scatter, scatter_squared = history_rel_uncertainty_from_files(
            img, sq_img, n_scatter, out
        )
        # combined
        uncert, mean = history_ff_combined_rel_uncertainty(
            prim, prim_squared, scatter, scatter_squared, n_prim, n_scatter
        )
        scaling = n_target / n_prim
        mean = mean * scaling
        print(f"Primary n = {n_prim}  Scatter n = {n_scatter}  Target n = {n_target}")
        print(f"Primary to scatter ratio = {n_prim / n_scatter:.01f}")
        print(f"Scaling to target        = {scaling:.01f}")

        # write combined image
        prim_img = sitk.ReadImage(img)
        img = sitk.GetImageFromArray(mean)
        img.CopyInformation(prim_img)
        fn = output_folder / f"mean_{i}.mhd"
        sitk.WriteImage(img, fn)
        print(fn)

        # write combined relative uncertainty
        img = sitk.GetImageFromArray(uncert)
        img.CopyInformation(prim_img)
        fn = output_folder / f"relative_uncertainty_{i}.mhd"
        sitk.WriteImage(img, fn)
        print(fn)


def plot_ddaa(acceptance_angle, output_filename=None):
    # plot dd
    a1 = acceptance_angle.angle1
    a2 = acceptance_angle.angle2
    d1 = acceptance_angle.distance1
    d2 = acceptance_angle.distance2
    distances = np.linspace(d1 / 2, d2 * 2, 200)
    angles = [distance_dependent_angle_tolerance(a1, a2, d1, d2, d) for d in distances]

    cm = g4_units.cm
    plt.figure(figsize=(8, 6))
    plt.plot(distances / cm, np.degrees(angles), label="Distance vs Angle")
    plt.xlabel("Distance (cm)")
    plt.ylabel("Angle (degrees)")
    plt.title("Distance vs Angle Tolerance")
    plt.grid()
    plt.legend()
    # plt.show()
    if output_filename is not None:
        plt.savefig(output_filename)
    return plt
