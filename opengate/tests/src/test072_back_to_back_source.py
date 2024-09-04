#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
import uproot
import numpy as np

#########################################################################################
# Simulations configuration that may be relevant to change
#########################################################################################
# Number of back-to-back to generate
nbEvents = 100

#########################################################################################
# Constants
#########################################################################################
# Units
MeV = gate.g4_units.MeV
keV = gate.g4_units.keV
Bq = gate.g4_units.Bq
deg = gate.g4_units.deg
mm = gate.g4_units.mm
m = gate.g4_units.m
cm = gate.g4_units.cm


#########################################################################################
# Methods used in this test
#########################################################################################
def test_back_to_back(_path_to_root_file, _nb_b2b):
    """
    Def.: zxc FIXME
    """
    # get data from root file
    b2b_root = uproot.open(_path_to_root_file)["phsp;1"].arrays(library="numpy")

    # Assuming that trackId is relative to a eventId, it provides use a way to check
    # that everything start with two gammas.
    # It does not take into account 3+ gamma cases, but I do not know how to do better
    b2b_eventId_adamEve = b2b_root["TrackID"] <= 2

    b2b_emissionEnergy = b2b_root["EventKineticEnergy"][b2b_eventId_adamEve]

    b2b_particleName = b2b_root["ParticleName"][b2b_eventId_adamEve]

    b2b_dir = (
        np.stack(
            (
                b2b_root["PreDirection_X"],
                b2b_root["PreDirection_Y"],
                b2b_root["PreDirection_Z"],
            )
        ).T
    )[b2b_eventId_adamEve]
    # For easier manipulation
    b2b_dir = b2b_dir.reshape((_nb_b2b, 2, 3))

    # Note: We assumes that thing that are not specific to back-to-back were already
    # tested, for example the number of particle
    # FIXME Would be better to check fAccolinearityFlag but might not be accessible?
    is_b2b = source.particle == "back_to_back"
    is_monoEnergy = source.energy.type == "mono"
    is_def511kev = source.energy.mono == 511 * keV
    is_defNoAcolin = source.direction.accolinearity_flag == False
    is_allB2b511keV = np.all(np.isclose(b2b_emissionEnergy, 0.511, atol=10**-3))
    is_allEmissionGamme = np.all(b2b_particleName == "gamma")
    is_b2bColin = np.all(
        np.isclose(
            np.sum(b2b_dir[:, 0, :] * b2b_dir[:, 1, :], axis=-1), -1.0, atol=10**-3
        )
    )
    # FIXME: Confirm it stay in the sphere?

    print(f"is_b2: {is_b2b}")
    print(f"is_monoEnergy: {is_monoEnergy}")
    print(f"is_def511kev: {is_def511kev}")
    print(f"is_defNoAcolin: {is_defNoAcolin}")
    print(f"is_allB2b511keV: {is_allB2b511keV}")
    print(f"is_allEmissionGamme: {is_allEmissionGamme}")
    print(f"is_b2bColin: {is_b2bColin}")

    return (
        is_b2b
        & is_monoEnergy
        & is_def511kev
        & is_defNoAcolin
        & is_allB2b511keV
        & is_allEmissionGamme
        & is_b2bColin
    )


#########################################################################################
# Main : We use this to launch the test
#########################################################################################
if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, output_folder="test072")

    # create the simulation
    sim = gate.Simulation()

    # main options
    sim.g4_verbose = False
    sim.g4_verbose_level = 1
    # sim.visu = True
    sim.visu_type = "vrml"
    sim.number_of_threads = 1
    sim.random_seed = 123456
    sim.output_dir = paths.output

    # set the world size like in the Gate macro
    world = sim.world
    world.size = [2 * m, 2 * m, 2 * m]

    # test sources
    source = sim.add_source("GenericSource", "b2b")
    source.particle = "back_to_back"
    source.n = nbEvents
    source.position.type = "sphere"
    source.position.radius = 5 * mm
    source.direction.type = "iso"
    source.direction.accolinearity_flag = False
    # note : source.energy is ignored (always 511 keV)
    # FIXME : do another test with accolinearity_flag set to True

    # actors
    stats_actor = sim.add_actor("SimulationStatisticsActor", "Stats")

    # store phsp
    phsp_actor = sim.add_actor("PhaseSpaceActor", "phsp")
    phsp_actor.attributes = [
        "EventID",
        "TrackID",
        "EventPosition",
        "EventDirection",
        "Direction",
        "EventKineticEnergy",
        "KineticEnergy",
        "ParticleName",
        "TimeFromBeginOfEvent",
        "GlobalTime",
        "LocalTime",
        "PDGCode",
        "PostPosition",
        "PreDirection",
    ]
    phsp_actor.steps_to_store = "first"
    phsp_actor.output_filename = "b2b.root"

    # verbose
    # sim.g4_verbose = True
    # sim.g4_commands_after_init.append("/tracking/verbose 2")
    # sim.g4_commands_after_init.append("/run/verbose 2")
    # sim.g4_commands_after_init.append("/event/verbose 2")
    # sim.g4_commands_after_init.append("/tracking/verbose 1")

    # start simulation
    sim.run()

    # test
    is_ok = test_back_to_back(phsp_actor.get_output_path(), nbEvents)
    # FIXME confirm acolin when activated
    # FIXME Other tests?

    # this is the end, my friend
    utility.test_ok(is_ok)
