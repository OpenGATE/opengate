#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import opengate.contrib.spect_ge_nm670 as gate_spect

paths = gate.get_default_test_paths(__file__, "", "test033")


def create_test(sim, nb_thread=1):
    # main options
    ui = sim.user_info
    ui.g4_verbose = False
    ui.running_verbose_level = gate.RUN
    ui.check_volumes_overlap = False
    ui.visu = False
    ui.visu_type = "qt"
    ui.random_seed = 123456

    # units
    m = gate.g4_units("m")
    cm = gate.g4_units("cm")
    keV = gate.g4_units("keV")
    mm = gate.g4_units("mm")
    Bq = gate.g4_units("Bq")
    sec = gate.g4_units("second")
    deg = gate.g4_units("deg")
    kBq = 1000 * Bq
    MBq = 1000 * kBq

    # main parameters
    ui.g4_verbose = False
    ui.visu_verbose = False
    ui.number_of_threads = nb_thread
    ac = 3 * MBq
    distance = 15 * cm
    psd = 6.11 * cm
    p = [0, 0, -(distance + psd)]
    if ui.visu:
        ac = ac / 100

    # world size
    world = sim.world
    world.size = [1.5 * m, 1.5 * m, 1.5 * m]
    world.material = "G4_AIR"

    # spect head (debug mode = very small collimator)
    spect1, crystal = gate_spect.add_ge_nm67_spect_head(
        sim, "spect1", collimator_type="lehr", debug=ui.visu
    )
    spect1.translation, spect1.rotation = gate.get_transform_orbiting(p, "x", 180)

    # spect head (debug mode = very small collimator)
    spect2, crystal = gate_spect.add_ge_nm67_spect_head(
        sim, "spect2", collimator_type="lehr", debug=ui.visu
    )
    spect2.translation, spect2.rotation = gate.get_transform_orbiting(p, "x", 0)

    # physic list
    sim.set_production_cut("world", "all", 10 * mm)
    sim.set_production_cut("spect1_crystal", "all", 1 * mm)
    sim.set_production_cut("spect2_crystal", "all", 1 * mm)

    # source #1
    sources = []
    source = sim.add_source("GenericSource", "source1")
    source.particle = "gamma"
    source.energy.type = "mono"
    source.energy.mono = 140.5 * keV
    source.position.type = "sphere"
    source.position.radius = 2 * mm
    source.position.translation = [0, 0, 20 * mm]
    source.direction.type = "iso"
    source.direction.acceptance_angle.volumes = ["spect1", "spect2"]
    source.direction.acceptance_angle.intersection_flag = (
        True  # will be set to false in noaa tests
    )
    source.direction.acceptance_angle.normal_flag = True
    source.direction.acceptance_angle.normal_vector = [0, 0, -1]
    source.direction.acceptance_angle.normal_tolerance = 10 * deg
    source.direction.acceptance_angle.skip_policy = "ZeroEnergy"
    source.activity = ac / ui.number_of_threads
    sources.append(source)

    # source #2
    source2 = sim.add_source("GenericSource", "source2")
    gate.copy_user_info(source, source2)
    source2.position.radius = 1 * mm
    source2.position.translation = [20 * mm, 0, -20 * mm]
    sources.append(source2)

    # add stat actor
    stat = sim.add_actor("SimulationStatisticsActor", "Stats")
    stat.output = paths.output / "test033_stats.txt"

    # add default digitizer (it is easy to change parameters if needed)
    proj = gate_spect.add_simplified_digitizer_Tc99m(
        sim, "spect1_crystal", paths.output / "test033_proj_1.mhd"
    )
    proj.origin_as_image_center = False
    proj = gate_spect.add_simplified_digitizer_Tc99m(
        sim, "spect2_crystal", paths.output / "test033_proj_2.mhd"
    )
    proj.origin_as_image_center = False

    # motion of the spect, create also the run time interval
    heads = [spect1, spect2]

    # create a list of run
    n = 9
    sim.run_timing_intervals = gate.range_timing(0, 1 * sec, n)
    for head in heads:
        motion = sim.add_actor("MotionVolumeActor", f"Move_{head.name}")
        motion.mother = head.name
        motion.translations, motion.rotations = gate.volume_orbiting_transform(
            "x", 0, 180, n, head.translation, head.rotation
        )
        motion.priority = 5

    return sources


def evaluate_test(output, sources, itol, ref_skipped):
    stats = output.get_actor("Stats")
    print(stats)
    # ref with _noaa
    # stats.write(paths.output_ref / "test033_stats.txt")

    se = 0
    ze = 0
    for source in sources:
        se += gate.get_source_skipped_events(output, source.name)
        ze += gate.get_source_zero_events(output, source.name)
    print(f"Skipped particles {se}")
    print(f"Zeros E particles {ze}")
    s = max(se, ze)

    # check nb of avoided events (either skipped or energy zero)
    gate.warning(f"Check nb of skipped particles")
    tol = 0.01
    if ref_skipped != 0:
        d = abs(ref_skipped - s) / ref_skipped
    else:
        d = 0
    is_ok = d < tol
    gate.print_test(
        is_ok,
        f"Skipped particles ref={ref_skipped}, get {s} -> {d * 100}% vs tol={tol * 100}%",
    )

    # check stats
    gate.warning(f"Check stats")
    stats_ref = gate.read_stat_file(paths.output_ref / "test033_stats.txt")
    print(f"Steps counts not compared (was {stats.counts.step_count})")
    nbt = output.simulation.user_info.number_of_threads
    stats.counts.step_count = stats_ref.counts.step_count
    stats_ref.counts.run_count *= nbt
    if se > 0:
        print(f"Track counts not compared (was {stats.counts.track_count})")
        print(f"Modify Events + skipped {stats.counts.event_count + se})")
        stats.counts.event_count += se
        stats.counts.track_count = stats_ref.counts.track_count
    if ze > 0:
        print(f"Track counts not compared (was {stats.counts.track_count})")
        stats.counts.track_count = stats_ref.counts.track_count
    is_ok = gate.assert_stats(stats, stats_ref, 0.03) and is_ok

    # compare edep map
    gate.warning(f"Check images")
    is_ok = (
        gate.assert_images(
            paths.output_ref / "test033_proj_1.mhd",
            paths.output / "test033_proj_1.mhd",
            stats,
            tolerance=68,
            axis="x",
            sum_tolerance=itol,
        )
        and is_ok
    )
    is_ok = (
        gate.assert_images(
            paths.output_ref / "test033_proj_2.mhd",
            paths.output / "test033_proj_2.mhd",
            stats,
            tolerance=68,
            axis="x",
            sum_tolerance=itol,
        )
        and is_ok
    )

    return is_ok
