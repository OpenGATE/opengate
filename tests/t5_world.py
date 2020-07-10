#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam_g4 as g4

# --------------------------------------------------------------
# Detector
class MyWorld(g4.G4VUserDetectorConstruction):
    """
    World + waterbox
    """

    def __init__(self):
        print('Constructor MyWorld')
        g4.G4VUserDetectorConstruction.__init__(self)
        print('end constructor MyWorld')

    def __del__(self):
        #print('===========================>  MyWorld destructor')
        #del self.logic_waterbox
        # it seems that phys_waterbox should be delete here, before the auto delete.
        # it not, sometimes, it seg fault after the simulation end
        if hasattr(self, 'phys_waterbox'):
            del self.phys_waterbox
        #del self.logic_world
        #del self.phys_world
        #print('===========================>  MyWorld destructor')
        
    def Construct(self):
        print('MyWorld::Construct')

        # Get some materials
        self.nist = g4.G4NistManager.Instance()
        self.air = self.nist.FindOrBuildMaterial('G4_AIR')
        self.water = self.nist.FindOrBuildMaterial('G4_WATER')
        print(self.air, self.water)

        ###### WARNING
        # logic_XXXX must be store in self to avoid segmenation fault
        # not fully clear why, probably pointer ownership issue 
        ###### WARNING

        # Create world box: Solid / LogicalVolume / PhysicalVolume
        self.solid_world = g4.G4Box("World",       # name
                                    4000, 4000, 4000) # size in mm
        print('solid', self.solid_world)
        self.logic_world = g4.G4LogicalVolume(self.solid_world, # solid
                                              self.air,         # material
                                              "World")    # name

        print('self.logic_world, ', self.logic_world)
        print('self.logic_world name ', self.logic_world.GetName())
        
        print('logical', self.logic_world)
        self.phys_world = g4.G4PVPlacement(None,              # no rotation
                                           g4.G4ThreeVector(),    # at (0,0,0)
                                           self.logic_world,      # logical volume
                                           "World",               # name
                                           None,                  # no mother volume
                                           False,                 # no boolean operation
                                           0,                     # copy number
                                           True)                  # overlaps checking

        print('phys', self.phys_world)

        # Create water box
        self.solid_waterbox = g4.G4Box("Waterbox",       # name
                                       200, 200, 200) # size in mm
        print('solid_waterbox', self.solid_waterbox)
        self.logic_waterbox = g4.G4LogicalVolume(self.solid_waterbox, # solid
                                                 self.water,         # material
                                                 "Waterbox")    # name
        print('self.logic_waterbox', self.logic_waterbox)
        self.phys_waterbox = g4.G4PVPlacement(None,              # no rotation
                                              g4.G4ThreeVector(0, 0, 250),    # at (0,0,0)
                                              self.logic_waterbox,        # logical volume
                                              "Waterbox",            # name
                                              self.logic_world,           # mother  volume ### FIXME??
                                              False,                 # no boolean operation
                                              0,                     # copy number
                                              True)                  # overlaps checking
        print('phys_waterbox', self.phys_waterbox)
        print('self.phys_world', self.phys_world)
        print(f'translation wb {self.phys_waterbox.GetTranslation()}')
        return self.phys_world

