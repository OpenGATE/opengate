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
from ..geometry.materials import create_mass_img, create_density_img


class DoseActor(g4.GateDoseActor, ActorBase):
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

    type_name = "DoseActor"

    def set_default_user_info(user_info):
        ActorBase.set_default_user_info(user_info)
        # required user info, default values
        mm = g4_units.mm
        user_info.size = [10, 10, 10]
        user_info.spacing = [1 * mm, 1 * mm, 1 * mm]
        user_info.output = "edep.mhd"  # FIXME change to 'output' ?
        user_info.translation = [0, 0, 0]
        user_info.img_coord_system = None
        user_info.output_origin = None
        user_info.uncertainty = True
        user_info.square = False
        user_info.physical_volume_index = None
        user_info.hit_type = "random"

        user_info.dose = False
        user_info.to_water = False
        user_info.use_more_ram = False
        user_info.ste_of_mean = False
        user_info.ste_of_mean_unbiased = False

        # stop simulation when stat goal reached
        user_info.goal_uncertainty = 0
        user_info.thresh_voxel_edep_for_unc_calc = 0.7

        user_info.dose_calc_on_the_fly = True  # dose calculation in stepping action c++

    def __init__(self, user_info):
        ActorBase.__init__(self, user_info)
        if user_info.ste_of_mean_unbiased or user_info.ste_of_mean:
            self.user_info.ste_of_mean = True
            self.user_info.use_more_ram = True
        g4.GateDoseActor.__init__(self, user_info.__dict__)
        # attached physical volume (at init)
        self.g4_phys_vol = None
        # default image (py side)
        self.py_edep_image = None
        # self.py_dose_image = None
        self.py_temp_image = None
        self.py_square_image = None
        self.py_last_id_image = None
        # default uncertainty
        self.uncertainty_image = None
        # internal states
        self.img_origin_during_run = None
        self.first_run = None
        self.output_origin = None

    def __str__(self):
        u = self.user_info
        s = f'DoseActor "{u.name}": dim={u.size} spacing={u.spacing} {u.output} tr={u.translation}'
        return s

    def __getstate__(self):
        # superclass getstate
        ActorBase.__getstate__(self)
        # do not pickle itk images
        self.py_edep_image = None
        # self.py_dose_image = None
        self.py_temp_image = None
        self.py_square_image = None
        # self.py_last_id_image = None
        self.uncertainty_image = None
        return self.__dict__

    def initialize(self, volume_engine=None):
        """
        At the start of the run, the image is centered according to the coordinate system of
        the mother volume. This function computes the correct origin = center + translation.
        Note that there is a half-pixel shift to align according to the center of the pixel,
        like in ITK.
        """

        if (
            self.user_info.goal_uncertainty < 0.0
            or self.user_info.goal_uncertainty > 1.0
        ):
            raise ValueError("goal uncertainty must be > 0 and < 1")

        if self.user_info.ste_of_mean_unbiased:
            self.user_info.ste_of_mean = True

        if self.user_info.ste_of_mean:
            self.user_info.use_more_RAM = True

        if (
            self.user_info.ste_of_mean == True
            and self.simulation.user_info.number_of_threads <= 4
        ):
            raise ValueError(
                "number_of_threads should be > 4 when using dose actor with ste_of_mean flag enabled"
            )

        if self.user_info.goal_uncertainty:
            if (
                self.user_info.uncertainty == False
                and self.user_info.ste_of_mean == False
            ):
                raise ValueError(
                    "To set an uncertainty goal, set at least one of this flags to True: uncertainty, ste_of_mean"
                )

        if self.user_info.uncertainty == True and self.user_info.ste_of_mean == True:
            raise ValueError(
                "select only one way to calculate uncertainty: uncertainty or ste_of_mean"
            )

        super().initialize(volume_engine)
        # create itk image (py side)
        size = np.array(self.user_info.size)
        spacing = np.array(self.user_info.spacing)
        self.py_edep_image = create_3d_image(size, spacing, pixel_type="double")
        # compute the center, using translation and half pixel spacing
        self.img_origin_during_run = (
            -size * spacing / 2.0 + spacing / 2.0 + self.user_info.translation
        )
        # for initialization during the first run
        self.first_run = True

    def StartSimulationAction(self):
        # init the origin and direction according to the physical volume
        # (will be updated in the BeginOfRun)
        attached_to_volume = self.volume_engine.get_volume(self.user_info.mother)
        if self.user_info.physical_volume_index is None:
            physical_volume_index = 0
        else:
            physical_volume_index = self.user_info.physical_volume_index
        try:
            self.g4_phys_vol = attached_to_volume.g4_physical_volumes[
                physical_volume_index
            ]
        except IndexError:
            fatal(
                f"Error in the DoseActor {self.user_info.name}. "
                f"Could not find the physical volume with index {physical_volume_index} "
                f"in volume '{self.user_info.mother}' to which this actor is attached. "
            )
        align_image_with_physical_volume(
            attached_to_volume,
            self.py_edep_image,
            initial_translation=self.user_info.translation,
        )

        # Set the real physical volume name
        self.fPhysicalVolumeName = str(self.g4_phys_vol.GetName())

        # FIXME for multiple run and motion
        if not self.first_run:
            warning(f"Not implemented yet: DoseActor with several runs")
        # send itk image to cpp side, copy data only the first run.
        update_image_py_to_cpp(self.py_edep_image, self.cpp_edep_image, self.first_run)

        # for uncertainty and square dose image
        if (
            self.user_info.uncertainty
            or self.user_info.square
            or self.user_info.ste_of_mean
        ):
            self.py_square_image = create_image_like(
                self.py_edep_image, pixel_type="double"
            )
            update_image_py_to_cpp(
                self.py_square_image, self.cpp_square_image, self.first_run
            )

        # now, indicate the next run will not be the first
        self.first_run = False

        # If attached to a voxelized volume, we may want to use its coord system.
        # So, we compute in advance what will be the final origin of the dose map
        attached_to_volume = self.simulation.volume_manager.volumes[
            self.user_info.mother
        ]
        vol_type = attached_to_volume.volume_type
        self.output_origin = self.img_origin_during_run

        # FIXME put out of the class ?
        if vol_type == "ImageVolume":
            if self.user_info.img_coord_system:
                # Translate the output dose map so that its center correspond to the image center.
                # The origin is thus the center of the first voxel.
                img_info = get_info_from_image(attached_to_volume.itk_image)
                dose_info = get_info_from_image(self.py_edep_image)
                self.output_origin = get_origin_wrt_images_g4_position(
                    img_info, dose_info, self.user_info.translation
                )
        else:
            if self.user_info.img_coord_system:
                warning(
                    f'DoseActor "{self.user_info.name}" has '
                    f"the flag img_coord_system set to True, "
                    f"but it is not attached to an ImageVolume "
                    f'volume ("{attached_to_volume.name}", of type "{vol_type}"). '
                    f"So the flag is ignored."
                )
        # user can set the output origin
        if self.user_info.output_origin is not None:
            if self.user_info.img_coord_system:
                warning(
                    f'DoseActor "{self.user_info.name}" has '
                    f"the flag img_coord_system set to True, "
                    f"but output_origin is set, so img_coord_system ignored."
                )
            self.output_origin = self.user_info.output_origin

    def EndSimulationAction(self):
        g4.GateDoseActor.EndSimulationAction(self)

        # Get the itk image from the cpp side
        # Currently a copy. Maybe later as_pyarray ?
        self.py_edep_image = get_cpp_image(self.cpp_edep_image)

        # set the property of the output image:
        # in the coordinate system of the attached volume
        # FIXME no direction for the moment ?
        self.py_edep_image.SetOrigin(self.output_origin)
        self.user_info.output = self.simulation.get_output_path(self.user_info.output)

        # dose in gray
        if self.user_info.dose:
            self.user_info.output = self.simulation.get_output_path(
                self.user_info.output, suffix="dose"
            )
            if not self.user_info.dose_calc_on_the_fly:
                self.user_info.output = self.simulation.get_output_path(
                    self.user_info.output, suffix="postprocessing"
                )

        else:
            self.user_info.output = self.simulation.get_output_path(
                self.user_info.output, suffix="edep"
            )

        if self.user_info.to_water:
            self.user_info.output = self.simulation.get_output_path(
                self.user_info.output, suffix="ToWater"
            )

        # Uncertainty stuff need to be called before writing edep (to terminate temp events)
        if self.user_info.uncertainty or self.user_info.ste_of_mean:
            self.create_uncertainty_img()
            self.user_info.output_uncertainty = self.simulation.get_output_path(
                self.user_info.output, suffix="uncertainty"
            )
            write_itk_image(self.uncertainty_image, self.user_info.output_uncertainty)

        # Write square image too
        if self.user_info.square:
            self.fetch_square_image_from_cpp()
            n = self.simulation.get_output_path(self.user_info.output, suffix="Squared")
            write_itk_image(self.py_square_image, n)

        if not self.user_info.dose_calc_on_the_fly and self.user_info.dose:
            self.compute_dose_from_edep_img()

        # write the image at the end of the run
        # FIXME : maybe different for several runs
        if self.user_info.output:
            write_itk_image(self.py_edep_image, self.user_info.output)

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
        N = self.NbOfEvent
        if self.user_info.ste_of_mean:
            """
            Standard error of mean, where each thread is considered one subsample.
            """
            N = self.simulation.user_info.number_of_threads

        self.fetch_square_image_from_cpp()

        edep = itk.array_view_from_image(self.py_edep_image)
        square = itk.array_view_from_image(self.py_square_image)

        self.py_edep_image_tmp = itk_image_view_from_array(edep)
        self.py_edep_image_tmp.CopyInformation(self.py_edep_image)
        self.py_edep_image = self.py_edep_image_tmp
        del self.py_edep_image_tmp

        # uncertainty image
        self.uncertainty_image = create_image_like(
            self.py_edep_image, pixel_type="double"
        )
        # unc = itk.array_view_from_image(self.uncertainty_image)

        unc = self.compute_std_from_sample(
            N, edep, square, correct_bias=self.user_info.ste_of_mean_unbiased
        )
        self.uncertainty_image = itk_image_view_from_array(unc)
        self.uncertainty_image.CopyInformation(self.py_edep_image)
        self.uncertainty_image.SetOrigin(self.output_origin)
        # debug
        """write_itk_image(self.py_square_image, "square.mhd")
        write_itk_image(self.py_temp_image, "temp.mhd")
        write_itk_image(self.py_last_id_image, "lastid.mhd")
        write_itk_image(self.uncertainty_image, "uncer.mhd")"""


