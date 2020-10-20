import gam
import gam_g4 as g4
import itk
import numpy as np


class ImageVolume(gam.VolumeBase):
    """
        Store information about a voxelized volume
    """

    volume_type = 'Image'

    def __init__(self, name):
        """
        FIXME
        """
        gam.VolumeBase.__init__(self, self.volume_type, name)
        u = self.user_info
        # initialize key before the mother constructor
        u.image = None
        u.material = 'G4_AIR'
        u.voxel_materials = [[None, 'G4_AIR']]
        u.dump_label_image = None
        # the (itk) image
        self.image = None

    def __del__(self):
        # for debug
        print('ImageVolume destructor <--- BUG somewhere here ?')

    def construct(self, vol_manager):
        # check the user parameters
        self.check_user_info()

        # read image
        self.image = itk.imread(self.user_info.image)
        size_pix = np.array(itk.size(self.image)).astype(int)
        spacing = np.array(self.image.GetSpacing())
        size_mm = size_pix * spacing

        # shorter coding
        name = self.user_info.name
        hsize_mm = size_mm / 2.0
        hspacing = spacing / 2.0

        # build the bounding box volume
        self.g4_solid = g4.G4Box(name, hsize_mm[0], hsize_mm[1], hsize_mm[2])
        def_mat = vol_manager.find_or_build_material(self.user_info.material)
        self.g4_logical_volume = g4.G4LogicalVolume(self.g4_solid, def_mat, name)

        # param Y
        self.g4_solid_y = g4.G4Box(name + '_Y', hsize_mm[0], hspacing[1], hsize_mm[2])
        self.g4_logical_y = g4.G4LogicalVolume(self.g4_solid_y, def_mat, name + '_log_Y')
        self.g4_physical_y = g4.G4PVReplica(name + '_Y',
                                            self.g4_logical_y,
                                            self.g4_logical_volume,
                                            g4.EAxis.kYAxis,
                                            size_pix[1], spacing[1], 0.0)

        # param X
        self.g4_solid_x = g4.G4Box(name + '_X', hspacing[0], hspacing[1], hsize_mm[2])
        self.g4_logical_x = g4.G4LogicalVolume(self.g4_solid_x, def_mat, name + '_log_X')
        self.g4_physical_x = g4.G4PVReplica(name + '_X',
                                            self.g4_logical_x,
                                            self.g4_logical_y,
                                            g4.EAxis.kXAxis,
                                            size_pix[0], spacing[0], 0.0)

        # param Z
        self.g4_solid_z = g4.G4Box(name + '_Z', hspacing[0], hspacing[1], hspacing[2])
        self.g4_logical_z = g4.G4LogicalVolume(self.g4_solid_z, def_mat, name + '_log_Z')
        self.initialize_image_parameterisation()
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
        self.g4_physical_volume = g4.G4PVPlacement(transform,
                                                   self.g4_logical_volume,  # logical volume
                                                   vol.name,  # volume name
                                                   mother_logical,  # mother volume or None if World
                                                   False,  # no boolean operation
                                                   0,  # copy number
                                                   True)  # overlaps checking

    def initialize_image_parameterisation(self):
        self.g4_voxel_param = g4.GamImageNestedParameterisation()
        # create image with same size
        info = gam.get_img_info(self.image)
        self.py_image = gam.create_3d_image(info.size, info.spacing)

        # intervals of voxels <-> materials
        mat = self.user_info.voxel_materials
        interval_values = [row[0] for row in mat]
        interval_materials = [row[1] for row in mat]

        # build the material
        for m in interval_materials:
            self.simulation.volume_manager.find_or_build_material(m)

        # convert interval to material id ; probably not very efficient
        input = itk.array_view_from_image(self.image).ravel()
        output = itk.array_view_from_image(self.py_image)
        out = output.ravel()
        for idx, pi in enumerate(input):
            mi = 0
            while mi < len(interval_values) and \
                    (interval_values[mi] is not None and pi > interval_values[mi]):
                mi += 1
            out[idx] = mi

        # dump label image ?
        if self.user_info.dump_label_image:
            itk.imwrite(self.py_image, self.user_info.dump_label_image)

        # send image to cpp size
        gam.update_image_py_to_cpp(self.py_image, self.g4_voxel_param.cpp_image, True)

        # initialize parametrisation
        self.g4_voxel_param.initialize_image()
        self.g4_voxel_param.initialize_material(interval_materials)
