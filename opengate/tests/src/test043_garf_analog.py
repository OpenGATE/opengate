#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import itk
import numpy as np
import opengate.contrib.spect.genm670 as gate_spect
import opengate as gate
import test043_garf_helpers as test43
from opengate.tests import utility


if __name__ == "__main__":
    # create the simulation
    sim = gate.Simulation()

    # main options
    ui = sim.user_info
    ui.g4_verbose = False
    ui.g4_verbose_level = 1
    ui.visu = False
    ui.random_seed = 123654
    ui.number_of_threads = 1
    colli = "lehr"

    # units
    mm = gate.g4_units.mm
    cm = gate.g4_units.cm
    Bq = gate.g4_units.Bq
    keV = gate.g4_units.keV

    activity = 1e6 * Bq / ui.number_of_threads

    # world
    test43.sim_set_world(sim)

    # spect head
    spect, crystal = gate_spect.add_ge_nm67_spect_head(
        sim, "spect", collimator_type=colli, debug=ui.visu
    )
    spect_translation = 15 * cm
    spect.translation = [0, 0, -spect_translation]
    crystal_name = f"{spect.name}_crystal"

    # physics
    test43.sim_phys(sim)

    # sources
    test43.sim_source_test(sim, activity)

    # digitizer
    channels = [
        {"name": f"spectrum_{spect.name}", "min": 0 * keV, "max": 160 * keV},
        {"name": f"scatter_{spect.name}", "min": 114 * keV, "max": 126 * keV},
        {"name": f"peak140_{spect.name}", "min": 126 * keV, "max": 154 * keV},
    ]
    proj = gate_spect.add_digitizer(sim, crystal_name, channels)
    proj.spacing = [4.41806 * mm, 4.41806 * mm]
    proj.output = test43.paths.output / "test043_projection_analog.mhd"

    # add stat actor
    s = sim.add_actor("SimulationStatisticsActor", "stats")
    s.track_types_flag = True

    # start simulation
    sim.run()

    # print results at the end
    stat = sim.output.get_actor("stats")
    print(stat)

    # dump the output image with offset like in old gate (for comparison)
    print("We change the spacing/origin to be compared to the old gate")
    proj = sim.output.get_actor(f"Projection_{crystal_name}")
    spacing = np.array([4.41806 * mm, 4.41806 * mm, 1])
    img = itk.imread(str(proj.user_info.output))
    img.SetSpacing(spacing)
    img.SetOrigin(spacing / 2.0)
    fn = str(proj.user_info.output).replace(".mhd", "_offset.mhd")
    itk.imwrite(img, fn)

    # ----------------------------------------------------------------------------------------------------------------
    # tests
    print()
    gate.exception.warning("Tests stats file")
    stats_ref = utility.read_stat_file(test43.paths.gate_output / "stats_analog.txt")
    stat.counts.run_count = 1  # force to one run (ref only have 1 thread)
    is_ok = utility.assert_stats(stat, stats_ref, 0.01)

    print()
    gate.exception.warning("Tests projection (old gate)")
    is_ok = (
        utility.assert_images(
            test43.paths.gate_output / "projection_analog.mhd",
            fn,
            stat,
            tolerance=75,
            ignore_value=0,
            axis="x",
        )
        and is_ok
    )

    print()
    gate.exception.warning("Tests projection (new)")
    is_ok = (
        utility.assert_images(
            test43.paths.output_ref / "test043_projection_analog.mhd",
            proj.user_info.output,
            stat,
            tolerance=80,
            ignore_value=0,
            axis="x",
        )
        and is_ok
    )
