import numpy as np
from scipy.spatial.transform import Rotation

import opengate_core as g4
from .base import ActorBase
from ..exception import fatal, warning
from ..utility import (
    g4_units,
    standard_error_c4_correction,
)
from ..image import (
    update_image_py_to_cpp,
    get_py_image_from_cpp_image,
    images_have_same_domain,
    resample_itk_image_like,
)
from ..geometry.utility import get_transform_world_to_local
from ..base import process_cls
from .actoroutput import (
    ActorOutputSingleImage,
    ActorOutputSingleMeanImage,
    ActorOutputQuotientMeanImage,
    ActorOutputSingleImageWithVariance,
    UserInterfaceToActorOutputImage,
)


class VoxelDepositActor(ActorBase):
    """Base class which holds user input parameters common to all actors
    that deposit quantities in a voxel grid, e.g. the DoseActor.
    """

    # hints for IDE
    size: list
    spacing: list
    translation: list
    rotation: list
    repeated_volume_index: int
    hit_type: str
    output: str
    img_coord_system: str
    output_coordinate_system: str

    user_info_defaults = {
        "size": (
            [10, 10, 10],
            {
                "doc": "Size of the dose grid in number of voxels [N_x, N_y, N_z]. Expects a list of integer values of size 3.",
            },
        ),
        "spacing": (
            [1 * g4_units.mm, 1 * g4_units.mm, 1 * g4_units.mm],
            {
                "doc": "Voxel spacing vector along the [x, y, z] coordinates with units. "
                "The user sets the units by multiplication with g4_units.XX. "
                "The default unit is g4_unit.mm amd the default spacing is [1, 1, 1] [g4_units.mm]",
            },
        ),
        "translation": (
            [0 * g4_units.mm, 0 * g4_units.mm, 0 * g4_units.mm],
            {
                "doc": "Translation vector to (optionally) translate the image in along [x, y, z] from the center of the attached volume. The default unit is g4_units.mm and default value is the unity operation [0, 0, 0] * g4_units.mm. ",
            },
        ),
        "rotation": (
            Rotation.identity().as_matrix(),
            {
                "doc": "Rotation matrix to (optionally) rotate the image. Default is the identiy matrix.",
            },
        ),
        "repeated_volume_index": (
            0,
            {
                "doc": "Index of the repeated volume (G4PhysicalVolume) to which this actor is attached. "
                "For non-repeated volumes, this value is always 0. ",
            },
        ),
        "hit_type": (
            "random",
            {
                "doc": "For advanced users: define the position of interaction to which the deposited quantity is associated to, "
                "i.e. at the Geant4 PreStepPoint, PostStepPoint, or somewhere in between (middle or (uniform) random). In doubt use/start with random.",
                "allowed_values": ("random", "pre", "post", "middle"),
            },
        ),
        "output": (
            None,
            {
                "deprecated": "The output filename is now set via output_filename relative to the output "
                "directory of the simulation, which can be set via sim.output_dir. "
                "If no output_filename is provided, it will be generated automatically. "
                "To specify whether the actor output should be written to disk, use write_to_disk=True/False."
            },
        ),
        "img_coord_system": (
            None,
            {
                "deprecated": "The user input parameter 'img_coord_system' is deprecated. "
                "Use my_actor.output_coordinate_system='attached_to_image' instead, "
                "where my_actor should be replaced with your actor object. ",
            },
        ),
        "output_coordinate_system": (
            "local",
            {
                "doc": "This command sets the reference coordinate system, which can be the local volume (attached_to commmand), global or attached to image.",
                "allowed_values": ("local", "global", "attached_to_image", None),
            },
        ),
    }

    def __init__(self, *args, **kwargs) -> None:
        ActorBase.__init__(self, *args, **kwargs)

    def check_user_input(self):
        if self.output_coordinate_system == "attached_to_image":
            if not hasattr(
                self.attached_to_volume, "native_translation"
            ) or not hasattr(self.attached_to_volume, "native_rotation"):
                fatal(
                    f"User input 'output_coordinate_system' = {self.output_coordinate_system} "
                    f"of actor {self.name} is not compatible "
                    f"with the volume to which this actor is attached: "
                    f"{self.attached_to} ({self.attached_to_volume.volume_type})"
                )

    def initialize(self):
        super().initialize()

        msg = (
            f"cannot be used in actor {self.name} "
            f"because the volume ({self.attached_to}, {self.attached_to_volume.type_name}) "
            f"to which the actor is attached does not support it. "
        )
        if isinstance(self.spacing, str) and self.spacing == "like_image_volume":
            if not hasattr(self.attached_to_volume, "spacing"):
                fatal("spacing = 'like_image_volume' " + msg)
            self.spacing = self.attached_to_volume.spacing
        if isinstance(self.size, str) and self.size == "like_image_volume":
            if not hasattr(self.attached_to_volume, "size_pix"):
                fatal("size = 'like_image_volume' " + msg)
            self.size = self.attached_to_volume.size_pix

    def get_physical_volume_name(self):
        # init the origin and direction according to the physical volume
        # (will be updated in the BeginOfRun)
        if self.repeated_volume_index is None:
            repeated_volume_index = 0
        else:
            repeated_volume_index = self.repeated_volume_index
        try:
            g4_phys_volume = self.attached_to_volume.g4_physical_volumes[
                repeated_volume_index
            ]
        except IndexError:
            fatal(
                f"Error in the actor {self.type_name} named {self.name}. "
                f"Could not find the physical volume with index {repeated_volume_index} "
                f"in volume '{self.attached_to}' to which this actor is attached. "
            )
        # Return the real physical volume name
        return str(g4_phys_volume.GetName())

    def _update_output_coordinate_system(self, which_output, run_index):
        """Method to be called at the end of a run.
        Note: The output image is aligned with the volume to which the actor as attached
        at the beginning of a run. So for the option output_coordinate_system='global',
        nothing has to be done here.
        """
        size = np.array(self.size)
        spacing = np.array(self.spacing)
        origin = -size * spacing / 2.0 + spacing / 2.0

        translation = np.array(self.translation)
        origin_local = Rotation.from_matrix(self.rotation).apply(origin) + translation

        # image centered at (0,0,0), no rotation
        if self.output_coordinate_system is None:
            self.user_output[which_output].set_image_properties(
                run_index,
                origin=origin.tolist(),
                rotation=Rotation.identity().as_matrix(),
            )
        # image centered at self.translation and rotated by self.rotation,
        # i.e. in the reference frame of the volume to which the actor is attached.
        elif self.output_coordinate_system in ("local",):
            self.user_output[which_output].set_image_properties(
                run_index, origin=origin_local.tolist(), rotation=self.rotation
            )
        # only applicable if the attached_to volume is an image volume
        # as 'local', but considering the origin and direction (rotation) of the image
        # used to create the image volume. Useful overlay output and image volume for further analysis
        elif self.output_coordinate_system in ("attached_to_image",):
            native_origin_image = self.attached_to_volume.native_translation
            native_rotation_image = self.attached_to_volume.native_rotation
            origin_wrt_image = (
                Rotation.from_matrix(native_rotation_image).apply(origin_local)
                + native_origin_image
            )
            rotation_wrt_image = np.matmul(native_rotation_image, self.rotation)

            self.user_output[which_output].set_image_properties(
                run_index, origin=origin_wrt_image.tolist(), rotation=rotation_wrt_image
            )
        elif self.output_coordinate_system in ("global",):
            translation_phys_vol, rotation_phys_vol = get_transform_world_to_local(
                self.attached_to_volume, self.repeated_volume_index
            )
            origin_global = (
                Rotation.from_matrix(rotation_phys_vol).apply(origin_local)
                + translation_phys_vol
            )
            rotation_global = np.matmul(rotation_phys_vol, self.rotation)
            self.user_output[which_output].set_image_properties(
                run_index, origin=origin_global.tolist(), rotation=rotation_global
            )
        else:
            fatal(
                f"Illegal parameter 'output_coordinate_system': {self.output_coordinate_system}"
            )

    def prepare_output_for_run(self, output_name, run_index, **kwargs):
        self._assert_output_exists(output_name)
        # self.user_output[output_name].size = self.size
        # self.user_output[output_name].spacing = self.spacing
        self.user_output[output_name].create_empty_image(
            run_index, self.size, self.spacing, origin=self.translation, **kwargs
        )

    def fetch_from_cpp_image(self, output_name, run_index, *cpp_image):
        self._assert_output_exists(output_name)
        data = []
        for i, cppi in enumerate(cpp_image):
            if self.user_output[output_name].get_active(item=i):
                py_image = get_py_image_from_cpp_image(cppi, view=False)
                # FIXME: not needed, I think, because get_py_image_from_cpp_image copies spacing and origin
                # There is an empty image already which has served as storage for meta info like size and spacing.
                # So we get this info back
                # py_image.CopyInformation(
                #     self.user_output[output_name].get_data(run_index, item=i)
                # )
                data.append(py_image)
            else:
                data.append(None)
        self.user_output[output_name].store_data(run_index, *data)

    def push_to_cpp_image(self, output_name, run_index, *cpp_image, copy_data=True):
        self._assert_output_exists(output_name)
        for i, cppi in enumerate(cpp_image):
            if self.user_output[output_name].get_active(item=i):
                update_image_py_to_cpp(
                    self.user_output[output_name].get_data(run_index, item=i),
                    cppi,
                    copy_data,
                )

    def EndOfRunActionMasterThread(self, run_index):
        # inform actor output that this run is over
        for u in self.user_output.values():
            if u.get_active(item="all"):
                u.end_of_run(run_index)
        return 0

    def StartSimulationAction(self):
        # inform actor output that this simulation is starting
        for u in self.user_output.values():
            if u.get_active(item="any"):
                u.start_of_simulation()

    def EndSimulationAction(self):
        # inform actor output that this simulation is over and write data
        for u in self.user_output.values():
            if u.get_active(item="any"):
                u.end_of_simulation()


