from typing import List

import numpy as np
from scipy.spatial.transform import Rotation

import opengate_core as g4
from .base import ActorBase
from ..exception import fatal
from ..definitions import fwhm_to_sigma
from ..utility import g4_units
from ..image import (
    align_image_with_physical_volume,
    update_image_py_to_cpp,
    get_py_image_from_cpp_image,
)
from .actoroutput import ActorOutputRoot, ActorOutputSingleImage


def ene_win_peak(name, energy, energy_width_percent):
    energy_width_percent = energy * energy_width_percent / 2
    e_min = energy - energy_width_percent
    e_max = energy + energy_width_percent
    a = {"name": name, "min": e_min, "max": e_max}
    return a


def ene_win_down_scatter(name, peak_min_value, energy_width_percent):
    e_max = peak_min_value
    e_min = e_max / (1 + energy_width_percent / 2)
    a = {"name": name, "min": e_min, "max": e_max}
    return a


def ene_win_up_scatter(name, peak_max_value, energy_width_percent):
    e_min = peak_max_value
    e_max = e_min / (1 - energy_width_percent / 2)
    a = {"name": name, "min": e_min, "max": e_max}
    return a


def energy_windows_peak_scatter(
    peak_name,
    down_scatter_name,
    up_scatter_name,
    peak,
    peak_width,
    down_scatter_width,
    up_scatter_width=None,
):
    if up_scatter_width is None:
        up_scatter_width = down_scatter_width
    p = ene_win_peak(peak_name, peak, peak_width)
    do = ene_win_down_scatter(down_scatter_name, p["min"], down_scatter_width)
    up = ene_win_up_scatter(up_scatter_name, p["max"], up_scatter_width)
    return do, p, up


def get_simplified_digitizer_channels_Tc99m(spect_name, scatter_flag):
    keV = g4_units.keV
    # Tc99m
    channels = [
        {"name": f"scatter_{spect_name}", "min": 114 * keV, "max": 126 * keV},
        {"name": f"peak140_{spect_name}", "min": 126 * keV, "max": 154 * keV},
    ]
    if not scatter_flag:
        channels.pop(0)
    return channels


def get_simplified_digitizer_channels_Lu177(spect_name, scatter_flag):
    # Lu177, Ljungberg2016
    keV = g4_units.keV
    channels = [
        {"name": f"scatter1_{spect_name}", "min": 96 * keV, "max": 104 * keV},
        {"name": f"peak113_{spect_name}", "min": 104 * keV, "max": 121.48 * keV},
        {"name": f"scatter2_{spect_name}", "min": 122.48 * keV, "max": 133.12 * keV},
        {"name": f"scatter3_{spect_name}", "min": 176.46 * keV, "max": 191.36 * keV},
        {"name": f"peak208_{spect_name}", "min": 192.36 * keV, "max": 223.6 * keV},
    ]
    if not scatter_flag:
        channels.pop(0)
        channels.pop(1)
        channels.pop(1)
    return channels


def get_simplified_digitizer_channels_In111(spect_name, scatter_flag):
    # In111
    keV = g4_units.keV
    channels = [
        {"name": f"scatter1_{spect_name}", "min": 150 * keV, "max": 156 * keV},
        {"name": f"peak171_{spect_name}", "min": 156 * keV, "max": 186 * keV},
        {"name": f"scatter2_{spect_name}", "min": 186 * keV, "max": 192 * keV},
        {"name": f"scatter3_{spect_name}", "min": 218 * keV, "max": 224 * keV},
        {"name": f"peak245_{spect_name}", "min": 224 * keV, "max": 272 * keV},
    ]
    if not scatter_flag:
        channels.pop(0)
        channels.pop(1)
        channels.pop(1)
    return channels


def get_simplified_digitizer_channels_I131(spect_name, scatter_flag):
    # I131
    keV = g4_units.keV
    channels = [
        {"name": f"scatter1_{spect_name}", "min": 314 * keV, "max": 336 * keV},
        {"name": f"peak364_{spect_name}", "min": 336 * keV, "max": 392 * keV},
        {"name": f"scatter2_{spect_name}", "min": 392 * keV, "max": 414 * keV},
        {"name": f"scatter3_{spect_name}", "min": 414 * keV, "max": 556 * keV},
        {"name": f"scatter4_{spect_name}", "min": 556 * keV, "max": 595 * keV},
        {"name": f"peak637_{spect_name}", "min": 595 * keV, "max": 679 * keV},
    ]
    if not scatter_flag:
        channels.pop(0)
        channels.pop(1)
        channels.pop(1)
        channels.pop(1)
    return channels


