#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.utility import g4_units
import opengate.tests.utility as utility
import opengate_core as g4
import math

if __name__ == "__main__":
    # Get Nist Material Manager
    n = g4.G4NistManager.Instance()
    print("Nist manager", n)

    # http://geant4-userdoc.web.cern.ch/geant4-userdoc/UsersGuides/ForApplicationDeveloper/html/Appendix/materialNames.html
    mat = n.FindOrBuildMaterial("G4_WATER")
    print("Mat Water", mat)
    assert mat.GetName() == "G4_WATER"
    gcm3 = g4_units.g_cm3
    print("Density ", mat.GetDensity(), mat.GetDensity() / gcm3)
    assert math.isclose(mat.GetDensity(), gcm3)
    print("Elements", mat.GetElementVector())
    print("Nb of elements", mat.GetNumberOfElements())
    assert mat.GetNumberOfElements() == 2
    elements = mat.GetElementVector()
    assert elements[0].GetSymbol() == "H"
    assert elements[1].GetSymbol() == "O"

    eV = g4_units.eV
    Imean = mat.GetIonisation().GetMeanExcitationEnergy()
    print("I mean = ", Imean / eV, "eV")
    assert math.isclose(Imean / eV, 78.0)

    # Another material
    mat = n.FindOrBuildMaterial("G4_TISSUE-PROPANE")
    print("Mat 2", mat, mat.GetName())
    N = mat.GetElementVector()[2]
    gmol = g4_units.g_mol
    print("N Z", N.GetZ())
    print("N A", N.GetA() / gmol)
    assert N.GetZ() == 7
    assert math.isclose(N.GetA() / gmol, 14.00676896)

    # n.ListMaterials('all')

    # simple simulation object
    print("-" * 80)
    sim = gate.Simulation()
    print(sim)

    utility.test_ok(True)