def compute_std_from_sample(
    number_of_samples, value_array, squared_value_array, correct_bias=False
):
    unc = np.ones_like(value_array)
    if number_of_samples > 1:
        # unc = np.sqrt(1 / (N - 1) * (square / N - np.power(edep / N, 2)))
        unc = np.sqrt(
            np.clip(
                (
                    squared_value_array / number_of_samples
                    - np.power(value_array / number_of_samples, 2)
                )
                / (number_of_samples - 1),
                0,
                None,
            )
        )
        if correct_bias:
            # Standard error is biased (to underestimate the error);
            # this option allows to correct for the bias - assuming normal distribution.
            # For few N this in is huge, but for N>8 the difference is minimal
            unc /= standard_error_c4_correction(number_of_samples)
        unc = np.divide(
            unc,
            value_array / number_of_samples,
            out=np.ones_like(unc),
            where=value_array != 0,
        )

    else:
        # unc += 1 # we init with 1.
        warning(
            "You try to compute statistical errors with only one or zero event! "
            "The uncertainty value for all voxels has been fixed at 1"
        )
    return unc


def _setter_hook_ste_of_mean_unbiased(self, value):
    if value is True:
        self.ste_of_mean = True
    return value


def _setter_hook_ste_of_mean(self, value):
    if value is True:
        self.square = True
        self.use_more_ram = True
    return value


