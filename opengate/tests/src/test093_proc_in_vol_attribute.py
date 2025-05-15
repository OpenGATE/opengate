#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from opengate.tests.utility import *
from opengate.managers import Simulation
from opengate.actors.digitizers import *

if __name__ == "__main__":
    paths = get_default_test_paths(__file__, None, "test093")

    # units
    m = g4_units.m
    mm = g4_units.mm
    cm = g4_units.cm
    keV = g4_units.keV

    # simulation
    sim = Simulation()
    sim.progress_bar = True
    sim.visu = False
    sim.visu_type = "qt"
    sim.output_dir = paths.output
    sim.random_seed = 32145987

    # add a volume
    waterbox1 = sim.add_volume("Box", "Waterbox1")
    waterbox1.size = [20 * cm, 20 * cm, 10 * cm]
    waterbox1.translation = [0 * cm, 0 * cm, 0 * cm]
    waterbox1.material = "G4_WATER"

    # add a volume
    waterbox2 = sim.add_volume("Box", "Waterbox2")
    waterbox2.size = [20 * cm, 20 * cm, 10 * cm]
    waterbox2.translation = [0 * cm, 0 * cm, -10 * cm]
    waterbox2.material = "G4_WATER"

    # add a "detector"
    detector = sim.add_volume("Box", "detector")
    detector.size = [150 * cm, 150 * cm, 1 * cm]
    detector.translation = [0 * cm, 0 * cm, 20 * cm]
    detector.material = "G4_LEAD_OXIDE"

    # source 1
    source = sim.add_source("GenericSource", "low_energy")
    source.particle = "gamma"
    source.energy.mono = 50 * keV
    source.position.type = "sphere"
    source.position.radius = 20 * mm
    source.position.translation = [0 * cm, 0 * cm, -30 * cm]
    source.direction.type = "focused"
    source.direction.focus_point = [0 * cm, 0 * cm, -25 * cm]
    source.direction.momentum = [0, 0, -1]
    source.n = 50000

    # add a stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.track_types_flag = True

    # needed for Rayl !
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option4"

    # phsp
    phsp = sim.add_actor("PhaseSpaceActor", "PhaseSpace")
    phsp.attached_to = detector

    att1 = ProcessDefinedStepInVolumeAttribute(sim, "compt", waterbox1.name)
    att2 = ProcessDefinedStepInVolumeAttribute(sim, "compt", "world")
    att3 = ProcessDefinedStepInVolumeAttribute(sim, "Rayl", "world")
    att4 = ProcessDefinedStepInVolumeAttribute(sim, "Rayl", waterbox2.name)
    phsp.attributes = [
        "KineticEnergy",
        "PrePosition",
        "EventID",
        att1.name,
        att2.name,
        att3.name,
        att4.name,
    ]

    # not possible:
    is_ok = True
    try:
        att3.volume_name = "toto"
        att3.process_name = "toto"
        print(f"volume_name and process_name cannot be changed")
        is_ok = False
    except Exception as e:
        print("OK, cannot change the volume_name")

    phsp.output_filename = "phsp.root"
    phsp.steps_to_store = "all"

    # go
    sim.run()
    print(stats)

    # check
    ref_root = paths.output_ref / "phsp.root"
    test_root = paths.output / "phsp.root"
    print(phsp.attributes)
    keys = [att1.name, att2.name, att3.name, att4.name]
    n = len(keys)
    is_ok = (
        compare_root3(
            ref_root,
            test_root,
            "PhaseSpace",
            "PhaseSpace",
            keys1=keys,
            keys2=keys,
            tols=[0.07, 0.07, 0.05, 0.05],
            scalings1=[1] * n,
            scalings2=[1] * n,
            img=paths.output / "phsp.png",
        )
        and is_ok
    )

    test_ok(is_ok)