def get_simplified_digitizer_channels_rad(spect_name, rad, scatter_flag):
    available_rad = {
        "Tc99m": get_simplified_digitizer_channels_Tc99m,
        "Lu177": get_simplified_digitizer_channels_Lu177,
        "In111": get_simplified_digitizer_channels_In111,
        "I131": get_simplified_digitizer_channels_I131,
    }

    if rad not in available_rad:
        fatal(
            f"Error, the radionuclide {rad} is not known, list of available is: {available_rad}"
        )

    return available_rad[rad](spect_name, scatter_flag)


class Digitizer:
    """
    Simple helper class to reduce the code size when creating a digitizer.
    It only avoids repeating attached_to, output and input_digi_collection parameters.
    """

    def __init__(self, sim, volume_name, digit_name):
        # input param
        self.simulation = sim
        self.volume_name = volume_name
        self.name = digit_name
        # store
        self.actors = []

        # start by the hit collection
        self.hc = self.set_hit_collection()

    def set_hit_collection(self):
        hc = self.simulation.add_actor(
            "DigitizerHitsCollectionActor", f"{self.name}_hits"
        )
        hc.attached_to = self.volume_name
        hc.output_filename = ""
        hc.attributes = [
            "PostPosition",
            "TotalEnergyDeposit",
            "PreStepUniqueVolumeID",
            "PostStepUniqueVolumeID",
            "GlobalTime",
        ]
        self.actors.append(hc)
        return hc

    def add_module(self, module_type, module_name=None):
        index = len(self.actors)
        if module_name is None:
            module_name = f"{self.name}_{index}"
        mod = self.simulation.add_actor(module_type, module_name)
        mod.attached_to = self.actors[index - 1].attached_to
        if "input_digi_collection" in mod.user_info:
            mod.input_digi_collection = self.actors[index - 1].name
        first_key = next(iter(mod.user_output))
        mod.user_output[first_key].write_to_disk = False
        self.actors.append(mod)
        return mod

    def get_last_module(self):
        return self.actors[-1]

    def find_first_module(self, s):
        """
        Find the first module that contains the s string
        """
        for m in self.actors:
            if s in m.name:
                return m
        return None


class DigitizerBase(ActorBase):
    _output_name_root = "root_output"

    # hints for IDE
    authorize_repeated_volumes: bool

    user_info_defaults = {
        "authorize_repeated_volumes": (
            False,
            {
                "doc": "User must say explicitly that the digitizer can work with repeated volumes",
            },
        ),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)

    def _add_user_output_root(self, **kwargs):
        """Specialized method to add a root user output in digitizers.
        The output name is hard-coded at the class-level and the same for all digitizers,
        i.e. in all digitizers, the user can do:
        digitizer.user_output.root_output
        Additionally, the C++ classes expect an output with this name.
        """

        if self._output_name_root in self.user_output:
            fatal(
                f"The actor '{self.name}' already has a user_output called '{self._output_name_root}'."
                f"Probably, the method _add_user_output_root() was called more than once, "
                f"while it can be used only to add a single root output as in most digitizers. "
            )
        return self._add_user_output(ActorOutputRoot, self._output_name_root, **kwargs)

    def initialize(self):
        ActorBase.initialize(self)
        if self.authorize_repeated_volumes is True:
            return
        att = self.attached_to
        if not isinstance(self.attached_to, (list, tuple)):
            att = [self.attached_to]
        for a in att:
            current = self.simulation.volume_manager.get_volume(a).parent
            while current.name != "world" and hasattr(current, "g4_transform"):
                if len(current.g4_transform) > 1:
                    fatal(
                        f"This digitizer actor name '{self.name}' is attached to the volume '{self.attached_to}'. "
                        f"However, this volume is a daughter of the repeated volume '{current.name}'. It means it will "
                        f"gather data from all repeated instances. If you are "
                        f"sure, enable the option 'authorize_repeated_volumes'."
                    )
                current = current.parent