def _setter_hook_uncertainty(self, value):
    if value is True:
        self.square = True
    return value


def _setter_hook_uncertainty_goal(self, value):
    if value is not None and (value < 0.0 or value > 1.0):
        fatal(
            f"Uncertainty goal must be > 0 and < 1, where 1 means 100%. The provided value is: {value}"
        )
    return value


class DoseActor(VoxelDepositActor, g4.GateDoseActor):
    """Computes the deposited energy or absorbed dose in the volume to which it is attached.
    It creates a virtual voxelized scoring image, whose shape and position can be defined by the user.
    """

    # hints for IDE
    score_in: str

    user_info_defaults = {
        "square": (
            True,
            {
                "doc": "This option will provide an additional output image with the squared energy (or dose) deposited per event. This image can be used to calculate the variance of the output variable, as Var(X) = E[X^2] - E[X]^2. This option enables the E[X^2] image.",
                "deprecated": "Use: my_actor.square.active=True/False "
                "to request uncertainty scoring of the respective quantity, "
                "where 'my_actor' should be your actor object. "
                "Note: activating user_output.edep_uncertainty or user_output.dose_uncertainty "
                "implies activating user_output.square. ",
            },
        ),
        "uncertainty": (
            True,
            {
                "doc": "This option will create an additional output image providing the uncertainty of the scored variable (dose or edep).",
                "deprecated": "Use: my_actor.dose_uncertainty.active=True/False and"
                "my_actor.user_output.edep_uncertainty.active=True/False "
                "to request uncertainty scoring of the respective quantity, "
                "where 'my_actor' should be your actor object. ",
                # "setter_hook": _setter_hook_uncertainty,
            },
        ),
        "dose": (
            False,
            {
                "doc": "This option will enable the calculation of the dose image.",
                "deprecated": "Use: my_actor.dose.active=True/False "
                "to request the actor to score dose, "
                "where 'my_actor' should be your actor object. "
                "By default, only the deposited energy is scored. ",
            },
        ),
        "to_water": (
            False,
            {
                "doc": "This option will convert the dose image to dose to water.",
                "deprecated": "Use my_dose_actor.score_in='G4_WATER' instead. ",
            },
        ),
        "score_in": (
            "material",
            {
                "doc": """The score_in command allows to convert the LET from the material, which is defined in the geometry, to any user defined material. Note, that this does not change the material definition in the geometry. The default value is 'material', which means that no conversion is performed and the LET to the local material is scored. You can use any material defined in the simulation or pre-defined by Geant4 such as 'G4_WATER', which may be one of the most use cases of this functionality.
                """,
                "allowed_values": (
                    "material",
                    "G4_WATER",
                ),
            },
        ),
        "ste_of_mean": (
            False,
            {
                "doc": "Calculate the standard error of the mean. Only working in MT mode and the number of threads are considered the sample. To have a meaningful uncertainty at least 8 threads are needed.",
                "setter_hook": _setter_hook_ste_of_mean,
                "deactivated": True,
            },
        ),
        "ste_of_mean_unbiased": (
            False,
            {
                "doc": "Similar to ste_of_mean, but compensates for a bias in ste_of_mean for small sample sizes (<8).  ",
                "setter_hook": _setter_hook_ste_of_mean_unbiased,
                "deactivated": True,
            },
        ),
        "uncertainty_goal": (
            None,
            {
                "doc": "If set, it defines the statistical uncertainty goal. The simulation will stop once the statistical uncertainty is smaller or equal this value.",
                "setter_hook": _setter_hook_uncertainty_goal,
            },
        ),
        "uncertainty_first_check_after_n_events": (
            1e4,
            {
                "doc": "Only applies if uncertainty_goal is set True: Number of events after which uncertainty is evaluated the first time. "
                "After the first evaluation, the value is updated with an estimation of the N events needed to achieve the uncertainty goal, Therefore it is recommended to select a sufficiently large number so the uncertainty of the uncertainty is not too large.",
            },
        ),
        "uncertainty_voxel_edep_threshold": (
            0.7,
            {
                "doc": "Only applies if uncertainty_goal is set True: The calculation of the mean uncertainty of the edep image, only voxels that are above this relative threshold are considered. The threshold must range between [0, 1] and gives the fraction relative to max edep value in the image.",
            },
        ),
        "uncertainty_overshoot_factor_N_events": (
            1.05,
            {
                "doc": "Only applies if uncertainty_goal is set True: Factor multiplying the estimated N events needed to achieve the uncertainty goal, to ensure convergence.",
            },
        ),
        "dose_calc_on_the_fly": (
            False,
            {
                "doc": "FIXME",
                "deactivated": True,
            },
        ),
    }

    user_output_config = {
        "edep_with_uncertainty": {
            "actor_output_class": ActorOutputSingleImageWithVariance,
            "interfaces": {
                "edep": {
                    "interface_class": UserInterfaceToActorOutputImage,
                    "item": 0,
                    "active": True,
                },
                "edep_squared": {
                    "interface_class": UserInterfaceToActorOutputImage,
                    "item": 1,
                    "active": False,
                },
                "edep_uncertainty": {
                    "interface_class": UserInterfaceToActorOutputImage,
                    "item": "uncertainty",
                    "active": False,
                },
            },
        },
        "dose_with_uncertainty": {
            "actor_output_class": ActorOutputSingleImageWithVariance,
            "interfaces": {
                "dose": {
                    "interface_class": UserInterfaceToActorOutputImage,
                    "item": 0,
                    "active": False,
                },
                "dose_squared": {
                    "interface_class": UserInterfaceToActorOutputImage,
                    "item": 1,
                    "active": False,
                },
                "dose_uncertainty": {
                    "interface_class": UserInterfaceToActorOutputImage,
                    "item": "uncertainty",
                    "active": False,
                },
            },
        },
        "density": {
            "actor_output_class": ActorOutputSingleMeanImage,
            "active": False,
        },
        "counts": {
            "actor_output_class": ActorOutputSingleImage,
            "active": False,
        },
    }

    def __init__(self, *args, **kwargs):
        VoxelDepositActor.__init__(self, *args, **kwargs)
        self.__initcpp__()

    def __initcpp__(self):
        g4.GateDoseActor.__init__(self, self.user_info)
        self.AddActions(
            {
                "BeginOfRunActionMasterThread",
                "EndOfRunActionMasterThread",
                "BeginOfRunAction",
                "EndOfRunAction",
                "BeginOfEventAction",
                "SteppingAction",
                "EndOfEventAction",
            }
        )

    def create_density_image_from_image_volume(self, deposit_image):
        if self.attached_to_volume.volume_type != "ImageVolume":
            fatal(
                f"Cannot calculate the density map from the ImageVolume "
                f"because this actor is attached to a {self.attached_to_volume.volume_type}. "
            )

        density_image = self.attached_to_volume.create_density_image()
        if images_have_same_domain(deposit_image, density_image) is False:
            density_image = resample_itk_image_like(
                density_image, deposit_image, 0, linear=True
            )
        return density_image

    def initialize(self, *args):
        """
        At the start of the run, the image is centered according to the coordinate system of
        the attached volume. This function computes the correct origin = center + translation.
        Note that there is a half-pixel shift to align according to the center of the pixel,
        like in ITK.
        """
        self.check_user_input()

        VoxelDepositActor.initialize(self)

        # the edep component has to be active in any case
        self.user_output.edep_with_uncertainty.set_active(True, item=0)

        # Make sure the squared component (item 1) is active if any of the quantities relying on it are active
        if (
            self.user_output.edep_with_uncertainty.get_active(
                item=("uncertainty", "std", "variance")
            )
            is True
            or self.uncertainty_goal is not None
        ):
            # activate the squared component, but avoid writing it to disk
            # because the user has not activated it and thus most likely does not want it
            if not self.user_output.edep_with_uncertainty.get_active(item=1):
                self.user_output.edep_with_uncertainty.set_write_to_disk(False, item=1)
                self.user_output.edep_with_uncertainty.set_active(
                    True, item=1
                )  # activate squared component

        # Make sure the squared component (item 1) is active if any of the quantities relying on it are active
        if (
            self.user_output.dose_with_uncertainty.get_active(
                item=("uncertainty", "std", "variance")
            )
            is True
        ):
            # activate the dose component
            self.user_output.dose_with_uncertainty.set_active(True, item=0)
            # activate the squared component, but avoid writing it to disk
            # because the user has not activated it and thus most likely does not want it
            if not self.user_output.dose_with_uncertainty.get_active(item=1):
                self.user_output.dose_with_uncertainty.set_write_to_disk(False, item=1)
                self.user_output.dose_with_uncertainty.set_active(
                    True, item=1
                )  # activate squared component

        if (
            self.user_output.density.get_active() is True
            and self.attached_to_volume.volume_type != "ImageVolume"
        ):
            fatal(
                "The dose actor can only produce a density map if it is attached to an ImageVolume. "
                f"This actor is attached to a {self.attached_to_volume.volume_type} volume. "
            )

        self.InitializeUserInfo(self.user_info)  # C++ side
        # Set the flags on C++ side so the C++ knows which quantities need to be scored
        self.SetEdepSquaredFlag(
            self.user_output.edep_with_uncertainty.get_active(item=1)
        )
        self.SetDoseFlag(self.user_output.dose_with_uncertainty.get_active(item=0))
        self.SetDoseSquaredFlag(
            self.user_output.dose_with_uncertainty.get_active(item=1)
        )
        # item=0 is the default
        self.SetCountsFlag(self.user_output.counts.get_active())
        # C++ side has a boolean toWaterFlag and self.score_in == "water" yields True/False
        self.SetToWaterFlag(self.score_in == "G4_WATER")

        # variables for stop on uncertainty functionality
        if self.uncertainty_goal is None:
            self.SetUncertaintyGoal(0)
        else:
            self.SetUncertaintyGoal(self.uncertainty_goal)
        self.SetThreshEdepPerc(self.uncertainty_voxel_edep_threshold)
        self.SetOvershoot(self.uncertainty_overshoot_factor_N_events)
        self.SetNbEventsFirstCheck(int(self.uncertainty_first_check_after_n_events))

        # Set the physical volume name on the C++ side
        self.SetPhysicalVolumeName(self.get_physical_volume_name())
        self.InitializeCpp()

    def BeginOfRunActionMasterThread(self, run_index):
        self.prepare_output_for_run("edep_with_uncertainty", run_index)
        self.push_to_cpp_image(
            "edep_with_uncertainty",
            run_index,
            self.cpp_edep_image,
            self.cpp_edep_squared_image,
        )

        if self.user_output.dose_with_uncertainty.get_active(item="any"):
            self.prepare_output_for_run("dose_with_uncertainty", run_index)
            self.push_to_cpp_image(
                "dose_with_uncertainty",
                run_index,
                self.cpp_dose_image,
                self.cpp_dose_squared_image,
            )

        if self.user_output.counts.get_active():
            self.prepare_output_for_run("counts", run_index)
            self.push_to_cpp_image("counts", run_index, self.cpp_counts_image)

        g4.GateDoseActor.BeginOfRunActionMasterThread(self, run_index)

    def EndOfRunActionMasterThread(self, run_index):
        self.fetch_from_cpp_image(
            "edep_with_uncertainty",
            run_index,
            self.cpp_edep_image,
            self.cpp_edep_squared_image,
        )
        self._update_output_coordinate_system("edep_with_uncertainty", run_index)
        self.user_output.edep_with_uncertainty.store_meta_data(
            run_index, number_of_samples=self.NbOfEvent
        )

        if self.user_output.dose_with_uncertainty.get_active(item="any"):
            self.fetch_from_cpp_image(
                "dose_with_uncertainty",
                run_index,
                self.cpp_dose_image,
                self.cpp_dose_squared_image,
            )
            self._update_output_coordinate_system("dose_with_uncertainty", run_index)
            self.user_output.dose_with_uncertainty.store_meta_data(
                run_index, number_of_samples=self.NbOfEvent
            )
            # divide by voxel volume and scale to unit Gy
            if self.user_output.dose_with_uncertainty.get_active(item=0):
                self.user_output.dose_with_uncertainty.data_per_run[run_index].data[
                    0
                ] /= (g4_units.Gy * self.spacing[0] * self.spacing[1] * self.spacing[2])
            if self.user_output.dose_with_uncertainty.get_active(item=1):
                # in the squared component 1, the denominator needs to be squared
                self.user_output.dose_with_uncertainty.data_per_run[run_index].data[
                    1
                ] /= (
                    g4_units.Gy * self.spacing[0] * self.spacing[1] * self.spacing[2]
                ) ** 2

        if self.user_output.counts.get_active():
            self.fetch_from_cpp_image("counts", run_index, self.cpp_counts_image)
            self._update_output_coordinate_system("counts", run_index)
            self.user_output.counts.store_meta_data(
                run_index, number_of_samples=self.NbOfEvent
            )

        # density image
        if self.user_output.density.get_active():
            edep_image = self.user_output.edep_with_uncertainty.get_data(
                run_index, item=0
            )
            self.user_output.density.store_data(
                run_index, self.create_density_image_from_image_volume(edep_image)
            )
            self.user_output.density.store_meta_data(
                run_index, number_of_samples=self.NbOfEvent
            )

        VoxelDepositActor.EndOfRunActionMasterThread(self, run_index)

        # FIXME: should check if uncertainty goal is reached (return value: 0),
        # but the current mechanism is quite hacky and it is therefore temporarily not in use!
        return 0

    def EndSimulationAction(self):
        g4.GateDoseActor.EndSimulationAction(self)
        VoxelDepositActor.EndSimulationAction(self)