class LETActor(g4.GateLETActor, ActorBase):
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

    type_name = "LETActor"

    def set_default_user_info(user_info):
        ActorBase.set_default_user_info(user_info)
        # required user info, default values
        mm = g4_units.mm
        user_info.size = [10, 10, 10]
        user_info.spacing = [1 * mm, 1 * mm, 1 * mm]
        user_info.output = "LETActor.mhd"  # FIXME change to 'output' ?
        user_info.translation = [0, 0, 0]
        user_info.img_coord_system = None
        user_info.output_origin = None
        user_info.physical_volume_index = None
        user_info.hit_type = "random"

        ## Settings for LET averaging
        user_info.dose_average = False
        user_info.track_average = False
        user_info.let_to_other_material = False
        user_info.let_to_water = False
        user_info.other_material = ""
        user_info.separate_output = False

    def __init__(self, user_info):
        ## TODO: why not super? what would happen?
        ActorBase.__init__(self, user_info)
        g4.GateLETActor.__init__(self, user_info.__dict__)
        # attached physical volume (at init)
        self.g4_phys_vol = None
        # default image (py side)
        self.py_numerator_image = None
        self.py_denominator_image = None
        self.py_output_image = None

        # internal states
        self.img_origin_during_run = None
        self.first_run = None
        self.output_origin = None

    def __str__(self):
        u = self.user_info
        s = f'LETActor "{u.name}": dim={u.size} spacing={u.spacing} {u.output} tr={u.translation}'
        return s

    def __getstate__(self):
        # superclass getstate
        ActorBase.__getstate__(self)
        # do not pickle itk images
        self.py_numerator_image = None
        self.py_denominator_image = None
        self.py_output_image = None
        return self.__dict__

    def initialize(self, volume_engine=None):
        """
        At the start of the run, the image is centered according to the coordinate system of
        the mother volume. This function computes the correct origin = center + translation.
        Note that there is a half-pixel shift to align according to the center of the pixel,
        like in ITK.
        """
        super().initialize(volume_engine)
        # create itk image (py side)
        size = np.array(self.user_info.size)
        spacing = np.array(self.user_info.spacing)
        self.py_numerator_image = create_3d_image(size, spacing, "double")
        # TODO remove code
        # self.py_denominator_image = create_3d_image(size, spacing)
        # self.py_output_image = create_3d_image(size, spacing)
        # compute the center, using translation and half pixel spacing
        self.img_origin_during_run = (
            -size * spacing / 2.0 + spacing / 2.0 + self.user_info.translation
        )
        # for initialization during the first run
        self.first_run = True

        if self.user_info.dose_average == self.user_info.track_average:
            fatal(
                f"Ambiguous to enable dose and track averaging: \ndose_average: {self.user_info.dose_average} \ntrack_average: { self.user_info.track_average} \nOnly one option can and must be set to True"
            )

        if self.user_info.other_material:
            self.user_info.let_to_other_material = True
        if self.user_info.let_to_other_material and not self.user_info.other_material:
            fatal(
                f"let_to_other_material enabled, but other_material not set: {self.user_info.other_material}"
            )
        if self.user_info.let_to_water:
            self.user_info.other_material = "G4_WATER"

    def StartSimulationAction(self):
        # init the origin and direction according to the physical volume
        # (will be updated in the BeginOfRun)
        attached_to_volume = self.volume_engine.get_volume(self.user_info.mother)
        if self.user_info.physical_volume_index is None:
            physical_volume_index = 0
        else:
            physical_volume_index = self.user_info.physical_volume_index
        try:
            self.g4_phys_vol = attached_to_volume.g4_physical_volumes[
                physical_volume_index
            ]
        except:  # FIXME: need explicit exception
            fatal(f"Error in the LETActor {self.user_info.name}")
        align_image_with_physical_volume(
            attached_to_volume,
            self.py_numerator_image,
            initial_translation=self.user_info.translation,
        )

        # Set the real physical volume name
        self.fPhysicalVolumeName = str(self.g4_phys_vol.GetName())

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

        self.py_output_image = create_image_like(
            self.py_numerator_image, pixel_type="double"
        )

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