class DigitizerAdderActor(DigitizerBase, g4.GateDigitizerAdderActor):
    """
    Equivalent to Gate "adder": gather all hits of an event in the same volume.
    Input: a HitsCollection, need aat least TotalEnergyDeposit and PostPosition attributes
    Output: a Single collections

    Policies:
    - EnergyWinnerPosition: consider position and energy of the hit with the max energy
       for all other attributes (Time, etc.): the value of the winner is used.
    - EnergyWeightedCentroidPosition: computed the energy-weighted centroid position
       for all other attributes (Time, etc.): the value the last seen hit is used.

    """

    user_info_defaults = {
        "attributes": (
            [],
            {
                "doc": "Attributes to be considered. ",
            },
        ),
        "output": (
            "singles.root",
            {
                "deprecated": "Use output_filename instead. ",
            },
        ),
        "input_digi_collection": (
            "Hits",
            {
                "doc": "Digi collection to be used as input. ",
            },
        ),
        "policy": (
            "EnergyWinnerPosition",
            {
                "doc": "Digi collection to be used as input. ",
                "allowed_values": (
                    "EnergyWeightedCentroidPosition",
                    "EnergyWinnerPosition",
                ),
            },
        ),
        "time_difference": (
            False,
            {
                "doc": "FIXME",
            },
        ),
        "number_of_hits": (
            False,
            {
                "doc": "FIXME",
            },
        ),
        "skip_attributes": (
            [],
            {
                "doc": "FIXME",
            },
        ),
        "clear_every": (
            1e5,
            {
                "doc": "FIXME",
            },
        ),
        "group_volume": (
            None,
            {
                "doc": "FIXME",
            },
        ),
    }

    def __init__(self, *args, **kwargs):
        DigitizerBase.__init__(self, *args, **kwargs)
        self._add_user_output_root()
        self.__initcpp__()

    def __initcpp__(self):
        g4.GateDigitizerAdderActor.__init__(self, self.user_info)
        self.AddActions({"StartSimulationAction", "EndSimulationAction"})

    def initialize(self):
        if (
            self.policy != "EnergyWinnerPosition"
            and self.policy != "EnergyWeightedCentroidPosition"
        ):
            fatal(
                f"Error, the policy for the Adder '{self.name}' must be EnergyWinnerPosition or "
                f"EnergyWeightedCentroidPosition, while is is '{self.policy}'"
            )
        DigitizerBase.initialize(self)
        self.InitializeUserInput(self.user_info)
        self.InitializeCpp()

    def set_group_by_depth(self):
        depth = -1
        if self.user_info.group_volume is not None:
            depth = self.simulation.volume_manager.get_volume(
                self.user_info.group_volume
            ).volume_depth_in_tree
        self.SetGroupVolumeDepth(depth)

    def StartSimulationAction(self):
        self.set_group_by_depth()
        DigitizerBase.StartSimulationAction(self)
        g4.GateDigitizerAdderActor.StartSimulationAction(self)

    def EndSimulationAction(self):
        g4.GateDigitizerAdderActor.EndSimulationAction(self)


