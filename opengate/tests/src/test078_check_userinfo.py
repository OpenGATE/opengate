#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from opengate.exception import GateDeprecationError
from opengate.tests.utility import (
    get_default_test_paths,
    test_ok,
    print_test,
)
from opengate.utility import g4_units
import opengate as gate


def set_wrong_attribute(obj, attr):
    # set a WRONG attribute
    number_of_warnings_before = getattr(obj, "number_of_warnings")
    setattr(obj, attr, "nothing")
    number_of_warnings_after = getattr(obj, "number_of_warnings")

    # check the number of warnings before and after
    print(
        f"Number of warnings for {obj.type_name} object {obj.name}: {number_of_warnings_before}"
    )
    print(
        f"Number of warnings for {obj.type_name} object {obj.name}: {number_of_warnings_after}"
    )
    b = number_of_warnings_after - number_of_warnings_before == 1
    print_test(
        b, f"Tried to set a wrong attribute '{attr}'. It should print a single warning"
    )
    return b


if __name__ == "__main__":
    paths = get_default_test_paths(
        __file__,
    )

    sim = gate.Simulation()

    m = g4_units.m
    cm = g4_units.cm
    keV = g4_units.keV
    mm = g4_units.mm
    um = g4_units.um
    Bq = g4_units.Bq

    world = sim.world
    world.size = [3 * m, 3 * m, 3 * m]
    world.material = "G4_AIR"

    is_ok = True

    # create the volume without adding it to the simulation
    waterbox = gate.geometry.volumes.BoxVolume(name="Waterbox")
    waterbox.size = [40 * cm, 40 * cm, 40 * cm]
    waterbox.translation = [0 * cm, 0 * cm, 25 * cm]
    waterbox.material = "G4_WATER"
    # provoke a warning
    is_ok = is_ok and set_wrong_attribute(waterbox, "mohter")
    # now add the volume to the simulation
    sim.add_volume(waterbox)
    # a warning about the wrong attribute "mohter" should appear
    # in the list of warnings at the end of the simulation
    # because it should be transferred from the object's warning cache
    # to the simulation's warning cache once the object is added to the simulation

    source = sim.add_source("GenericSource", "Default")
    source.particle = "gamma"
    source.energy.mono = 80 * keV
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    source.n = 20

    # test wrong attributes
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.track_types_flag = True
    try:
        stats.mother = "nothing"
        is_ok = False and is_ok
    except GateDeprecationError as e:
        print("Exception caught: ", e)
        pass
    print_test(
        is_ok, f"Try to set deprecated attribute 'mother', it should raise an exception"
    )
    print()

    is_ok = is_ok and set_wrong_attribute(stats, "TOTO")
    is_ok = is_ok and set_wrong_attribute(sim, "nthreads")

    sim.run(start_new_process=True)

    found_warning_about_waterbox_mohter = False
    for w in sim.warnings:
        if "mohter" in w:
            found_warning_about_waterbox_mohter = True
            break
    is_ok = is_ok and found_warning_about_waterbox_mohter

    print(
        f"(after run) Number of warnings for stats object: {stats.number_of_warnings}"
    )
    b = stats.number_of_warnings == 1
    print_test(b, f"No additional warning should be raised")
    is_ok = is_ok and b

    test_ok(is_ok)
