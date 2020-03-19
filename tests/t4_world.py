#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import geant4 as g4

# --------------------------------------------------------------
# Detector
class MyWorld(g4.G4VUserDetectorConstruction):
    """
    Example class to create a scene
    """

    def __init__(self):
        print('Constructor MyWorld')
        g4.G4VUserDetectorConstruction.__init__(self)
        print('end constructor MyWorld')

    def Construct(self):
        print('MyWorld::Construct')

        # Get some materials
        nist = g4.G4NistManager.Instance()
        air = nist.FindOrBuildMaterial('G4_AIR')
        water = nist.FindOrBuildMaterial('G4_WATER')
        #print(air, water)

        ###### WARNING
        # logic_XXXX must be store in self to avoid segmenation fault
        # not fully clear why, probably pointer ownership issue 
        ###### WARNING

        # Create world box: Solid / LogicalVolume / PhysicalVolume
        solid_world = g4.G4Box("World",       # name
                               2000, 2000, 2000) # size in mm
        print('solid', solid_world)
        self.logic_world = g4.G4LogicalVolume(solid_world, # solid
                                         air,         # material
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

        #print('phys repr', repr(self.phys_world))
        #self.phys_world.__class__ = g4.G4VPhysicalVolume # kind of a cast
        #print('phys repr', repr(self.phys_world))

        print(f'translation {self.phys_world.GetTranslation()}')
        print(f'GetCopyNo {self.phys_world.GetCopyNo()}')
        
        print('RETURN')
        return self.phys_world

        # Create water box
        solid_waterbox = g4.G4Box("Waterbox",       # name
                                  200, 200, 200) # size in mm
        print('solid_waterbox', solid_waterbox)
        self.logic_waterbox = g4.G4LogicalVolume(solid_waterbox, # solid
                                            air,         # material
                                            "Waterbox")    # name
        print('self.logic_waterbox', self.logic_waterbox)
        phys_waterbox = g4.G4PVPlacement(None,              # no rotation
                                         g4.G4ThreeVector(),    # at (0,0,0)
                                         self.logic_waterbox,        # logical volume
                                         "Waterbox",            # name
                                         self.logic_world,           # mother  volume ### FIXME??
                                         #FIXME BUG HERE ?
                                         False,                 # no boolean operation
                                         0,                     # copy number
                                         True)                  # overlaps checking
        print('phys_waterbox', phys_waterbox)
        print('self.phys_world', self.phys_world)
        print('return')
        return self.phys_world



## TEST

# a = MyWorld()
# print(a)
# pw = a.Construct()
# print('here')
# print('pw', pw)
# print('pw copy ', pw.GetCopyNo())
# print('end')