class DigitizerBlurringActor(DigitizerBase, g4.GateDigitizerBlurringActor):
    """
    Digitizer module for blurring an attribute (single value only, not a vector).
    Usually for energy or time.
    """

    user_info_defaults = {
        "input_digi_collection": (
            "Hits",
            {
                "doc": "Digi collection to be used as input. ",
            },
        ),
        "blur_attribute": (
            None,
            {
                "doc": "FIXME",
            },
        ),
        "skip_attributes": (
            [],
            {
                "doc": "FIXME",
            },
        ),
        "clear_every": (
            1e5,
            {
                "doc": "FIXME",
            },
        ),
        "blur_method": (
            "Gaussian",
            {
                "doc": "FIXME",
                "allowed_values": (
                    "Gaussian",
                    "InverseSquare",
                    "Linear",
                ),
            },
        ),
        "blur_sigma": (
            None,
            {
                "doc": "FIXME",
            },
        ),
        "blur_fwhm": (
            None,
            {
                "doc": "FIXME",
            },
        ),
        "blur_reference_value": (
            0,
            {
                "doc": "FIXME",
            },
        ),
        "blur_resolution": (
            0,
            {
                "doc": "FIXME",
            },
        ),
        "blur_slope": (
            0,
            {
                "doc": "FIXME",
            },
        ),
    }

    type_name = "DigitizerBlurringActor"

    def __init__(self, *args, **kwargs):
        DigitizerBase.__init__(self, *args, **kwargs)
        self._add_user_output_root()
        self.__initcpp__()

    def __initcpp__(self):
        g4.GateDigitizerBlurringActor.__init__(self, self.user_info)
        self.AddActions({"StartSimulationAction", "EndSimulationAction"})

    def initialize(self):
        self.initialize_blurring_parameters()
        DigitizerBase.initialize(self)
        self.InitializeUserInput(self.user_info)
        self.InitializeCpp()

    def initialize_blurring_parameters(self):
        if self.blur_method == "Gaussian":
            self.set_param_gauss()
        if self.blur_method == "InverseSquare":
            self.set_param_inverse_square()
        if self.blur_method == "Linear":
            self.set_param_linear()

    def set_param_gauss(self):
        if self.blur_fwhm is not None and self.blur_sigma is not None:
            fatal(
                f"Error, use blur_sigma or blur_fwhm, not both "
                f"(there are: {self.blur_sigma} and {self.blur_fwhm}"
            )
        if self.blur_fwhm is not None:
            self.blur_sigma = self.blur_fwhm * fwhm_to_sigma
        if self.blur_sigma is None:
            fatal(f"Error, use blur_sigma or blur_fwhm")
        self.blur_reference_value = -1
        self.blur_resolution = -1
        self.blur_slope = 0

    def set_param_inverse_square(self):
        if self.blur_reference_value < 0 or self.blur_reference_value is None:
            fatal(
                f"Error, use positive blur_reference_value "
                f"(current value =  {self.blur_reference_value}"
            )
        if self.blur_resolution < 0 or self.blur_resolution is None:
            fatal(
                f"Error, use positive blur_resolution "
                f"(current value =  {self.blur_resolution}"
            )
        self.blur_fwhm = -1
        self.blur_sigma = -1
        if self.blur_slope is None:
            self.blur_slope = 0

    def set_param_linear(self):
        self.set_param_inverse_square()
        if self.blur_slope is None:
            fatal(
                f"Error, use positive blur_slope "
                f"(current value =  {self.blur_slope}"
            )

    def StartSimulationAction(self):
        DigitizerBase.StartSimulationAction(self)
        g4.GateDigitizerBlurringActor.StartSimulationAction(self)

    def EndSimulationAction(self):
        g4.GateDigitizerBlurringActor.EndSimulationAction(self)


class DigitizerSpatialBlurringActor(
    DigitizerBase, g4.GateDigitizerSpatialBlurringActor
):
    """
    Digitizer module for blurring a (global) spatial position.
    """

    user_info_defaults = {
        "attributes": (
            [],
            {
                "doc": "Attributes to be considered. ",
            },
        ),
        "input_digi_collection": (
            "Hits",
            {
                "doc": "FIXME",
            },
        ),
        "skip_attributes": (
            [],
            {
                "doc": "FIXME",
            },
        ),
        "clear_every": (
            1e5,
            {
                "doc": "FIXME",
            },
        ),
        "blur_attribute": (
            None,
            {
                "doc": "FIXME",
            },
        ),
        "blur_fwhm": (
            None,
            {
                "doc": "FIXME",
            },
        ),
        "blur_sigma": (
            None,
            {
                "doc": "FIXME",
            },
        ),
        "keep_in_solid_limits": (
            True,
            {
                "doc": "FIXME",
            },
        ),
    }

    def __init__(self, *args, **kwargs):
        # base classes
        ActorBase.__init__(self, *args, **kwargs)
        self._add_user_output_root()
        self.__initcpp__()

    def __initcpp__(self):
        g4.GateDigitizerSpatialBlurringActor.__init__(self, self.user_info)
        self.AddActions({"StartSimulationAction", "EndSimulationAction"})

    def initialize_blurring_parameters(self):
        if self.blur_fwhm is not None and self.blur_sigma is not None:
            fatal(
                f"Error, use blur_sigma or blur_fwhm, not both "
                f"(there are: {self.blur_sigma} and {self.blur_fwhm}"
            )
        if not hasattr(self.blur_sigma, "__len__"):
            self.blur_sigma = [self.blur_sigma] * 3
        if not hasattr(self.blur_fwhm, "__len__"):
            self.blur_fwhm = [self.blur_fwhm] * 3
        if self.blur_fwhm is not None:
            self.blur_sigma = np.array(self.blur_fwhm) * fwhm_to_sigma
        if self.blur_sigma is None:
            fatal(f"Error, use blur_sigma or blur_fwhm")

    def initialize(self):
        self.initialize_blurring_parameters()
        DigitizerBase.initialize(self)
        self.InitializeUserInput(self.user_info)
        self.InitializeCpp()

    def StartSimulationAction(self):
        DigitizerBase.StartSimulationAction(self)
        g4.GateDigitizerSpatialBlurringActor.StartSimulationAction(self)

    def EndSimulationAction(self):
        g4.GateDigitizerSpatialBlurringActor.EndSimulationAction(self)


