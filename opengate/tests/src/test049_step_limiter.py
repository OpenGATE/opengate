#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import numpy as np
import itk

paths = gate.get_default_test_paths(__file__)


def simulate(stepsize):
    # create the simulation
    energy = 200.0
    sim = gate.Simulation()
    sim.number_of_threads = 1

    # main options
    ui = sim.user_info
    ui.g4_verbose = True
    ui.g4_verbose_level = 2
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

    # default source for tests
    source = sim.add_source(
        "Generic", "Default"
    )  # FIXME warning ref not OK (cppSource not the same)
    source.particle = "proton"
    source.energy.mono = energy * MeV
    source.position.radius = 1 * mm
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    source.n = 1e1

    dose = sim.add_actor("DoseActor", "dose")
    dose.output = str(paths.output / "t049_dose.mhd")
    dose.mother = "waterbox"
    mm = gate.g4_units("mm")
    dose.spacing = [waterbox.size[0], waterbox.size[1], 1 * mm]
    dose.size = [1, 1, int(waterbox.size[2] / dose.spacing[2])]
    # dose.translation = [2 * mm, 3 * mm, -2 * mm]
    dose.uncertainty = False
    dose.counts = True
    dose.hit_type = "random"

    # add stat actor
    sim.add_actor("SimulationStatisticsActor", "Stats")

    sim.set_max_step_size("waterbox", stepsize * mm)

    # create G4 objects
    sim.initialize()

    print(sim.dump_sources())
    print("Simulation seed:", sim.actual_random_seed)

    # verbose
    sim.apply_g4_command("/tracking/verbose 0")

    # start simulation
    sim.start()

    stats = sim.get_actor("Stats")
    print(stats)

    counts_profile = itk.GetArrayFromImage(
        itk.imread(dose.output.replace(".mhd", "_counts.mhd"))
    ).squeeze()
    profile = itk.GetArrayFromImage(itk.imread(dose.output)).squeeze()
    x = np.arange(0, profile.size) * dose.spacing[2]  # in mm
    np.savetxt(
        str(paths.output / f"t049_profile_sz{stepsize}.txt"),
        np.vstack((x, profile, counts_profile)).T,
    )

    # FIXME: We should try to parse the Geant4 output and verify that the
    # step size has been set properly.


# --------------------------------------------------------------------------
if __name__ == "__main__":
    simulate(1.0)
