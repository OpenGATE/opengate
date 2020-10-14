import gam
import gam_g4 as g4
import itk
import numpy as np

class ImageVolume(gam.VolumeBase):
    """
        Store information about a voxelized volume
    """

    def __init__(self, volume_info):
        """
        FIXME
        """
        # initialize key before the mother constructor
        volume_info.image = None
        # the (itk) image
        self.image = None
        # mother constructor
        gam.VolumeBase.__init__(self, volume_info)
        self.user_info.material = 'G4_AIR'

    def __del__(self):
        # for debug
        print('ImageVolume destructor <--- BUG somewhere here!')

    def __str__(self):
        # FIXME to modify according to the volume type,
        # for example with nb of copy (repeat), etc etc
        s = f'{self.user_info}'
        return s

    def construct(self, vol_manager):
        print('Image volume construct')

        # check the user parameters
        self.check_user_info()

        # read image
        self.image = itk.imread(self.user_info.image)
        size_pix = np.array(itk.size(self.image)).astype(int)
        spacing = np.array(self.image.GetSpacing())
        size_mm = size_pix * spacing

        # shorter coding
        name = self.user_info.name
        hsize_mm = size_mm/2.0
        hspacing = spacing / 2.0

        # build the bounding box volume
        print('bounding vol size', size_mm, hsize_mm)
        self.g4_solid = g4.G4Box(name, hsize_mm[0], hsize_mm[1], hsize_mm[2])
        air = vol_manager.find_or_build_material('G4_AIR')
        # print(air)
        self.g4_logical_volume = g4.G4LogicalVolume(self.g4_solid, air, name)
        print('pixel size', spacing, hspacing)

        # param Y
        self.g4_solid_y = g4.G4Box(name + '_Y', hsize_mm[0], hspacing[1], hsize_mm[2])
        self.g4_logical_y = g4.G4LogicalVolume(self.g4_solid_y, air, name + '_log_Y')
        self.g4_physical_y = g4.G4PVReplica(name + '_Y',
                                            self.g4_logical_y,
                                            self.g4_logical_volume,
                                            g4.EAxis.kYAxis,
                                            size_pix[1], spacing[1], 0.0)

        # param X
        self.g4_solid_x = g4.G4Box(name + '_X', hspacing[0], hspacing[1], hsize_mm[2])
        self.g4_logical_x = g4.G4LogicalVolume(self.g4_solid_x, air, name + '_log_X')
        self.g4_physical_x = g4.G4PVReplica(name + '_X',
                                            self.g4_logical_x,
                                            self.g4_logical_y,
                                            g4.EAxis.kXAxis,
                                            size_pix[0], spacing[0], 0.0)

        # param Z
        self.g4_solid_z = g4.G4Box(name + '_Z', hspacing[0], hspacing[1], hspacing[2])
        self.g4_logical_z = g4.G4LogicalVolume(self.g4_solid_z, air, name + '_log_Z')
        self.g4_voxel_param = g4.GamImageNestedParameterisation()
        self.g4_physical_z = g4.G4PVParameterised(name + '_Z',
                                                  self.g4_logical_z,
                                                  self.g4_logical_x,
                                                  g4.EAxis.kUndefined,
                                                  size_pix[2],
                                                  self.g4_voxel_param,
                                                  True)

        # find the mother's logical volume
        vol = self.user_info
        if vol.mother:
            st = g4.G4LogicalVolumeStore.GetInstance()
            mother_logical = st.GetVolume(vol.mother, False)
        else:
            mother_logical = None

        # consider the 3D transform -> helpers_transform.
        transform = gam.get_vol_g4_transform(vol)
        print('transform ', transform)
        self.g4_physical_volume = g4.G4PVPlacement(transform,
                                                   self.g4_logical_volume,  # logical volume
                                                   vol.name,  # volume name
                                                   mother_logical,  # mother volume or None if World
                                                   False,  # no boolean operation
                                                   0,  # copy number
                                                   True)  # overlaps checking
