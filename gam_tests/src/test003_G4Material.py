#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam_gate as gam
import gam_g4 as g4
import math

# Get Nist Material Manager
n = g4.G4NistManager.Instance()
print('Nist manager', n)

# http://geant4-userdoc.web.cern.ch/geant4-userdoc/UsersGuides/ForApplicationDeveloper/html/Appendix/materialNames.html
mat = n.FindOrBuildMaterial('G4_WATER')
print('Mat Water', mat)
assert mat.GetName() == 'G4_WATER'
gcm3 = gam.g4_units('g/cm3')
print('Density ', mat.GetDensity(), mat.GetDensity() / gcm3)
assert math.isclose(mat.GetDensity(), gcm3)
print('Elements', mat.GetElementVector())
print('Nb of elements', mat.GetNumberOfElements())
assert mat.GetNumberOfElements() == 2
elements = mat.GetElementVector()
assert elements[0].GetSymbol() == 'H'
assert elements[1].GetSymbol() == 'O'

eV = gam.g4_units('eV')
Imean = mat.GetIonisation().GetMeanExcitationEnergy()
print('I mean = ', Imean / eV, 'eV')
assert math.isclose(Imean / eV, 78.0)

# Another material
mat = n.FindOrBuildMaterial('G4_TISSUE-PROPANE')
print('Mat 2', mat, mat.GetName())
N = mat.GetElementVector()[2]
gmol = gam.g4_units('g/mol')
print('N Z', N.GetZ())
print('N A', N.GetA() / gmol)
assert N.GetZ() == 7
assert math.isclose(N.GetA() / gmol, 14.00676896)

# n.ListMaterials('all')

# simple simulation object
print('-' * 80)
sim = gam.Simulation()
print(sim)

gam.test_ok(True)