class TLEDoseActor(DoseActor, g4.GateTLEDoseActor):
    """TLE = Track Length Estimator"""

    energy_min: float
    energy_max: float
    database: str

    user_info_defaults = {
        "energy_min": (
            0.0,
            {"doc": "Kill the gamma if below this energy"},
        ),
        "energy_max": (
            1.0 * g4_units.MeV,
            {
                "doc": "Above this energy, do not perform TLE (TLE is only relevant for low energy gamma)"
            },
        ),
        "database": (
            "EPDL",
            {
                "doc": "which database to use",
                "allowed_values": ("EPDL", "NIST"),  # "simulated" does not work
            },
        ),
    }

    def __initcpp__(self):
        g4.GateTLEDoseActor.__init__(self, self.user_info)
        self.AddActions(
            {
                "BeginOfRunActionMasterThread",
                "EndOfRunActionMasterThread",
                "BeginOfRunAction",
                "EndOfRunAction",
                "BeginOfEventAction",
                "SteppingAction",
                "PreUserTrackingAction",
            }
        )

    def initialize(self, *args):
        if self.score_in != "material":
            fatal(
                f"TLEDoseActor cannot score in {self.score_in}, only 'material' is allowed."
            )
        super().initialize(args)


def _setter_hook_score_in_let_actor(self, value):
    if value.lower() in ("g4_water", "g4water"):
        """Assuming a misspelling of G4_WATER and correcting it to correct spelling; Note that this is rather dangerous operation."""
        return "G4_WATER"
    else:
        return value


