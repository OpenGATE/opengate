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

    def __str__(self):
        u = self.user_info
        s = f'DoseActor "{u.name}": dim={u.dimension} spacing={u.spacing} {u.save} tr={u.translation}'
        return s

    def initialize(self):
        gam.ActorBase.initialize(self)
        # FIXME helpers_image
        # create itk image (py side)
        dim = 3
        pixel_type = itk.ctype('float')
        image_type = itk.Image[pixel_type, dim]
        self.py_image = image_type.New()
        region = itk.ImageRegion[dim]()
        size = np.array(self.user_info.dimension)
        region.SetSize(size.tolist())
        region.SetIndex([0, 0, 0])
        spacing = np.array(self.user_info.spacing)
        self.py_image.SetRegions(region)
        self.py_image.SetSpacing(spacing)
        # compute the cente, taking translation into account
        self.img_center = -size * spacing / 2.0 + spacing / 2.0 + self.user_info.translation
        print('center', self.img_center)
        self.py_image.Allocate()  # needed !
        self.py_image.FillBuffer(0.0)

    def BeginOfRunAction(self, run):
        print('Dose3 begin of run')
        # Compute the transformation from global (world) position 
        # to local (attachedTo volume) position
        vol_name = self.user_info.attachedTo
        translation, rotation = gam.get_transform_world_to_local(vol_name)
        t = gam.get_translation_from_rotation_with_center(Rotation.from_matrix(rotation), self.img_center)
        # compute and set the origin
        origin = translation + self.img_center - t
        self.py_image.SetOrigin(origin)
        self.py_image.SetDirection(rotation)

        # send itk image to cpp side
        gam.update_image_py_to_cpp(self.py_image, self.cpp_image, rotation)
        #arr = itk.array_view_from_image(self.py_image)
        # print('array done', arr.shape)
        #self.cpp_image.set_spacing(self.py_image.GetSpacing())
        #self.cpp_image.set_origin(self.py_image.GetOrigin())
        # self.cpp_image.set_direction(self.user_info.rotation) # FIXME
        #self.cpp_image.set_direction(rotation)
        #self.cpp_image.from_pyarray(arr)

    def EndOfRunAction(self, run):
        print('Dose3 end of run')
        # get itk image from cpp side
        print('From cpp to py')
        arr = self.cpp_image.to_pyarray()  # Currently a copy. Maybe latter as_pyarray ?
        # print('array done', arr.shape)
        self.py_image = itk.image_from_array(arr)
        self.py_image.SetSpacing(self.cpp_image.spacing())
        self.py_image.SetOrigin(self.img_center)  # + self.user_info.translation)  # self.cpp_image.origin())
        # self.py_image.SetDirection(self.cpp_image.direction())
        # print('img done', self.py_image.GetLargestPossibleRegion().GetSize(), self.py_image.GetSpacing())
        itk.imwrite(self.py_image, self.user_info.save)
        print('write dose image ok')
