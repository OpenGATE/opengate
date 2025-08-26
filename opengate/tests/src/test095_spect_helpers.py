#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import opengate.contrib.spect.siemens_intevo as intevo
import opengate.contrib.spect.ge_discovery_nm670 as nm670
from opengate.geometry.volume_info import store_volumes_info


def vol_info(sim, filename):
    store_volumes_info(sim, filename)
    print(f"opengate_plot_volume_info {filename} --hl arf")


def build_test_simu(
    paths, spect_model, colli_type, rotation, radius, crystal_size=None
):
    sim = gate.Simulation()
    sim.verbose_level = gate.logger.NONE
    sim.output_dir = paths.output
    sim.visu_type = "qt"
    sim.user_hook_after_init = vol_info
    if crystal_size is None:
        fn = f"vol_info_{spect_model}_{colli_type}_{rotation}.json"
    else:
        fn = f"vol_info_{spect_model}_{crystal_size.replace('/', '-')}_{colli_type}_{rotation}.json"
    sim.user_hook_after_init_arg = sim.output_dir / fn

    m = None
    head = None
    if spect_model == "intevo":
        m = intevo
        head, colli, crystal = m.add_spect_head(
            sim, "spect", collimator_type=colli_type, debug=sim.visu == True
        )

    if spect_model == "nm670":
        m = nm670
        head, colli, crystal = m.add_spect_head(
            sim,
            "spect",
            collimator_type=colli_type,
            debug=sim.visu == True,
            crystal_size=crystal_size,
        )

    # sim.visu = True # debug

    # add the arf plane
    arf_plane = m.add_detection_plane_for_arf(sim, "arf", colli_type)

    # rotate the gantry of the real spect
    m.rotate_gantry(head, radius=radius, start_angle_deg=rotation)

    # rotate the gantry of the arf plane
    m.rotate_gantry(arf_plane, radius=radius, start_angle_deg=rotation)

    return sim, fn