class DigitizerEfficiencyActor(DigitizerBase, g4.GateDigitizerEfficiencyActor):
    """
    Digitizer module for simulating efficiency.
    """

    user_info_defaults = {
        "attributes": (
            [],
            {
                "doc": "Attributes to be considered. ",
            },
        ),
        "input_digi_collection": (
            "Hits",
            {
                "doc": "FIXME",
            },
        ),
        "skip_attributes": (
            [],
            {
                "doc": "FIXME",
            },
        ),
        "clear_every": (
            1e5,
            {
                "doc": "FIXME",
            },
        ),
        "efficiency": (
            1.0,
            {
                "doc": "FIXME",
            },
        ),
    }

    def __init__(self, *args, **kwargs):
        # base classes
        ActorBase.__init__(self, *args, **kwargs)
        self._add_user_output_root()
        self.__initcpp__()

    def __initcpp__(self):
        g4.GateDigitizerEfficiencyActor.__init__(self, self.user_info)
        self.AddActions({"StartSimulationAction", "EndSimulationAction"})

    def initialize_blurring_parameters(self):
        if not (0.0 <= self.efficiency <= 1.0):
            self.warn_user(
                f"Efficency set to {self.efficiency}, which is not in [0;1]."
            )

    def initialize(self):
        self.initialize_blurring_parameters()
        DigitizerBase.initialize(self)
        self.InitializeUserInput(self.user_info)
        self.InitializeCpp()

    def StartSimulationAction(self):
        DigitizerBase.StartSimulationAction(self)
        g4.GateDigitizerEfficiencyActor.StartSimulationAction(self)

    def EndSimulationAction(self):
        g4.GateDigitizerEfficiencyActor.EndSimulationAction(self)


class DigitizerEnergyWindowsActor(DigitizerBase, g4.GateDigitizerEnergyWindowsActor):
    """
    Consider a list of hits and arrange them according to energy intervals.
    Input: one DigiCollection
    Output: as many DigiCollections as the number of energy windows
    """

    user_info_defaults = {
        "attributes": (
            [],
            {
                "doc": "Attributes to be considered. ",
            },
        ),
        "input_digi_collection": (
            "Hits",
            {
                "doc": "FIXME",
            },
        ),
        "skip_attributes": (
            [],
            {
                "doc": "FIXME",
            },
        ),
        "clear_every": (
            1e5,
            {
                "doc": "FIXME",
            },
        ),
        "channels": (
            [],
            {
                "doc": "FIXME",
            },
        ),
    }

    def __init__(self, *args, **kwargs):
        DigitizerBase.__init__(self, *args, **kwargs)
        self._add_user_output_root()
        self.__initcpp__()

    def __initcpp__(self):
        g4.GateDigitizerEnergyWindowsActor.__init__(self, self.user_info)
        self.AddActions({"StartSimulationAction", "EndSimulationAction"})

    def initialize(self):
        DigitizerBase.initialize(self)
        self.InitializeUserInput(self.user_info)
        self.InitializeCpp()

    def StartSimulationAction(self):
        DigitizerBase.StartSimulationAction(self)
        g4.GateDigitizerEnergyWindowsActor.StartSimulationAction(self)

    def EndSimulationAction(self):
        DigitizerBase.EndSimulationAction(self)
        g4.GateDigitizerEnergyWindowsActor.EndSimulationAction(self)


