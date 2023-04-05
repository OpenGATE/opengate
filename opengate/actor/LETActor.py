import opengate_core as g4
import itk
import numpy as np
import opengate as gate
from scipy.spatial.transform import Rotation


class LETActor(g4.GateLETActor, gate.ActorBase):
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
        gate.ActorBase.set_default_user_info(user_info)
        # required user info, default values
        mm = gate.g4_units("mm")
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
        gate.ActorBase.__init__(self, user_info)
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
        gate.ActorBase.__getstate__(self)
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
        self.py_numerator_image = gate.create_3d_image(size, spacing, "double")
        # TODO remove code
        # self.py_denominator_image = gate.create_3d_image(size, spacing)
        # self.py_output_image = gate.create_3d_image(size, spacing)
        # compute the center, using translation and half pixel spacing
        self.img_origin_during_run = (
            -size * spacing / 2.0 + spacing / 2.0 + self.user_info.translation
        )
        # for initialization during the first run
        self.first_run = True

        if self.user_info.dose_average == self.user_info.track_average:
            gate.fatal(
                f"Ambiguous to enable dose and track averaging: \ndose_average: {self.user_info.dose_average} \ntrack_average: { self.user_info.track_average} \nOnly one option can and must be set to True"
            )

        if self.user_info.other_material:
            self.user_info.let_to_other_material = True
        if self.user_info.let_to_other_material and not self.user_info.other_material:
            gate.fatal(
                f"let_to_other_material enabled, but other_material not set: {self.user_info.other_material}"
            )
        if self.user_info.let_to_water:
            self.user_info.other_material = "G4_WATER"

    def StartSimulationAction(self):
        # init the origin and direction according to the physical volume
        # (will be updated in the BeginOfRun)
        try:
            self.g4_phys_vol = gate.get_physical_volume(
                self.volume_engine,
                self.user_info.mother,
                self.user_info.physical_volume_index,
            )
        except:
            gate.fatal(f"Error in the LETActor {self.user_info.name}")
        gate.attach_image_to_physical_volume(
            self.g4_phys_vol.GetName(),
            self.py_numerator_image,
            self.user_info.translation,
        )

        # Set the real physical volume name
        self.fPhysicalVolumeName = str(self.g4_phys_vol.GetName())

        # FIXME for multiple run and motion
        if not self.first_run:
            gate.warning(f"Not implemented yet: LETActor with several runs")
        # send itk image to cpp side, copy data only the first run.
        gate.update_image_py_to_cpp(
            self.py_numerator_image, self.cpp_numerator_image, self.first_run
        )

        # TODO
        self.py_denominator_image = gate.create_image_like(
            self.py_numerator_image, pixel_type="double"
        )
        gate.update_image_py_to_cpp(
            self.py_denominator_image, self.cpp_denominator_image, self.first_run
        )

        self.py_output_image = gate.create_image_like(self.py_numerator_image)

        # now, indicate the next run will not be the first
        self.first_run = False

        # If attached to a voxelized volume, we may want to use its coord system.
        # So, we compute in advance what will be the final origin of the dose map
        vol_name = self.user_info.mother
        vol_type = self.simulation.get_volume_user_info(vol_name).type_name
        self.output_origin = self.img_origin_during_run

        # FIXME put out of the class ?
        if vol_type == "Image":
            if self.user_info.img_coord_system:
                vol = self.volume_engine.g4_volumes[vol_name]
                # Translate the output dose map so that its center correspond to the image center.
                # The origin is thus the center of the first voxel.
                img_info = gate.get_info_from_image(vol.image)
                dose_info = gate.get_info_from_image(self.py_numerator_image)
                self.output_origin = gate.get_origin_wrt_images_g4_position(
                    img_info, dose_info, self.user_info.translation
                )
        else:
            if self.user_info.img_coord_system:
                gate.warning(
                    f'LETActor "{self.user_info.name}" has '
                    f"the flag img_coord_system set to True, "
                    f"but it is not attached to an Image "
                    f'volume ("{vol_name}", of type "{vol_type}"). '
                    f"So the flag is ignored."
                )
        # user can set the output origin
        if self.user_info.output_origin is not None:
            if self.user_info.img_coord_system:
                gate.warning(
                    f'LETActor "{self.user_info.name}" has '
                    f"the flag img_coord_system set to True, "
                    f"but output_origin is set, so img_coord_system ignored."
                )
            self.output_origin = self.user_info.output_origin

    def EndSimulationAction(self):
        g4.GateLETActor.EndSimulationAction(self)

        # Get the itk image from the cpp side
        # Currently a copy. Maybe latter as_pyarray ?
        self.py_numerator_image = gate.get_cpp_image(self.cpp_numerator_image)
        self.py_denominator_image = gate.get_cpp_image(self.cpp_denominator_image)

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
            self.py_LETd_image = gate.divide_itk_images(
                img1_numerator=self.py_numerator_image,
                img2_denominator=self.py_denominator_image,
                filterVal=0,
                replaceFilteredVal=0,
            )
            itk.imwrite(self.py_LETd_image, gate.check_filename_type(fPath))

            # for parrallel computation we need to provide both outputs
            if self.user_info.separate_output:
                fPath = fPath.replace(".mhd", "_numerator.mhd")
                itk.imwrite(self.py_numerator_image, gate.check_filename_type(fPath))
                fPath = fPath.replace("_numerator", "_denominator")
                itk.imwrite(self.py_denominator_image, gate.check_filename_type(fPath))

        # debug
        """itk.imwrite(self.py_square_image, "square.mhd")
        itk.imwrite(self.py_temp_image, "temp.mhd")
        itk.imwrite(self.py_last_id_image, "lastid.mhd")
        itk.imwrite(self.uncertainty_image, "uncer.mhd")"""
