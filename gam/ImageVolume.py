import gam
import gam_g4 as g4


class ImageVolume(gam.VolumeBase):
    """
        Store information about a voxelized volume
    """

    def __init__(self, volume_info):
        """
        FIXME
        """
        # initialize key before the mother constructor
        volume_info.image = ''
        volume_info.pixel_size = None
        volume_info.image_size = None
        # mother constructor
        gam.VolumeBase.__init__(self, volume_info)
        self.user_info.material = 'G4_AIR'

    def __del__(self):
        # for debug
        print('ImageVolume destructor')
        pass

    def __str__(self):
        # FIXME to modify according to the volume type,
        # for example with nb of copy (repeat), etc etc
        s = f'{self.user_info}'
        return s

    def construct(self, vol_manager):
        print('Image volume construct')

        # check the user parameters
        self.check_user_info()

        # shorter coding
        size = self.user_info.size
        hsize = [size[0] / 2.0, size[1] / 2.0, size[2] / 2.0]
        name = self.user_info.name
        pixel_size = self.user_info.pixel_size
        hpixel_size = [pixel_size[0] / 2.0, pixel_size[1] / 2.0, pixel_size[2] / 2.0]
        image_size = self.user_info.image_size

        # build the bounding box volume
        print('bounding vol size', size, hsize)
        self.g4_solid = g4.G4Box(name, hsize[0], hsize[1], hsize[2])
        air = vol_manager.find_or_build_material('G4_AIR')
        # print(air)
        self.g4_logical_volume = g4.G4LogicalVolume(self.g4_solid, air, name)
        print('log bounding box ok')

        # param Y
        self.g4_solid_y = g4.G4Box(name + '_Y', hsize[0], hpixel_size[1], hsize[2])
        self.g4_logical_y = g4.G4LogicalVolume(self.g4_solid_y, air, name + '_Y')
        self.g4_physical_y = g4.G4PVReplica(name + '_Y',
                                            self.g4_logical_y,
                                            self.g4_logical_volume,
                                            g4.EAxis.kYAxis,
                                            image_size[1], pixel_size[1], 0.0)

        # param X
        self.g4_solid_x = g4.G4Box(name + '_X', hsize[0], hsize[1], hpixel_size[2])
        self.g4_logical_x = g4.G4LogicalVolume(self.g4_solid_x, air, name + '_X')
        self.g4_physical_x = g4.G4PVReplica(name + '_X',
                                            self.g4_logical_x,
                                            self.g4_logical_y,
                                            g4.EAxis.kXAxis,
                                            image_size[0], pixel_size[0], 0.0)

        # param Z
        self.g4_solid_z = g4.G4Box(name + '_Z', hsize[0], hsize[1], hpixel_size[2])
        self.g4_logical_z = g4.G4LogicalVolume(self.g4_solid_z, air, name + '_Z')
        self.g4_voxel_param = g4.GamImageNestedParameterisation()
        self.g4_physical_z = g4.G4PVParameterised(name + '_Z',
                                                  self.g4_logical_z,
                                                  self.g4_logical_x,
                                                  g4.EAxis.kUndefined, image_size[2],
                                                  self.g4_voxel_param, False)

        # find the mother's logical volume
        vol = self.user_info
        if vol.mother:
            st = g4.G4LogicalVolumeStore.GetInstance()
            mother_logical = st.GetVolume(vol.mother, False)
        else:
            mother_logical = None

        # consider the 3D transform -> helpers_transform.
        transform = gam.get_vol_transform(vol)
        self.g4_physical_volume = g4.G4PVPlacement(transform,
                                                   self.g4_logical_volume,  # logical volume
                                                   vol.name,  # volume name
                                                   mother_logical,  # mother volume or None if World
                                                   False,  # no boolean operation
                                                   0,  # copy number
                                                   True)  # overlaps checking
