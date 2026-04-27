#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Apr 2 09:48:30 2025

@author: fava
"""

import matplotlib.pyplot as plt
import numpy as np
from scipy.spatial.transform import Rotation
import opengate as gate
from opengate.utility import g4_units
import opengate.tests.utility as utility


def simuation_IDD(test_material):
    paths = utility.get_default_test_paths(__file__, "gate_test044_pbs")

    # units
    eV = g4_units.eV
    MeV = g4_units.MeV
    cm = g4_units.cm
    mm = g4_units.mm

    # create simulation object
    sim = gate.Simulation()
    # sim.number_of_threads = 4
    sim.volume_manager.add_material_database(paths.data / "GateMaterials.db")

    # waterbox
    phantom = sim.add_volume("Box", "phantom")
    phantom.size = [10 * cm, 10 * cm, 10 * cm]
    phantom.translation = [-5 * cm, 0, 0]
    phantom.material = "G4_WATER"
    phantom.color = [0, 0, 1, 1]

    phantom_off = sim.add_volume("Box", "phantom_off")
    phantom_off.mother = phantom.name
    phantom_off.size = [100 * mm, 60 * mm, 60 * mm]
    phantom_off.translation = [0 * mm, 0 * mm, 0 * mm]
    phantom_off.material = test_material
    phantom_off.color = [0, 0, 1, 1]

    # physics
    sim.physics_manager.physics_list_name = "QGSP_BIC_EMZ"

    # default source for tests
    source = sim.add_source("GenericSource", "mysource")
    source.energy.mono = 1424 * MeV
    source.particle = "ion 6 12"

    source.position.type = "disc"
    source.position.rotation = Rotation.from_euler("y", 90, degrees=True).as_matrix()
    source.position.radius = 4 * mm
    source.position.translation = [0, 0, 0]
    source.direction.type = "momentum"
    source.direction.momentum = [-1, 0, 0]
    # print(dir(source.energy))
    source.n = 1e3
    # source.activity = 100 * kBq

    size = [500, 1, 1]
    spacing = [0.2 * mm, 60.0 * mm, 60.0 * mm]

    doseActorName_IDD_d = "IDD"
    doseIDD = sim.add_actor("DoseActor", doseActorName_IDD_d)
    doseIDD.output_filename = paths.output / ("test087-" + doseActorName_IDD_d + ".mhd")
    #    print(f'actor: {paths.output / ("test087-" + doseActorName_IDD_d + ".mhd")}')
    doseIDD.attached_to = phantom_off.name
    doseIDD.size = size
    doseIDD.spacing = spacing
    doseIDD.hit_type = "random"
    doseIDD.dose.active = True

    return sim, doseIDD


if __name__ == "__main__":
    # units
    eV = g4_units.eV
    cm = g4_units.cm

    # overrides for material ionisation potential
    test_material = "Water"
    materials_Ival_dict = {test_material: 30 * eV}

    sim, dose = simuation_IDD(test_material)

    # dump ionisation value before modification
    mat = sim.volume_manager.find_or_build_material(test_material)
    ionisation = mat.GetIonisation().GetMeanExcitationEnergy()
    print(f"Default ionisation potential of {test_material}: {ionisation} eV")

    # run simulation with default value for material
    sim.run(True)

    # get idd
    idd_pre = np.flip(np.asarray(dose.dose.image), axis=2)
    x1, d1_pre = utility.get_1D_profile(
        idd_pre, np.flip(dose.size), dose.spacing, axis="x"
    )
    r80_pre, _ = utility.getRange(x1, d1_pre)
    plt.plot(x1, d1_pre)
    print(f"Range in water: {r80_pre} mm")

    # run simulation again, but with modified ionisation potential
    sim, dose = simuation_IDD(test_material)
    sim.physics_manager.material_ionisation_potential = materials_Ival_dict

    # run simulation with new value
    sim.run(True)

    # dump ionisation value after modification
    ionisation = mat.GetIonisation().GetMeanExcitationEnergy()
    print(f"New ionisation potential of {test_material}: {ionisation} eV")

    # get idd
    idd_after = np.flip(np.asarray(dose.dose.image), axis=2)
    x1, d1_after = utility.get_1D_profile(
        idd_after, np.flip(dose.size), dose.spacing, axis="x"
    )
    r80_after, _ = utility.getRange(x1, d1_after)
    plt.plot(x1, d1_after)
    print(f"Range in water: {r80_after} mm")

    ok = (r80_pre - r80_after) > dose.spacing[0]
    utility.test_ok(ok)
