import opengate as gate
from opengate.contrib.spect.spect_helpers import *
from opengate.actors.biasingactors import distance_dependent_angle_tolerance
from opengate.exception import fatal
from opengate import g4_units
import opengate.contrib.spect.ge_discovery_nm670 as nm670
import opengate.contrib.spect.siemens_intevo as intevo
from opengate.image import read_image_info
from opengate.utility import get_basename_and_extension
from opengate.sources.utility import set_source_energy_spectrum
import numpy as np
import matplotlib.pyplot as plt
import os
import json
from pathlib import Path


class SPECTConfig:
    """
    Represents the configuration object for a SPECT simulation.

    This class organises and manages the configuration details required to set up
    and execute a SPECT (Single Photon Emission Computed Tomography) simulation.

    It includes settings for the simulation output, main configurable elements,
    such as detector, phantom, source, and protocol, as well as simulation
    initialisation and execution methods.
    """

    def __init__(self, simu_name="spect"):
        # default
        self.output_folder = Path("output")
        self.output_basename = "projection.mhd"
        self.simu_name = simu_name
        self.number_of_threads = 1

        # only used if ff
        self.output_folder_primary = None
        self.output_folder_scatter = None

        # main elements
        self.detector_config = DetectorConfig(self)
        self.phantom_config = PhantomConfig(self)
        self.source_config = SourceConfig(self)
        self.acquisition_config = AcquisitionConfig(self)
        self.free_flight_config = FreeFlightConfig(self)

    def __str__(self):
        s = f"SPECT simulation\n"
        s += f"Output folder: {self.output_folder}\n"
        s += f"Output basename: {self.output_basename}\n"
        s += f"Nb of threads: {self.number_of_threads}\n"
        s += f"{self.detector_config}\n"
        s += f"{self.phantom_config}\n"
        s += f"{self.source_config}\n"
        s += f"{self.acquisition_config}"
        # do not print ff, only on demand.
        # s += f"{self.free_flight_config}\n"
        return s

    def setup_simulation(self, sim, visu=False):
        # create the output folder if not exist
        os.makedirs(self.output_folder, exist_ok=True)
        # default initialization
        self.initialize_simulation(sim, visu)
        # init all elements
        self.detector_config.setup_simulation(sim)
        phantom = self.phantom_config.setup_simulation(sim)
        self.source_config.setup_simulation(sim, phantom)
        self.acquisition_config.setup_simulation(sim, self.detector_config.head_names)

    def setup_simulation_ff_primary(self, sim, sources=None, visu=False):
        # we temporarily change the output folder
        save_folder = Path(self.output_folder)
        self.output_folder_primary = save_folder / "primary"
        self.output_folder = self.output_folder_primary
        # set the initial simulation
        self.setup_simulation(sim, visu)
        # but keep the initial folder for further use of config
        self.output_folder = save_folder
        if sources is None:
            n = f"{self.simu_name}_source"
            source = sim.source_manager.get_source(n)
            sources = [source]
        for source in sources:
            self.free_flight_config.setup_simulation_primary(sim, source)
        self.dump_ff_info_primary()

    def setup_simulation_ff_scatter(self, sim, sources=None, visu=False):
        # because primary was probably config/run before we clean the
        # static variables from G4 to avoid issues.
        g4.GateGammaFreeFlightOptrActor.ClearOperators()
        # we temporarily change the output folder
        save_folder = Path(self.output_folder)
        self.output_folder_scatter = save_folder / "scatter"
        self.output_folder = self.output_folder_scatter
        # set the initial simulation
        self.setup_simulation(sim, visu)
        # but keep the initial folder for further use of config
        self.output_folder = save_folder
        if sources is None:
            name = f"{self.simu_name}_source"
            source = sim.source_manager.get_source(name)  # FIXME
            sources = [source]
        for source in sources:
            self.free_flight_config.setup_simulation_scatter(sim, source)
        self.dump_ff_info_scatter()

    def dump_ff_info_primary(self, filename="ff_info.json"):
        n = {
            "primary_activity": self.free_flight_config.primary_activity / g4_units.Bq,
            "angle_tolerance": self.free_flight_config.angle_tolerance / g4_units.deg,
        }
        fn = self.output_folder_primary / filename
        with open(fn, "w") as f:
            json.dump(n, f, indent=4)

    def dump_ff_info_scatter(self, filename="ff_info.json"):
        n = {
            "scatter_activity": self.free_flight_config.scatter_activity / g4_units.Bq,
            "angle_tolerance": self.free_flight_config.angle_tolerance / g4_units.deg,
            "max_compton_level": self.free_flight_config.max_compton_level,
            "compton_splitting_factor": self.free_flight_config.compton_splitting_factor,
            "rayleigh_splitting_factor": self.free_flight_config.rayleigh_splitting_factor,
        }
        fn = self.output_folder_scatter / filename
        with open(fn, "w") as f:
            json.dump(n, f, indent=4)

    def initialize_simulation(self, sim, visu):
        # main options
        sim.random_seed = "auto"
        sim.check_volumes_overlap = True
        sim.visu = visu
        sim.visu_type = "qt"
        sim.output_dir = self.output_folder
        sim.progress_bar = True
        sim.store_json_archive = True
        sim.store_input_files = False
        sim.json_archive_filename = f"simulation.json"

        # threads
        if visu:
            self.number_of_threads = 1
        sim.number_of_threads = self.number_of_threads

        # world
        m = gate.g4_units.m
        sim.world.size = [3 * m, 3 * m, 3 * m]
        sim.world.material = "G4_AIR"

        # physics
        sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option3"
        sim.physics_manager.global_production_cuts.all = 2 * gate.g4_units.mm

        # add the "stats" actor
        stats = sim.add_actor("SimulationStatisticsActor", "stats")
        stats.output_filename = "stats.txt"


