import itk
import numpy as np
import opengate_core as g4
from .base import ActorBase
from ..exception import fatal, warning
from ..utility import (
    g4_units,
    ensure_filename_is_str,
    standard_error_c4_correction,
)
from ..image import (
    create_3d_image,
    align_image_with_physical_volume,
    update_image_py_to_cpp,
    create_image_like,
    get_info_from_image,
    get_origin_wrt_images_g4_position,
    get_py_image_from_cpp_image,
    itk_image_view_from_array,
    divide_itk_images,
    scale_itk_image,
    write_itk_image,
)
from ..geometry.materials import create_density_img
from ..base import process_cls


class VoxelDepositActor(ActorBase):
    """Base class which holds user input parameters common to all actors
    that deposit quantities in a voxel grid, e.g. the DoseActor.
    """

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
                "doc": "File (path) to which the output image should be written. ",
            },
        ),
        "img_coord_system": (
            False,
            {
                "doc": "FIXME",
            },
        ),
        "output_origin": (
            None,
            {
                "doc": "FIXME",
            },
        ),
    }

    def __init__(self, *args, **kwargs):
        ActorBase.__init__(self, *args, **kwargs)
        # attached physical volume (at init)
        self.g4_phys_vol = None
        # internal states
        self.img_origin_during_run = None
        self.first_run = None

    def initialize(self):
        super().initialize()
        size = np.array(self.size)
        spacing = np.array(self.spacing)
        # compute the center, using translation and half pixel spacing
        self.img_origin_during_run = (
            -size * spacing / 2.0 + spacing / 2.0 + self.translation
        )
        # for initialization during the first run
        self.first_run = True

    def get_physical_volume_name(self):
        # init the origin and direction according to the physical volume
        # (will be updated in the BeginOfRun)
        if self.repeated_volume_index is None:
            repeated_volume_index = 0
        else:
            repeated_volume_index = self.user_info.repeated_volume_index
        try:
            g4_phys_volume = self.attached_to_volume.g4_physical_volumes[
                repeated_volume_index
            ]
        except IndexError:
            fatal(
                f"Error in the {self.actor_type} named {self.name}. "
                f"Could not find the physical volume with index {repeated_volume_index} "
                f"in volume '{self.attached_to}' to which this actor is attached. "
            )
        # Return the real physical volume name
        return str(g4_phys_volume.GetName())

    def align_output_with_physical_volume(self, which_output, run_index):
        self._assert_output_exists(which_output)
        align_image_with_physical_volume(
            self.attached_to_volume,
            self.user_output[which_output].data_per_run[run_index],
            initial_translation=self.translation,
        )

    def update_output_origin(self, output_name, run_index):
        # If attached to a voxelized volume, we may want to use its coord system.
        # So, we compute in advance what will be the final origin of the dose map
        self._assert_output_exists(output_name)

        output_origin = self.img_origin_during_run

        vol_type = self.simulation.volume_manager.get_volume(
            self.attached_to
        ).volume_type

        if self.output_origin in ["image", "img_coord_system", "image_coord_system"]:
            if vol_type == "ImageVolume":
                # Translate the output dose map so that its center correspond to the image center.
                # The origin is thus the center of the first voxel.
                volume_image_info = get_info_from_image(
                    self.attached_to_volume.itk_image
                )
                self._assert_output_exists(output_name)
                output_image_info = self.user_output[output_name].data_per_run[
                    run_index
                ]
                output_origin = get_origin_wrt_images_g4_position(
                    volume_image_info, output_image_info, self.translation
                )
            else:
                fatal(
                    f"{self.actor_type} '{self.name}' has "
                    f"the user input parameter 'output_origin' set to {self.output_origin}, "
                    f"but it is not attached to an ImageVolume. Instead, it is attached to "
                    f"volume '{self.attached_to_volume.name}' of type '{vol_type}'). "
                )
        # take the user-defined output origin
        elif self.output_origin is not None:
            output_origin = self.output_origin

        self.user_output[output_name].set_image_properties(
            run_index, origin=output_origin
        )

        return output_origin

    def prepare_output_for_run(self, output_name, run_index, **kwargs):
        self._assert_output_exists(output_name)
        self.user_output[output_name].size = self.size
        self.user_output[output_name].spacing = self.spacing
        self.user_output[output_name].create_empty_image(run_index, **kwargs)
        self.align_output_with_physical_volume(output_name, run_index)

    def fetch_from_cpp_image(self, cpp_image, output_name, run_index):
        self._assert_output_exists(output_name)
        self.user_output[output_name].update_from_cpp_image(
            cpp_image, run_index=run_index
        )

    def push_to_cpp_image(self, cpp_image, output_name, run_index, copy_data=False):
        self._assert_output_exists(output_name)
        update_image_py_to_cpp(
            # FIXME: run_index 0 is hard-coded. actors need to become run_index-aware
            self.user_output[output_name].data_per_run[0],
            cpp_image,
            copy_data,
        )

    def EndOfRunActionMasterThread(self, run_index):
        # inform actor output that this run is over
        for u in self.user_output.values():
            u.end_of_run(run_index)

    def EndSimulationAction(self):
        # inform actor output that this simulation is over and write data
        for u in self.user_output.values():
            u.end_of_simulation()
            u.write_data_if_requested("all")


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
        # unc = np.ma.masked_array(
        #     unc, unc < 0
        # )  # this function leaves unc<0 values untouched! what do we do with < 0 values?
        # unc = np.ma.sqrt(unc)
        if correct_bias:
            # Standard error is biased (to underestimate the error);
            # this option allows to correct for the bias - assuming normal distribution.
            # For few N this influence is huge, but for N>8 the difference is minimal
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

    user_info_defaults = {
        "use_more_ram": (
            False,
            {
                "doc": "FIXME",
            },
        ),
        "square": (
            False,
            {
                "doc": "FIXME",
            },
        ),
        "uncertainty": (
            True,
            {
                "doc": "FIXME",
            },
        ),
        "dose": (
            False,
            {
                "doc": "FIXME",
            },
        ),
        "to_water": (
            False,
            {
                "doc": "FIXME",
            },
        ),
        "ste_of_mean": (
            False,
            {
                "doc": "FIXME",
            },
        ),
        "ste_of_mean_unbiased": (
            False,
            {
                "doc": "FIXME",
            },
        ),
        "goal_uncertainty": (
            0,
            {
                "doc": "FIXME",
            },
        ),
        "thresh_voxel_edep_for_unc_calc": (
            0.7,
            {
                "doc": "FIXME",
            },
        ),
        "dose_calc_on_the_fly": (
            True,
            {
                "doc": "FIXME",
            },
        ),
    }

    def __init__(self, *args, **kwargs):
        VoxelDepositActor.__init__(self, *args, **kwargs)
        g4.GateDoseActor.__init__(self, self.user_info)
        if self.ste_of_mean_unbiased or self.ste_of_mean:
            self.ste_of_mean = True
            self.use_more_ram = True

        self._add_user_output("image", "edep")
        self._add_user_output("image", "dose")
        self._add_user_output("image", "dose_to_water")
        self._add_user_output("image", "squared")
        self._add_user_output("image", "uncertainty")

    def __getstate__(self):
        # superclass getstate
        return_dict = super().__getstate__()
        return_dict["g4_phys_vol"] = None
        return return_dict

    def check_user_input(self):
        if self.goal_uncertainty < 0.0 or self.goal_uncertainty > 1.0:
            raise ValueError("goal uncertainty must be > 0 and < 1")

        if self.ste_of_mean_unbiased:
            self.ste_of_mean = True

        if self.ste_of_mean:
            self.use_more_RAM = True

        if self.ste_of_mean is True and self.simulation.number_of_threads <= 4:
            raise ValueError(
                "number_of_threads should be > 4 when using dose actor with ste_of_mean flag enabled"
            )

        if self.goal_uncertainty:
            if self.uncertainty is False and self.ste_of_mean is False:
                raise ValueError(
                    "To set an uncertainty goal, set at least one of this flags to True: uncertainty, ste_of_mean"
                )

        if self.uncertainty is True and self.ste_of_mean is True:
            raise ValueError(
                "select only one way to calculate uncertainty: uncertainty or ste_of_mean"
            )

    def initialize(self, *args):
        """
        At the start of the run, the image is centered according to the coordinate system of
        the mother volume. This function computes the correct origin = center + translation.
        Note that there is a half-pixel shift to align according to the center of the pixel,
        like in ITK.
        """
        self.check_user_input()

        VoxelDepositActor.initialize(self)

        self.InitializeUserInput(self.user_info)  # C++ side
        # Set the physical volume name on the C++ side
        self.fPhysicalVolumeName = self.get_physical_volume_name()
        self.ActorInitialize()

    def BeginOfRunActionMasterThread(self, run_index):
        self.prepare_output_for_run("edep", run_index)
        self.prepare_output_for_run("dose", run_index)
        self.prepare_output_for_run("dose_to_water", run_index)
        self.prepare_output_for_run("squared", run_index)
        self.prepare_output_for_run("uncertainty", run_index)

        self.push_to_cpp_image(self.cpp_edep_image, "edep", run_index)
        self.push_to_cpp_image(self.cpp_square_image, "square", run_index)

    def EndOfRunActionMasterThread(self, run_index):
        # edep
        self.fetch_from_cpp_image(self.cpp_edep_image, "edep", run_index)
        self.update_output_origin("edep", run_index)

        # dose
        if not self.dose_calc_on_the_fly and self.dose:
            self.store_output_data(
                "dose",
                self.compute_dose_from_edep_img(
                    self.user_output["edep"].data_per_run[run_index]
                ),
                run_index,
            )
            self.update_output_origin("dose", run_index)

        # square
        if any([self.uncertainty, self.ste_of_mean, self.square]):
            self.fetch_from_cpp_image(self.cpp_square_image, "square", run_index)
            self.update_output_origin("square", run_index)

        # uncertainty
        if any([self.uncertainty, self.ste_of_mean]):
            if self.ste_of_mean:
                n = (
                    self.simulation.number_of_threads
                )  # each thread is considered one subsample.
            else:
                n = self.NbOfEvent

            edep = itk.array_view_from_image(
                self.user_output["edep"].data_per_run[run_index]
            )
            square = itk.array_view_from_image(
                self.user_output["square"].data_per_run[run_index]
            )

            uncertainty_image = itk_image_view_from_array(
                compute_std_from_sample(
                    n, edep, square, correct_bias=self.user_info.ste_of_mean_unbiased
                )
            )
            uncertainty_image.CopyInformation(
                self.user_output["edep"].data_per_run[run_index]
            )
            self.user_output["uncertainty"].store_data(uncertainty_image, run_index)
            self.update_output_origin("uncertainty", run_index)

        VoxelDepositActor.EndOfRunActionMasterThread(self, run_index)

    def EndSimulationAction(self):
        g4.GateDoseActor.EndSimulationAction(self)
        VoxelDepositActor.EndSimulationAction(self)

    def compute_dose_from_edep_img(self, edep_image):
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
            material_database = (
                self.simulation.volume_manager.material_database.g4_materials
            )
            if self.to_water:
                # for dose to water, divide by density of water and not density of material
                dose_image = scale_itk_image(edep_image, 1 / (1.0 * gcm3))
            else:
                density_img = create_density_img(vol, material_database)
                dose_image = divide_itk_images(
                    img1_numerator=edep_image,
                    img2_denominator=density_img,
                    filterVal=0,
                    replaceFilteredVal=0,
                )
            # divide by voxel volume and convert unit
            dose_image = scale_itk_image(dose_image, 1 / (Gy * voxel_volume))

        else:
            if self.to_water:
                # for dose to water, divide by density of water and not density of material
                density = 1.0 * gcm3
            else:
                density = vol.g4_material.GetDensity()
            dose_image = scale_itk_image(edep_image, 1 / (voxel_volume * density * Gy))

        return dose_image


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

    user_info_defaults = {
        "dose_average": (
            False,
            {
                "doc": "Calculate dose-averaged LET?",
            },
        ),
        "track_average": (
            False,
            {
                "doc": "Calculate track-averaged LET?",
            },
        ),
        "let_to_other_material": (
            False,
            {
                "doc": "FIXME",
            },
        ),
        "let_to_water": (
            False,
            {
                "doc": "FIXME",
            },
        ),
        "other_material": (
            "",
            {
                "doc": "FIXME",
            },
        ),
        "separate_output": (
            False,
            {
                "doc": "FIXME",
            },
        ),
    }

    def __init__(self, *args, **kwargs):
        ## TODO: why not super? what would happen?
        VoxelDepositActor.__init__(self, *args, **kwargs)
        g4.GateLETActor.__init__(self, self.user_info)
        # default image (py side)

        self._add_user_output("image", "let")
        self._add_user_output("image", "let_denominator", write_to_disk=False)
        self._add_user_output("image", "let_numerator", write_to_disk=False)

    def __getstate__(self):
        # superclass getstate
        return_dict = VoxelDepositActor.__getstate__(self)
        # do not pickle itk images
        return_dict["py_numerator_image"] = None
        return_dict["py_denominator_image"] = None
        return_dict["py_output_image"] = None
        return return_dict

    def initialize(self):
        """
        At the start of the run, the image is centered according to the coordinate system of
        the mother volume. This function computes the correct origin = center + translation.
        Note that there is a half-pixel shift to align according to the center of the pixel,
        like in ITK.
        """
        VoxelDepositActor.initialize(self)

        if self.dose_average == self.track_average:
            fatal(
                f"Ambiguous to enable dose and track averaging: \ndose_average: {self.user_info.dose_average} \ntrack_average: {self.user_info.track_average} \nOnly one option can and must be set to True"
            )

        if self.other_material:
            self.let_to_other_material = True
        if self.let_to_other_material and not self.other_material:
            fatal(
                f"let_to_other_material enabled, but other_material not set: {self.other_material}"
            )
        if self.let_to_water:
            self.other_material = "G4_WATER"

        extra_suffix = ""
        if self.dose_average:
            extra_suffix = "letd"
        elif self.track_average:
            extra_suffix = "lett"
        if self.let_to_other_material or self.let_to_water:
            extra_suffix += f"_convto_{self.other_material}"
        extra_suffix.lstrip(
            "_"
        )  # make sure to remove left-sided underscore in case there is one

        self.user_output["let_numerator"].extra_suffix = extra_suffix
        self.user_output["let_denominator"].extra_suffix = extra_suffix
        self.user_output["let"].extra_suffix = extra_suffix

        self.InitializeUserInput(self.user_info)
        # Set the physical volume name on the C++ side
        self.fPhysicalVolumeName = self.get_physical_volume_name()
        self.ActorInitialize()

    def BeginOfRunActionMasterThread(self, run_index):
        self.prepare_output_for_run("let", run_index)
        self.prepare_output_for_run("let_numerator", run_index)
        self.prepare_output_for_run("let_denominator", run_index)

        self.push_to_cpp_image(self.cpp_numerator_image, "let_numerator", run_index)
        self.push_to_cpp_image(self.cpp_denominator_image, "let_denominator", run_index)

    def EndOfRunActionMasterThread(self, run_index):
        self.fetch_from_cpp_image(self.cpp_numerator_image, "let_numerator", run_index)
        self.fetch_from_cpp_image(
            self.cpp_denominator_image, "let_denominator", run_index
        )

        self.user_output["let"].store_data(
            divide_itk_images(
                img1_numerator=self.user_output["let_numerator"].data_per_run[
                    run_index
                ],
                img2_denominator=self.user_output["let_denominator"].data_per_run[
                    run_index
                ],
                filterVal=0,
                replaceFilteredVal=0,
            ),
            run_index,
        )

        VoxelDepositActor.EndOfRunActionMasterThread(self, run_index)

    def EndSimulationAction(self):
        g4.GateLETActor.EndSimulationAction(self)

        self.user_output["let"].write_data_if_requested("all")
        self.user_output["let_numerator"].write_data_if_requested("all")
        self.user_output["let_denominator"].write_data_if_requested("all")


