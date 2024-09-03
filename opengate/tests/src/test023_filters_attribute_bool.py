#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
import uproot
import numpy as np

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "", "test023")

    # create the simulation
    sim = gate.Simulation()
    sim_name = "test023_filters_attribute_bool"

    # main options
    # sim.visu = True
    sim.visu_type = "vrml"
    sim.random_seed = 321456987
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
    plane1a = sim.add_volume("Box", "plane1a")
    plane1a.size = [1 * m, 1 * m, 1 * nm]
    plane1a.translation = [0, 0, 1 * cm]
    plane1a.material = "G4_WATER"
    plane1a.color = [1, 0, 0, 1]

    # filter according to time
    filter1 = sim.add_filter("ThresholdAttributeFilter", "time_filter")
    filter1.attribute = "GlobalTime"
    filter1.value_min = 20 * sec
    filter1.value_max = 70 * sec
    filter1.policy = "accept"

    # filter according to energy
    filter2 = sim.add_filter("ThresholdAttributeFilter", "ene_filter")
    filter2.attribute = "KineticEnergy"
    filter2.value_min = 300 * keV
    filter2.value_max = 1200 * keV
    filter2.policy = "accept"

    # filter according to particle
    filter3 = sim.add_filter("ParticleFilter", "p_filter")
    filter3.particle = "gamma"

    # phsp
    phsp_and = sim.add_actor("PhaseSpaceActor", "phsp_and")
    phsp_and.attached_to = plane1a.name
    phsp_and.attributes = ["GlobalTime", "KineticEnergy", "ParticleName"]
    phsp_and.output_filename = f"{sim_name}_and.root"
    phsp_and.filters = [filter1, filter2, filter3]
    phsp_and.filters_boolean_operator = "and"  # default is and

    # phsp
    phsp_or = sim.add_actor("PhaseSpaceActor", "phsp_or")
    phsp_or.attached_to = plane1a.name
    phsp_or.attributes = ["GlobalTime", "KineticEnergy"]
    phsp_or.output_filename = f"{sim_name}_or.root"
    phsp_or.filters.append(filter1)
    phsp_or.filters.append(filter2)
    phsp_or.filters_boolean_operator = "or"  # default is and

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

    # check 'or'
    print()
    print()
    tree = uproot.open(phsp_and.get_output_path())["phsp_and"]
    print("nb entries", tree.num_entries)
    ene = tree.arrays(["GlobalTime", "KineticEnergy"])["KineticEnergy"]
    emin = np.min(ene)
    emax = np.max(ene)
    is_ok = emin >= filter2.value_min and emax <= filter2.value_max
    utility.print_test(is_ok, f"Ene = {len(ene)} min={emin/keV} max={emax/keV}")
    ti = tree.arrays(["GlobalTime", "KineticEnergy"])["GlobalTime"]
    tmin = np.min(ti)
    tmax = np.max(ti)
    is_ok = tmin >= filter1.value_min and tmax <= filter1.value_max and is_ok
    utility.print_test(is_ok, f"Time = {len(ti)} min={tmin/sec} max={tmax/sec}")

    # check 'or'
    print()
    print()
    tree = uproot.open(phsp_or.get_output_path())["phsp_or"]
    print("nb entries", tree.num_entries)
    ene = tree.arrays(
        ["GlobalTime", "KineticEnergy"],
        f"(GlobalTime <= {filter1.value_min}) | "
        f"(GlobalTime >= {filter1.value_max})",
    )["KineticEnergy"]
    emin = np.min(ene)
    emax = np.max(ene)
    is_ok = emin >= filter2.value_min and emax <= filter2.value_max
    utility.print_test(is_ok, f"Ene = {len(ene)} min={emin/keV} max={emax/keV}")
    ti = tree.arrays(
        ["GlobalTime", "KineticEnergy"],
        f"(KineticEnergy <= {filter2.value_min}) | "
        f"(KineticEnergy >= {filter2.value_max})",
    )["GlobalTime"]
    tmin = np.min(ti)
    tmax = np.max(ti)
    is_ok = tmin >= filter1.value_min and tmax <= filter1.value_max and is_ok
    utility.print_test(is_ok, f"Time = {len(ti)} min={tmin/sec} max={tmax/sec}")

    # tests
    print()
    print()
    stats_ref = utility.read_stat_file(paths.output_ref / f"{sim_name}.txt")
    is_ok = utility.assert_stats(stat, stats_ref, 0.01)

    utility.test_ok(is_ok)
