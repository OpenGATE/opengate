import gam_g4 as g4
import itk
import numpy as np
import gam
from scipy.spatial.transform import Rotation


class DoseActor(g4.GamDoseActor, gam.ActorBase):
    """
    DoseActor: compute a 3D edep/dose map for deposited
    energy/absorbed dose in the attached volume

    The dose map is parameterized with:
        - dimension (number of voxels)
        - spacing (voxel size)
        - translation (according to the coordinate system of the "attachedTo" volume
        - (no rotation yet)

    Options
        - edep only for the moment
        - later: add dose, uncertainty, squared etc 

    """

    def __init__(self, actor_info):
        g4.GamDoseActor.__init__(self)
        gam.ActorBase.__init__(self, actor_info)
        # define the actions that will trigger the actor
        self.actions = ['BeginOfRunAction', 'EndOfRunAction', 'ProcessHits']
        # required user info, default values
        mm = gam.g4_units('mm')
        self.add_default_info('dimension', [10, 10, 10])
        self.add_default_info('spacing', [1 * mm, 1 * mm, 1 * mm])
        self.add_default_info('save', 'edep.mhd')
        self.add_default_info('translation', [0, 0, 0])
        # default image (py side)
        self.py_image = None
        self.img_center = None
        self.first_run = None

    def __str__(self):
        u = self.user_info
        s = f'DoseActor "{u.name}": dim={u.dimension} spacing={u.spacing} {u.save} tr={u.translation}'
        return s

    def initialize(self):
        gam.ActorBase.initialize(self)
        # create itk image (py side)
        size = np.array(self.user_info.dimension)
        spacing = np.array(self.user_info.spacing)
        self.py_image = gam.create_3d_image(size, spacing)
        # compute the center, taking translation into account
        self.img_center = -size * spacing / 2.0 + spacing / 2.0 + self.user_info.translation
        # run
        self.first_run = True

    def BeginOfRunAction(self, run):
        # Compute the transformation from global (world) position 
        # to local (attachedTo volume) position
        vol_name = self.user_info.attachedTo
        translation, rotation = gam.get_transform_world_to_local(vol_name)
        t = gam.get_translation_from_rotation_with_center(Rotation.from_matrix(rotation), self.img_center)
        # compute and set the origin: the center of the volume
        origin = translation + self.img_center - t
        self.py_image.SetOrigin(origin)
        self.py_image.SetDirection(rotation)
        # send itk image to cpp side, copy data only the first run.
        gam.update_image_py_to_cpp(self.py_image, self.cpp_image, self.first_run)
        self.first_run = False

    def EndOfRunAction(self, run):
        # get itk image from cpp side
        # Currently a copy. Maybe latter as_pyarray ?
        arr = self.cpp_image.to_pyarray()
        self.py_image = itk.image_from_array(arr)
        # set the property of the output image:
        # in the coordinate system of the attached volume
        self.py_image.SetOrigin(self.img_center)
        self.py_image.SetSpacing(np.array(self.user_info.spacing))
        itk.imwrite(self.py_image, self.user_info.save)
