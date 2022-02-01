import gam_gate as gam
import gam_g4 as g4
import numpy as np
import itk
from scipy.spatial.transform import Rotation


class HitsProjectionActor(g4.GamHitsProjectionActor, gam.ActorBase):
    """
    FIXME TODO
    """

    type_name = 'HitsProjectionActor'

    @staticmethod
    def set_default_user_info(user_info):
        gam.ActorBase.set_default_user_info(user_info)
        # fixme add options here
        user_info.attributes = []
        user_info.output = 'projections.mhd'
        user_info.input_hits_collections = 'Hits'
        mm = gam.g4_units('mm')
        user_info.spacing = [4 * mm, 4 * mm, 100 * mm]
        user_info.dimension = [128, 128, 1]

    def __init__(self, user_info):
        gam.ActorBase.__init__(self, user_info)
        g4.GamHitsProjectionActor.__init__(self, user_info.__dict__)
        actions = {'StartSimulationAction', 'EndSimulationAction'}
        self.AddActions(actions)
        self.fStepFillNames = user_info.attributes
        self.image = None
        self.img_center = None

    def __del__(self):
        pass

    def __str__(self):
        s = f'HitsProjectionActor {self.user_info.name}'
        return s

    def StartSimulationAction(self):  # not needed, only if need to do something in python
        print("StartSimulationAction")
        # create image
        size = np.array(self.user_info.dimension)
        spacing = np.array(self.user_info.spacing)
        print(size, spacing)
        self.image = gam.create_3d_image(size, spacing)
        self.img_center = -size * spacing / 2.0 + spacing / 2.0  # + self.user_info.translation
        print(f'{self.img_center=}')
        # position according to the crystal
        vol = self.simulation.volume_manager.get_volume('spect_crystal')  # FIXME
        vol = vol.g4_physical_volumes[0].GetName()
        translation, rotation = gam.get_transform_world_to_local(vol)
        t = gam.get_translation_from_rotation_with_center(Rotation.from_matrix(rotation), self.img_center)
        print(f'{translation=} {rotation=} {t=}')
        origin = translation + self.img_center - t
        self.image.SetOrigin(origin)
        self.image.SetDirection(rotation)
        gam.update_image_py_to_cpp(self.image, self.fImage, True)
        g4.GamHitsProjectionActor.StartSimulationAction(self)

    def EndSimulationAction(self):
        print('EndSimulationAction')
        g4.GamHitsProjectionActor.EndSimulationAction(self)
        self.image = gam.get_cpp_image(self.fImage)
        # FIXME
        spacing = np.array(self.user_info.spacing)
        origin = spacing / 2.0
        origin[2] = 0.5
        self.image.SetOrigin(origin)

        itk.imwrite(self.image, gam.check_filename_type(self.user_info.output))