class DigitizerHitsCollectionActor(DigitizerBase, g4.GateDigitizerHitsCollectionActor):
    """
    Build a list of hits in a given volume.
    - the list of attributes to be stored is given in the 'attributes' options
    - output as root
    """

    user_info_defaults = {
        "attributes": (
            [],
            {
                "doc": "Attributes to be considered. ",
            },
        ),
        "clear_every": (
            1e5,
            {
                "doc": "FIXME",
            },
        ),
        "debug": (
            False,
            {
                "doc": "FIXME",
            },
        ),
        "keep_zero_edep": (
            False,
            {
                "doc": "FIXME",
            },
        ),
    }

    def __init__(self, *args, **kwargs):
        DigitizerBase.__init__(self, *args, **kwargs)
        self._add_user_output_root()
        self.__initcpp__()

    def __initcpp__(self):
        g4.GateDigitizerHitsCollectionActor.__init__(self, self.user_info)
        self.AddActions({"StartSimulationAction", "EndSimulationAction"})

    def initialize(self):
        DigitizerBase.initialize(self)
        self.InitializeUserInput(self.user_info)
        self.InitializeCpp()

    def StartSimulationAction(self):
        DigitizerBase.StartSimulationAction(self)
        g4.GateDigitizerHitsCollectionActor.StartSimulationAction(self)

    def EndSimulationAction(self):
        DigitizerBase.EndSimulationAction(self)
        g4.GateDigitizerHitsCollectionActor.EndSimulationAction(self)


