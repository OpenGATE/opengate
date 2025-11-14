import opengate as gate
from opengate.contrib.spect.spect_helpers import *
from opengate.exception import fatal
from opengate import g4_units
import opengate.contrib.spect.ge_discovery_nm670 as nm670
import opengate.contrib.spect.siemens_intevo as intevo
from opengate.image import read_image_info
from opengate.utility import get_basename_and_extension, g4_best_unit
from opengate.sources.utility import set_source_energy_spectrum
import os
import json
from pathlib import Path


class ConfigBase:
    """
    Base class that provides generic to_dict and from_dict methods
    for configuration objects and equality operator __eq__.
    """

    def __eq__(self, other):
        """
        Generic comparison for ConfigBase and derived classes.
        Recursively compares attributes, handling special cases like functions and paths.
        """
        if not isinstance(other, self.__class__):
            return False

        # Compare all attributes
        for key, value1 in vars(self).items():
            if key == "spect_config":
                continue
            if key not in vars(other):
                print(f'Attribute "{key}" not in other')
                return False
            value2 = getattr(other, key)
            if not self.compare_values(value1, value2):
                print(f"Values for attribute '{key}' differ :" f" {value1} != {value2}")
                return False

        # Ensure consistent attributes in both objects
        if set(vars(self).keys()) != set(vars(other).keys()):
            return False

        return True

    @staticmethod
    def compare_values(value1, value2):
        """
        Compare two values, handling special cases like callables, paths, and ConfigBase objects.
        """
        # Handle function comparison by name and module
        if callable(value1) and callable(value2):
            return (
                value1.__name__ == value2.__name__
                and value1.__module__ == value2.__module__
            )
        # Handle Path objects comparison
        if isinstance(value1, Path) and isinstance(value2, Path):
            return str(value1) == str(value2)
        # Handle nested ConfigBase objects
        if isinstance(value1, ConfigBase) and isinstance(value2, ConfigBase):
            return value1 == value2
        # Default comparison
        return value1 == value2

    def serialize_value(self, value):
        """Helper method to serialise different types of values."""
        if callable(value):
            return {
                "type": "function",
                "module": value.__module__,
                "function_name": value.__name__,
            }
        if isinstance(value, Path):
            return str(value)
        if isinstance(value, ConfigBase):
            return value.to_dict()
        if isinstance(value, (list, tuple)):
            return [self.serialize_value(item) for item in value]
        if isinstance(value, dict):
            return {k: self.serialize_value(v) for k, v in value.items()}
        return value

    def deserialize_value(self, key, value):
        """Helper method to deserialize different types of values."""
        if isinstance(value, dict):
            if "type" in value and value["type"] == "function":
                try:
                    module = __import__(
                        value["module"], fromlist=[value["function_name"]]
                    )
                    return getattr(module, value["function_name"])
                except (ImportError, AttributeError) as e:
                    raise RuntimeError(
                        f"Cannot import function {value['function_name']} "
                        f"from module {value['module']}"
                    ) from e
            # Check if this is a nested config
            if "_config" in key:
                return self._create_config_instance(key, value)
            # Normal dict
            return {k: self.deserialize_value(k, v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self.deserialize_value(key, v) for v in value]
        elif isinstance(value, str):
            # Try to detect if the string represents a path
            path_indicators = ["/", "\\", "output", "data"]
            if any(indicator in value for indicator in path_indicators):
                try:
                    path = Path(value)
                    # Additional validation could be added here if needed
                    return path
                except Exception:
                    return value
        return value

    def _create_config_instance(self, key, data):
        """Create and populate a config instance based on data structure."""
        # Determine the config class type based on the data
        config_class = None
        if "detector" in key:
            config_class = DetectorConfig
        elif "acquisition" in key:
            config_class = AcquisitionConfig
        elif "phantom" in key:
            config_class = PhantomConfig
        elif "source" in key:
            config_class = SourceConfig
        elif "free_flight" in key:
            config_class = FreeFlightConfig
        elif "garf" in key:
            config_class = GARFConfig

        if config_class:
            instance = config_class(
                spect_config=self
            )  # getattr(self, "spect_config", None))
            instance.from_dict(data)
            return instance
        return data

    def get_excluded_keys(self):
        """Keys to exclude from serialisation (e.g. circular references)."""
        return ["spect_config"] if hasattr(self, "spect_config") else []

    def to_dict(self):
        """Convert configuration to dictionary, handling special types."""
        excluded = self.get_excluded_keys()
        return {
            k: self.serialize_value(v)
            for k, v in vars(self).items()
            if k not in excluded
        }

    def from_dict(self, data):
        """Populate configuration from a dictionary, handling special types."""
        for key, value in data.items():
            if key not in self.get_excluded_keys():
                setattr(self, key, self.deserialize_value(key, value))
        return self

    def to_json(self, file_path=None):
        """Serialise configuration to JSON."""
        json_dict = self.to_dict()
        if file_path:
            with open(file_path, "w") as f:
                json.dump(json_dict, f, indent=4)
        return json.dumps(json_dict, indent=4)

    @classmethod
    def from_json(cls, file_path=None, json_str=None):
        """Create a configuration instance from JSON."""
        if file_path is not None:
            with open(file_path, "r") as f:
                data = json.load(f)
        elif json_str is not None:
            data = json.loads(json_str)
        else:
            raise ValueError("Either file_path or json_str must be provided")

        instance = cls()
        instance.from_dict(data)
        return instance


class SPECTConfig(ConfigBase):
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
        s += f"{self.acquisition_config}\n"
        s += f"{self.free_flight_config}"
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

    def setup_simulation_ff_primary(
        self, sim, sources=None, visu=False, folder_name="primary"
    ):
        # we temporarily change the output folder
        save_folder = Path(self.output_folder)
        self.output_folder_primary = save_folder / folder_name
        self.output_folder = self.output_folder_primary
        # set the initial simulation
        self.source_config.total_activity = self.free_flight_config.energy_cutoff
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
        # g4.GateGammaFreeFlightOptrActor.ClearOperators()

        # we temporarily change the output folder
        save_folder = Path(self.output_folder)
        self.output_folder_scatter = save_folder / "scatter"
        self.output_folder = self.output_folder_scatter
        # set the initial simulation
        self.source_config.total_activity = self.free_flight_config.scatter_activity
        self.setup_simulation(sim, visu)
        # but keep the initial folder for further use of config
        self.output_folder = save_folder
        if sources is None:
            name = f"{self.simu_name}_source"
            source = sim.source_manager.get_source(name)
            sources = [source]
        if len(sources) > 1:
            fatal(f"SORRY multiple sources not implemented with FF-scatter yet")
        for source in sources:
            self.free_flight_config.setup_simulation_scatter(sim, source)
        self.dump_ff_info_scatter()

    def dump_ff_info_primary(self, filename="ff_info.json"):
        n = {
            "primary_activity": self.free_flight_config.energy_cutoff / g4_units.Bq,
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
        sim.physics_manager.global_production_cuts.all = 1 * gate.g4_units.mm

        # add the "stats" actor
        stats = sim.add_actor("SimulationStatisticsActor", "stats")
        stats.output_filename = "stats.txt"
        stats.track_types_flag = True


class PhantomConfig(ConfigBase):
    """
    This class is used in SPECTConfig. Represents a phantom configuration

    This class is used to configure and handle a phantom in a medical imaging
    simulation context. It includes properties for the phantom image,
    labels, density tolerance, and provides methods for printing the
    phantom configuration and generating a simulation. The phantom's
    construction and materials are based on Hounsfield Unit (HU) mappings
    to materials defined in external files.
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

    def get_phantom_volume_name(self):
        return f"{self.spect_config.simu_name}_phantom"

    def setup_simulation(self, sim):
        # can be: nothing or voxelized
        if self.image is None:
            return None
        # special case for visu
        if sim.visu is True:
            phantom = self.add_fake_phantom_for_visu(sim)
            if self.translation is not None:
                phantom.translation = self.translation
            return phantom
        # insert voxelized phantom
        phantom = sim.add_volume("Image", self.get_phantom_volume_name())
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
        phantom = sim.add_volume("Box", self.get_phantom_volume_name())
        phantom.material = "G4_WATER"
        phantom.size = img_info.size * img_info.spacing
        return phantom


class DetectorConfig(ConfigBase):
    """
    Used in SPECTConfig. Represents the configuration for a SPECT detector.

    Manage: detector models, crystals, collimators, digitizers,
    and the number of detector heads.
    """

    def __init__(self, spect_config):
        self.spect_config = spect_config
        # spect models
        self.available_models = ["intevo", "nm670"]
        # user param
        self.model = None
        self.collimator = None
        self.digitizer_function = "default"
        self.digitizer_channels = None
        self.number_of_heads = 2
        self.size = None
        self.spacing = None
        # computed (not user-defined)
        self.head_names = []
        self.proj_names = []
        # fix later
        self.garf_config = GARFConfig(spect_config)

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
        if self.model == "nm670":  # FIXME must be in intevo / nm670 module
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

    def get_energy_cutoff(self, tol=0.1):
        channels = self.digitizer_channels
        if channels is not None:
            min_e = 1e6 * g4_units.GeV
            for c in channels:
                if c["min"] < min_e:
                    min_e = c["min"]
            return min_e * (1 - tol)
        else:
            return None

    def setup_simulation(self, sim):
        if self.model not in self.available_models:
            fatal(
                f'The model "{self.model}" is unknown. '
                f"Known models are: {self.available_models}"
            )

        # get the module intevo or nm670
        m = self.get_model_module()

        # GARF ?
        if self.garf_config.is_enabled():
            if self.size is None:
                self.size = m.get_default_size_and_spacing()[0]
            if self.spacing is None:
                self.spacing = m.get_default_size_and_spacing()[1]
            self.head_names = self.garf_config.create_simulation(sim)
            return

        # digit function ?
        if self.digitizer_function == "default":
            self.digitizer_function = m.add_digitizer
        self.head_names = []
        self.proj_names = []

        # channels? Keep the initial digitizer_channels value.
        channels = self.digitizer_channels
        if self.digitizer_channels is None:
            rad = self.spect_config.source_config.radionuclide
            if rad is None:
                fatal(
                    f'Unknown radionuclide: "{self.spect_config.source_config.radionuclide}"'
                )
            channels = get_default_energy_windows(rad)
            self.digitizer_channels = channels

        # create the SPECT detector for each head
        simu_name = self.spect_config.simu_name
        for i in range(self.number_of_heads):
            # Create the head detector
            hn = f"{simu_name}_head_{i}"
            self.head_names.append(hn)
            det, colli, crystal = m.add_spect_head(
                sim,
                hn,
                collimator_type=self.collimator,
                debug=sim.visu == True,
            )
            # set the digitizer
            dname = f"{simu_name}_digit_{i}"
            if self.digitizer_function is not None:
                self.digitizer_function(
                    sim,
                    crystal.name,
                    dname,
                    self.size,
                    self.spacing,
                    channels,
                    self.get_proj_base_filename(i),
                )
                proj = sim.actor_manager.find_actor_by_type(
                    "DigitizerProjectionActor", dname
                )
                # update size/spacing that may have been set in the digitizer_function
                self.size = proj.size
                self.spacing = proj.spacing
                # keep the name of the projection actors
                self.proj_names.append(proj.name)


class GARFConfig(ConfigBase):
    """
    Used in DetectorConfig.
    Configuration class for GARF detector.
    """

    def __init__(self, spect_config):
        self.spect_config = spect_config
        # options
        self.pth_filename = None
        self.batch_size = 1e5
        self.verbose_batch = True
        self.gpu_mode = "auto"
        self.arf_actors = []

    def __str__(self):
        s = f"GARF : {self.pth_filename}\n"
        s += f"GARF image size: {self.spect_config.detector_config.size}\n"
        s += f"GARF image spacing: {self.spect_config.detector_config.spacing}\n"
        s += f"GARF batch size: {self.batch_size}"
        return s

    def is_enabled(self):
        return self.pth_filename is not None

    def create_simulation(self, sim):
        # get the module (intevo, nm670)
        m = self.spect_config.detector_config.get_model_module()
        colli = self.spect_config.detector_config.collimator
        size = self.spect_config.detector_config.size
        spacing = self.spect_config.detector_config.spacing
        head_names = []
        for i in range(self.spect_config.detector_config.number_of_heads):
            name = f"{self.spect_config.simu_name}__arf_{i}"
            _, arf = m.add_arf_detector(
                sim, name, colli, size, spacing, self.pth_filename
            )
            # same name as conventional detector
            arf.output_filename = (
                self.spect_config.detector_config.get_proj_base_filename(i)
            )
            self.arf_actors.append(arf)
            head_names.append(name)
        return head_names


class SourceConfig(ConfigBase):
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
        self.source_name = None
        self.remove_low_energy_lines = True

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
        if phantom is not None:
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

        # remove gamma line lower than min energy
        if self.remove_low_energy_lines:
            dc = self.spect_config.detector_config
            min_e = dc.get_energy_cutoff()
            if min_e is not None:
                weights = source.energy.spectrum_weights
                ene = source.energy.spectrum_energies
                index = 0
                for e in ene:
                    if e < min_e:
                        weights[index] = 0.0
                    index += 1
                print(
                    f"Source energy spectrum modified, lines below {g4_best_unit(min_e, 'Energy')} removed"
                )

        if sim.visu is True:
            source.activity = 10 * gate.g4_units.Bq
        self.source_name = source.name


class AcquisitionConfig(ConfigBase):
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
        self.radius = 30 * g4_units.cm
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


class FreeFlightConfig(ConfigBase):

    def __init__(self, spect_config):
        self.spect_config = spect_config
        # user param
        self.angle_tolerance = 6 * g4_units.deg
        self.min_angle_tolerance = 0 * g4_units.deg
        self.forced_direction_flag = True
        self.angle_tolerance_min_distance = 6 * g4_units.cm
        self.max_compton_level = 5
        self.compton_splitting_factor = 50
        self.rayleigh_splitting_factor = 50
        self.weight_cutoff = 1e-30
        self.energy_cutoff = "auto"
        self.primary_activity = 1 * g4_units.Bq
        self.scatter_activity = 1 * g4_units.Bq
        self.max_rejection = None
        # primary: do not bias in those volumes
        self.primary_exclude_volumes = "detector"
        # scatter options
        self.scatter_exclude_volumes = "detector"
        self.scatter_kill_interacting_in_volumes = "crystal"

    def __str__(self):
        s = f"FreeFlight FD: {self.forced_direction_flag}\n"
        s += f"FreeFlight angle tol: {self.angle_tolerance / g4_units.deg} deg\n"
        s += f"FreeFlight angle tol min dist: {self.angle_tolerance_min_distance / g4_units.mm} mm\n"
        s += f"FreeFlight max_compton_level: {self.max_compton_level}\n"
        s += f"FreeFlight compton_splitting_factor: {self.compton_splitting_factor}\n"
        s += f"FreeFlight rayleigh_splitting_factor: {self.rayleigh_splitting_factor}\n"
        s += f"FreeFlight weight_cutoff: {self.weight_cutoff}\n"
        s += f"FreeFlight energy_cutoff: {g4_best_unit(self.energy_cutoff, "Energy")}\n"
        s += f"FreeFlight primary_activity: {self.primary_activity / g4_units.Bq} Bq\n"
        s += f"FreeFlight scatter_activity: {self.scatter_activity / g4_units.Bq} Bq\n"
        s += f"FreeFlight primary_unbiased_volumes: {self.primary_exclude_volumes} \n"
        s += f"FreeFlight scatter_unbiased_volumes: {self.scatter_exclude_volumes} \n"
        s += f"FreeFlight scatter_kill_interacting_in_volumes: {self.scatter_kill_interacting_in_volumes} \n"
        return s

    def initialize(self, sim):
        # Weights MUST be in the digitizer
        # FIXME change the way to get the hits
        hits_actors = sim.actor_manager.find_actors("_hits")
        if len(hits_actors) != 0:
            for ha in hits_actors:
                if "Weight" not in ha.attributes:
                    ha.attributes.append("Weight")
        # be sure the squared counts flag is enabled
        proj_actors = sim.actor_manager.find_actors("projection")
        if len(proj_actors) != 0:
            for d in proj_actors:
                d.squared_counts.active = True

        # if garf is used, compute the squared counts
        if self.spect_config.detector_config.garf_config.pth_filename is not None:
            for arf in self.spect_config.detector_config.garf_config.arf_actors:
                arf.squared_counts.active = True

        # GeneralProcess must *NOT* be used with FF
        s = f"/process/em/UseGeneralProcess false"
        if s not in sim.g4_commands_before_init:
            sim.g4_commands_before_init.append(s)

        # auto set the minimal energy (to avoid warning)
        if self.energy_cutoff == "auto":
            dc = self.spect_config.detector_config
            e = dc.get_energy_cutoff()
            if e is not None:
                self.energy_cutoff = dc.get_energy_cutoff()
            else:
                self.energy_cutoff = 0 * g4_units.keV

    def get_crystal_volume_names(self):
        volume_names = [
            f"{self.spect_config.simu_name}_head_{i}_crystal"
            for i in range(self.spect_config.detector_config.number_of_heads)
        ]
        return volume_names

    def get_detector_volume_names(self):
        volume_names = self.spect_config.detector_config.head_names
        return volume_names

    def setup_simulation_primary(self, sim, source):
        self.initialize(sim)

        # consider the volume where we stop applying ff
        target_volume_names = None
        if self.primary_exclude_volumes == "crystal":
            target_volume_names = self.get_crystal_volume_names()
        elif self.primary_exclude_volumes == "detector":
            target_volume_names = self.get_detector_volume_names()
        else:
            fatal(
                f"FF primary: unknown ignored volume: "
                f"{self.primary_exclude_volumes}. Should be detector or crystal"
            )

        # add the ff actor (only once !)
        ff_name = f"{self.spect_config.simu_name}_ff"
        if ff_name not in sim.actor_manager.actors:
            ff = sim.add_actor("GammaFreeFlightActor", ff_name)
            ff.attached_to = "world"
            ff.exclude_volumes = target_volume_names
            ff.weight_cutoff = self.weight_cutoff
            ff.energy_cutoff = self.energy_cutoff
        else:
            ff = sim.actor_manager.get_actor(ff_name)

        if self.forced_direction_flag:
            self.setup_forced_detection(sim, source, target_volume_names)
        else:
            self.setup_angular_acceptance(sim, source, target_volume_names)

        return ff

    def setup_angular_acceptance(self, sim, source, target_volume_names):
        detector_config = self.spect_config.detector_config
        normal_vector = detector_config.get_detector_normal()
        n = self.spect_config.number_of_threads
        source.activity = self.energy_cutoff / n
        source.direction.angular_acceptance.forced_direction_flag = False
        source.direction.angular_acceptance.skip_policy = "SkipEvents"
        if self.max_rejection is not None:
            source.direction.angular_acceptance.max_rejection = self.max_rejection
        source.direction.angular_acceptance.volumes = target_volume_names
        source.direction.angular_acceptance.intersection_flag = True
        source.direction.angular_acceptance.normal_flag = True
        source.direction.angular_acceptance.normal_vector = normal_vector
        source.direction.angular_acceptance.normal_tolerance = self.angle_tolerance
        # distance dependent normal tol is very slow, dont use it
        # source.direction.angular_acceptance.distance_dependent_normal_tolerance = False
        # minimal distance should not be used for primary
        source.direction.angular_acceptance.normal_tolerance_min_distance = 0

        return source

    def setup_forced_detection(self, sim, source, target_volume_names):
        detector_config = self.spect_config.detector_config

        # need an additional source copy for each head
        sources = [source]
        for i in range(1, detector_config.number_of_heads):
            s = sim.source_manager.add_source_copy(source.name, f"{source.name}_{i}")
            sources.append(s)

        normal_vector = detector_config.get_detector_normal()
        i = 0

        for source in sources:
            # force the direction to one single volume for each source
            source.direction.angular_acceptance.volumes = [target_volume_names[i]]
            source.direction.angular_acceptance.normal_vector = normal_vector
            source.direction.angular_acceptance.normal_tolerance = self.angle_tolerance
            source.direction.angular_acceptance.min_normal_tolerance = (
                self.min_angle_tolerance
            )
            source.direction.angular_acceptance.skip_policy = "SkipEvents"
            source.direction.angular_acceptance.normal_flag = False
            source.direction.angular_acceptance.intersection_flag = False
            source.direction.angular_acceptance.forced_direction_flag = True
            i += 1
        return sources

    def setup_simulation_scatter(self, sim, source):
        self.initialize(sim)

        target_volume_names = None
        if self.scatter_exclude_volumes == "crystal":
            target_volume_names = self.get_crystal_volume_names()
        elif self.scatter_exclude_volumes == "detector":
            target_volume_names = self.get_detector_volume_names()
        else:
            fatal(f"Unknown ff-scatter unbiased volume: {self.scatter_exclude_volumes}")

        kill_volumes = []
        if self.scatter_kill_interacting_in_volumes == "crystal":
            kill_volumes = self.get_crystal_volume_names()
        elif self.scatter_kill_interacting_in_volumes == "detector":
            kill_volumes = self.get_detector_volume_names()

        print("unbiased_volumes:", target_volume_names)
        print("kill_volumes:", kill_volumes)

        n = self.spect_config.number_of_threads
        source.activity = self.scatter_activity / n

        # set the FF actor for scatter
        normal_vector = self.spect_config.detector_config.get_detector_normal()
        g4.GateGammaFreeFlightOptrActor.ClearOperators()  # needed linux when no MT ?
        ff = sim.add_actor(
            "ScatterSplittingFreeFlightActor",
            f"{self.spect_config.simu_name}_ff",
        )
        ff.attached_to = "world"  # FIXME -> remove this, always world + ignored_vol ?
        ff.weight_cutoff = self.weight_cutoff
        ff.energy_cutoff = self.energy_cutoff
        ff.exclude_volumes = target_volume_names
        ff.kill_interacting_in_volumes = kill_volumes
        ff.compton_splitting_factor = self.compton_splitting_factor
        ff.rayleigh_splitting_factor = self.rayleigh_splitting_factor
        ff.max_compton_level = self.max_compton_level
        ff.angular_acceptance.intersection_flag = True
        ff.angular_acceptance.normal_flag = True
        ff.angular_acceptance.forced_direction_flag = False
        ff.angular_acceptance.volumes = target_volume_names
        ff.angular_acceptance.normal_vector = normal_vector
        ff.angular_acceptance.normal_tolerance = self.angle_tolerance
        ff.angular_acceptance.normal_tolerance_min_distance = (
            self.angle_tolerance_min_distance
        )
        ff.angular_acceptance.distance_dependent_normal_tolerance = False

        """ REMOVED because too slow
        ff.angular_acceptance.distance_dependent_normal_tolerance = True
        tol = options.scatter_angle_tolerance
        ff.angular_acceptance.distance1 = tol[0]
        ff.angular_acceptance.angle1 = tol[1]
        ff.angular_acceptance.distance2 = tol[2]
        ff.angular_acceptance.angle2 = tol[3]
        """

        return ff
