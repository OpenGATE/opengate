#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
from opengate.actors.filters import GateFilter
import uproot
import numpy as np

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "", "test023")

    # create the simulation
    sim = gate.Simulation()
    sim_name = "test023_filters_generic1"

    # main options
    sim.output_dir = paths.output

    # units
    m = gate.g4_units.m
    cm = gate.g4_units.cm
    MeV = gate.g4_units.MeV
    Bq = gate.g4_units.Bq
    nm = gate.g4_units.nm
    mm = gate.g4_units.mm
    sec = gate.g4_units.second
    keV = gate.g4_units.keV

    #  change world size
    sim.world.size = [1 * m, 1 * m, 1 * m]
    sim.world.material = "G4_WATER"

    # default source for tests
    source = sim.add_source("GenericSource", "mysource")
    source.energy.type = "gauss"
    source.energy.mono = 1 * MeV
    source.energy.sigma_gauss = 1 * MeV
    source.particle = "gamma"
    source.position.type = "sphere"
    source.position.radius = 1 * cm
    source.direction.type = "iso"
    source.activity = 100 * Bq

    # plane
    plane = sim.add_volume("Box", "plane1a")
    plane.size = [1 * m, 1 * m, 1 * nm]
    plane.translation = [0, 0, 1 * cm]
    plane.material = "G4_WATER"
    plane.color = [1, 0, 0, 1]

    # create filter
    F = GateFilter(sim)
    combined_filter = (
        (30 * sec < F.GlobalTime)
        & (F.GlobalTime < 70 * sec)
        & (F.ParticleName == "gamma")
    )

    # phsp
    phsp = sim.add_actor("PhaseSpaceActor", "phsp")
    phsp.attached_to = plane
    phsp.attributes = ["GlobalTime", "KineticEnergy", "ParticleName"]
    phsp.output_filename = f"{sim_name}.root"
    # phsp.filters = combined_filter # raise error deprecated
    phsp.filter = combined_filter

    # stats
    stat = sim.add_actor("SimulationStatisticsActor", "stats")
    stat.track_types_flag = True

    # physics
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option4"

    # start simulation
    duration = 100 * sec
    sim.run_timing_intervals = [[0, duration]]
    sim.run()

    # print results at the end
    print(stat)
    # reference :
    # stat.write(paths.output_ref / f"{sim_name}.txt")

    # check
    is_ok = True
    print()
    print()
    tree = uproot.open(phsp.get_output_path())["phsp"]
    print("nb entries", tree.num_entries)

    ti = tree.arrays(phsp.attributes)["GlobalTime"]
    tmin = np.min(ti)
    tmax = np.max(ti)
    b = 30 * sec < tmin and 70 * sec > tmax
    utility.print_test(b, f"Time = min={tmin / sec} max={tmax / sec}")
    is_ok = b and is_ok

    utility.test_ok(is_ok)
