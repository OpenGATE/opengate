import gam_gate as gam
import gam_g4 as g4
import itk
import numpy as np


class ImageVolume(gam.VolumeBase):
    """
        Store information about a voxelized volume
    """

    type_name = 'Image'

    @staticmethod
    def set_default_user_info(user_info):
        gam.VolumeBase.set_default_user_info(user_info)
        user_info.image = None
        user_info.material = 'G4_AIR'
        user_info.voxel_materials = [[None, 'G4_AIR']]
        user_info.dump_label_image = None

    def __init__(self, user_info):
        super().__init__(user_info)
        # the (itk) image
        self.image = None
        # the list of regions
        self.g4_regions = []

    def __del__(self):
        pass

    def construct(self, vol_manager):

        ## FIXME split in  solid lv etc

        # check the user parameters
        # self.check_user_info()  # FIXME will be in init

        # read image
        self.image = itk.imread(gam.check_filename_type(self.user_info.image))
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
                                            size_pix[1],  # nReplicas
                                            spacing[1],  # width
                                            0.0)  # offset

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
                                                  g4.EAxis.kZAxis,  # g4.EAxis.kUndefined, ## FIXME ?
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

        # construct region
        # not clear -> should we create region for all other LV ?
        # (seg fault if region for g4_logical_z)
        self.add_region(self.g4_logical_volume)

    def add_region(self, lv):
        name = lv.GetName()
        rs = g4.G4RegionStore.GetInstance()
        r = rs.FindOrCreateRegion(name)
        self.g4_regions.append(r)
        lv.SetRegion(r)
        r.AddRootLogicalVolume(lv, True)

    def initialize_image_parameterisation(self):
        self.g4_voxel_param = g4.GamImageNestedParameterisation()
        # create image with same size
        info = gam.get_image_info(self.image)
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
            itk.imwrite(self.py_image, gam.check_filename_type(self.user_info.dump_label_image))

        # compute image origin
        size_pix = np.array(itk.size(self.py_image))
        spacing = np.array(self.py_image.GetSpacing())
        orig = -(size_pix * spacing) / 2.0 + spacing / 2.0
        self.py_image.SetOrigin(orig)

        # send image to cpp size
        gam.update_image_py_to_cpp(self.py_image, self.g4_voxel_param.cpp_edep_image, True)

        # initialize parametrisation
        self.g4_voxel_param.initialize_image()
        self.g4_voxel_param.initialize_material(interval_materials)
