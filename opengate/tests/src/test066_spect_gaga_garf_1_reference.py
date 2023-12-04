#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from test066_spect_gaga_garf_helpers import *
from opengate.tests import utility


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, None, "test066")
    output_path = paths.output

    """
    Test066
    Spect image simulation of IEC phantom with Tc99m source, two heads (two projections).
    With analog methods and gaga+garf method (within and outside Gate).
    The activity concentration is the same in all spheres, 100 kBq, so 4.78 MBq in total.
    No background activity.
    The total events for 30 sec acquisition (no half life) is around 1.3e8 gammas.

    Test on linux
    - test066_1 : reference
    - test066_2 : gaga + garf, within gate (around ~x4 faster than reference, and need less particles)
    - test066_3 : gaga + garf, outside gate, only one thread, ~50% faster than within gate

    test066_2 uses 2x less particles than test066_1 (because ARF)
    test066_3 uses 2x less particles than test066_2 (to save time)

    """

    # create the simulation
    sim = gate.Simulation()
    simu_name = "test066_1_reference"

    # options
    ui = sim.user_info
    ui.number_of_threads = 10
    # ui.visu = True
    ui.visu_type = "vrml"
    ui.random_seed = "auto"

    # units
    mm = gate.g4_units.mm
    sec = gate.g4_units.second
    Bq = gate.g4_units.Bq
    cm3 = gate.g4_units.cm3
    BqmL = Bq / cm3

    # main elements : spect + phantom
    proj1, proj2 = create_simu_with_genm670(sim, debug=ui.visu)
    proj1.output = f"{output_path}/{simu_name}_0.mhd"
    proj2.output = f"{output_path}/{simu_name}_1.mhd"

    # add IEC phantom
    iec = gate_iec.add_iec_phantom(sim, name="iec")
    sim.physics_manager.set_production_cut("iec", "all", 1 * mm)
    iec.rotation = Rotation.from_euler("x", 90, degrees=True).as_matrix()

    # sources IEC
    ac = 1e5 * BqmL  # 1e5 = about 10 min with 10 threads linux
    if ui.visu:
        ac = 0.01 * BqmL
    total_activity, w, e = add_iec_Tc99m_source(sim, ac)

    # duration
    set_duration(sim, total_activity, w, 30 * sec)

    # run
    sim.run()

    # print results at the end
    stats = sim.output.get_actor("stats")
    stats.write(f"{output_path}/{simu_name}_stats.txt")
    print(stats)
    print(output_path)
