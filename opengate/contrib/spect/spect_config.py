import opengate as gate
from opengate.actors.biasingactors import generic_source_default_aa
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

    # This flag signals if __init__ is complete.
    # It's a class attribute, but we'll set it on the instance.
    _init_complete = False

    def __setattr__(self, name, value):
        """
        Overrides the default attribute setting.

        If the object is "sealed" (self._init_complete is True),
        this method will only allow *existing* attributes to be changed.
        It will raise an AttributeError if you try to set a *new* one.
        """

        # Allow setting attributes if:
        # 1. Initialization is not yet complete (we are in __init__)
        # 2. The attribute name already exists on the object
        # 3. The attribute is "private" (starts with '_')
        if not self._init_complete or hasattr(self, name) or name.startswith("_"):
            super().__setattr__(name, value)
        else:
            # If _init_complete is True and the attribute is new, raise an error.
            # This is what catches the typo.
            raise AttributeError(
                f"Cannot add new attribute '{name}' to '{self.__class__.__name__}'. "
                f"This attribute does not exist. Check for a typo."
                f"Current attribute names are: {self.__dict__.keys()}"
            )

    def _seal(self):
        """
        "Seals" this configuration object and all nested ConfigBase objects
        recursively. After sealing, no new attributes can be added.
        """
        self._init_complete = True

        # Recursively seal all sub-configs
        for key, value in vars(self).items():
            if key == "spect_config":
                return
            if isinstance(value, ConfigBase):
                value._seal()
            elif isinstance(value, (list, tuple)):
                for item in value:
                    if isinstance(item, ConfigBase):
                        item._seal()

    def validate(self):
        """
        Validates the configuration. Subclasses should override this
        to check their specific attributes.
        Raises ValueError for invalid configuration.
        """
        # Recursively validate nested ConfigBase objects
        for key, value in vars(self).items():
            if isinstance(value, ConfigBase):
                value.validate()
            elif isinstance(value, (list, tuple)):
                for item in value:
                    if isinstance(item, ConfigBase):
                        item.validate()

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
        self.projection_filename = "projection.mhd"
        self.simu_name = simu_name
        self.number_of_threads = 1

        # only used if ff
        self.output_folder_primary = None

        # main elements
        self.detector_config = DetectorConfig(self)
        self.phantom_config = PhantomConfig(self)
        self.source_config = SourceConfig(self)
        self.acquisition_config = AcquisitionConfig(self)
        self.free_flight_config = FreeFlightConfig(self)
        self._seal()

    def __str__(self):
        s = f"SPECT simulation\n"
        s += f"Output folder: {self.output_folder}\n"
        s += f"Output projection: {self.projection_filename}\n"
        s += f"Nb of threads: {self.number_of_threads}\n"
        s += f"{self.detector_config}\n"
        s += f"{self.phantom_config}\n"
        s += f"{self.source_config}\n"
        s += f"{self.acquisition_config}\n"
        s += f"{self.free_flight_config}"
        return s

    def validate(self):
        super().validate()

    def setup_simulation(self, sim, visu=False):
        # validate all options
        self.validate()

        # create the output folder if not exist
        os.makedirs(self.output_folder, exist_ok=True)

        # default initialization
        self.setup_default_simulation(sim, visu)

        # init all elements
        self.detector_config.setup_simulation(sim)
        self.phantom_config.setup_simulation(sim)
        self.source_config.setup_simulation(sim)
        self.acquisition_config.setup_simulation(sim)
        self.free_flight_config.setup_simulation(sim)

    def setup_default_simulation(self, sim, visu):
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

    By default : no phantom.
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
        gcm3 = gate.g4_units.g_cm3
        s = f"Phantom image: {self.image}\n"
        s += f"Phantom labels: {self.labels}\n"
        s += f"Phantom material: {self.material_db}\n"
        s += f"Phantom density tol: {self.density_tol/gcm3} gcm3\n"
        s += f"Phantom translation: {self.translation}"
        return s

    def validate(self):
        if self.image is not None:
            if not Path(self.image).exists():
                fatal(f"Phantom image does not exist: {self.image}")
        if self.labels is not None:
            if not Path(self.labels).exists():
                fatal(f"Phantom labels does not exist: {self.labels}")
        if self.material_db is not None:
            if not Path(self.material_db).exists():
                fatal(f"Phantom material db does not exist: {self.material_db}")
        if self.density_tol < 0:
            fatal(f"Phantom density tolerance must be positive: {self.density_tol}")
        if self.translation is not None:
            if len(self.translation) != 3:
                fatal(f"Phantom translation must be a 3D vector: {self.translation}")

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
        if self.digitizer_channels is not None:
            s += f"Detector # of channels: {len(self.digitizer_channels)}\n"
        else:
            s += f"Detector # of channels: None\n"
        s += f"Detector # of heads: {self.number_of_heads}\n"
        s += f"Detector size: {self.size}\n"
        s += f"Detector spacing: {self.spacing}\n"
        s += f"Detector names: {self.head_names}\n"
        s += f"Detector proj names: {self.proj_names}"
        s += str(self.garf_config)
        return s

    def validate(self):
        if self.model not in self.available_models:
            fatal(
                f"Detector model must be one of: {self.available_models}, while it is {self.model}"
            )
        self.garf_config.validate()

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

    def get_detectors(self, sim):
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
        filename, ext = get_basename_and_extension(
            self.spect_config.projection_filename
        )
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
        if self.pth_filename is None:
            return ""
        s = f"\nGARF : {self.pth_filename}\n"
        s += f"GARF image size: {self.spect_config.detector_config.size}\n"
        s += f"GARF image spacing: {self.spect_config.detector_config.spacing}\n"
        s += f"GARF batch size: {self.batch_size}\n"
        s += f"GARF gpu mode: {self.gpu_mode}\n"
        s += f"GARF arf actors: {self.arf_actors}"
        return s

    def validate(self):
        if self.pth_filename is not None:
            if not os.path.exists(self.pth_filename):
                fatal(f"GARF file does not exist: {self.pth_filename}")
        if self.gpu_mode not in ["auto", "cpu", "gpu"]:
            fatal(f"GARF gpu mode is not in ['auto', 'cpu', 'gpu']")

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
        s += f"Activity source: {self.total_activity / gate.g4_units.Bq:.1f} Bq\n"
        s += f"Activity source name: {self.source_name}\n"
        s += f"Activity remove_low_energy_lines: {self.remove_low_energy_lines}"
        return s

    def validate(self):
        if self.image is not None:
            if not Path(self.image).exists():
                fatal(f"Source image does not exist: {self.image}")
        else:
            return
        if self.radionuclide is None:
            fatal(f"Source radionuclide is None")
        if self.total_activity < 0:
            fatal(
                f"Source total activity must be positive: {self.total_activity/gate.g4_units.Bq} Bq"
            )

    def setup_simulation(self, sim):
        # can be: nothing or voxelized or gaga (later)
        if self.image is None:
            return
        if self.radionuclide is None:
            fatal(f"Radionuclide is None, please set a radionuclide (eg. 'lu177')")

        # retrieve phantom
        phantom_name = self.spect_config.phantom_config.get_phantom_volume_name()
        if phantom_name in sim.volume_manager.volume_names:
            phantom = sim.volume_manager.get_volume(phantom_name)
        else:
            phantom = None

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

        # remove gamma lines lower than min energy
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

    def validate(self):
        pass

    def setup_simulation(self, sim):
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
        detectors = self.spect_config.detector_config.get_detectors(sim)

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
        # if the mode is 'analog': no freeflight
        self.mode = "analog"
        self.available_modes = [
            "analog",
            "primary",
            "scatter",
            "septal_penetration",
        ]
        # user param
        self.weight_cutoff = 1e-30
        self.energy_cutoff = "auto"
        self.angular_acceptance = generic_source_default_aa()

        # copied from ffscatter
        self.compton_splitting_factor = 100
        self.rayleigh_splitting_factor = 100
        self.max_compton_level = 5

        # computed
        self.ff_output_folder = None

    def __str__(self):
        if self.mode == "analog":
            return ""
        s = f"FreeFlight mode: {self.mode}\n"
        s += f"FreeFlight weight_cutoff: {self.weight_cutoff}\n"
        e = self.energy_cutoff
        if e == "auto":
            s += f"FreeFlight energy_cutoff: auto\n"
        else:
            s += f"FreeFlight energy_cutoff: {g4_best_unit(self.energy_cutoff, 'Energy')}\n"
        if self.mode == "scatter":
            s += f"FreeFlight max_compton_level: {self.max_compton_level}\n"
            s += f"FreeFlight compton_splitting_factor: {self.compton_splitting_factor}\n"
            s += f"FreeFlight rayleigh_splitting_factor: {self.rayleigh_splitting_factor}\n"
        for key, value in self.angular_acceptance.items():
            if "angle_tolerance" in key:
                s += f"FreeFlight angular_acceptance: {key} = {value/g4_units.deg:.2f} deg\n"
            else:
                s += f"FreeFlight angular_acceptance: {key} = {value}\n"
        return s

    def validate(self):
        if self.mode not in self.available_modes:
            fatal(f"FreeFlight mode: {self.mode} not in {self.available_modes}")

    def setup_simulation(self, sim):
        if self.mode == "analog":
            return

        # set output sub folder
        self.ff_output_folder = self.spect_config.output_folder / self.mode
        os.makedirs(self.ff_output_folder, exist_ok=True)
        sim.output_dir = self.ff_output_folder

        # common parameters
        self.setup_required_parameters(sim)

        if self.mode == "primary":
            self.setup_simulation_primary(sim)
        if self.mode == "scatter":
            self.setup_simulation_scatter(sim)
        if self.mode == "septal_penetration":
            self.setup_simulation_septal_penetration(sim)

    def setup_required_parameters(self, sim):
        # Weights MUST be in the digitizer
        hits_actors = sim.actor_manager.find_actors_by_type(
            "DigitizerHitsCollectionActor"
        )
        if len(hits_actors) != 0:
            for ha in hits_actors:
                if "Weight" not in ha.attributes:
                    ha.attributes.append("Weight")
        # be sure the squared counts flag is enabled
        proj_actors = sim.actor_manager.find_actors_by_type("DigitizerProjectionActor")
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

        # auto set the minimal energy
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
        if self.spect_config.detector_config.garf_config.pth_filename is not None:
            volume_names = self.get_detector_volume_names()
        return volume_names

    def get_detector_volume_names(self):
        volume_names = self.spect_config.detector_config.head_names
        return volume_names

    def setup_simulation_primary(self, sim, sources=None):
        # get the sources
        if sources is None:
            # by default, all the sources in the simulation are used
            sources = []
            for s in sim.source_manager.sources.values():
                sources.append(s)
        # set the FFAA for all sources
        for source in sources:
            self.setup_simulation_primary_for_one_source(sim, source)
        # dump debug file
        self.dump_ff_info_primary()

    def setup_simulation_primary_for_one_source(self, sim, source):
        # consider the volumes where we stop applying ff: at the entrance of the detectors
        target_volume_names = self.get_detector_volume_names()

        # add the ff actor (only once !)
        ff_name = f"{self.spect_config.simu_name}_ff"
        if ff_name not in sim.actor_manager.actors:
            ff = sim.add_actor("GammaFreeFlightActor", ff_name)
            ff.attached_to = "world"
            ff.weight_cutoff = self.weight_cutoff
            ff.energy_cutoff = self.energy_cutoff
            # we stop FF in the detector, particles became analog
            ff.exclude_volumes = target_volume_names
        else:
            ff = sim.actor_manager.get_actor(ff_name)

        # set the normal to the detector
        detector_config = self.spect_config.detector_config
        normal_vector = detector_config.get_detector_normal()
        self.angular_acceptance.angle_check_reference_vector = normal_vector

        # set the target volumes
        if not self.angular_acceptance.target_volumes:
            self.angular_acceptance.target_volumes = target_volume_names

        # set the AA to the source (this is not a copy)
        source.direction.angular_acceptance = self.angular_acceptance

        # set the options for Rejection or ForceDirection
        if self.angular_acceptance.policy == "ForceDirection":
            self.setup_force_direction(sim, source, target_volume_names)
        return ff

    def setup_force_direction(self, sim, source, target_volume_names):
        # We need an additional source copy for each head
        detector_config = self.spect_config.detector_config
        sources = [source]
        for i in range(1, detector_config.number_of_heads):
            s = sim.source_manager.add_source_copy(source.name, f"{source.name}_{i}")
            sources.append(s)
        i = 0
        # We set the AA parameters for each source
        for source in sources:
            # force the direction to one single volume for each source
            source.direction.angular_acceptance = self.angular_acceptance.copy()
            aa = source.direction.angular_acceptance
            aa.target_volumes = [target_volume_names[i]]
            i += 1
        return sources

    def setup_simulation_scatter(self, sim):
        normal_vector = self.spect_config.detector_config.get_detector_normal()
        target_volume_names = self.get_detector_volume_names()
        # set the FF actor for scatter
        # g4.GateGammaFreeFlightOptrActor.ClearOperators()  # needed linux when no MT?
        ff = sim.add_actor(
            "ScatterSplittingFreeFlightActor",
            f"{self.spect_config.simu_name}_ff",
        )
        ff.attached_to = "world"  # FIXME -> remove this, always world + ignored_vol ?
        ff.weight_cutoff = self.weight_cutoff
        ff.energy_cutoff = self.energy_cutoff
        # no splitting/scatter in the detectors, back to analog particle
        ff.exclude_volumes = target_volume_names
        # kill primary analog particle in the detector:
        # - when an analog primary particle scatters in the colli, we DON'T want to
        # consider it because it was already included in the primary simulation
        # - when a scattered analog particle also scatters in the colli, we also DON'T want
        # to consider it because it was already considered by the splitter scatter
        ff.kill_interacting_in_volumes = target_volume_names
        # other parameters
        ff.compton_splitting_factor = self.compton_splitting_factor
        ff.rayleigh_splitting_factor = self.rayleigh_splitting_factor
        ff.max_compton_level = self.max_compton_level
        ## AA
        ff.angular_acceptance = self.angular_acceptance
        ff.angular_acceptance.target_volumes = target_volume_names
        ff.angular_acceptance.angle_check_reference_vector = normal_vector
        # dump debug file
        self.dump_ff_info_scatter()

        # should we also limit the angular acceptance for the source?
        # NOT REALLY: only possible if one head is used

        return ff

    def dump_ff_info_primary(self, filename="ff_info.json"):
        n = {
            "primary_activity": self.spect_config.source_config.total_activity
            / g4_units.Bq,
            "angle_tolerance_max": self.angular_acceptance.angle_tolerance_max
            / g4_units.deg,
            "angle_tolerance_min": self.angular_acceptance.angle_tolerance_min
            / g4_units.deg,
        }
        fn = self.ff_output_folder / filename
        with open(fn, "w") as f:
            json.dump(n, f, indent=4)

    def dump_ff_info_scatter(self, filename="ff_info.json"):
        n = {
            "scatter_activity": self.spect_config.source_config.total_activity
            / g4_units.Bq,
            "angle_tolerance_max": self.angular_acceptance.angle_tolerance_max
            / g4_units.deg,
            "angle_tolerance_min": self.angular_acceptance.angle_tolerance_min
            / g4_units.deg,
            "max_compton_level": self.max_compton_level,
            "compton_splitting_factor": self.compton_splitting_factor,
            "rayleigh_splitting_factor": self.rayleigh_splitting_factor,
        }
        fn = self.ff_output_folder / filename
        with open(fn, "w") as f:
            json.dump(n, f, indent=4)

    def setup_simulation_septal_penetration(self, sim, sources=None):
        # get the sources
        if sources is None:
            # by default, all the sources in the simulation are used
            sources = []
            for s in sim.source_manager.sources.values():
                sources.append(s)
        # set the FFAA for all sources
        for source in sources:
            self.setup_simulation_septal_penetration_for_one_source(sim, source)
        # dump debug file
        self.dump_ff_info_primary()

    def setup_simulation_septal_penetration_for_one_source(self, sim, source):

        # FIXME FIXME FIXME refactor with primary and option

        # consider the volumes where we stop applying ff: at the entrance of the detectors
        target_volume_names = self.get_detector_volume_names()
        crystal_volume_names = self.get_crystal_volume_names()

        # add the ff actor (only once !)
        ff_name = f"{self.spect_config.simu_name}_ff"
        if ff_name not in sim.actor_manager.actors:
            ff = sim.add_actor("GammaFreeFlightActor", ff_name)
            ff.attached_to = "world"
            ff.weight_cutoff = self.weight_cutoff
            ff.energy_cutoff = self.energy_cutoff
            # we stop FF in the detector, particles became analog
            ff.exclude_volumes = crystal_volume_names
        else:
            ff = sim.actor_manager.get_actor(ff_name)

        # set the normal to the detector
        detector_config = self.spect_config.detector_config
        normal_vector = detector_config.get_detector_normal()
        self.angular_acceptance.angle_check_reference_vector = normal_vector

        # set the target volumes
        if not self.angular_acceptance.target_volumes:
            self.angular_acceptance.target_volumes = target_volume_names

        # set the AA to the source (this is not a copy)
        source.direction.angular_acceptance = self.angular_acceptance

        # set the options for Rejection or ForceDirection
        if self.angular_acceptance.policy == "ForceDirection":
            self.setup_force_direction(sim, source, target_volume_names)
        return ff
