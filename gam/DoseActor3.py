import gam_g4 as g4
import itk
import numpy as np
import gam


class DoseActor3(g4.GamDoseActor3, gam.ActorBase):
    """
    TODO
    """

    def __init__(self, actor_info):
        g4.GamDoseActor3.__init__(self)
        gam.ActorBase.__init__(self, actor_info)
        # define the actions that will trigger the actor
        self.actions = ['BeginOfRunAction', 'EndOfRunAction', 'ProcessHits']
        # required user info
        mm = gam.g4_units('mm')
        self.add_default_info('dimension', [10, 10, 10])
        self.add_default_info('spacing', [1 * mm, 1 * mm, 1 * mm])
        self.add_default_info('save', 'dose.mhd')
        self.add_default_info('translation', [0, 0, 0])
        self.add_default_info('rotation', None)
        # default members
        self.py_image = None

    def __str__(self):
        # FIXME
        s = f'str Dose Actor3 '
        return s

    def initialize(self):
        gam.ActorBase.initialize(self)
        # create itk image
        dim = 3
        pixel_type = itk.ctype('float')
        image_type = itk.Image[pixel_type, dim]
        self.py_image = image_type.New()
        region = itk.ImageRegion[dim]()
        size = np.array(self.user_info.dimension)
        region.SetSize(size.tolist())
        region.SetIndex([0, 0, 0])
        spacing = np.array(self.user_info.spacing)
        origin = -size * spacing / 2.0
        print(spacing, origin)
        # FIXME translation / rotation ?
        self.py_image.SetRegions(region)
        self.py_image.SetOrigin(origin)
        self.py_image.SetSpacing(spacing)
        self.py_image.Allocate()  # needed !
        self.py_image.FillBuffer(0.0)

    def BeginOfRunAction(self, run):
        print('Dose3 begin of run')
        # send itk image to cpp side
        # print('From py to cpp')
        # FIXME conversion in helper class
        arr = itk.array_view_from_image(self.py_image)
        # print('array done', arr.shape)
        self.cpp_image.set_spacing(self.py_image.GetSpacing())
        self.cpp_image.set_origin(self.py_image.GetOrigin())
        # self.cpp_image.set_direction(self.py_image.GetDirection())
        self.cpp_image.from_pyarray(arr)
        itk.imwrite(self.py_image, 'dose_before.mhd')
        print('img done')

    def EndOfRunAction(self, run):
        print('Dose3 end of run')
        # get itk image from cpp side
        print('From cpp to py')
        arr = self.cpp_image.to_pyarray()  # Currently a copy. Maybe latter as_pyarray ?
        # print('array done', arr.shape)
        self.py_image = itk.image_from_array(arr)
        self.py_image.SetSpacing(self.cpp_image.spacing())
        origin = [25, 25, 9]
        self.py_image.SetOrigin(origin)
        #self.py_image.SetOrigin(self.cpp_image.origin())

        # self.py_image.SetDirection(self.cpp_image.direction())
        # print('img done', self.py_image.GetLargestPossibleRegion().GetSize(), self.py_image.GetSpacing())
        itk.imwrite(self.py_image, 'dose.mhd')
        print('write dose image ok')
