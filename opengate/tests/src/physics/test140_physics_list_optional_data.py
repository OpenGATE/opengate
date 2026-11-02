#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test 140: the physics lists that need an optional Geant4 dataset (AllHP:
G4TENDL, LEND: LEND), not downloaded with the other Geant4 data.

1. without the dataset, the simulation stops before Geant4 is initialised with
   a GateUserError that says how to install it (opengate_download_data -o)
2. with the dataset (environment variable set), the check passes
3. the other physics lists do not need it

No simulation is run: the check is done when the configuration is resolved.
"""

import os

import opengate as gate
from opengate.exception import GateUserError
from opengate.tests import utility


def make_simulation(physics_list_name):
    sim = gate.Simulation()
    sim.physics_manager.physics_list_name = physics_list_name
    source = sim.add_source("GenericSource", "source")
    source.particle = "proton"
    source.energy.mono = 150 * gate.g4_units.MeV
    source.number_of_primaries = 10
    return sim


if __name__ == "__main__":
    is_ok = True
    for physics_list_name, variable in [
        ("QGSP_BIC_AllHP_EMZ", "G4PARTICLEHPDATA"),
        ("ShieldingLEND", "G4LENDDATA"),
    ]:
        saved = os.environ.pop(variable, None)
        try:
            # 1. dataset missing
            sim = make_simulation(physics_list_name)
            message = ""
            try:
                sim.run()
            except GateUserError as e:
                message = str(e)
            b = "opengate_download_data -o" in message and variable in message
            utility.print_test(
                b, f"{physics_list_name} without {variable}: {message!r}"
            )
            is_ok = is_ok and b

            # 2. dataset present
            os.environ[variable] = "/path/to/the/dataset"
            sim = make_simulation(physics_list_name)
            try:
                sim.physics_manager.check_optional_g4_data()
                b = True
            except GateUserError:
                b = False
            utility.print_test(b, f"{physics_list_name} with {variable}: no error")
            is_ok = is_ok and b
        finally:
            os.environ.pop(variable, None)
            if saved is not None:
                os.environ[variable] = saved

    # 3. other physics lists
    saved = {v: os.environ.pop(v, None) for v in ("G4PARTICLEHPDATA", "G4LENDDATA")}
    try:
        for physics_list_name in ("QGSP_BIC_HP_EMZ", "QGSP_BERT_EMV"):
            sim = make_simulation(physics_list_name)
            try:
                sim.physics_manager.check_optional_g4_data()
                b = True
            except GateUserError:
                b = False
            utility.print_test(b, f"{physics_list_name}: no optional data needed")
            is_ok = is_ok and b
    finally:
        for v, value in saved.items():
            if value is not None:
                os.environ[v] = value

    utility.test_ok(is_ok)
