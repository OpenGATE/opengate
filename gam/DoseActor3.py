import gam_g4 as g4
import itk
import numpy as np


class DoseActor3(g4.GamDoseActor3):
    """
    TODO
    """

    def __init__(self):
        g4.GamDoseActor3.__init__(self)
        self.actions = ['BeginOfRunAction', 'EndOfRunAction', 'ProcessHits']
        # here create itk image (no allocation)
        dim = 3
        pixel_type = itk.ctype('float')
        image_type = itk.Image[pixel_type, dim]
        self.py_image = image_type.New()
        region = itk.ImageRegion[dim]()
        size = np.array([100, 100, 100])
        region.SetSize(size.tolist())
        region.SetIndex([0, 0, 0])
        spacing = np.array([200, 200, 200]) / size
        origin = -size * spacing / 2.0
        # print(spacing, origin)
        self.py_image.SetRegions(region)
        self.py_image.SetOrigin(origin)
        self.py_image.SetSpacing(spacing)
        self.py_image.Allocate()  # needed !
        self.py_image.FillBuffer(0.0)
        # print(self.py_image)

    def __str__(self):
        s = f'str Dose Actor3 '
        return s

    def BeginOfRunAction(self, run):
        # print('Dose3 begin of run')
        # send itk image to cpp side
        # print('From py to cpp')
        # FIXME conversion in helper class
        arr = itk.array_view_from_image(self.py_image)
        # print('array done', arr.shape)
        self.cpp_image.set_spacing(self.py_image.GetSpacing())
        self.cpp_image.set_origin(self.py_image.GetOrigin())
        # self.cpp_image.set_direction(self.py_image.GetDirection())
        self.cpp_image.from_pyarray(arr)
        # itk.imwrite(self.py_image, 'dose_before.mhd')
        # print('img done')

    def EndOfRunAction(self, run):
        # print('Dose3 end of run')
        # get itk image from cpp side
        # print('From cpp to py')
        arr = self.cpp_image.to_pyarray()  # Currently a copy. Maybe latter as_pyarray ?
        # print('array done', arr.shape)
        self.py_image = itk.image_from_array(arr)
        self.py_image.SetSpacing(self.cpp_image.spacing())
        self.py_image.SetOrigin(self.cpp_image.origin())
        # self.py_image.SetDirection(self.cpp_image.direction())
        # print('img done', self.py_image.GetLargestPossibleRegion().GetSize(), self.py_image.GetSpacing())
        itk.imwrite(self.py_image, 'dose.mhd')
        # print('write ok')