class FluenceActor(g4.GateFluenceActor, ActorBase):
    """
    FluenceActor: compute a 3D map of fluence

    FIXME: add scatter order and uncertainty
    """

    type_name = "FluenceActor"

    def set_default_user_info(user_info):
        ActorBase.set_default_user_info(user_info)
        # required user info, default values
        mm = g4_units.mm
        user_info.size = [10, 10, 10]
        user_info.spacing = [1 * mm, 1 * mm, 1 * mm]
        user_info.output = "fluence.mhd"
        user_info.translation = [0, 0, 0]
        user_info.physical_volume_index = None
        user_info.uncertainty = False
        user_info.scatter = False

    def __init__(self, user_info):
        ActorBase.__init__(self, user_info)
        g4.GateFluenceActor.__init__(self, user_info.__dict__)
        # attached physical volume (at init)
        self.g4_phys_vol = None
        # default image (py side)
        self.py_fluence_image = None

    def __str__(self):
        u = self.user_info
        s = f'FluenceActor "{u.name}": dim={u.size} spacing={u.spacing} {u.output} tr={u.translation}'
        return s

    def __getstate__(self):
        # superclass getstate
        DoseActor.__getstate__(self)
        return self.__dict__

    def initialize(self, volume_engine=None):
        super().initialize(volume_engine)
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

    def StartSimulationAction(self):
        # init the origin and direction according to the physical volume
        # (will be updated in the BeginOfRun)
        attached_to_volume = self.volume_engine.get_volume(self.user_info.mother)
        if self.user_info.physical_volume_index is None:
            physical_volume_index = 0
        else:
            physical_volume_index = self.user_info.physical_volume_index
        try:
            self.g4_phys_vol = attached_to_volume.g4_physical_volumes[
                physical_volume_index
            ]
        except IndexError:
            fatal(
                f"Error in the FluenceActor {self.user_info.name}. "
                f"Could not find the physical volume with index {physical_volume_index} "
                f"in volume '{self.user_info.mother}' to which this actor is attached. "
            )
        align_image_with_physical_volume(
            attached_to_volume,
            self.py_fluence_image,
            initial_translation=self.user_info.translation,
        )

        # Set the real physical volume name
        self.fPhysicalVolumeName = str(self.g4_phys_vol.GetName())

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
