import numpy as np
import itk
from scipy.spatial.transform import Rotation

import opengate_core as g4
from .ActorBase import ActorBase
from ..exception import fatal, warning
from ..definitions import fwhm_to_sigma, sigma_to_fwhm


from ..helpers import g4_units, check_filename_type
from ..image import (
    attach_image_to_physical_volume,
    update_image_py_to_cpp,
    get_cpp_image,
    get_info_from_image,
    create_3d_image,
    get_physical_volume,
)


class Digitizer:
    """
    Simple helper class to reduce the code size when creating a digitizer.
    It only avoids repeating mother, output and input_digi_collection parameters.
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
        hc.mother = self.volume_name
        hc.output = ""
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
        mod.mother = self.actors[index - 1].mother
        if "input_digi_collection" in mod.__dict__:
            mod.input_digi_collection = self.actors[index - 1].name
        mod.output = ""
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


class DigitizerAdderActor(g4.GateDigitizerAdderActor, ActorBase):
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

    type_name = "DigitizerAdderActor"

    @staticmethod
    def set_default_user_info(user_info):
        ActorBase.set_default_user_info(user_info)
        user_info.attributes = []
        user_info.output = "singles.root"
        user_info.input_digi_collection = "Hits"
        user_info.policy = "EnergyWinnerPosition"  # EnergyWeightedCentroidPosition
        user_info.time_difference = False
        user_info.number_of_hits = False
        user_info.skip_attributes = []
        user_info.clear_every = 1e5
        user_info.group_volume = None

    def __init__(self, user_info):
        ActorBase.__init__(self, user_info)
        g4.GateDigitizerAdderActor.__init__(self, user_info.__dict__)
        actions = {"StartSimulationAction", "EndSimulationAction"}
        self.AddActions(actions)
        if (
            user_info.policy != "EnergyWinnerPosition"
            and user_info.policy != "EnergyWeightedCentroidPosition"
        ):
            fatal(
                f"Error, the policy for the Adder '{user_info.name}' must be EnergyWinnerPosition or "
                f"EnergyWeightedCentroidPosition, while is is '{user_info.policy}'"
            )

    def __del__(self):
        pass

    def __str__(self):
        s = f"DigitizerAdderActor {self.user_info.name}"
        return s

    def set_group_by_depth(self):
        depth = -1
        if self.user_info.group_volume is not None:
            depth = self.simulation.volume_manager.get_volume_depth(
                self.user_info.group_volume
            )
        self.SetGroupVolumeDepth(depth)

    def StartSimulationAction(self):
        self.set_group_by_depth()
        g4.GateDigitizerAdderActor.StartSimulationAction(self)

    def EndSimulationAction(self):
        g4.GateDigitizerAdderActor.EndSimulationAction(self)


class DigitizerBlurringActor(g4.GateDigitizerBlurringActor, ActorBase):
    """
    Digitizer module for blurring an attribute (single value only, not a vector).
    Usually for energy or time.
    """

    type_name = "DigitizerBlurringActor"

    @staticmethod
    def set_default_user_info(user_info):
        ActorBase.set_default_user_info(user_info)
        user_info.attributes = []
        user_info.output = "singles.root"
        user_info.input_digi_collection = "Hits"
        user_info.skip_attributes = []
        user_info.clear_every = 1e5
        user_info.blur_attribute = None
        user_info.blur_method = "Gaussian"
        user_info.blur_fwhm = None
        user_info.blur_sigma = None
        user_info.blur_reference_value = None
        user_info.blur_resolution = None
        user_info.blur_slope = None

    def __init__(self, user_info):
        # check and adjust parameters
        self.set_param(user_info)
        # base classes
        ActorBase.__init__(self, user_info)
        g4.GateDigitizerBlurringActor.__init__(self, user_info.__dict__)
        actions = {"StartSimulationAction", "EndSimulationAction"}
        self.AddActions(actions)

    def set_param(self, user_info):
        am = ["Gaussian", "InverseSquare", "Linear"]
        m = user_info.blur_method
        if m not in am:
            fatal(
                f"Error, the blur_method must be within {am}, while it is {user_info.blur_method}"
            )
        if m == "Gaussian":
            self.set_param_gauss(user_info)
        if m == "InverseSquare":
            self.set_param_inverse_square(user_info)
        if m == "Linear":
            self.set_param_linear(user_info)

    def set_param_gauss(self, user_info):
        if user_info.blur_fwhm is not None and user_info.blur_sigma is not None:
            fatal(
                f"Error, use blur_sigma or blur_fwhm, not both "
                f"(there are: {user_info.blur_sigma} and {user_info.blur_fwhm}"
            )
        if user_info.blur_fwhm is not None:
            user_info.blur_sigma = user_info.blur_fwhm * fwhm_to_sigma
        if user_info.blur_sigma is None:
            fatal(f"Error, use blur_sigma or blur_fwhm")
        user_info.blur_reference_value = -1
        user_info.blur_resolution = -1
        user_info.blur_slope = 0

    def set_param_inverse_square(self, user_info):
        if user_info.blur_reference_value < 0 or user_info.blur_reference_value is None:
            fatal(
                f"Error, use positive blur_reference_value "
                f"(current value =  {user_info.blur_reference_value}"
            )
        if user_info.blur_resolution < 0 or user_info.blur_resolution is None:
            fatal(
                f"Error, use positive blur_resolution "
                f"(current value =  {user_info.blur_resolution}"
            )
        user_info.blur_fwhm = -1
        user_info.blur_sigma = -1
        if user_info.blur_slope is None:
            user_info.blur_slope = 0

    def set_param_linear(self, user_info):
        self.set_param_inverse_square(user_info)
        if user_info.blur_slope is None:
            fatal(
                f"Error, use positive blur_slope "
                f"(current value =  {user_info.blur_slope}"
            )

    def __del__(self):
        pass

    def __str__(self):
        s = f"DigitizerBlurringActor {self.user_info.name}"
        return s

    def StartSimulationAction(self):
        g4.GateDigitizerBlurringActor.StartSimulationAction(self)

    def EndSimulationAction(self):
        g4.GateDigitizerBlurringActor.EndSimulationAction(self)


class DigitizerSpatialBlurringActor(g4.GateDigitizerSpatialBlurringActor, ActorBase):
    """
    Digitizer module for blurring a (global) spatial position.
    """

    type_name = "DigitizerSpatialBlurringActor"

    @staticmethod
    def set_default_user_info(user_info):
        ActorBase.set_default_user_info(user_info)
        user_info.attributes = []
        user_info.output = "singles.root"
        user_info.input_digi_collection = "Hits"
        user_info.skip_attributes = []
        user_info.clear_every = 1e5
        user_info.blur_attribute = None
        user_info.blur_fwhm = None
        user_info.blur_sigma = None
        user_info.keep_in_solid_limits = True

    def __init__(self, user_info):
        # check and adjust parameters
        self.set_param(user_info)
        # base classes
        ActorBase.__init__(self, user_info)
        if not hasattr(user_info.blur_sigma, "__len__"):
            user_info.blur_sigma = [user_info.blur_sigma] * 3
        g4.GateDigitizerSpatialBlurringActor.__init__(self, user_info.__dict__)
        actions = {"StartSimulationAction", "EndSimulationAction"}
        self.AddActions(actions)

    def set_param(self, user_info):
        if user_info.blur_fwhm is not None and user_info.blur_sigma is not None:
            fatal(
                f"Error, use blur_sigma or blur_fwhm, not both "
                f"(there are: {user_info.blur_sigma} and {user_info.blur_fwhm}"
            )
        if user_info.blur_fwhm is not None:
            user_info.blur_sigma = np.array(user_info.blur_fwhm) * fwhm_to_sigma
        if user_info.blur_sigma is None:
            fatal(f"Error, use blur_sigma or blur_fwhm")

    def __del__(self):
        pass

    def __str__(self):
        s = f"DigitizerSpatialBlurringActor {self.user_info.name}"
        return s

    def StartSimulationAction(self):
        g4.GateDigitizerSpatialBlurringActor.StartSimulationAction(self)

    def EndSimulationAction(self):
        g4.GateDigitizerSpatialBlurringActor.EndSimulationAction(self)


class DigitizerEfficiencyActor(g4.GateDigitizerEfficiencyActor, ActorBase):
    """
    Digitizer module for simulating efficiency.
    """

    type_name = "DigitizerEfficiencyActor"

    @staticmethod
    def set_default_user_info(user_info):
        ActorBase.set_default_user_info(user_info)
        user_info.attributes = []
        user_info.output = "efficiency.root"
        user_info.input_digi_collection = "Hits"
        user_info.skip_attributes = []
        user_info.clear_every = 1e5
        user_info.efficiency = 1.0  # keep everything

    def __init__(self, user_info):
        # check and adjust parameters
        self.set_param(user_info)
        # base classes
        ActorBase.__init__(self, user_info)
        g4.GateDigitizerEfficiencyActor.__init__(self, user_info.__dict__)
        actions = {"StartSimulationAction", "EndSimulationAction"}
        self.AddActions(actions)

    def set_param(self, user_info):
        efficiency = user_info.efficiency
        if not (0.0 <= efficiency <= 1.0):
            warning(f"Efficency set to {efficiency}, which is not in [0;1].")

    def __del__(self):
        pass

    def __str__(self):
        s = f"DigitizerEfficiencyActor {self.user_info.name}"
        return s

    def StartSimulationAction(self):
        g4.GateDigitizerEfficiencyActor.StartSimulationAction(self)

    def EndSimulationAction(self):
        g4.GateDigitizerEfficiencyActor.EndSimulationAction(self)


class DigitizerEnergyWindowsActor(g4.GateDigitizerEnergyWindowsActor, ActorBase):
    """
    Consider a list of hits and arrange them according to energy intervals.
    Input: one DigiCollection
    Output: as many DigiCollections as the number of energy windows
    """

    type_name = "DigitizerEnergyWindowsActor"

    @staticmethod
    def set_default_user_info(user_info):
        ActorBase.set_default_user_info(user_info)
        user_info.attributes = []
        user_info.output = "EnergyWindows.root"
        user_info.input_digi_collection = "Hits"
        user_info.channels = []
        user_info.skip_attributes = []
        user_info.clear_every = 1e5

    def __init__(self, user_info):
        ActorBase.__init__(self, user_info)
        g4.GateDigitizerEnergyWindowsActor.__init__(self, user_info.__dict__)
        actions = {"StartSimulationAction", "EndSimulationAction"}
        self.AddActions(actions)

    def __del__(self):
        pass

    def __str__(self):
        s = f"DigitizerEnergyWindowsActor {self.user_info.name}"
        return s

    def StartSimulationAction(
        self,
    ):  # not needed, only if need to do something in python
        g4.GateDigitizerEnergyWindowsActor.StartSimulationAction(self)

    def EndSimulationAction(self):
        g4.GateDigitizerEnergyWindowsActor.EndSimulationAction(self)


class DigitizerHitsCollectionActor(g4.GateDigitizerHitsCollectionActor, ActorBase):
    """
    Build a list of hits in a given volume.
    - the list of attributes to be stored is given in the 'attributes' options
    - output as root
    """

    type_name = "DigitizerHitsCollectionActor"

    @staticmethod
    def set_default_user_info(user_info):
        ActorBase.set_default_user_info(user_info)
        user_info.attributes = []
        user_info.output = "hits.root"
        user_info.debug = False
        user_info.clear_every = 1e5
        user_info.keep_zero_edep = False

    def __init__(self, user_info):
        ActorBase.__init__(self, user_info)
        g4.GateDigitizerHitsCollectionActor.__init__(self, user_info.__dict__)
        actions = {"StartSimulationAction", "EndSimulationAction"}
        self.AddActions(actions)

    def __del__(self):
        pass

    def __str__(self):
        s = f"DigitizerHitsCollectionActor {self.user_info.name}"
        return s

    def StartSimulationAction(
        self,
    ):  # not needed, only if need to do something in python
        g4.GateDigitizerHitsCollectionActor.StartSimulationAction(self)

    def EndSimulationAction(self):
        g4.GateDigitizerHitsCollectionActor.EndSimulationAction(self)


class DigitizerProjectionActor(g4.GateDigitizerProjectionActor, ActorBase):
    """
    This actor takes as input HitsCollections and performed binning in 2D images.
    If there are several HitsCollection as input, the slices will correspond to each HC.
    If there are several runs, images will also be slice-stacked.
    """

    type_name = "DigitizerProjectionActor"

    @staticmethod
    def set_default_user_info(user_info):
        ActorBase.set_default_user_info(user_info)
        mm = g4_units("mm")
        user_info.output = False
        user_info.input_digi_collections = ["Hits"]
        user_info.spacing = [4 * mm, 4 * mm]
        user_info.size = [128, 128]
        user_info.physical_volume_index = None
        user_info.origin_as_image_center = True
        user_info.detector_orientation_matrix = Rotation.from_euler("x", 0).as_matrix()

    def __init__(self, user_info):
        ActorBase.__init__(self, user_info)
        g4.GateDigitizerProjectionActor.__init__(self, user_info.__dict__)
        actions = {"StartSimulationAction", "EndSimulationAction"}
        self.AddActions(actions)
        self.output_image = None
        if len(user_info.input_digi_collections) < 1:
            fatal(f"Error, not input hits collection.")
        self.start_output_origin = None

    def __del__(self):
        pass

    def __str__(self):
        s = f"DigitizerProjectionActor {self.user_info.name}"
        return s

    def __getstate__(self):
        ActorBase.__getstate__(self)
        self.output_image = None
        self.start_output_origin = None
        return self.__dict__

    def compute_thickness(self, volume, channels):
        """
        Get the thickness of the detector volume, in the correct direction.
        By default, it is Z. We use the 'projection_orientation' to get the correct one.
        """
        vol = self.volume_engine.get_volume(volume)
        solid = vol.g4_physical_volumes[0].GetLogicalVolume().GetSolid()
        pMin = g4.G4ThreeVector()
        pMax = g4.G4ThreeVector()
        solid.BoundingLimits(pMin, pMax)
        d = np.array([0, 0, 1.0])
        d = np.dot(self.user_info.detector_orientation_matrix, d)
        imax = np.argmax(d)
        thickness = (pMax[imax] - pMin[imax]) / channels
        return thickness

    def StartSimulationAction(self):
        # check size and spacing
        if len(self.user_info.size) != 2:
            fatal(f"Error, the size must be 2D while it is {self.user_info.size}")
        if len(self.user_info.spacing) != 2:
            fatal(f"Error, the spacing must be 2D while it is {self.user_info.spacing}")
        self.user_info.size.append(1)
        self.user_info.spacing.append(1)

        # for the moment, we cannot use this actor with several volumes
        m = self.user_info.mother
        if hasattr(m, "__len__") and not isinstance(m, str):
            fatal(
                f"Sorry, cannot (yet) use several mothers volumes for "
                f"DigitizerProjectionActor {self.user_info.name}"
            )

        # define the new size and spacing according to the nb of channels
        # and according to the volume shape
        size = np.array(self.user_info.size)
        spacing = np.array(self.user_info.spacing)
        size[2] = len(self.user_info.input_digi_collections) * len(
            self.simulation.run_timing_intervals
        )
        spacing[2] = self.compute_thickness(self.user_info.mother, size[2])

        # create image
        self.output_image = create_3d_image(size, spacing)

        # initial position (will be anyway updated in BeginOfRunSimulation)
        pv = None
        try:
            pv = get_physical_volume(
                self.volume_engine,
                self.user_info.mother,
                self.user_info.physical_volume_index,
            )
        except:
            fatal(f"Error in the DigitizerProjectionActor {self.user_info.name}")
        attach_image_to_physical_volume(pv.GetName(), self.output_image)
        self.fPhysicalVolumeName = str(pv.GetName())
        # update the cpp image and start
        update_image_py_to_cpp(self.output_image, self.fImage, True)
        g4.GateDigitizerProjectionActor.StartSimulationAction(self)
        # keep initial origin
        self.start_output_origin = self.output_image.GetOrigin()

    def EndSimulationAction(self):
        g4.GateDigitizerProjectionActor.EndSimulationAction(self)
        # retrieve the image
        self.output_image = get_cpp_image(self.fImage)
        # put back the origin
        self.output_image.SetOrigin(self.start_output_origin)
        info = get_info_from_image(self.output_image)
        # change the spacing / origin for the third dimension
        spacing = self.output_image.GetSpacing()
        origin = self.output_image.GetOrigin()
        # should we center the projection ?
        if self.user_info.origin_as_image_center:
            origin = -info.size * info.spacing / 2.0 + info.spacing / 2.0
        spacing[2] = 1
        origin[2] = 0
        self.output_image.SetSpacing(spacing)
        self.output_image.SetOrigin(origin)
        if self.user_info.output:
            itk.imwrite(self.output_image, check_filename_type(self.user_info.output))


class DigitizerReadoutActor(g4.GateDigitizerReadoutActor, ActorBase):
    """
    This actor is a DigitizerAdderActor + a discretization step:
    the final position is the center of the volume
    """

    type_name = "DigitizerReadoutActor"

    @staticmethod
    def set_default_user_info(user_info):
        DigitizerAdderActor.set_default_user_info(user_info)
        user_info.discretize_volume = None

    def __init__(self, user_info):
        ActorBase.__init__(self, user_info)
        g4.GateDigitizerReadoutActor.__init__(self, user_info.__dict__)
        actions = {"StartSimulationAction", "EndSimulationAction"}
        self.AddActions(actions)

    def __del__(self):
        pass

    def __str__(self):
        s = f"DigitizerReadoutActor {self.user_info.name}"
        return s

    def StartSimulationAction(self):
        DigitizerAdderActor.set_group_by_depth(self)
        if self.user_info.discretize_volume is None:
            fatal(f'Please, set the option "discretize_volume"')
        depth = self.simulation.volume_manager.get_volume_depth(
            self.user_info.discretize_volume
        )
        self.SetDiscretizeVolumeDepth(depth)
        g4.GateDigitizerReadoutActor.StartSimulationAction(self)

    def EndSimulationAction(self):
        g4.GateDigitizerReadoutActor.EndSimulationAction(self)