class FluenceActor(VoxelDepositActor, g4.GateFluenceActor):
    """
    FluenceActor: compute a 3D map of fluence

    FIXME: add scatter order and uncertainty
    """

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
        VoxelDepositActor.__init__(self)
        g4.GateFluenceActor.__init__(self, self.user_info)

        # self.py_fluence_image = None
        self._add_user_output("image", "fluence")

    def __getstate__(self):
        return VoxelDepositActor.__getstate__(self)

    def initialize(self):
        VoxelDepositActor().initialize()
        self.prepare_output_for_run("fluence")

        # no options yet
        if self.uncertainty or self.scatter:
            fatal(f"FluenceActor : uncertainty and scatter not implemented yet")

        self.InitializeUserInput(self.user_info)
        # Set the physical volume name on the C++ side
        self.fPhysicalVolumeName = self.get_physical_volume_name()
        self.ActorInitialize()

    def StartSimulationAction(self):
        # FIXME for multiple run and motion
        if not self.first_run:
            warning(f"Not implemented yet: FluenceActor with several runs")
        # send itk image to cpp side, copy data only the first run.
        update_image_py_to_cpp(
            self.py_fluence_image, self.cpp_fluence_image, self.first_run
        )
        # now, indicate the next run will not be the first
        self.first_run = False

    def EndSimulationAction(self):
        g4.GateFluenceActor.EndSimulationAction(self)

        self.fetch_from_cpp_image(
            output_name="fluence", cpp_image=self.cpp_fluence_image
        )
        self.user_output["fluence"].write_data_if_requested()


process_cls(VoxelDepositActor)
process_cls(DoseActor)
process_cls(LETActor)
process_cls(FluenceActor)
