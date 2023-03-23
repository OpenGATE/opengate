#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import opengate_core as g4

paths = gate.get_default_test_paths(__file__)


def simulate():
    # create the simulation
    energy = 200.0
    sim = gate.Simulation()
    sim.number_of_threads = 1

    # main options
    ui = sim.user_info
    ui.g4_verbose = True
    ui.g4_verbose_level = 0
    ui.visu = False
    ui.random_engine = "MersenneTwister"

    cm = gate.g4_units("cm")
    mm = gate.g4_units("mm")
    MeV = gate.g4_units("MeV")

    # add a simple volume
    waterbox = sim.add_volume("Box", "waterbox")
    waterbox.size = [40 * cm, 40 * cm, 40 * cm]
    waterbox.translation = [0 * cm, 0 * cm, 21 * cm]
    waterbox.material = "G4_WATER"

    # Arbritrary source because we do not really need
    # the simulation, only the initialization
    source = sim.add_source(
        "GenericSource", "Default"
    )  # FIXME warning ref not OK (cppSource not the same)
    source.particle = "proton"
    source.energy.mono = energy * MeV
    source.position.radius = 1 * mm
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    source.n = 1e1

    # Choose an "awkward" step size
    # which does not corrispond to any of Geant4's
    # defaults to make the assertion (below) significant
    stepsize = 1.47
    sim.set_max_step_size("waterbox", stepsize * mm)

    se = gate.SimulationEngine(sim)
    # Set the hook function user_fct_after_init
    # to the function defined below
    se.user_fct_after_init = check_user_limit
    output = se.start()

    # Assert that the retrieved step size
    # equals the requested one
    print(f"Requested step limit in {waterbox.name} was {stepsize}.")
    print(f"Geant4 reports {output.hook_log[0]}.")
    assert stepsize == output.hook_log[0]
    print("Test passed")

    # return RunManager to avoid garbage collection before the other objects
    # and thus a segfault
    return se.g4_RunManager


def check_user_limit(simulation_engine):
    """Function to be called by opengate after initialization
    of the simulation, i.e. when G4 volumes and regions exist.
    The purpose is to check whether Geant4 has properly set
    the step limit in the specific region.

    The value max_step_size is stored in the attribute hook_log
    which can be accessed via the output of the simulation.

    """
    print(f"Entered hook")
    g4_volume = simulation_engine.volume_engine.g4_volumes["waterbox"]
    if g4_volume.g4_region is not None:
        name = g4_volume.g4_region.GetName()
        print(f"In hook: found region {name}")
        user_limits = g4_volume.g4_region.GetUserLimits()
        print(f"In hook: found UserLimit {user_limits}")

        max_step_size = g4_volume.g4_region.GetUserLimits().GetMaxAllowedStep(
            g4.G4Track()
        )
        simulation_engine.hook_log.append(max_step_size)
        print(f"In hook: found max_step_size {max_step_size}")


# --------------------------------------------------------------------------
if __name__ == "__main__":
    rm = simulate()
