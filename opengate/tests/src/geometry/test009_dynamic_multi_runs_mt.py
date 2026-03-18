#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
from opengate.sources.utility import get_spectrum
import opengate.contrib.spect.siemens_intevo as intevo

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, None, "test009_mr_mt")

    sim = gate.Simulation()
    sim.visu = False
    sim.visu_type = "qt"
    sim.number_of_threads = 4
    sim.output_dir = paths.output
    sim.random_seed = 32175121

    Bq = gate.g4_units.Bq
    sec = gate.g4_units.s
    mm = gate.g4_units.mm

    duration = 15 * sec
    number_of_angles = 7
    radius = 150 * mm

    spectrum = get_spectrum("Lu177", "gamma")
    source = sim.add_source("GenericSource", "src")
    source.attached_to = "world"
    source.particle = "gamma"
    source.activity = 10000 * Bq / sim.number_of_threads
    if sim.visu:
        source.activity = 10 * Bq / sim.number_of_threads
    source.position.type = "point"
    source.direction.type = "iso"
    source.energy.type = "spectrum_discrete"
    source.energy.spectrum_energies = spectrum.energies
    source.energy.spectrum_weights = spectrum.weights

    phantom = sim.add_volume("Box", "phantom")
    phantom.material = "G4_AIR"
    phantom.size = [312, 240, 225]
    # phantom.size =[112, 140, 125]

    det = sim.add_volume("Box", "detector")
    det.material = "G4_AIR"
    det.size = [2, 400, 400]
    det.translation = [0, radius, 0]

    stats = sim.add_actor("SimulationStatisticsActor", "stats")
    stats.output_filename = "stats.txt"
    stats.track_types_flag = True

    phsp1 = sim.add_actor("PhaseSpaceActor", "phsp")
    phsp1.attached_to = "phantom"
    phsp1.attributes = [
        "KineticEnergy",
        "GlobalTime",
        "LocalTime",
        "PrePosition",
        "PostPosition",
        "ThreadID",
        "RunID",
        "EventID",
    ]
    phsp1.output_filename = "a.root"
    phsp1.steps_to_store = "exiting"

    phsp2 = sim.add_actor("PhaseSpaceActor", "phsp2")
    phsp2.attached_to = "detector"
    phsp2.attributes = [
        "KineticEnergy",
        "GlobalTime",
        "LocalTime",
        "PrePosition",
        "PostPosition",
        "ThreadID",
        "RunID",
        "EventID",
    ]
    phsp2.output_filename = "b.root"
    phsp2.steps_to_store = "entering"

    step_time = duration / number_of_angles
    sim.run_timing_intervals = [
        [i * step_time, (i + 1) * step_time] for i in range(number_of_angles)
    ]
    print(sim.run_timing_intervals)

    step_angle = 360.0 / number_of_angles
    intevo.rotate_gantry(det, radius, 0, step_angle, number_of_angles)

    sim.running_verbose_level = gate.logger.RUN
    sim.run(start_new_process=False)

    stats = sim.find_actors("stats")[0]
    print(stats)

    # -------------------------------------
    ref_root = paths.output_ref / "b.root"
    k = [
        "KineticEnergy",
        "GlobalTime",
        "LocalTime",
        "PrePosition_X",
        "PrePosition_Y",
        "PrePosition_Z",
        "PostPosition_X",
        "PostPosition_Y",
        "PostPosition_Z",
        "ThreadID",
        "RunID",
        "EventID",
    ]
    k = ["RunID"]
    is_ok = utility.compare_root3(
        ref_root,
        phsp2.get_output_path(),
        "phsp2",
        "phsp2",
        keys1=k,
        keys2=k,
        tols=[0.070],
        scalings1=None,
        scalings2=None,
        img=paths.output / "output.png",
        nb_bins=50,
        hits_tol=8,
    )

    utility.test_ok(is_ok)