class DigitizerProjectionActor(DigitizerBase, g4.GateDigitizerProjectionActor):
    """
    This actor takes as input HitsCollections and performed binning in 2D images.
    If there are several HitsCollection as input, the slices will correspond to each HC.
    If there are several runs, images will also be slice-stacked.
    """

    # hints for IDE
    input_digi_collections: List[str]
    spacing: List[float]
    size: List[int]
    physical_volume_index: int
    origin_as_image_center: bool
    detector_orientation_matrix: np.ndarray

    user_info_defaults = {
        # FIXME: implement a setter hook so the user can provided digitizer instances instead of their name,
        # like in attached_to
        "input_digi_collections": (
            ["Hits"],
            {
                "doc": "FIXME",
            },
        ),
        "spacing": (
            [4 * g4_units.mm, 4 * g4_units.mm],
            {"doc": "FIXME"},
        ),
        "size": (
            [128, 128],
            {"doc": "FIXME"},
        ),
        "physical_volume_index": (
            -1,
            {
                "doc": "When attached to a repeated volume, this option indicate which copy is used",
            },
        ),
        "origin_as_image_center": (
            True,
            {
                "doc": "FIXME",
            },
        ),
        "detector_orientation_matrix": (
            Rotation.from_euler("x", 0).as_matrix(),
            {
                "doc": "FIXME",
            },
        ),
    }

    def __init__(self, *args, **kwargs):
        DigitizerBase.__init__(self, *args, **kwargs)
        self._add_user_output(ActorOutputSingleImage, "projection")
        self.start_output_origin = None
        self.__initcpp__()

    def __initcpp__(self):
        g4.GateDigitizerProjectionActor.__init__(self, self.user_info)
        self.AddActions({"StartSimulationAction", "EndSimulationAction"})

    def initialize(self):
        # for the moment, we cannot use this actor with several volumes
        m = self.attached_to
        if hasattr(m, "__len__") and not isinstance(m, str):
            fatal(
                f"Sorry, cannot (yet) use several attached_to volumes for "
                f"DigitizerProjectionActor {self.user_info.name}"
            )
        if self.authorize_repeated_volumes is True:
            fatal(
                f"Sorry, cannot (yet) use ProjectionActor with repeated volumes, "
                f"set 'authorize_repeated_volumes' to False"
            )
        DigitizerBase.initialize(self)
        self.InitializeUserInput(self.user_info)
        self.InitializeCpp()

    @property
    def output_size(self):
        # consider 3D images, third dimension can be the energy windows
        output_size = list(self.size)
        if len(output_size) != 2:
            fatal(
                f"Error, the size must be a 2-vector (2D) while it is {output_size}. "
                f"Note: The size along the third dimension is automatically set to 1."
            )
        output_size.append(1)
        return output_size

    @property
    def output_spacing(self):
        # consider 3D images, third dimension can be the energy windows
        output_spacing = list(self.spacing)
        if len(output_spacing) != 2:
            fatal(
                f"Error, the spacing must be a 2-vector (2D) while it is {output_spacing}. "
                f"Note: The spacing along the third dimension is automatically set to 1."
            )
        output_spacing.append(1)
        return output_spacing

    def compute_thickness(self, volume, channels):
        """
        Get the thickness of the detector volume, in the correct direction.
        By default, it is Z. We use the 'projection_orientation' to get the correct one.
        """
        vol = self.actor_engine.simulation_engine.volume_engine.get_volume(volume)
        if len(vol.g4_physical_volumes) < 1:
            fatal(
                f"The actor {self.name} is attached to '{self.attached_to}' which has "
                f"no associated g4_physical_volumes (probably a parameterized volume?) and cannot "
                f"be used. Try to attach it to the mother volume of the parameterized volume."
            )

        solid = vol.g4_physical_volumes[0].GetLogicalVolume().GetSolid()
        pMin = g4.G4ThreeVector()
        pMax = g4.G4ThreeVector()
        solid.BoundingLimits(pMin, pMax)
        d = np.array([0, 0, 1.0])
        d = np.dot(self.detector_orientation_matrix, d)
        imax = np.argmax(d)
        thickness = (pMax[imax] - pMin[imax]) / channels
        return thickness

    def StartSimulationAction(self):
        DigitizerBase.StartSimulationAction(self)
        # for the moment, we cannot use this actor with several volumes
        if hasattr(self.attached_to, "__len__") and not isinstance(
            self.attached_to, str
        ):
            fatal(
                f"Sorry, cannot (yet) use several mothers volumes for "
                f"DigitizerProjectionActor {self.name}"
            )

        # define the new size and spacing according to the nb of channels
        # and according to the volume shape
        size = self.output_size
        spacing = self.output_spacing
        size[2] = len(self.input_digi_collections) * len(
            self.simulation.run_timing_intervals
        )
        spacing[2] = self.compute_thickness(self.attached_to, size[2])

        # we use the image associated with run 0 for the entire simulation
        # in the future, this actor should implement a BeginOfRunActionMasterThread
        # to be able to work on a per-run basis
        self.user_output.projection.create_empty_image(0, size, spacing)

        # check physical_volume_index and number of repeating
        n = len(self.attached_to_volume.g4_physical_volumes)
        if n > 1:
            if self.physical_volume_index >= n or self.physical_volume_index < 0:
                fatal(
                    f"The actor '{self.name}' is attached to '{self.attached_to}' which is repeated {n} times. "
                    f"You must set a valid 'physical_volume_index' between O to {n-1} while "
                    f"it is {self.physical_volume_index}."
                )
        else:
            # force the index to be zero
            self.physical_volume_index = 0

        # initial position (will be anyway updated in BeginOfRunSimulation)
        try:
            pv = self.attached_to_volume.g4_physical_volumes[self.physical_volume_index]
        except KeyError:
            fatal(
                f"Error in the DigitizerProjectionActor {self.name}. "
                f"No physical volume found for index {self.physical_volume_index} "
                f"in volume {self.attached_to_volume.name}"
            )
            pv = None  # avoid warning from IDE
        align_image_with_physical_volume(
            self.attached_to_volume, self.user_output.projection.data_per_run[0].image
        )
        self.SetPhysicalVolumeName(str(pv.GetName()))

        # update the cpp image and start
        update_image_py_to_cpp(
            self.user_output.projection.data_per_run[0].image, self.fImage, True
        )
        # keep initial origin
        self.start_output_origin = list(
            self.user_output.projection.data_per_run[0].get_image_properties()[0].origin
        )
        g4.GateDigitizerProjectionActor.StartSimulationAction(self)

    def EndSimulationAction(self):
        g4.GateDigitizerProjectionActor.EndSimulationAction(self)

        # retrieve the image
        self.user_output.projection.store_data(
            "merged", get_py_image_from_cpp_image(self.fImage)
        )

        # set its properties
        info = self.user_output.projection.data_per_run[0].get_image_properties()[0]
        spacing = info.spacing
        if self.origin_as_image_center:
            origin = -info.size * spacing / 2.0 + spacing / 2.0
        else:
            origin = self.start_output_origin
        origin[2] = 0
        spacing[2] = 1
        self.user_output.projection.merged_data.SetSpacing(list(spacing))
        self.user_output.projection.merged_data.SetOrigin(list(origin))

        self.user_output.projection.data_per_run.pop(
            0
        )  # remove the image for run 0 as result is in merged_data

        self.user_output.projection.write_data_if_requested(which="merged")


