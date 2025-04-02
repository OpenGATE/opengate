#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Apr  2 09:48:30 2025

@author: fava
"""


import opengate as gate
from opengate.utility import g4_units
import opengate.tests.utility as utility
import opengate_core as g4

if __name__ == "__main__":
    # units
    eV = g4_units.eV
    cm = g4_units.cm

    # create simulation object
    sim = gate.Simulation()

    # overrides for material ionisation potential
    test_material = "G4_WATER"
    materials_Ival_dict = {test_material: 75 * eV}

    # add a waterbox
    wb = sim.add_volume("Box", "box")
    wb.size = [50 * cm, 50 * cm, 50 * cm]
    wb.material = test_material

    # dump ionisation value before modification
    mat = sim.volume_manager.find_or_build_material(test_material)
    ionisation = mat.GetIonisation().GetMeanExcitationEnergy()
    print(f"Default ionisation potential of {test_material}: {ionisation} eV")

    # set to physics manager
    sim.physics_manager.material_ionization_potential = materials_Ival_dict

    sim.run()

    # dump ionisation value after modification
    mat = sim.volume_manager.find_or_build_material(test_material)
    ionisation = mat.GetIonisation().GetMeanExcitationEnergy()
    print(f"New ionisation potential of {test_material}: {ionisation} eV")

    ok = ionisation == materials_Ival_dict[test_material]
    utility.test_ok(ok)
