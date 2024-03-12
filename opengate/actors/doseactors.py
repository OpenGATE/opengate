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
    get_cpp_image,
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
        self.output_origin = None

    def initialize(self):
        super().initialize()

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

    # def set_default_user_info(user_info):
    #     ActorBase.set_default_user_info(user_info)
    #     # required user info, default values
    #     mm = g4_units.mm
    #     user_info.size = [10, 10, 10]
    #     user_info.spacing = [1 * mm, 1 * mm, 1 * mm]
    #     user_info.output = "edep.mhd"  # FIXME change to 'output' ?
    #     user_info.translation = [0, 0, 0]
    #     user_info.img_coord_system = None
    #     user_info.output_origin = None
    #     user_info.repeated_volume_index = None
    #     user_info.hit_type = "random"
    #
    #     user_info.use_more_ram = False
    #
    #     user_info.uncertainty = True
    #     user_info.square = False
    #     user_info.dose = False
    #     user_info.to_water = False
    #     user_info.ste_of_mean = False
    #     user_info.ste_of_mean_unbiased = False
    #
    #     # stop simulation when stat goal reached
    #     user_info.goal_uncertainty = 0
    #     user_info.thresh_voxel_edep_for_unc_calc = 0.7
    #
    #     user_info.dose_calc_on_the_fly = True  # dose calculation in stepping action c++

    def __init__(self, *args, **kwargs):
        VoxelDepositActor.__init__(self, *args, **kwargs)
        g4.GateDoseActor.__init__(self, self.user_info)
        if self.ste_of_mean_unbiased or self.ste_of_mean:
            self.ste_of_mean = True
            self.use_more_ram = True
        # attached physical volume (at init)
        # default image (py side)
        self.py_edep_image = None
        # self.py_dose_image = None
        self.py_temp_image = None
        self.py_square_image = None
        self.py_last_id_image = None
        # default uncertainty
        self.uncertainty_image = None

        self._add_actor_output("image", "edep")
        self._add_actor_output("image", "dose")
        self._add_actor_output("image", "dose_to_water")
        self._add_actor_output("image", "squared")
        self._add_actor_output("image", "uncertainty")

    def __getstate__(self):
        # superclass getstate
        return_dict = super().__getstate__()
        return_dict["g4_phys_vol"] = None
        return return_dict

    def initialize(self, *args):
        """
        At the start of the run, the image is centered according to the coordinate system of
        the mother volume. This function computes the correct origin = center + translation.
        Note that there is a half-pixel shift to align according to the center of the pixel,
        like in ITK.
        """

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

        VoxelDepositActor.initialize(self)
        # create itk image (py side)
        size = np.array(self.size)
        spacing = np.array(self.spacing)
        self.py_edep_image = create_3d_image(size, spacing)
        # compute the center, using translation and half pixel spacing
        self.img_origin_during_run = (
            -size * spacing / 2.0 + spacing / 2.0 + self.translation
        )
        # for initialization during the first run
        self.first_run = True

        self.InitializeUserInput(self.user_info)
        # Set the physical volume name on the C++ side
        self.fPhysicalVolumeName = self.get_physical_volume_name()
        self.ActorInitialize()

    def StartSimulationAction(self):

        align_image_with_physical_volume(
            self.attached_to_volume,
            self.py_edep_image,
            initial_translation=self.translation,
        )

        # FIXME for multiple run and motion
        if not self.first_run:
            warning(f"Not implemented yet: DoseActor with several runs")
        # send itk image to cpp side, copy data only the first run.
        update_image_py_to_cpp(self.py_edep_image, self.cpp_edep_image, self.first_run)

        # for uncertainty and square dose image
        if self.uncertainty or self.square or self.ste_of_mean:
            self.py_square_image = create_image_like(self.py_edep_image)
            update_image_py_to_cpp(
                self.py_square_image, self.cpp_square_image, self.first_run
            )

        # now, indicate the next run will not be the first
        self.first_run = False

        # If attached to a voxelized volume, we may want to use its coord system.
        # So, we compute in advance what will be the final origin of the dose map
        vol_type = self.simulation.volume_manager.get_volume(
            self.attached_to
        ).volume_type
        self.output_origin = self.img_origin_during_run

        # FIXME put out of the class ?
        if vol_type == "ImageVolume":
            if self.img_coord_system:
                # Translate the output dose map so that its center correspond to the image center.
                # The origin is thus the center of the first voxel.
                img_info = get_info_from_image(self.attached_to_volume.itk_image)
                dose_info = get_info_from_image(self.py_edep_image)
                self.output_origin = get_origin_wrt_images_g4_position(
                    img_info, dose_info, self.translation
                )
        else:
            if self.user_info.img_coord_system:
                warning(
                    f'{self.actor_type} "{self.name}" has '
                    f"the flag img_coord_system set to True, "
                    f"but it is not attached to an ImageVolume "
                    f'volume ("{self.attached_to_volume.name}", of type "{vol_type}"). '
                    f"So the flag is ignored."
                )
        # user can set the output origin
        if self.output_origin is not None:
            if self.img_coord_system:
                warning(
                    f'DoseActor "{self.name}" has '
                    f"the flag img_coord_system set to True, "
                    f"but output_origin is set, so img_coord_system ignored."
                )
            self.output_origin = self.output_origin

    def EndSimulationAction(self):
        g4.GateDoseActor.EndSimulationAction(self)

        # Get the itk image from the cpp side
        # Currently a copy. Maybe later as_pyarray ?
        self.py_edep_image = get_cpp_image(self.cpp_edep_image)

        # set the property of the output image:
        # in the coordinate system of the attached volume
        # FIXME no direction for the moment ?
        self.py_edep_image.SetOrigin(self.output_origin)

        # self.user_info.output = self.simulation.get_output_path(self.user_info.output)
        #
        # # dose in gray
        # if self.user_info.dose:
        #     self.user_info.output = self.simulation.get_output_path(
        #         self.user_info.output, suffix="dose"
        #     )
        #     if not self.user_info.dose_calc_on_the_fly:
        #         self.user_info.output = self.simulation.get_output_path(
        #             self.user_info.output, suffix="postprocessing"
        #         )

        # else:
        #     self.user_info.output = self.simulation.get_output_path(
        #         self.user_info.output, suffix="edep"
        #     )
        #
        # if self.user_info.to_water:
        #     self.user_info.output = self.simulation.get_output_path(
        #         self.user_info.output, suffix="ToWater"
        #     )

        # Uncertainty stuff need to be called before writing edep (to terminate temp events)
        if self.uncertainty or self.ste_of_mean:
            self.store_output_data(
                "uncertainty", self.create_uncertainty_img(), run_index=0
            )
            self.write_output_to_disk_if_requested("uncertainty")
            # self.user_info.output_uncertainty = self.simulation.get_output_path(
            #     self.user_info.output, suffix="uncertainty"
            # )
            # write_itk_image(self.uncertainty_image, self.user_info.output_uncertainty)

        # Write square image too
        if self.square:
            # FIXME: the fetch should write directly into the actor_output
            self.fetch_square_image_from_cpp()
            self.store_output_data("squared", self.py_square_image, run_index=0)
            self.write_output_to_disk_if_requested("squared")
            # n = self.simulation.get_output_path(self.user_info.output, suffix="Squared")
            # write_itk_image(self.py_square_image, n)

        if not self.dose_calc_on_the_fly and self.dose:
            self.compute_dose_from_edep_img()

        self.store_output_data("edep", self.py_edep_image, run_index=0)
        self.write_output_to_disk_if_requested("edep")

        # # write the image at the end of the run
        # # FIXME : maybe different for several runs
        # if self.user_info.output:
        #     write_itk_image(self.py_edep_image, self.user_info.output)

    def compute_dose_from_edep_img(self):
        """
        * create mass image:
            - from ct HU units, if dose actor attached to ImageVolume.
            - from material density, if standard volume
        * compute dose as edep_image /  mass_image
        """
        vol = self.simulation.volume_manager.get_volume(self.user_info.mother)
        spacing = np.array(self.user_info.spacing)
        voxel_volume = spacing[0] * spacing[1] * spacing[2]
        Gy = g4_units.Gy
        gcm3 = g4_units.g_cm3

        if vol.volume_type == "ImageVolume":
            material_database = (
                self.simulation.volume_manager.material_database.g4_materials
            )
            if self.user_info.to_water:
                # for dose to water, divide by density of water and not density of material
                self.py_edep_image = scale_itk_image(
                    self.py_edep_image, 1 / (1.0 * gcm3)
                )
            else:
                density_img = create_density_img(vol, material_database)
                self.py_edep_image = divide_itk_images(
                    img1_numerator=self.py_edep_image,
                    img2_denominator=density_img,
                    filterVal=0,
                    replaceFilteredVal=0,
                )
            # divide by voxel volume and convert unit
            self.py_edep_image = scale_itk_image(
                self.py_edep_image, 1 / (Gy * voxel_volume)
            )

        else:
            if self.user_info.to_water:
                # for dose 2 water, divide by density of water and not density of material
                density = 1.0 * gcm3
            else:
                density = vol.g4_material.GetDensity()
            self.py_edep_image = scale_itk_image(
                self.py_edep_image, 1 / (voxel_volume * density * Gy)
            )

    def fetch_square_image_from_cpp(self):
        if self.py_square_image == None:
            self.py_square_image = get_cpp_image(self.cpp_square_image)
            self.py_square_image.SetOrigin(self.output_origin)
            self.py_square_image.CopyInformation(self.py_edep_image)

    def compute_std_from_sample(self, N, val, val_squared, correct_bias=False):
        unc = np.ones_like(val)
        if N > 1:
            # unc = np.sqrt(1 / (N - 1) * (square / N - np.power(edep / N, 2)))
            unc = 1 / (N - 1) * (val_squared / N - np.power(val / N, 2))
            unc = np.ma.masked_array(
                unc, unc < 0
            )  # this function leaves unc<0 values untouched! what do we do with < 0 values?
            unc = np.ma.sqrt(unc)
            if correct_bias:
                """Standard error is biased (to underestimate the error); this option allows to correct for the bias - assuming normal distribution. For few N this influence is huge, but for N>8 the difference is minimal"""
                unc /= standard_error_c4_correction(N)
            unc = np.divide(unc, val / N, out=np.ones_like(unc), where=val != 0)

        else:
            # unc += 1 # we init with 1.
            warning(
                "You try to compute statistical errors with only one or zero event ! The uncertainty value for all voxels has been fixed at 1"
            )
        return unc

    def create_uncertainty_img(self):
        self.fetch_square_image_from_cpp()

        if self.user_info.ste_of_mean:
            """
            Standard error of mean, where each thread is considered one subsample.
            """
            N = self.simulation.user_info.number_of_threads
        else:
            N = self.NbOfEvent

        edep = itk.array_view_from_image(self.py_edep_image)
        square = itk.array_view_from_image(self.py_square_image)

        # self.py_edep_image_tmp = itk_image_view_from_array(edep)
        # self.py_edep_image_tmp.CopyInformation(self.py_edep_image)
        # self.py_edep_image = self.py_edep_image_tmp
        # del self.py_edep_image_tmp

        # uncertainty image
        # uncertainty_image = create_image_like(self.py_edep_image)
        # unc = itk.array_view_from_image(self.uncertainty_image)

        unc = self.compute_std_from_sample(
            N, edep, square, correct_bias=self.user_info.ste_of_mean_unbiased
        )
        uncertainty_image = itk_image_view_from_array(unc)
        uncertainty_image.CopyInformation(self.py_edep_image)
        uncertainty_image.SetOrigin(self.output_origin)
        return uncertainty_image
        # debug
        # write_itk_image(self.py_square_image, "square.mhd")
        # write_itk_image(self.py_temp_image, "temp.mhd")
        # write_itk_image(self.py_last_id_image, "lastid.mhd")
        # write_itk_image(self.uncertainty_image, "uncer.mhd")


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
        self.py_numerator_image = None
        self.py_denominator_image = None
        self.py_output_image = None

        self._add_actor_output("image", "let")
        self._add_actor_output("image", "let_denominator")
        self._add_actor_output("image", "let_numerator")

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
        # create itk image (py side)
        self.py_numerator_image = create_3d_image(self.size, self.spacing, "double")
        # compute the center, using translation and half pixel spacing
        size = np.array(self.size)
        spacing = np.array(self.spacing)
        translation = np.array(self.translationg)
        self.img_origin_during_run = (
            -size * spacing / 2.0 + spacing / 2.0 + self.translation
        )
        # for initialization during the first run
        self.first_run = True

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

        self.InitializeUserInput(self.user_info)
        # Set the physical volume name on the C++ side
        self.fPhysicalVolumeName = self.get_physical_volume_name()
        self.ActorInitialize()

    def StartSimulationAction(self):

        align_image_with_physical_volume(
            self.attached_to_volume,
            self.py_numerator_image,
            initial_translation=self.user_info.translation,
        )

        # FIXME for multiple run and motion
        if not self.first_run:
            warning(f"Not implemented yet: LETActor with several runs")
        # send itk image to cpp side, copy data only the first run.
        update_image_py_to_cpp(
            self.py_numerator_image, self.cpp_numerator_image, self.first_run
        )

        # TODO
        self.py_denominator_image = create_image_like(
            self.py_numerator_image, pixel_type="double"
        )
        update_image_py_to_cpp(
            self.py_denominator_image, self.cpp_denominator_image, self.first_run
        )

        self.py_output_image = create_image_like(self.py_numerator_image)

        # now, indicate the next run will not be the first
        self.first_run = False

        # If attached to a voxelized volume, we may want to use its coord system.
        # So, we compute in advance what will be the final origin of the dose map
        vol = self.simulation.volume_manager.volumes[self.user_info.mother]
        self.output_origin = self.img_origin_during_run

        # FIXME put out of the class ?
        if vol.volume_type == "Image":
            if self.user_info.img_coord_system:
                vol = self.volume_engine.g4_volumes[vol.name]
                # Translate the output dose map so that its center correspond to the image center.
                # The origin is thus the center of the first voxel.
                img_info = get_info_from_image(vol.image)
                dose_info = get_info_from_image(self.py_numerator_image)
                self.output_origin = get_origin_wrt_images_g4_position(
                    img_info, dose_info, self.user_info.translation
                )
        else:
            if self.user_info.img_coord_system:
                warning(
                    f'LETActor "{self.user_info.name}" has '
                    f"the flag img_coord_system set to True, "
                    f"but it is not attached to an Image "
                    f'volume ("{vol.name}", of type "{vol.volume_type}"). '
                    f"So the flag is ignored."
                )
        # user can set the output origin
        if self.user_info.output_origin is not None:
            if self.user_info.img_coord_system:
                warning(
                    f'LETActor "{self.user_info.name}" has '
                    f"the flag img_coord_system set to True, "
                    f"but output_origin is set, so img_coord_system ignored."
                )
            self.output_origin = self.user_info.output_origin

    def EndSimulationAction(self):
        g4.GateLETActor.EndSimulationAction(self)

        # Get the itk image from the cpp side
        # Currently a copy. Maybe later as_pyarray ?
        self.py_numerator_image = get_cpp_image(self.cpp_numerator_image)
        self.py_denominator_image = get_cpp_image(self.cpp_denominator_image)

        # set the property of the output image:
        # in the coordinate system of the attached volume
        # FIXME no direction for the moment ?
        self.py_numerator_image.SetOrigin(self.output_origin)
        # self.py_denominator_image.SetOrigin(self.output_origin)

        # write the image at the end of the run
        # FIXME : maybe different for several runs
        if self.user_info.output:
            suffix = ""
            if self.user_info.dose_average:
                suffix += "_letd"
            elif self.user_info.track_average:
                suffix += "_lett"
            if self.user_info.let_to_other_material or self.user_info.let_to_water:
                suffix += f"_convto_{self.user_info.other_material}"

            fPath = str(self.user_info.output).replace(".mhd", f"{suffix}.mhd")
            self.user_info.output = fPath
            # self.output = fPath
            self.py_LETd_image = divide_itk_images(
                img1_numerator=self.py_numerator_image,
                img2_denominator=self.py_denominator_image,
                filterVal=0,
                replaceFilteredVal=0,
            )
            write_itk_image(self.py_LETd_image, fPath)

            # for parallel computation we need to provide both outputs
            if self.user_info.separate_output:
                fPath = self.simulation.get_output_path(
                    self.user_info.output, suffix="numerator"
                )
                write_itk_image(self.py_numerator_image, fPath)
                fPath = self.simulation.get_output_path(
                    self.user_info.output, suffix="denominator"
                )
                write_itk_image(self.py_denominator_image, fPath)


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

        self.py_fluence_image = None

    def __getstate__(self):
        return VoxelDepositActor.__getstate__(self)

    def initialize(self):
        VoxelDepositActor().initialize()
        # create itk image (py side)
        size = np.array(self.user_info.size)
        spacing = np.array(self.user_info.spacing)
        self.py_fluence_image = create_3d_image(size, spacing)
        # compute the center, using translation and half pixel spacing
        self.img_origin_during_run = (
            -size * spacing / 2.0 + spacing / 2.0 + self.user_info.translation
        )
        # for initialization during the first run
        self.first_run = True
        # no options yet
        if self.user_info.uncertainty or self.user_info.scatter:
            fatal(f"FluenceActor : uncertainty and scatter not implemented yet")

        self.InitializeUserInput(self.user_info)
        # Set the physical volume name on the C++ side
        self.fPhysicalVolumeName = self.get_physical_volume_name()
        self.ActorInitialize()

    def StartSimulationAction(self):
        # init the origin and direction according to the physical volume
        # (will be updated in the BeginOfRun)
        align_image_with_physical_volume(
            self.attached_to_volume,
            self.py_fluence_image,
            initial_translation=self.user_info.translation,
        )

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

        # Get the itk image from the cpp side
        # Currently a copy. Maybe later as_pyarray ?
        self.py_fluence_image = get_cpp_image(self.cpp_fluence_image)

        # set the property of the output image:
        origin = self.img_origin_during_run
        self.py_fluence_image.SetOrigin(origin)

        # write the image at the end of the run
        # FIXME : maybe different for several runs
        if self.user_info.output:
            out_p = ensure_filename_is_str(
                self.simulation.get_output_path(self.user_info.output)
            )
            itk.imwrite(self.py_fluence_image, out_p)


process_cls(VoxelDepositActor)
process_cls(DoseActor)
process_cls(LETActor)
process_cls(FluenceActor)
