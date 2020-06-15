from box import Box

import gam  # needed for gam_setup
import geant4 as g4


class Geometry(g4.G4VUserDetectorConstruction):
    """
    TODO
    """

    def __init__(self, geometry):
        """
        TODO
        """
        g4.G4VUserDetectorConstruction.__init__(self)
        self.geometry = geometry
        self.g4_solid_volumes = Box()
        self.g4_logical_volumes = Box()
        self.g4_physical_volumes = Box()
        self.g4_materials = Box()

    def __del__(self):
        print('===========================>  Geometry destructor')
        #del self.logic_waterbox
        # it seems that phys_waterbox should be delete here, before the auto delete.
        # it not, sometimes, it seg fault after the simulation end
        #if hasattr(self, 'phys_waterbox'):
        del self.g4_physical_volumes.Waterbox
        #del self.g4_physical_volumes.World
        #del self.g4_logical_volumes.Waterbox
        #del self.g4_logical_volumes.World
        print('===========================>  Geometry destructor')

    def Construct(self):
        print('Geometry::Construct')

        # tree re-order

        # material
        self.nist = g4.G4NistManager.Instance()
        self.g4_materials.Air = self.nist.FindOrBuildMaterial('G4_AIR')
        self.g4_materials.Water = self.nist.FindOrBuildMaterial('G4_WATER')

        for volname in self.geometry:
            print(volname)
            vol  =self.geometry[volname]
            p = self.construct_volume(vol)
            self.g4_physical_volumes[vol.name] = p

        return self.g4_physical_volumes.World

    def construct_volume(self, vol):
        """
        -> standard build, other build functions will build complex vol (voxelized, repeater)
        """
        print('construct volume ', vol)
        solid = g4.G4Box(vol.name,  # name
                         vol.size[0], vol.size[1], vol.size[2])  # size in mm
        print('solid', solid)
        material = self.g4_materials[vol.material]
        print('material', material)
        logical = g4.G4LogicalVolume(solid,  # solid
                                     material,  # material
                                     vol.name)  # name
        print('logical', logical)
        if vol.mother:
            mother_logical = self.g4_logical_volumes[vol.mother]
        else:
            mother_logical = None
        print('mother', mother_logical)
        physical = g4.G4PVPlacement(None,  # no rotation
                                    vol.translation, #
                                    logical,  # logical volume
                                    vol.name,
                                    mother_logical,  # no mother volume
                                    False,  # no boolean operation
                                    0,  # copy number
                                    True)  # overlaps checking
        print('physical', physical)
        self.g4_solid_volumes[vol.name] = solid
        self.g4_logical_volumes[vol.name] = logical
        return physical
