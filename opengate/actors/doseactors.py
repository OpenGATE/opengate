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
    divide_itk_images,
    scale_itk_image,
    get_info_from_image,
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
                "(The user set the units by multiplication with g4_units.XX)",
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
                "If no output_filename is provided, it will be generated automatically. \n"
                "To specify whether the actor output should be written to disk, use write_to_disk=True/False."
            },
        ),
        "img_coord_system": (
            None,
            {
                "deprecated": f"The user input parameter 'img_coord_system' is deprecated. "
                f"Use my_actor.output_coordinate_system='attached_to_image' instead, "
                f"where my_actor should be replaced with your actor object. ",
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

    def __init__(self, *args, **kwargs):
        ActorBase.__init__(self, *args, **kwargs)

    def check_user_input(self):
        if self.output_coordinate_system == "attached_to_image":
            if not hasattr(
                self.attached_to_volume, "native_translation"
            ) or not hasattr(self.attached_to_volume, "native_rotation"):
                fatal(
                    f"User input 'output_coordinate_system' = {self.output_coordinate_system} is not compatible "
                    f"with the volume to which this actor is attached: "
                    f"{self.attached_to} ({self.attached_to_volume.volume_type})"
                )

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

    def EndSimulationAction(self):
        # inform actor output that this simulation is over and write data
        for u in self.user_output.values():
            if u.get_active(item="all"):
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


def _setter_hook_goal_uncertainty(self, value):
    if value < 0.0 or value > 1.0:
        fatal(f"Goal uncertainty must be > 0 and < 1. The provided value is: {value}")
    return value


class DoseActor(VoxelDepositActor, g4.GateDoseActor):
    """
    DoseActor: compute a 3D edep/dose map for deposited
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
        - edep only for the moment
        - later: add dose, uncertainty, squared etc

    """

    # hints for IDE
    use_more_ram: bool
    score_in: str

    user_info_defaults = {
        "use_more_ram": (
            False,
            {
                "doc": "FIXME",
                "deactivated": True,
            },
        ),
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
        "goal_uncertainty": (
            0,
            {
                "doc": "FIXME",
                "setter_hook": _setter_hook_goal_uncertainty,
                "deprecated": "Currently not implemented. ",
            },
        ),
        "thresh_voxel_edep_for_unc_calc": (
            0.7,
            {
                "doc": "FIXME",
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

        self._add_user_output(
            ActorOutputSingleImage,
            "dose",
        )

        self._add_user_output(
            ActorOutputSingleImage,
            "dose_uncertainty",
        )

        self._add_user_output(ActorOutputSingleMeanImage, "density")

        self.user_output.dose.set_active(False)
        self.user_output.dose_uncertainty.set_active(False)

        self.user_output.edep_with_uncertainty.set_item_suffix("edep", item=0)
        self.user_output.edep_with_uncertainty.set_item_suffix("edep_squared", item=1)
        self.user_output.edep_with_uncertainty.set_item_suffix(
            "edep_uncertainty", item="uncertainty"
        )
        self.user_output.dose.set_item_suffix("dose")
        self.user_output.dose_uncertainty.set_item_suffix("dose_uncertainty")
        self.user_output.density.set_item_suffix("density")

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
            }
        )

    def compute_dose_from_edep_img(self, input_image, density_image=None):
        """
        * create mass image:
            - from ct HU units, if dose actor attached to ImageVolume.
            - from material density, if standard volume
        * compute dose as edep_image /  mass_image
        """
        vol = self.attached_to_volume
        voxel_volume = self.spacing[0] * self.spacing[1] * self.spacing[2]
        Gy = g4_units.Gy
        gcm3 = g4_units.g_cm3

        if vol.volume_type == "ImageVolume":
            if self.score_in == "water":
                # for dose to water, divide by density of water and not density of material
                scaled_image = scale_itk_image(input_image, 1 / (1.0 * gcm3))
            else:
                density_image = vol.create_density_image()
                if images_have_same_domain(input_image, density_image) is False:
                    density_image = resample_itk_image_like(
                        density_image, input_image, 0, linear=True
                    )
                scaled_image = divide_itk_images(
                    img1_numerator=input_image,
                    img2_denominator=density_image,
                    filterVal=0,
                    replaceFilteredVal=0,
                )
            # divide by voxel volume and convert unit
            scaled_image = scale_itk_image(scaled_image, 1 / (Gy * voxel_volume))

        else:
            if self.score_in == "water":
                # for dose to water, divide by density of water and not density of material
                scaled_image = scale_itk_image(input_image, 1 / (1.0 * gcm3))
            else:
                # the dose actor is attached to a volume, we need the density image
                # to be computed from the cpp side
                if density_image is None:
                    fatal(f"A density image computed via the G4 simulation is needed.")
                scaled_image = divide_itk_images(
                    img1_numerator=input_image,
                    img2_denominator=density_image,
                    filterVal=0,
                    replaceFilteredVal=0,
                )
            # divide by voxel volume and convert unit
            scaled_image = scale_itk_image(scaled_image, 1 / (Gy * voxel_volume))

        return scaled_image

    def initialize(self, *args):
        """
        At the start of the run, the image is centered according to the coordinate system of
        the attached volume. This function computes the correct origin = center + translation.
        Note that there is a half-pixel shift to align according to the center of the pixel,
        like in ITK.
        """
        self.check_user_input()

        VoxelDepositActor.initialize(self)

        # dose uncertainty relies on edep_uncertainty. Set active flag accordingly
        if self.user_output.dose_uncertainty.get_active() is True:
            self.user_output.dose.set_active(True)
            self.user_output.edep_with_uncertainty.set_active(True, item="uncertainty")
        # Make sure the squared component (item 1) is active if any of the quantities relying on it are active
        if (
            self.user_output.edep_with_uncertainty.get_active(
                item=("uncertainty", "std", "variance")
            )
            is True
        ):
            self.user_output.edep_with_uncertainty.set_active(
                True, item=1
            )  # activate squared component

        # activate density if we need the dose and the DoseActor is not attached to a volume
        if (
            self.user_output.dose.get_active() is True
            and self.attached_to_volume.volume_type != "ImageVolume"
        ):
            if not self.user_output.density.get_active():
                self.user_output.density.set_active(True)
                self.user_output.density.set_write_to_disk(False)

        self.InitializeUserInput(self.user_info)  # C++ side
        self.SetSquareFlag(self.user_output.edep_with_uncertainty.get_active(item=1))
        self.SetDensityFlag(
            self.user_output.density.get_active()
        )  # item=0 is the default
        self.SetToWaterFlag(self.score_in == "water")

        # Set the physical volume name on the C++ side
        self.SetPhysicalVolumeName(self.get_physical_volume_name())
        self.InitializeCpp()

    def BeginOfRunActionMasterThread(self, run_index):
        self.prepare_output_for_run("edep_with_uncertainty", run_index)
        self.push_to_cpp_image(
            "edep_with_uncertainty",
            run_index,
            self.cpp_edep_image,
            self.cpp_square_image,
        )

        if self.user_output.density.get_active():
            self.prepare_output_for_run("density", run_index)
            self.push_to_cpp_image("density", run_index, self.cpp_density_image)

        if self.user_output.dose_uncertainty.get_active():
            self.prepare_output_for_run("dose_uncertainty", run_index)

        g4.GateDoseActor.BeginOfRunActionMasterThread(self, run_index)

    def EndOfRunActionMasterThread(self, run_index):
        self.fetch_from_cpp_image(
            "edep_with_uncertainty",
            run_index,
            self.cpp_edep_image,
            self.cpp_square_image,
        )
        self._update_output_coordinate_system("edep_with_uncertainty", run_index)
        self.user_output.edep_with_uncertainty.store_meta_data(
            run_index, number_of_samples=self.NbOfEvent
        )

        # density image
        if self.user_output.density.get_active():
            self.fetch_from_cpp_image("density", run_index, self.cpp_density_image)
            self._update_output_coordinate_system("density", run_index)
            self.user_output.density.store_meta_data(
                run_index, number_of_samples=self.NbOfEvent
            )

        # dose
        if self.user_output.dose.get_active():
            edep_image = self.user_output.edep_with_uncertainty.get_data(
                run_index, item=0
            )
            density_image = None
            if self.user_output.density.get_active():
                density_image = self.user_output.density.get_data(run_index)
            dose_image = self.compute_dose_from_edep_img(edep_image, density_image)
            dose_image.CopyInformation(edep_image)
            self.store_output_data(
                "dose",
                run_index,
                dose_image,
            )
            self.user_output.dose.store_meta_data(
                run_index, number_of_samples=self.NbOfEvent
            )

        if self.user_output.dose_uncertainty.get_active() is True:
            # scale by density
            edep_uncertainty_image = self.user_output.edep_with_uncertainty.get_data(
                run_index, item="uncertainty"
            )
            density_image = None
            if self.user_output.density.get_active():
                density_image = self.user_output.density.get_data(run_index)
            dose_uncertainty_image = self.compute_dose_from_edep_img(
                edep_uncertainty_image, density_image
            )
            dose_uncertainty_image.CopyInformation(edep_uncertainty_image)
            self.user_output.dose_uncertainty.store_data(
                run_index, dose_uncertainty_image
            )
            self.user_output.dose_uncertainty.store_meta_data(
                run_index, number_of_samples=self.NbOfEvent
            )

        VoxelDepositActor.EndOfRunActionMasterThread(self, run_index)

        # FIXME: should check if uncertainty goal is reached (return value: 0),
        # but the current mechanism is quite hacky and it is therefore temporarily not in use!
        return 0

    def EndSimulationAction(self):
        g4.GateDoseActor.EndSimulationAction(self)
        VoxelDepositActor.EndSimulationAction(self)


def _setter_hook_score_in_let_actor(self, value):
    if value in ("water", "Water"):
        return "G4_WATER"
    else:
        return value


class LETActor(VoxelDepositActor, g4.GateLETActor):
    """
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

        self.InitializeUserInput(self.user_info)
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
            fatal(f"FluenceActor : uncertainty and scatter not implemented yet")

        self.InitializeUserInput(self.user_info)
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
process_cls(LETActor)
process_cls(FluenceActor)