class LETActor(VoxelDepositActor, g4.GateLETActor):
    """This actor scores the Linear Energy Transfer (LET) on a voxel grid in the volume to which the actor is attached. Note that the LET Actor puts a virtual grid on the volume it is attached to. Any changes on the LET Actor will not influence the geometry/material or physics of the particle tranpsort simulation."""

    # hints for IDE
    averaging_method: str
    score_in: str

    user_info_defaults = {
        "averaging_method": (
            "dose_average",
            {
                "doc": "The LET actor returns either dose or fluence (also called track) average. Select the type with this command.",
                "allowed_values": ("dose_average", "track_average"),
            },
        ),
        "score_in": (
            "G4_WATER",
            {
                "doc": "The score_in command allows to convert the LET from the material, "
                "which is defined in the geometry, to any user defined material. "
                "Note that this does not change the material definition in the geometry. "
                "The default value is 'material', which means that no conversion is "
                "performed and the LET to the local material is scored. "
                "You can use any material defined in the simulation "
                "or pre-defined by Geant4 such as 'G4_WATER', "
                "which may be one of the most use cases of this functionality.",
                "setter_hook": _setter_hook_score_in_let_actor,
            },
        ),
        "separate_output": (
            False,
            {
                "doc": "FIXME",
                "deprecated": "Denominator and numerator images are automatically handled and stored. ",
            },
        ),
    }

    user_output_config = {
        "let": {
            "actor_output_class": ActorOutputQuotientMeanImage,
            "interfaces": {
                "numerator": {
                    "interface_class": UserInterfaceToActorOutputImage,
                    "item": 0,
                    "active": True,
                    "write_to_disk": False,
                },
                "denominator": {
                    "interface_class": UserInterfaceToActorOutputImage,
                    "item": 1,
                    "active": True,
                    "write_to_disk": False,
                },
                "let": {
                    "interface_class": UserInterfaceToActorOutputImage,
                    "item": "quotient",
                    "write_to_disk": True,
                    "active": True,
                    "suffix": None,  # default suffix would be 'let', but we prefer no suffix
                },
            },
        },
    }

    def __init__(self, *args, **kwargs):
        VoxelDepositActor.__init__(self, *args, **kwargs)
        self.__initcpp__()

    def __initcpp__(self):
        g4.GateLETActor.__init__(self, self.user_info)
        self.AddActions(
            {
                "BeginOfRunActionMasterThread",
                "EndOfRunActionMasterThread",
                "BeginOfEventAction",
            }
        )

    def initialize(self):
        """
        At the start of the run, the image is centered according to the coordinate system of
        the attached volume. This function computes the correct origin = center + translation.
        Note that there is a half-pixel shift to align according to the center of the pixel,
        like in ITK.
        """
        VoxelDepositActor.initialize(self)

        self.check_user_input()

        self.InitializeUserInfo(self.user_info)
        # Set the physical volume name on the C++ side
        self.SetPhysicalVolumeName(self.get_physical_volume_name())
        self.InitializeCpp()

    def BeginOfRunActionMasterThread(self, run_index):
        self.prepare_output_for_run("let", run_index)
        # self.prepare_output_for_run("let_numerator", run_index)
        # self.prepare_output_for_run("let_denominator", run_index)

        self.push_to_cpp_image(
            "let", run_index, self.cpp_numerator_image, self.cpp_denominator_image
        )
        g4.GateLETActor.BeginOfRunActionMasterThread(self, run_index)

    def EndOfRunActionMasterThread(self, run_index):
        self.fetch_from_cpp_image(
            "let", run_index, self.cpp_numerator_image, self.cpp_denominator_image
        )
        self._update_output_coordinate_system("let", run_index)
        self.user_output.let.store_meta_data(
            run_index, number_of_samples=self.NbOfEvent
        )

        VoxelDepositActor.EndOfRunActionMasterThread(self, run_index)
        return 0

    def EndSimulationAction(self):
        g4.GateLETActor.EndSimulationAction(self)
        VoxelDepositActor.EndSimulationAction(self)


