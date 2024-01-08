#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from test066_spect_gaga_garf_helpers import *
from opengate.tests import utility


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, None, "test066")
    output_path = paths.output

    # create the simulation
    sim = gate.Simulation()
    simu_name = "test066_2"

    # options
    ui = sim.user_info
    ui.number_of_threads = 5
    # ui.visu = True
    ui.visu_type = "vrml"
    ui.random_seed = "auto"

    # units
    mm = gate.g4_units.mm
    sec = gate.g4_units.second
    Bq = gate.g4_units.Bq
    cm3 = gate.g4_units.cm3
    BqmL = Bq / cm3

    # activity
    # FIXME compute exact number
    w, e = get_rad_gamma_energy_spectrum("Tc99m")
    # Estimated gammas 127,008,708 gammas (weights = 0.8850)
    # so, because we use ARF, about 1/2 particles needed
    total_activity = 127008708 / 30 * Bq / ui.number_of_threads / 2
    # total_activity = 127008708 / 30 * Bq / ui.number_of_threads / 40  # FIXME
    print(f"Total activity: {total_activity/Bq:.0f} Bq")
    if ui.visu:
        total_activity = 1 * Bq

    # source
    # voxelize_iec_phantom -o ../data/iec_2mm.mhd -s 2 --output_source data/iec_source_same_spheres_2mm.mhd
    # -a 1 1 1 1 1 1 --no_shell

    # main elements : spect + phantom
    activity_source = paths.data / "iec_source_same_spheres_2mm.mhd"
    gaga_pth_filename = (
        paths.data
        / "gate"
        / "gate_test038_gan_phsp_spect"
        / "pth2"
        / "test001_GP_0GP_10_50000.pth"
    )
    garf_pth_filename = (
        paths.data / "gate" / "gate_test043_garf" / "data" / "pth" / "arf_Tc99m_v3.pth"
    )
    arf1, arf2 = create_simu_with_gaga(
        sim, total_activity, activity_source, gaga_pth_filename, garf_pth_filename
    )
    arf1.output = f"{output_path}/{simu_name}_0.mhd"
    arf2.output = f"{output_path}/{simu_name}_1.mhd"

    # duration
    set_duration(sim, total_activity, w, 30 * sec)

    # run
    sim.run()

    # print results at the end
    stats = sim.output.get_actor("stats")
    stats.write(f"{output_path}/{simu_name}_stats.txt")
    print(stats)
    print(output_path)