class DigitizerReadoutActor(DigitizerAdderActor, g4.GateDigitizerReadoutActor):
    """
    This actor is a DigitizerAdderActor + a discretization step:
    the final position is the center of the volume
    """

    user_info_defaults = {
        "discretize_volume": (
            None,
            {
                "doc": "FIXME",
            },
        ),
    }

    def __init__(self, *args, **kwargs):
        # warning : inherit from DigitizerAdderActor but should not use its
        # constructor because it adds an output
        ActorBase.__init__(self, *args, **kwargs)
        self._add_user_output_root()
        self.__initcpp__()

    def __initcpp__(self):
        # python 3.8 complains about init not called, we add explicit call to
        # GateDigitizerAdderActor here (not needed for py > 3.8)
        g4.GateDigitizerAdderActor.__init__(self, self.user_info)
        g4.GateDigitizerReadoutActor.__init__(self, self.user_info)
        self.AddActions({"StartSimulationAction", "EndSimulationAction"})

    def StartSimulationAction(self):
        DigitizerBase.StartSimulationAction(self)
        DigitizerAdderActor.set_group_by_depth(self)
        if self.user_info.discretize_volume is None:
            fatal(f'Please, set the option "discretize_volume"')
        depth = self.simulation.volume_manager.get_volume(
            self.discretize_volume
        ).volume_depth_in_tree
        self.SetDiscretizeVolumeDepth(depth)
        g4.GateDigitizerReadoutActor.StartSimulationAction(self)

    def EndSimulationAction(self):
        g4.GateDigitizerReadoutActor.EndSimulationAction(self)


class PhaseSpaceActor(DigitizerBase, g4.GatePhaseSpaceActor):
    """
    Similar to HitsCollectionActor : store a list of hits.
    However only the first hit of given event is stored here.
    """

    user_info_defaults = {
        "attributes": (
            [],
            {
                "doc": "FIXME",
            },
        ),
        "store_absorbed_event": (
            False,
            {
                "doc": "FIXME",
            },
        ),
        "debug": (
            False,
            {
                "doc": "print debug info",
            },
        ),
        "steps_to_store": (
            "entering",
            {
                "doc": "FIXME entering exiting first (can be combined)",
            },
        ),
    }

    def __init__(self, *args, **kwargs):
        DigitizerBase.__init__(self, *args, **kwargs)
        self._add_user_output_root()
        self.total_number_of_entries = 0
        self.number_of_absorbed_events = 0
        self.__initcpp__()

    def __initcpp__(self):
        g4.GatePhaseSpaceActor.__init__(self, self.user_info)

    def initialize(self):
        DigitizerBase.initialize(self)
        if "entering" in self.steps_to_store:
            self.SetStoreEnteringStepFlag(True)
        if "exiting" in self.steps_to_store:
            self.SetStoreExitingStepFlag(True)
        if "first" in self.steps_to_store:
            self.SetStoreFirstStepInVolumeFlag(True)
        self.InitializeUserInput(self.user_info)
        self.InitializeCpp()

    def StartSimulationAction(self):
        DigitizerBase.StartSimulationAction(self)
        g4.GatePhaseSpaceActor.StartSimulationAction(self)

    def EndSimulationAction(self):
        self.number_of_absorbed_events = self.GetNumberOfAbsorbedEvents()
        self.total_number_of_entries = self.GetTotalNumberOfEntries()
        if self.total_number_of_entries == 0:
            self.warn_user(
                f"Empty output, no particles stored in {self.get_output_path()}"
            )
        g4.GatePhaseSpaceActor.EndSimulationAction(self)
