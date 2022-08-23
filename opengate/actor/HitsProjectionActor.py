import opengate as gate
import opengate_core as g4
import numpy as np
import itk


class HitsProjectionActor(g4.GateHitsProjectionActor, gate.ActorBase):
    """
    This actor takes as input HitsCollections and performed binning in 2D images.
    If there are several HitsCollection as input, the slices will correspond to each HC.
    If there are several runs, images will also be slice-stacked.
    """

    type_name = "HitsProjectionActor"

    @staticmethod
    def set_default_user_info(user_info):
        gate.ActorBase.set_default_user_info(user_info)
        mm = gate.g4_units("mm")
        user_info.output = False
        user_info.input_hits_collections = ["Hits"]
        user_info.spacing = [4 * mm, 4 * mm]
        user_info.size = [128, 128]
        user_info.physical_volume_index = None

    def __init__(self, user_info):
        gate.ActorBase.__init__(self, user_info)
        g4.GateHitsProjectionActor.__init__(self, user_info.__dict__)
        actions = {"StartSimulationAction", "BeginOfRunAction", "EndSimulationAction"}
        self.AddActions(actions)
        self.output_image = None
        if len(user_info.input_hits_collections) < 1:
            gate.fatal(f"Error, not input hits collection.")

    def __del__(self):
        pass

    def __str__(self):
        s = f"HitsProjectionActor {self.user_info.name}"
        return s

    def compute_thickness(self, simulation, volume, channels):
        """
        Unused for the moment
        """
        vol = simulation.volume_manager.get_volume(volume)
        solid = vol.g4_physical_volumes[0].GetLogicalVolume().GetSolid()
        pMin = g4.G4ThreeVector()
        pMax = g4.G4ThreeVector()
        solid.BoundingLimits(pMin, pMax)
        thickness = (pMax[2] - pMin[2]) / channels
        return thickness

    def StartSimulationAction(self):
        # check size and spacing
        if len(self.user_info.size) != 2:
            gate.fatal(f"Error, the size must be 2D while it is {self.user_info.size}")
        if len(self.user_info.spacing) != 2:
            gate.fatal(
                f"Error, the spacing must be 2D while it is {self.user_info.spacing}"
            )
        self.user_info.size.append(1)
        self.user_info.spacing.append(1)
        # define the new size and spacing according to the nb of channels and volume shape
        size = np.array(self.user_info.size)
        spacing = np.array(self.user_info.spacing)
        size[2] = len(self.user_info.input_hits_collections) * len(
            self.simulation.run_timing_intervals
        )
        spacing[2] = self.compute_thickness(
            self.simulation, self.user_info.mother, size[2]
        )
        # create image
        self.output_image = gate.create_3d_image(size, spacing)
        # initial position (will be anyway updated in BeginOfRunSimulation)
        try:
            pv = gate.get_physical_volume(
                self.simulation,
                self.user_info.mother,
                self.user_info.physical_volume_index,
            )
        except:
            gate.fatal(f"Error in the HitsProjectionActor {self.user_info.name}")
        gate.attach_image_to_physical_volume(pv.GetName(), self.output_image)
        self.fPhysicalVolumeName = str(pv.GetName())
        # update the cpp image and start
        gate.update_image_py_to_cpp(self.output_image, self.fImage, True)
        g4.GateHitsProjectionActor.StartSimulationAction(self)

    def EndSimulationAction(self):
        g4.GateHitsProjectionActor.EndSimulationAction(self)
        # retrieve the image
        self.output_image = gate.get_cpp_image(self.fImage)
        # change the spacing and origin for the third dimension
        spacing = self.output_image.GetSpacing()
        origin = self.output_image.GetOrigin()
        spacing[2] = 1
        origin[2] = 0
        self.output_image.SetSpacing(spacing)
        self.output_image.SetOrigin(origin)
        if self.user_info.output:
            itk.imwrite(
                self.output_image, gate.check_filename_type(self.user_info.output)
            )
