import numpy as np
import itk
from scipy.spatial.transform import Rotation

import opengate_core as g4
from .ActorBase import ActorBase
from ..helpers import fatal, g4_units, check_filename_type
from ..image import (
    attach_image_to_physical_volume,
    update_image_py_to_cpp,
    get_cpp_image,
    get_info_from_image,
    create_3d_image,
    get_physical_volume,
)


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
