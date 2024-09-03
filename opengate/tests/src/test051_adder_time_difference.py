#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import matplotlib.pyplot as plt
import numpy as np
import opengate.contrib.spect.ge_discovery_nm670 as gate_spect
import opengate as gate
from opengate.tests import utility

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, output_folder="test051")

    """
    Check the options in DigitizerAdderActor
    - TimeDifference: to store the max time difference within all hits in one single
    - NumberOfHits: store the number of hits in one single
    """

    # create the simulation
    sim = gate.Simulation()

    # units
    m = gate.g4_units.m
    nm = gate.g4_units.nm
    mm = gate.g4_units.mm
    cm = gate.g4_units.cm
    Bq = gate.g4_units.Bq
    sec = gate.g4_units.s
    min = gate.g4_units.min

    # verbose
    sim.visu = False
    sim.g4_verbose = False
    sim.g4_verbose_level = 1
    sim.number_of_threads = 1
    sim.random_seed = 123456
    sim.output_dir = paths.output

    # world size
    world = sim.world
    world.size = [2.5 * m, 2.5 * m, 2.5 * m]
    world.material = "G4_AIR"

    # spect head without collimator
    spect, colli, crystal = gate_spect.add_spect_head(
        sim, "spect", collimator_type=False, debug=False
    )
    spect.translation = [0, 0, -15 * cm]

    # spect digitizer
    hc = sim.add_actor("DigitizerHitsCollectionActor", f"Hits")
    hc.attached_to = crystal.name
    hc.output_filename = ""  # No output
    hc.attributes = [
        "PostPosition",
        "TotalEnergyDeposit",
        "PreStepUniqueVolumeID",
        "GlobalTime",
    ]
    sc = sim.add_actor("DigitizerAdderActor", f"Singles")
    sc.attached_to = hc.attached_to
    sc.input_digi_collection = hc.name
    sc.time_difference = True
    sc.number_of_hits = True
    sc.output_filename = "test051_singles.root"

    # physics
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option3"
    sim.physics_manager.enable_decay = True
    sim.physics_manager.global_production_cuts.all = 100 * mm
    sim.physics_manager.set_production_cut("spect", "all", 0.1 * mm)

    # source of Ac225 ion
    s1 = sim.add_source("GenericSource", "source")
    s1.particle = "ion 89 225"  # Ac225
    s1.position.type = "sphere"
    s1.position.radius = 1 * nm
    s1.position.translation = [0, 0, 0]
    s1.direction.type = "iso"
    s1.activity = 1e4 * Bq / sim.number_of_threads

    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "stats")
    stats.track_types_flag = True
    stats.output_filename = "test051_stats.txt"

    # go
    sim.run(start_new_process=True)

    # check stats
    print()
    gate.exception.warning("Check stats")
    stats_ref = utility.read_stat_file(paths.output_ref / "test051_stats.txt")
    is_ok = utility.assert_stats(stats, stats_ref, tolerance=0.05)

    # check root
    print()
    gate.exception.warning("Check root time difference")
    root1, n1 = utility.open_root_as_np(
        paths.output_ref / "test051_singles.root", "Singles"
    )
    root2, n2 = utility.open_root_as_np(sc.get_output_path(), "Singles")

    # time difference
    td1 = root1["TimeDifference"]
    td2 = root2["TimeDifference"]
    td1 = td1[td1 > 1 * sec] / min
    td2 = td2[td2 > 1 * sec] / min
    is_ok = (
        utility.check_diff_abs(
            len(td1),
            len(td2),
            20,
            f"Number of time diff larger than 1 sec (~{len(td1)/n1*100:.2f}%):",
        )
        and is_ok
    )
    is_ok = (
        utility.check_diff_abs(
            np.mean(td1), np.mean(td2), 30, f"Time diff mean in minutes:"
        )
        and is_ok
    )

    print()
    gate.exception.warning("Check root nb of hits")
    nh1 = root1["NumberOfHits"]
    nh2 = root2["NumberOfHits"]
    is_ok = (
        utility.check_diff(np.mean(nh1), np.mean(nh2), 6, f"Number of hits in mean:")
        and is_ok
    )

    # plot
    f, ax = plt.subplots(1, 2, figsize=(25, 10))
    utility.plot_hist(ax[0], td1, f"Time diff ref (minutes)")
    utility.plot_hist(ax[0], td2, f"Time diff (minutes)")
    utility.plot_hist(ax[1], nh1, f"Nb of hits ref")
    utility.plot_hist(ax[1], nh2, f"Nb of hits")

    fn = paths.output / "test051_singles.png"
    plt.savefig(fn)
    print(f"Plot in {fn}")

    utility.test_ok(is_ok)