class PhantomConfig:
    """
    This class is used in SPECTConfig. Represents a phantom configuration

    This class is used to configure and handle a phantom in a medical imaging
    simulation context. It includes properties for the phantom image,
    labels, density tolerance, and provides methods for printing the
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
        self.translation = None

    def __str__(self):
        s = f"Phantom image: {self.image}\n"
        s += f"Phantom labels: {self.labels}"
        return s

    def setup_simulation(self, sim):
        # can be: nothing or voxelized
        if self.image is None:
            return
        # special case for visu
        if sim.visu is True:
            phantom = self.add_fake_phantom_for_visu(sim)
            if self.translation is not None:
                phantom.translation = self.translation
            return phantom
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

        # translation ?
        if self.translation is not None:
            phantom.translation = self.translation

        return phantom

    def add_fake_phantom_for_visu(self, sim):
        gate.exception.warning(f"FAKE voxelized phantom for visu: {self.image}")
        img_info = read_image_info(self.image)
        phantom = sim.add_volume("Box", f"{self.spect_config.simu_name}_phantom")
        phantom.material = "G4_WATER"
        phantom.size = img_info.size * img_info.spacing
        return phantom


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
        # user param
        self.model = None
        self.collimator = None
        self.digitizer_function = None
        self.digitizer_channels = None
        self.number_of_heads = 2
        self.size = None
        self.spacing = None
        # computed (not user-defined)
        self.head_names = []
        self.proj_names = []
        # fix later
        self.garf = GARFConfig(spect_config)

    def __str__(self):
        s = f"Detector model: {self.model}\n"
        s += f"Detector collimator: {self.collimator}\n"
        s += f"Detector digitizer: {self.digitizer_function}\n"
        s += f"Detector # of heads: {self.number_of_heads}"
        return s

    def get_model_module(self):
        m = None
        if self.model == "nm670":
            m = nm670
        if self.model == "intevo":
            m = intevo
        # FIXME veriton
        if m is None:
            fatal(
                f'Unknown detector model: "{self.model}", available models: {self.available_models}'
            )
        return m

    def get_heads(self, sim):
        # only set after initialisation
        detectors = [sim.volume_manager.get_volume(name) for name in self.head_names]
        return detectors

    def get_detector_normal(self):
        if self.model == "nm670":
            return [0, 0, -1]
        if self.model == "intevo":
            return [1, 0, 0]
        fatal(f"Unknown detector model: {self.model}")
        return None

    def get_proj_actors(self, sim):
        # only set after initialisation
        projs = [sim.actor_manager.get_actor(name) for name in self.proj_names]
        return projs

    def get_proj_base_filename(self, i):
        filename, ext = get_basename_and_extension(self.spect_config.output_basename)
        f = f"{filename}_{i}{ext}"
        return f

    def get_proj_filenames(self, sim):
        projs = self.get_proj_actors(sim)
        filenames = [
            self.spect_config.output_folder / proj.get_output_path("counts").name
            for proj in projs
        ]
        return filenames

    def setup_simulation(self, sim):
        if self.model not in self.available_models:
            fatal(
                f'The model "{self.model}" is unknown. '
                f"Known models are: {self.available_models}"
            )

        # GARF ?
        if self.garf.is_enabled():
            fatal(f"Not implemented yet")
            self.garf.create_simulation(sim)  # FIXME
            return

        # digitizer_function (with updated size if needed)
        func = self.digitizer_function
        if self.size is not None:
            if self.spacing is not None:
                # modify the digitizer to change the size/spacing
                def fdigit_with_size(sim, crystal_name, name, spectrum_channel=False):
                    self.digitizer_function(sim, crystal_name, name, spectrum_channel)
                    proj = sim.actor_manager.find_actor_by_type(
                        "DigitizerProjectionActor", name
                    )
                    proj.size = self.size
                    proj.spacing = self.spacing

                func = fdigit_with_size

        # create the SPECT detector
        m = self.get_model_module()
        simu_name = self.spect_config.simu_name
        for i in range(self.number_of_heads):
            hn = f"{simu_name}_spect{i}"
            self.head_names.append(hn)
            det, colli, crystal = m.add_spect_head(
                sim,
                hn,
                collimator_type=self.collimator,
                debug=sim.visu == True,
            )

            # set the digitizer
            if func is not None:
                dname = f"{simu_name}_digit{i}"
                func(sim, crystal.name, dname)
                proj = sim.actor_manager.find_actor_by_type(
                    "DigitizerProjectionActor", dname
                )
                proj.output_filename = self.get_proj_base_filename(i)
                self.proj_names.append(proj.name)

                # set the energy window channels if needed
                if self.digitizer_channels is not None:
                    ew = sim.actor_manager.find_actor_by_type(
                        "DigitizerEnergyWindowsActor", dname
                    )
                    ew.channels = self.digitizer_channels
                    channel_names = [c["name"] for c in ew.channels]
                    proj.input_digi_collections = channel_names


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

    def __str__(self):
        s = f"GARF : {self.pth_filename}\n"
        s += f"GARF image size: {self.size}\n"
        s += f"GARF image spacing: {self.spacing}\n"
        s += f"GARF batch size: {self.batch_size}"
        return s

    def is_enabled(self):
        return self.pth_filename is not None

    def create_simulation(self, sim, output):
        fatal("TODO")
        m = self.spect_config.get_model_module()
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
            arf.output_filename = (
                self.spect_config.detector_config.get_proj_base_filename(i)
            )
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
        self.total_activity = 1 * g4_units.Bq
        # self.gaga = GAGAConfig(spect_config) # FIXME todo

    def __str__(self):
        s = f"Activity source image: {self.image}\n"
        s += f"Activity source radionuclide: {self.radionuclide}\n"
        s += f"Activity source: {self.total_activity / gate.g4_units.Bq} Bq"
        return s

    def setup_simulation(self, sim, phantom):
        # can be: nothing or voxelized or gaga (later)
        if self.image is None:
            return
        if self.radionuclide is None:
            fatal(f"Radionuclide is None, please set a radionuclide (eg. 'lu177')")

        # set the source
        source = sim.add_source("VoxelSource", f"{self.spect_config.simu_name}_source")
        source.attached_to = phantom
        source.image = str(self.image)
        # mode voxelized source according to voxelized phantom
        if self.spect_config.phantom_config.image is not None:
            source.position.translation = (
                gate.image.get_translation_between_images_center(
                    self.spect_config.phantom_config.image, source.image
                )
            )
        set_source_energy_spectrum(source, self.radionuclide)
        source.particle = "gamma"
        source.activity = self.total_activity / self.spect_config.number_of_threads
        if sim.visu is True:
            source.activity = 10 * gate.g4_units.Bq


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

    def __str__(self):
        s = f"Acquisition duration: {self.duration / g4_units.s} sec\n"
        s += f"Acquisition radius: {self.radius / g4_units.mm} mm\n"
        s += f"Acquisition # angles: {self.number_of_angles}"
        return s

    def setup_simulation(self, sim, detector_names):
        # get the number of heads and starting angles
        nb = str(self.spect_config.detector_config.number_of_heads)
        if nb not in self.available_starting_head_angles:
            fatal(f"The number of heads must in {self.available_starting_head_angles}")
        starting_head_angles = self.available_starting_head_angles[nb]

        # set the rotation angles (runs)
        step_time = self.duration / self.number_of_angles
        sim.run_timing_intervals = [
            [i * step_time, (i + 1) * step_time] for i in range(self.number_of_angles)
        ]

        # get the detectors
        detectors = [sim.volume_manager.get_volume(n) for n in detector_names]

        # compute the gantry rotations
        step_angle = 360.0 / len(starting_head_angles) / self.number_of_angles
        m = self.spect_config.detector_config.get_model_module()
        i = 0
        for sa in starting_head_angles:
            m.rotate_gantry(
                detectors[i], self.radius, sa, step_angle, self.number_of_angles
            )
            i += 1


class FreeFlightConfig:

    def __init__(self, spect_config):
        self.spect_config = spect_config
        # user param
        self.angle_tolerance = 15 * g4_units.deg
        self.forced_direction_flag = True
        self.angle_tolerance_min_distance = 6 * g4_units.cm
        self.max_compton_level = 5
        self.compton_splitting_factor = 50
        self.rayleigh_splitting_factor = 50
        self.minimal_weight = 1e-100
        self.primary_activity = 1 * g4_units.Bq
        self.scatter_activity = 1 * g4_units.Bq
        self.max_rejection = None
        # keep volume names
        self.volume_names = None

    def __str__(self):
        s = f"FreeFlight FD: {self.forced_direction_flag}\n"
        s += f"FreeFlight angle tol: {self.angle_tolerance / g4_units.deg} deg\n"
        s += f"FreeFlight angle tol min dist: {self.angle_tolerance_min_distance / g4_units.mm} mm\n"
        s += f"FreeFlight max_compton_level: {self.max_compton_level}\n"
        s += f"FreeFlight compton_splitting_factor: {self.compton_splitting_factor}\n"
        s += f"FreeFlight rayleigh_splitting_factor: {self.rayleigh_splitting_factor}\n"
        s += f"FreeFlight minimal_weight: {self.minimal_weight}\n"
        s += f"FreeFlight primary_activity: {self.primary_activity / g4_units.Bq} Bq\n"
        s += f"FreeFlight scatter_activity: {self.scatter_activity / g4_units.Bq} Bq\n"
        return s

    def initialize(self, sim):
        # Weights MUST be in the digitizer
        hits_actors = sim.actor_manager.find_actors("hits")
        if len(hits_actors) == 0:
            fatal(
                f'Cannot find actors with name "hits". Actors:'
                f"{sim.actor_manager.actors}"
            )
        for ha in hits_actors:
            if "Weight" not in ha.attributes:
                ha.attributes.append("Weight")

        # be sure the squared counts flag is enabled
        proj_actors = sim.actor_manager.find_actors("projection")
        if len(proj_actors) == 0:
            fatal(
                f"Cannot find the 'projection' digitizers. Actors:"
                f"{sim.actor_manager.actors}"
            )

        for d in proj_actors:
            d.squared_counts.active = True

        # GeneralProcess must *NOT* be used
        s = f"/process/em/UseGeneralProcess false"
        if s not in sim.g4_commands_before_init:
            sim.g4_commands_before_init.append(s)

    def setup_simulation_primary(self, sim, source):
        self.initialize(sim)

        # consider the volume to *not* apply ff
        if self.volume_names is None:
            crystals = sim.volume_manager.find_volumes("crystal")
            crystal_names = [c.name for c in crystals]
            self.volume_names = crystal_names

        # add the ff actor (only once !)
        ff_name = f"{self.spect_config.simu_name}_ff"
        if ff_name not in sim.actor_manager.actors:
            ff = sim.add_actor("GammaFreeFlightActor", ff_name)
            ff.attached_to = "world"
            ff.ignored_volumes = self.volume_names
            ff.minimal_weight = self.minimal_weight
        else:
            ff = sim.actor_manager.get_actor(ff_name)

        if self.forced_direction_flag:
            self.setup_forced_detection(sim, source)
        else:
            self.setup_acceptance_angle(sim, source)

        return ff

    def setup_acceptance_angle(self, sim, source):
        detector_config = self.spect_config.detector_config
        normal_vector = detector_config.get_detector_normal()
        n = self.spect_config.number_of_threads
        source.activity = self.primary_activity / n
        source.direction.acceptance_angle.forced_direction_flag = False
        source.direction.acceptance_angle.skip_policy = "SkipEvents"
        if self.max_rejection is not None:
            source.direction.acceptance_angle.max_rejection = self.max_rejection
        source.direction.acceptance_angle.volumes = self.volume_names
        source.direction.acceptance_angle.intersection_flag = True
        source.direction.acceptance_angle.normal_flag = True
        source.direction.acceptance_angle.normal_vector = normal_vector
        source.direction.acceptance_angle.normal_tolerance = self.angle_tolerance
        # distance dependent normal tol is very slow, dont use it
        source.direction.acceptance_angle.distance_dependent_normal_tolerance = False
        # minimal distance should not be used for primary
        source.direction.acceptance_angle.normal_tolerance_min_distance = 0

    def setup_forced_detection(self, sim, source):
        detector_config = self.spect_config.detector_config
        # need an additional source copy for each head
        sources = [source]
        for i in range(1, detector_config.number_of_heads):
            s = sim.source_manager.add_source_copy(source.name, f"{source.name}_{i}")
            sources.append(s)

        normal_vector = detector_config.get_detector_normal()
        i = 0
        n = self.spect_config.number_of_threads

        for source in sources:
            source.activity = self.primary_activity / n
            source.direction.acceptance_angle.forced_direction_flag = True
            source.direction.acceptance_angle.skip_policy = "SkipEvents"
            # force the direction to one single volume for each source
            source.direction.acceptance_angle.volumes = [self.volume_names[i]]
            source.direction.acceptance_angle.normal_vector = normal_vector
            source.direction.acceptance_angle.normal_tolerance = self.angle_tolerance
            source.direction.acceptance_angle.normal_flag = False
            source.direction.acceptance_angle.intersection_flag = False
            i += 1

    def setup_simulation_scatter(self, sim, source):
        self.initialize(sim)

        # consider the volume to *not* apply ff
        if self.volume_names is None:
            crystals = sim.volume_manager.find_volumes("crystal")
            crystal_names = [c.name for c in crystals]
            self.volume_names = crystal_names

        n = self.spect_config.number_of_threads
        source.activity = self.scatter_activity / n

        # set the FF actor for scatter
        normal_vector = self.spect_config.detector_config.get_detector_normal()
        ff = sim.add_actor(
            "ScatterSplittingFreeFlightActor", f"{self.spect_config.simu_name}_ff"
        )
        ff.attached_to = "world"
        ff.minimal_weight = self.minimal_weight
        ff.ignored_volumes = self.volume_names
        ff.compton_splitting_factor = self.compton_splitting_factor
        ff.rayleigh_splitting_factor = self.rayleigh_splitting_factor
        ff.max_compton_level = self.max_compton_level
        ff.acceptance_angle.intersection_flag = True
        ff.acceptance_angle.normal_flag = True
        ff.acceptance_angle.forced_direction_flag = False
        ff.acceptance_angle.volumes = self.volume_names
        ff.acceptance_angle.normal_vector = normal_vector
        ff.acceptance_angle.normal_tolerance = self.angle_tolerance
        ff.acceptance_angle.normal_tolerance_min_distance = (
            self.angle_tolerance_min_distance
        )
        ff.acceptance_angle.distance_dependent_normal_tolerance = False

        """ REMOVED because too slow
        ff.acceptance_angle.distance_dependent_normal_tolerance = True
        tol = options.scatter_angle_tolerance
        ff.acceptance_angle.distance1 = tol[0]
        ff.acceptance_angle.angle1 = tol[1]
        ff.acceptance_angle.distance2 = tol[2]
        ff.acceptance_angle.angle2 = tol[3]
        """

        return ff


def spect_freeflight_merge_all_heads(
    folder,
    n_prim,
    n_scatter,
    n_target,
    prim_folder="primary",
    scatter_folder="scatter",
    nb_of_heads=2,
    counts_filename_pattern="projection_$I_counts.mhd",
    sq_counts_filename_pattern="projection_$I_squared_counts.mhd",
    mean_filename="projection_$I_counts.mhd",
    rel_uncert_suffix="relative_uncertainty_$I",
    verbose=True,
):
    for d in range(nb_of_heads):
        spect_freeflight_merge(
            folder,
            n_prim,
            n_scatter,
            n_target,
            prim_folder=prim_folder,
            scatter_folder=scatter_folder,
            counts_filename=counts_filename_pattern.replace("$I", str(d)),
            sq_counts_filename=sq_counts_filename_pattern.replace("$I", str(d)),
            mean_filename=mean_filename.replace("$I", str(d)),
            rel_uncert_suffix=rel_uncert_suffix.replace("$I", str(d)),
            verbose=verbose,
        )


def spect_freeflight_merge(
    folder,
    n_prim,
    n_scatter,
    n_target,
    prim_folder="primary",
    scatter_folder="scatter",
    counts_filename="projection_0_counts.mhd",
    sq_counts_filename="projection_0_squared_counts.mhd",
    mean_filename="mean.mhd",
    rel_uncert_suffix="relative_uncertainty",
    verbose=True,
):
    # make them path
    prim_folder = Path(prim_folder)
    scatter_folder = Path(scatter_folder)

    # primary
    img = folder / prim_folder / counts_filename
    sq_img = folder / prim_folder / sq_counts_filename
    out = folder / prim_folder / f"{img.stem}_{rel_uncert_suffix}.mhd"
    _, prim, prim_squared = history_rel_uncertainty_from_files(img, sq_img, n_prim, out)

    # scatter
    img = folder / scatter_folder / counts_filename
    sq_img = folder / scatter_folder / sq_counts_filename
    out = folder / scatter_folder / f"{img.stem}_{rel_uncert_suffix}.mhd"
    _, scatter, scatter_squared = history_rel_uncertainty_from_files(
        img, sq_img, n_scatter, out
    )

    # combined
    uncert, mean = history_ff_combined_rel_uncertainty(
        prim, prim_squared, scatter, scatter_squared, n_prim, n_scatter
    )

    scaling = n_target / n_prim
    mean = mean * scaling
    if verbose:
        print(f"Primary n = {n_prim}  Scatter n = {n_scatter}  Target n = {n_target}")
        print(f"Primary to scatter ratio = {n_prim / n_scatter:.01f}")
        print(f"Scaling to target        = {scaling:.01f}")

    # write combined image
    prim_img = sitk.ReadImage(img)
    img = sitk.GetImageFromArray(mean)
    img.CopyInformation(prim_img)
    fn = folder / mean_filename
    sitk.WriteImage(img, fn)
    if verbose:
        print(fn)

    # write combined relative uncertainty
    img = sitk.GetImageFromArray(uncert)
    img.CopyInformation(prim_img)
    fn = folder / f"{fn.stem}_{rel_uncert_suffix}.mhd"
    sitk.WriteImage(img, fn)
    if verbose:
        print(fn)

    # open info if the file exists
    prim_info = {}
    prim_info_fn = folder / prim_folder / "ff_info.json"
    if prim_info_fn.is_file():
        with open(prim_info_fn, "r") as f:
            prim_info = json.load(f)

    # open info if the file exists
    scatter_info = {}
    scatter_info_fn = folder / scatter_folder / "ff_info.json"
    if scatter_info_fn.is_file():
        with open(scatter_info_fn, "r") as f:
            scatter_info = json.load(f)

    # write combined information
    info = prim_info
    info.update(scatter_info)
    info_fn = folder / "ff_info.json"
    with open(info_fn, "w") as f:
        json.dump(info, f, indent=4)


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
