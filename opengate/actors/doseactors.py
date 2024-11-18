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
                "doc": "3D size of the dose grid (in number of voxels).",
            },
        ),
        "spacing": (
            [1 * g4_units.mm, 1 * g4_units.mm, 1 * g4_units.mm],
            {
                "doc": "Voxel spacing along the x-, y-, z-axes. "
                "The user sets the units by multiplication with g4_units.XX. "
                "The default spacing is in g4_unit.mm. ",
            },
        ),
        "translation": (
            [0, 0, 0],
            {
                # FIXME: check reference for translation of dose actor
                "doc": "FIXME: Translation with respect to the XXX ",
            },
        ),
        "rotation": (
            Rotation.identity().as_matrix(),
            {
                "doc": "FIXME",
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
                "doc": "How to determine the position to which the deposited quantity is associated, "
                "i.e. at the beginning or end of a Geant4 step, or somewhere in between. ",
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
                "doc": "FIXME",
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
    """
    DoseActor: compute a 3D edep/dose map for deposited
    energy/absorbed dose in the attached volume

    By default, the dose actor is centered according to the "attachedTo" volume center
    If the attachedTo volume is an Image AND the option "img_coord_system" is True:
    the origin of the attachedTo image is used for the output dose.
    Hence, the dose can be superimposed with the attachedTo volume.
    """

    # hints for IDE
    use_more_ram: bool
    score_in: str

    user_info_defaults = {
        "square": (
            True,
            {
                "doc": "FIXME",
                "deprecated": "Use: my_actor.user_output.square.active=True/False "
                "to request uncertainty scoring of the respective quantity, "
                "where 'my_actor' should be your actor object. "
                "Note: activating user_output.edep_uncertainty or user_output.dose_uncertainty "
                "implies activating user_output.square. ",
            },
        ),
        "uncertainty": (
            True,
            {
                "doc": "FIXME",
                "deprecated": "Use: my_actor.user_output.dose_uncertainty.active=True/False and"
                "my_actor.user_output.edep_uncertainty.active=True/False "
                "to request uncertainty scoring of the respective quantity, "
                "where 'my_actor' should be your actor object. ",
                # "setter_hook": _setter_hook_uncertainty,
            },
        ),
        "dose": (
            False,
            {
                "doc": "FIXME",
                "deprecated": "Use: my_actor.user_output.dose.active=True/False "
                "to request the actor to score dose, "
                "where 'my_actor' should be your actor object. "
                "By default, only the deposited energy is scored. ",
            },
        ),
        "to_water": (
            False,
            {
                "deprecated": "Use my_dose_actor.score_in='water' instead. ",
            },
        ),
        "score_in": (
            "material",
            {
                "doc": "In which kind of material should the deposited quantities be scored? "
                "'material' means the material defined by the volume to which the actor is attached. ",
                "allowed_values": (
                    "material",
                    "water",
                ),
            },
        ),
        "ste_of_mean": (
            False,
            {
                "doc": "FIXME",
                "setter_hook": _setter_hook_ste_of_mean,
                "deactivated": True,
            },
        ),
        "ste_of_mean_unbiased": (
            False,
            {
                "doc": "FIXME",
                "setter_hook": _setter_hook_ste_of_mean_unbiased,
                "deactivated": True,
            },
        ),
        "uncertainty_goal": (
            None,
            {
                "doc": "If set, it defines the statistical uncertainty at which the run is aborted.",
                "setter_hook": _setter_hook_uncertainty_goal,
            },
        ),
        "uncertainty_first_check_after_n_events": (
            1e4,
            {
                "doc": "Number of events after which uncertainty is evaluated the first time, for each run."
                "After the first evaluation, the value is updated with an estimation of the N events needed to achieve the target uncertainty.",
            },
        ),
        "uncertainty_voxel_edep_threshold": (
            0.7,
            {
                "doc": "For the calculation of the mean uncertainty of the edep image, only voxels that are above this fraction of the max edep are considered.",
            },
        ),
        "uncertainty_overshoot_factor_N_events": (
            1.05,
            {
                "doc": "Factor multiplying the estimated N events needed to achieve the target uncertainty, to ensure faster convergence.",
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

    def __init__(self, *args, **kwargs):
        VoxelDepositActor.__init__(self, *args, **kwargs)

        # **** EDEP ****
        # This creates a user output with two components: 0=edep, 1=edep_squared
        # additionally, it also provides variance, std, and uncertainty via dynamic properties
        self._add_user_output(
            ActorOutputSingleImageWithVariance,
            "edep_with_uncertainty",
            automatically_generate_interface=False,
        )
        # create an interface to item 0 of user output "edep_with_uncertainty"
        # and make it available via a property 'edep' in this actor
        self._add_interface_to_user_output(
            UserInterfaceToActorOutputImage, "edep_with_uncertainty", "edep", item=0
        )
        # create an interface to item 1 of user output "edep_with_uncertainty"
        # and make it available via a property 'square' in this actor
        self._add_interface_to_user_output(
            UserInterfaceToActorOutputImage,
            "edep_with_uncertainty",
            "edep_squared",
            item=1,
        )
        # create an interface to item 'uncertainty' of user output "edep_with_uncertainty"
        # and make it available via a property 'edep_uncertainty' in this actor
        self._add_interface_to_user_output(
            UserInterfaceToActorOutputImage,
            "edep_with_uncertainty",
            "edep_uncertainty",
            item="uncertainty",
        )

        # **** DOSE ****
        self._add_user_output(
            ActorOutputSingleImageWithVariance,
            "dose_with_uncertainty",
            automatically_generate_interface=False,
        )
        # create an interface to item 0 of user output "dose_with_uncertainty"
        # and make it available via a property 'dose' in this actor
        self._add_interface_to_user_output(
            UserInterfaceToActorOutputImage, "dose_with_uncertainty", "dose", item=0
        )
        # create an interface to item 1 of user output "dose_with_uncertainty"
        # and make it available via a property 'dose_squared' in this actor
        self._add_interface_to_user_output(
            UserInterfaceToActorOutputImage,
            "dose_with_uncertainty",
            "dose_squared",
            item=1,
        )
        self._add_interface_to_user_output(
            UserInterfaceToActorOutputImage,
            "dose_with_uncertainty",
            "dose_uncertainty",
            item="uncertainty",
        )

        # set the defaults for the user output of this actor
        self._add_user_output(ActorOutputSingleMeanImage, "density")
        self._add_user_output(ActorOutputSingleImage, "counts")
        self.user_output.dose_with_uncertainty.set_active(False, item="all")
        self.user_output.density.set_active(False)
        self.user_output.counts.set_active(False)

        # item suffix is used when the filename is auto-generated or
        # when the user sets one filename per actor
        self.user_output.edep_with_uncertainty.set_item_suffix("edep", item=0)
        self.user_output.edep_with_uncertainty.set_item_suffix("edep_squared", item=1)
        self.user_output.edep_with_uncertainty.set_item_suffix(
            "edep_uncertainty", item="uncertainty"
        )
        self.user_output.dose_with_uncertainty.set_item_suffix("dose", item=0)
        self.user_output.dose_with_uncertainty.set_item_suffix("dose_squared", item=1)
        self.user_output.dose_with_uncertainty.set_item_suffix(
            "dose_uncertainty", item="uncertainty"
        )
        # The following 2 are single item output and item=0 is default
        self.user_output.density.set_item_suffix("density")
        self.user_output.counts.set_item_suffix("counts")

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
        self.SetToWaterFlag(self.score_in == "water")

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
    """
    TLE = Track Length Estimator
    """

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
    if value in ("water", "Water"):
        return "G4_WATER"
    else:
        return value


class LETActor(VoxelDepositActor, g4.GateLETActor):
    """
    LET = Linear energy transfer
    LETActor: compute a 3D edep/dose map for deposited
    energy/absorbed dose in the attached volume

    The dose map is parameterized with:
        - size (number of voxels)
        - spacing (voxel size)
        - translation (according to the coordinate system of the "attachedTo" volume)
        - no rotation

    Position:
    - by default: centered according to the "attachedTo" volume center
    - if the attachedTo volume is an Image AND the option "img_coord_system" is True:
        the origin of the attachedTo image is used for the output dose.
        Hence, the dose can be superimposed with the attachedTo volume

    Options
        - LETd only for the moment
        - later: LETt, Q, fluence ...
    """

    # hints for IDE
    averaging_method: str
    score_in: str

    user_info_defaults = {
        "averaging_method": (
            "dose_average",
            {
                "doc": "How to calculate the LET?",
                "allowed_values": ("dose_average", "track_average"),
            },
        ),
        "dose_average": (
            False,
            {
                "doc": "Calculate dose-averaged LET?",
                "deprecated": "Use averaging_method='dose_average' instead",
            },
        ),
        "track_average": (
            False,
            {
                "doc": "Calculate track-averaged LET?",
                "deprecated": "Use averaging_method='track_average' instead",
            },
        ),
        "score_in": (
            "G4_WATER",
            {
                "doc": "In which material should the LET be scored? "
                "You can provide a valid G4 material name, the term 'water', "
                "or the term 'material' which means 'the local material where LET is scored. ",
                "setter_hook": _setter_hook_score_in_let_actor,
            },
        ),
        "let_to_other_material": (
            False,
            {
                "doc": "FIXME",
                "deprecated": "Use score_in=... to specifiy in which material LET should be scored. ",
            },
        ),
        "let_to_water": (
            True,
            {
                "doc": "FIXME",
                "deprecated": "Use score_in=... to specifiy in which material LET should be scored. ",
            },
        ),
        "other_material": (
            None,
            {
                "doc": "FIXME",
                "deprecated": "Use score_in=... to specifiy in which material LET should be scored. ",
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

    def __init__(self, *args, **kwargs):
        VoxelDepositActor.__init__(self, *args, **kwargs)

        self._add_user_output(
            ActorOutputQuotientMeanImage, "let", automatically_generate_interface=False
        )
        self._add_interface_to_user_output(
            UserInterfaceToActorOutputImage, "let", "numerator", item=0
        )
        self._add_interface_to_user_output(
            UserInterfaceToActorOutputImage, "let", "denominator", item=1
        )
        self._add_interface_to_user_output(
            UserInterfaceToActorOutputImage, "let", "let", item="quotient"
        )

        # configure the default item config for the output of the LET actor,
        # which is different from the generic quotient image container class:

        # Suffix to be appended in case a common output_filename per actor is assigned
        self.user_output.let.set_item_suffix(None, item="quotient")
        self.user_output.let.set_item_suffix("numerator", item=0)
        self.user_output.let.set_item_suffix("denominator", item=1)

        # the LET always needs both components to calculate LET
        self.user_output.let.set_active(True, item=0)
        self.user_output.let.set_active(True, item=1)

        # Most users will probably only want the LET image written to disk,
        # not the numerator and denominator
        self.user_output.let.set_write_to_disk(False, item=0)
        self.user_output.let.set_write_to_disk(False, item=1)
        self.user_output.let.set_write_to_disk(True, item="quotient")

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

    def __init__(self, *args, **kwargs):
        VoxelDepositActor.__init__(self, *args, **kwargs)

        # self.py_fluence_image = None
        self._add_user_output(ActorOutputSingleImage, "fluence")

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
