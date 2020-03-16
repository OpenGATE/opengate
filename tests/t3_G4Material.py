#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import geant4 as g4

n = g4.G4NistManager.Instance()

print('n', n)

# http://geant4-userdoc.web.cern.ch/geant4-userdoc/UsersGuides/ForApplicationDeveloper/html/Appendix/materialNames.html
mat = n.FindOrBuildMaterial('G4_WATER')
print('mat1', mat)

mat = n.FindOrBuildMaterial('G4_TISSUE-PROPANE')
print('mat2', mat)

#n.SetVerbose(10)
#n.PrintG4Material('all') #1 <--- seg fault

n.ListMaterials('all')

print('------------------------------')

# density = 1.0 #*g/cm3;
# ncomp = 2;
# h2o = g4.G4Material('Water', density, ncomp)

# print(f'mat = {h2o}')

# #print(f'mat pr = {m.Print()}')

# print(f'mat type= {type(h2o)}')


