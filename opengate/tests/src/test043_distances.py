#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from test043_garf_helpers import *
import opengate.contrib.spect_ge_nm670 as gate_spect
import math

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

    # units
    activity = 1 * Bq

    # world
    sim_set_world(sim)

    # distance
    spect_translation = 50 * cm
    debug = True

    # spect head n°1
    spect1, crystal = gate_spect.add_ge_nm67_spect_head(
        sim, "spect_lehr", "lehr", debug=debug
    )
    spect1.translation = [0, 0, -spect_translation]

    # spect head n°2
    spect2, crystal = gate_spect.add_ge_nm67_spect_head(
        sim, "spect_megp", "megp", debug=debug
    )
    p = [0, 0, -spect_translation]
    itr, irot = gate.get_transform_orbiting(p, "x", 180)
    spect2.translation = itr
    spect2.rotation = irot

    # spect head n°3
    spect3, crystal = gate_spect.add_ge_nm67_spect_head(
        sim, "spect_hegp", "hegp", debug=debug
    )
    p = [0, 0, -spect_translation]
    itr, irot = gate.get_transform_orbiting(p, "x", 90)
    spect3.translation = itr
    spect3.rotation = irot

    # physics
    sim_phys(sim)

    # sources
    sim_source_test(sim, activity)

    # add stat actor
    s = sim.add_actor("SimulationStatisticsActor", "stats")
    s.track_types_flag = True

    # create planes only to check visually (volume overlap of course)
    print()
    print(f"Distances are from the center of the head volume, in the Z direction")

    collis = ["lehr", "megp", "hegp"]
    plane_positions = {}
    distance_to_crystal = {}
    psd_dist = {}
    for colli in collis:
        name = f"spect_{colli}"
        x = gate_spect.get_volume_position_in_head(sim, name, "collimator_psd", "max")
        plane_positions[colli] = x
        print(f"{colli} PSD distance         : {x / mm} mm")
        a = spect1.size[2] / 2.0 - x
        psd_dist[colli] = a
        print(f"{colli} PSD distance from BB : {a / mm} mm")
        detPlane1 = sim_add_detector_plane(sim, name, x, f"dp_psd_{colli}")
        # for visualization purpose only we increase the size by 20%
        detPlane1.size[0] *= 1.2
        detPlane1.size[1] *= 1.2
        y = gate_spect.get_volume_position_in_head(sim, name, "crystal", "center")
        print(f"{colli} crystal distance     : {y / mm} mm")
        detPlane2 = sim_add_detector_plane(sim, name, y, f"dp_crystal_{colli}")
        # for visualization purpose only we increase the size by 20%
        detPlane2.size[0] *= 1.2
        detPlane2.size[1] *= 1.2
        print(f"{colli} crystal to PSD dist  : {(x - y / mm)} mm")
        distance_to_crystal[colli] = x - y
        print()

    # --------------------------------------------------------------------------------
    # create G4 objects only if visu (no need for the test)
    if ui.visu:
        ui.verbose_level = gate.NONE
        ui.check_volumes_overlap = False

        # start simulation
        sim.run()

    # --------------------------------------------------------------------------------
    # check values
    is_ok = True
    for colli in collis:
        pp, dc, psd = gate_spect.get_plane_position_and_distance_to_crystal(colli)
        ok = math.isclose(pp, plane_positions[colli])
        gate.print_test(
            ok,
            f"Colli {colli} detector plane position       : {pp:5.2f}  vs  {plane_positions[colli]:5.2f} mm",
        )
        is_ok = is_ok and ok
        ok = math.isclose(dc, distance_to_crystal[colli])
        gate.print_test(
            ok,
            f"Colli {colli} distance to crystal           : {dc:5.2f}  vs  {distance_to_crystal[colli]:5.2f} mm",
        )
        is_ok = is_ok and ok
        ok = math.isclose(psd, psd_dist[colli])
        gate.print_test(
            ok,
            f"Colli {colli} distance head boundary to PSD : {psd:5.2f}  vs  {psd_dist[colli]:5.2f} mm",
        )
        is_ok = is_ok and ok

    print()
    print(
        "Warning : with simulation, you should add 1 nm to the position to avoid overlap."
    )

    gate.test_ok(is_ok)
