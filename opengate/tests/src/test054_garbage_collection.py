#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import gc

# gc.set_debug(gc.DEBUG_STATS)


def simulate(provoke_segfault):
    # create the simulation
    sim = gate.Simulation()
    sim.number_of_threads = 1

    mm = gate.g4_units("mm")
    MeV = gate.g4_units("MeV")

    # add a simple volume
    waterbox = sim.add_volume("Box", "waterbox")

    # Arbritrary source because we do not really need
    # the simulation, only the initialization
    source = sim.add_source(
        "GenericSource", "Default"
    )  # FIXME warning ref not OK (cppSource not the same)
    source.particle = "proton"
    source.energy.mono = 200 * MeV
    source.position.radius = 1 * mm
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    source.n = 1e1

    se = gate.SimulationEngine(sim)
    se.initialize()  # only initialization needed to created RunManager, no actual run

    # if the RunManager is deleted early, it will cause a segfault
    if provoke_segfault is True:
        # del se.g4_RunManager
        # se.g4_RunManager = None
        return None
    # If a reference is kept outside of the scope of this function
    # all other simulation related objects will be garbage collected
    # before the RunManager is destroyed at the very end
    # --> no segfault
    else:
        return se.g4_RunManager


# --------------------------------------------------------------------------
if __name__ == "__main__":
    print("\n\n*** SEGFAULT: FALSE ***\n\n")
    rm = simulate(provoke_segfault=False)
    # Force garbage collection, just to be sure
    gc.collect()

    stats = gc.get_stats()
    for i, s in enumerate(stats):
        print(f"GC stats, generation {i}")
        print(s)

    # Commented by default to avoid failing test in CI
    # uncomment locally to try:
    # print('\n\n*** SEGFAULT: TRUE ***\n\n')
    # rm = simulate(provoke_segfault=True)
    # # Force garbage collection, just to be sure
    # gc.collect()