class ProductionAndStoppingActor(VoxelDepositActor, g4.GateProductionAndStoppingActor):
    """This actor scores the number of particles stopping or starting in a voxel grid in the volume to which the actor is attached to."""

    # hints for IDE
    method: str

    user_info_defaults = {
        "method": (
            "stopping",
            {
                "doc": "Want to score production or stopping of particles?",
                "allowed_values": ("production", "stopping"),
            },
        )
    }

    user_output_config = {
        "production_stopping": {
            "actor_output_class": ActorOutputSingleImage,
        },
    }

    def __init__(self, *args, **kwargs):
        VoxelDepositActor.__init__(self, *args, **kwargs)

        self.__initcpp__()

    def __initcpp__(self):
        g4.GateProductionAndStoppingActor.__init__(self, self.user_info)
        self.AddActions(
            {
                "BeginOfRunActionMasterThread",
                "EndOfRunActionMasterThread",
                "BeginOfEventAction",
            }
        )

    def initialize(self):
        """
        At the start of the run, the image is centered according to the coordinate system of
        the attached volume. This function computes the correct origin = center + translation.
        Note that there is a half-pixel shift to align according to the center of the pixel,
        like in ITK.
        """
        VoxelDepositActor.initialize(self)

        self.check_user_input()

        self.InitializeUserInfo(self.user_info)
        # Set the physical volume name on the C++ side
        self.SetPhysicalVolumeName(self.get_physical_volume_name())
        self.InitializeCpp()

    def BeginOfRunActionMasterThread(self, run_index):
        self.prepare_output_for_run("production_stopping", run_index)

        self.push_to_cpp_image("production_stopping", run_index, self.cpp_value_image)
        g4.GateProductionAndStoppingActor.BeginOfRunActionMasterThread(self, run_index)

    def EndOfRunActionMasterThread(self, run_index):
        self.fetch_from_cpp_image(
            "production_stopping", run_index, self.cpp_value_image
        )
        self._update_output_coordinate_system("production_stopping", run_index)
        self.user_output.production_stopping.store_meta_data(run_index)

        VoxelDepositActor.EndOfRunActionMasterThread(self, run_index)
        return 0

    def EndSimulationAction(self):
        g4.GateProductionAndStoppingActor.EndSimulationAction(self)
        VoxelDepositActor.EndSimulationAction(self)


