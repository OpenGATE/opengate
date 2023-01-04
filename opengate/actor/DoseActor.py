import opengate_core as g4
import itk
import numpy as np
import opengate as gate
from scipy.spatial.transform import Rotation


class DoseActor(g4.GateDoseActor, gate.ActorBase):
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
        gate.ActorBase.set_default_user_info(user_info)
        # required user info, default values
        mm = gate.g4_units("mm")
        user_info.size = [10, 10, 10]
        user_info.spacing = [1 * mm, 1 * mm, 1 * mm]
        user_info.output = "edep.mhd"  # FIXME change to 'output' ?
        user_info.translation = [0, 0, 0]
        user_info.img_coord_system = None
        user_info.output_origin = None
        user_info.uncertainty = True
        user_info.gray = False
        user_info.physical_volume_index = None
        user_info.hit_type = "random"

    def __init__(self, user_info):
        gate.ActorBase.__init__(self, user_info)
        g4.GateDoseActor.__init__(self, user_info.__dict__)
        # attached physical volume (at init)
        self.g4_phys_vol = None
        # default image (py side)
        self.py_edep_image = None
        self.py_dose_image = None
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
        gate.ActorBase.__getstate__(self)
        # do not pickle itk images
        self.py_edep_image = None
        self.py_dose_image = None
        self.py_temp_image = None
        self.py_square_image = None
        self.py_last_id_image = None
        self.uncertainty_image = None
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
        self.py_edep_image = gate.create_3d_image(size, spacing)
        # compute the center, using translation and half pixel spacing
        self.img_origin_during_run = (
            -size * spacing / 2.0 + spacing / 2.0 + self.user_info.translation
        )
        # for initialization during the first run
        self.first_run = True

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
            gate.fatal(f"Error in the DoseActor {self.user_info.name}")
        gate.attach_image_to_physical_volume(
            self.g4_phys_vol.GetName(), self.py_edep_image, self.user_info.translation
        )

        # Set the real physical volume name
        self.fPhysicalVolumeName = str(self.g4_phys_vol.GetName())

        # FIXME for multiple run and motion
        if not self.first_run:
            gate.warning(f"Not implemented yet: DoseActor with several runs")
        # send itk image to cpp side, copy data only the first run.
        gate.update_image_py_to_cpp(
            self.py_edep_image, self.cpp_edep_image, self.first_run
        )

        # for uncertainty
        if self.user_info.uncertainty:
            self.py_temp_image = gate.create_image_like(self.py_edep_image)
            self.py_square_image = gate.create_image_like(self.py_edep_image)
            self.py_last_id_image = gate.create_image_like(self.py_edep_image)
            gate.update_image_py_to_cpp(
                self.py_temp_image, self.cpp_temp_image, self.first_run
            )
            gate.update_image_py_to_cpp(
                self.py_square_image, self.cpp_square_image, self.first_run
            )
            gate.update_image_py_to_cpp(
                self.py_last_id_image, self.cpp_last_id_image, self.first_run
            )

        # for dose in Gray
        if self.user_info.gray:
            self.py_dose_image = gate.create_image_like(self.py_edep_image)
            gate.update_image_py_to_cpp(
                self.py_dose_image, self.cpp_dose_image, self.first_run
            )

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
                dose_info = gate.get_info_from_image(self.py_edep_image)
                self.output_origin = gate.get_origin_wrt_images_g4_position(
                    img_info, dose_info, self.user_info.translation
                )
        else:
            if self.user_info.img_coord_system:
                gate.warning(
                    f'DoseActor "{self.user_info.name}" has '
                    f"the flag img_coord_system set to True, "
                    f"but it is not attached to an Image "
                    f'volume ("{vol_name}", of type "{vol_type}"). '
                    f"So the flag is ignored."
                )
        # user can set the output origin
        if self.user_info.output_origin is not None:
            if self.user_info.img_coord_system:
                gate.warning(
                    f'DoseActor "{self.user_info.name}" has '
                    f"the flag img_coord_system set to True, "
                    f"but output_origin is set, so img_coord_system ignored."
                )
            self.output_origin = self.user_info.output_origin

    def EndSimulationAction(self):
        g4.GateDoseActor.EndSimulationAction(self)

        # Get the itk image from the cpp side
        # Currently a copy. Maybe latter as_pyarray ?
        self.py_edep_image = gate.get_cpp_image(self.cpp_edep_image)

        # set the property of the output image:
        # in the coordinate system of the attached volume
        # FIXME no direction for the moment ?
        self.py_edep_image.SetOrigin(self.output_origin)

        # Uncertainty stuff need to be called before writing edep (to terminate temp events)
        if self.user_info.uncertainty:
            self.compute_uncertainty()
            n = gate.check_filename_type(self.user_info.output).replace(
                ".mhd", "_uncertainty.mhd"
            )
            itk.imwrite(self.uncertainty_image, n)

        # dose in gray
        if self.user_info.gray:
            self.py_dose_image = gate.get_cpp_image(self.cpp_dose_image)
            self.py_dose_image.SetOrigin(self.output_origin)
            n = gate.check_filename_type(self.user_info.output).replace(
                ".mhd", "_dose.mhd"
            )
            itk.imwrite(self.py_dose_image, n)

        # write the image at the end of the run
        # FIXME : maybe different for several runs
        if self.user_info.output:
            itk.imwrite(
                self.py_edep_image, gate.check_filename_type(self.user_info.output)
            )

    def compute_uncertainty(self):
        self.py_temp_image = gate.get_cpp_image(self.cpp_temp_image)
        self.py_square_image = gate.get_cpp_image(self.cpp_square_image)
        self.py_last_id_image = gate.get_cpp_image(self.cpp_last_id_image)

        self.py_temp_image.SetOrigin(self.output_origin)
        self.py_square_image.SetOrigin(self.output_origin)
        self.py_last_id_image.SetOrigin(self.output_origin)

        # complete edep with temp values
        edep = itk.array_view_from_image(self.py_edep_image)
        tmp = itk.array_view_from_image(self.py_temp_image)
        edep = edep + tmp
        self.py_edep_image = itk.image_from_array(edep)
        self.py_edep_image.CopyInformation(self.py_temp_image)

        # complete square with temp values
        square = itk.array_view_from_image(self.py_square_image)
        square = square + tmp * tmp
        self.py_square_image = itk.image_from_array(square)
        self.py_square_image.CopyInformation(self.py_temp_image)

        # uncertainty image
        self.uncertainty_image = gate.create_image_like(self.py_edep_image)
        unc = itk.array_view_from_image(self.uncertainty_image)
        N = unc.size
        # unc = np.sqrt(1 / (N - 1) * (square / N - np.power(edep / N, 2)))
        unc = 1 / (N - 1) * (square / N - np.power(edep / N, 2))
        unc = np.ma.masked_array(unc, unc < 0)
        unc = np.ma.sqrt(unc)
        unc = np.divide(unc, edep / N, out=np.ones_like(unc), where=edep != 0)
        self.uncertainty_image = itk.image_from_array(unc)
        self.uncertainty_image.CopyInformation(self.py_temp_image)
        self.uncertainty_image.SetOrigin(self.output_origin)

        # debug
        """itk.imwrite(self.py_square_image, "square.mhd")
        itk.imwrite(self.py_temp_image, "temp.mhd")
        itk.imwrite(self.py_last_id_image, "lastid.mhd")
        itk.imwrite(self.uncertainty_image, "uncer.mhd")"""
