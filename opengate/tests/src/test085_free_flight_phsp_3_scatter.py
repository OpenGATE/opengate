#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from opengate import g4_units
from opengate.tests import utility
from test085_free_flight_helpers import *

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, None, output_folder="test085_phsp")

    # create the simulation
    sim = gate.Simulation()
    sim.number_of_threads = 4  # FIXME
    ac = 1e3
    # sim.visu = True
    source, actors = create_simulation_test085(
        sim,
        paths,
        simu_name="ff_sc",
        ac=ac,
        use_spect_head=False,
        use_spect_arf=False,
        use_phsp=True,
    )

    # no AA
    source.direction.acceptance_angle.intersection_flag = False
    source.direction.acceptance_angle.normal_flag = False

    # free flight actor
    # need to NOT use generalProcess to enable only for Compton ? FIXME NO !
    # FIXME to change? to automatize ?
    s = f"/process/em/UseGeneralProcess true"
    sim.g4_commands_before_init.append(s)

    ff = sim.add_actor("SplitComptonScatteringActor", "ff")
    ff.attached_to = "phantom"
    ff.splitting_factor = 4
    ff.max_compton_level = 1000

    ff.skip_policy = "SkipEvents"
    ff.intersection_flag = False
    # ff.volumes = ["spect_1"]  # , "spect_2"] # FIXME dont use spect2 ftm
    ff.normal_flag = False
    ff.normal_vector = [0, 0, -1]
    ff.normal_tolerance = 10 * g4_units.deg

    # go
    sim.run()
    stats = sim.get_actor("stats")
    print(stats)

    # compare histo
    is_ok = utility.compare_root3(
        paths.output_ref / "phsp_1_ff_sc.root",
        paths.output / "phsp_1_ff_sc.root",
        "phsp1",
        "phsp1",
        keys1=None,
        keys2=None,
        tols=[0.01, 0.7, 1.4, 1.4, 0.01],
        scalings1=[1] * 5,
        scalings2=[1] * 5,
        img=paths.output / "test085_phsp_ff_sc.png",
    )

    utility.test_ok(is_ok)