class FluenceActor(VoxelDepositActor, g4.GateFluenceActor):
    """
    FluenceActor: compute a 3D map of fluence
    FIXME: add scatter order and uncertainty
    """

    # hints for IDE
    uncertainty: bool
    scatter: bool

    user_info_defaults = {
        "uncertainty": (
            False,
            {
                "doc": "FIXME",
            },
        ),
        "scatter": (
            False,
            {
                "doc": "FIXME",
            },
        ),
    }

    user_output_config = {
        "fluence": {
            "actor_output_class": ActorOutputSingleImage,
        },
    }

    def __init__(self, *args, **kwargs):
        VoxelDepositActor.__init__(self, *args, **kwargs)
        self.__initcpp__()

    def __initcpp__(self):
        g4.GateFluenceActor.__init__(self, self.user_info)
        self.AddActions(
            {
                "BeginOfRunActionMasterThread",
                "EndOfRunActionMasterThread",
                "BeginOfEventAction",
            }
        )

    def initialize(self):
        VoxelDepositActor.initialize(self)

        self.check_user_input()

        # no options yet
        if self.uncertainty or self.scatter:
            fatal("FluenceActor : uncertainty and scatter not implemented yet")

        self.InitializeUserInfo(self.user_info)
        # Set the physical volume name on the C++ side
        self.SetPhysicalVolumeName(self.get_physical_volume_name())
        self.InitializeCpp()

    def BeginOfRunActionMasterThread(self, run_index):
        self.prepare_output_for_run("fluence", run_index)
        self.push_to_cpp_image("fluence", run_index, self.cpp_fluence_image)
        g4.GateFluenceActor.BeginOfRunActionMasterThread(self, run_index)

    def EndOfRunActionMasterThread(self, run_index):
        self.fetch_from_cpp_image("fluence", run_index, self.cpp_fluence_image)
        self._update_output_coordinate_system("fluence", run_index)
        self.user_output.fluence.store_meta_data(
            run_index, number_of_samples=self.NbOfEvent
        )
        VoxelDepositActor.EndOfRunActionMasterThread(self, run_index)
        return 0

    def EndSimulationAction(self):
        g4.GateFluenceActor.EndSimulationAction(self)
        VoxelDepositActor.EndSimulationAction(self)


process_cls(VoxelDepositActor)
process_cls(DoseActor)
process_cls(TLEDoseActor)
process_cls(LETActor)
process_cls(FluenceActor)
process_cls(ProductionAndStoppingActor)
