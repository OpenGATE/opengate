#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
from opengate.tests.src.actors.test081_tle_helpers import add_source
import numpy as np

from opengate.tests.utility import print_test

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, output_folder="test081_tle")

    # create the simulation
    sim = gate.Simulation()

    # main options
    # sim.visu = True
    sim.visu_type = "qt"
    sim.random_seed = 123654
    sim.output_dir = paths.output
    sim.progress_bar = True
    sim.number_of_threads = 1

    # units
    m = gate.g4_units.m
    cm = gate.g4_units.cm
    mm = gate.g4_units.mm
    keV = gate.g4_units.keV
    Bq = gate.g4_units.Bq

    #  change world size
    world = sim.world
    world.size = [1 * m, 1 * m, 1 * m]

    # insert voxelized waterbox
    spacing = 8
    waterbox = sim.add_volume("Image", "waterbox")
    fn = paths.data / "test081_tle" / f"waterbox_with_inserts_{spacing}mm_"
    waterbox.image = f"{fn}image.mhd"
    waterbox.set_materials_from_voxelisation(f"{fn}labels.json")
    waterbox_size = [30 * cm, 30 * cm, 20 * cm]

    # physics
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option3"
    sim.physics_manager.global_production_cuts.all = 1 * mm

    # default source for tests
    source = add_source(sim, n=1e5)

    # add conventional dose actor
    dose_actor = sim.add_actor("DoseActor", "dose_actor")
    dose_actor.output_filename = "test081_vox_speed.mhd"
    dose_actor.attached_to = waterbox
    dose_actor.dose_uncertainty.active = True
    dose_actor.dose.active = True
    dose_actor.size = [100, 100, 100]
    dose_actor.spacing = [x / y for x, y in zip(waterbox_size, dose_actor.size)]

    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "stats")
    stats.track_types_flag = True

    # start simulation
    sim.run(start_new_process=True)
    pps1 = stats.user_output.stats.pps

    # add tle dose actor
    tle_dose_actor = sim.add_actor("TLEDoseActor", "tle_dose_actor")
    tle_dose_actor.output_filename = "test081_vox_speed_tle.mhd"
    tle_dose_actor.attached_to = waterbox
    tle_dose_actor.dose_uncertainty.active = True
    tle_dose_actor.dose.active = True
    tle_dose_actor.size = dose_actor.size
    tle_dose_actor.spacing = dose_actor.spacing

    # remove first actor
    sim.actor_manager.remove_actor("dose_actor")

    # start simulation
    sim.run()
    pps2 = stats.user_output.stats.pps

    print()
    r = np.fabs(pps1 - pps2) / pps2
    tol = 0.4
    b = r < tol
    print_test(
        b, f"Speed PPS is {pps1} vs {pps2} = {r*100:.2f}% (tol={tol:.2f}) ==> {b}"
    )

    is_ok = b
    utility.test_ok(is_ok)
