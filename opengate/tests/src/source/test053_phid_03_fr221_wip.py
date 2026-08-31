#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from test053_phid_helpers1 import *
import opengate as gate

if __name__ == "__main__":
    """
    Consider a source of fr221 and store all emitted gammas
    """

    """
    WARNING
    PhotonIonDecayIsomericTransitionExtractor does NOT work anymore
    Now PHID extract data from the IAEA database, not directly from G4
    """
    fatal("PhotonIonDecayIsomericTransitionExtractor NOT implemented")

    test_ok(False)

    paths = get_default_test_paths(__file__, "", output_folder="test053")
    z = 87
    a = 221
    sim = gate.Simulation()

    ion_name, daughters = create_ion_gamma_simulation(sim, paths, z, a)

    # go
    sim.run(start_new_process=True)

    #
    is_ok = analyse(
        paths, sim, sim.output, ion_name, z, a, daughters, log_flag=False, tol=0.08
    )

    test_ok(is_ok)
