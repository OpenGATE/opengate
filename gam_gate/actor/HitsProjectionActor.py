import gam_gate as gam
import gam_g4 as g4
import numpy as np
import itk


class HitsProjectionActor(g4.GamHitsProjectionActor, gam.ActorBase):
    """
    This actor takes as input HitsCollections and performed binning in 2D images.
    If there are several HitsCollection as input, the slices will correspond to each HC.
    If there are several runs, images will also be slice-stacked.
    """

    type_name = 'HitsProjectionActor'

    @staticmethod
    def set_default_user_info(user_info):
        gam.ActorBase.set_default_user_info(user_info)
        # fixme add options here
        mm = gam.g4_units('mm')
        user_info.output = 'projections.mhd'
        user_info.input_hits_collections = ['Hits']
        user_info.spacing = [4 * mm, 4 * mm]
        user_info.dimension = [128, 128]
        user_info.physical_volume_index = None

    def __init__(self, user_info):
        gam.ActorBase.__init__(self, user_info)
        g4.GamHitsProjectionActor.__init__(self, user_info.__dict__)
        actions = {'StartSimulationAction', 'BeginOfRunAction', 'EndSimulationAction'}
        self.AddActions(actions)
        self.image = None
        if len(user_info.input_hits_collections) < 1:
            gam.fatal(f'Error, not input hits collection.')

    def __del__(self):
        pass

    def __str__(self):
        s = f'HitsProjectionActor {self.user_info.name}'
        return s

    def StartSimulationAction(self):
        # size according to the mother volume
        vol = self.simulation.volume_manager.get_volume(self.user_info.mother)
        solid = vol.g4_physical_volumes[0].GetLogicalVolume().GetSolid()
        pMin = g4.G4ThreeVector()
        pMax = g4.G4ThreeVector()
        solid.BoundingLimits(pMin, pMax)
        # check size and spacing
        if len(self.user_info.dimension) != 2:
            gam.fatal(f'Error, the dimension must be 2D while it is {self.user_info.dimension}')
        if len(self.user_info.spacing) != 2:
            gam.fatal(f'Error, the spacing must be 2D while it is {self.user_info.spacing}')
        self.user_info.dimension.append(1)
        self.user_info.spacing.append(1)
        # define the new size and spacing according to the nb of channels and volume shape
        size = np.array(self.user_info.dimension)
        spacing = np.array(self.user_info.spacing)
        size[2] = len(self.user_info.input_hits_collections) * len(self.simulation.run_timing_intervals)
        spacing[2] = (pMax[2] - pMin[2]) / size[2]
        # create image
        self.image = gam.create_3d_image(size, spacing)
        # initial position (will be anyway updated in BeginOfRunSimulation)
        try:
            pv = gam.get_physical_volume(self.simulation, self.user_info.mother,
                                         self.user_info.physical_volume_index)
        except:
            gam.fatal(f'Error in the HitsProjectionActor {self.user_info.name}')
        gam.attach_image_to_physical_volume(pv.GetName(), self.image)
        self.fPhysicalVolumeName = str(pv.GetName())
        # update the cpp image and start
        gam.update_image_py_to_cpp(self.image, self.fImage, True)
        g4.GamHitsProjectionActor.StartSimulationAction(self)

    def EndSimulationAction(self):
        g4.GamHitsProjectionActor.EndSimulationAction(self)
        self.image = gam.get_cpp_image(self.fImage)
        itk.imwrite(self.image, gam.check_filename_type(self.user_info.output))
