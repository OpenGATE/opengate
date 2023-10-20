#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import uproot
import numpy as np
import opengate_core as g4
import opengate as gate
from opengate.tests import utility

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "gate_test053_digit_efficiency")

    """
    PET simulation to test efficiency options of the digitizer
    Output: singles with and without decreased efficiency
    """

    sim = gate.Simulation()

    # main options
    ui = sim.user_info
    ui.g4_verbose = False
    ui.visu = False
    ui.number_of_threads = 1
    ui.check_volumes_overlap = False
    ui.random_seed = 321654

    # units
    m = gate.g4_units.m
    cm = gate.g4_units.cm
    keV = gate.g4_units.keV
    mm = gate.g4_units.mm
    Bq = gate.g4_units.Bq

    # world size
    world = sim.world
    world.size = [2 * m, 2 * m, 2 * m]

    # material
    sim.add_material_database(paths.data / "GateMaterials.db")

    # fake spect head
    waterbox = sim.add_volume("Box", "SPECThead")
    waterbox.size = [55 * cm, 42 * cm, 18 * cm]
    waterbox.material = "G4_AIR"

    # crystal
    crystal = sim.add_volume("Box", "crystal")
    crystal.mother = "SPECThead"
    crystal.size = [1.0 * cm, 1.0 * cm, 1.0 * cm]
    crystal.translation = None
    crystal.rotation = None
    crystal.material = "NaITl"
    start = [-25 * cm, -20 * cm, 4 * cm]
    size = [100, 40, 1]
    # size = [100, 80, 1]
    tr = [0.5 * cm, 0.5 * cm, 0]
    crystal.repeat = gate.geometry.utility.repeat_array_start(
        "crystal", start, size, tr
    )
    crystal.color = [1, 1, 0, 1]

    # physic list
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option4"
    sim.physics_manager.enable_decay = False
    sim.physics_manager.global_production_cuts.gamma = 0.01 * mm
    sim.physics_manager.global_production_cuts.electron = 0.01 * mm
    sim.physics_manager.global_production_cuts.positron = 1 * mm
    sim.physics_manager.global_production_cuts.proton = 1 * mm

    # default source for tests
    source = sim.add_source("GenericSource", "Default")
    source.particle = "gamma"
    source.energy.mono = 140.5 * keV
    source.position.type = "sphere"
    source.position.radius = 4 * cm
    source.position.translation = [0, 0, -15 * cm]
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    source.activity = 50000 * Bq / ui.number_of_threads

    # add stat actor
    sim.add_actor("SimulationStatisticsActor", "Stats")

    # print list of attributes
    am = g4.GateDigiAttributeManager.GetInstance()
    print(am.GetAvailableDigiAttributeNames())

    # hits collection
    hc = sim.add_actor("DigitizerHitsCollectionActor", "Hits")
    hc.mother = crystal.name
    mt = ""
    if ui.number_of_threads > 1:
        mt = "_MT"
    hc.output = paths.output / ("test053_hits" + mt + ".root")
    hc.attributes = [
        "TotalEnergyDeposit",
        "KineticEnergy",
        "PostPosition",
        "TrackCreatorProcess",
        "GlobalTime",
        "TrackVolumeName",
        "RunID",
        "ThreadID",
        "TrackID",
    ]

    # EfficiencyActor
    ea = sim.add_actor("DigitizerEfficiencyActor", "Efficiency")
    ea.mother = hc.mother
    ea.input_digi_collection = "Hits"
    ea.output = hc.output
    ea.efficiency = 0.3

    sim.run()
    output = sim.output

    # Compare Hits and Efficiency
    hits1 = uproot.open(hc.output)["Hits"]
    hits1_n = hits1.num_entries
    hits1 = hits1.arrays(library="numpy")

    hits2 = uproot.open(hc.output)["Efficiency"]
    hits2_n = hits2.num_entries
    hits2 = hits2.arrays(library="numpy")

    print(f"Reference tree: Hits       n={hits1_n}")
    print(f"Current tree:   Efficiency n={hits2_n}")
    print(f"Digitizer efficiency = {ea.efficiency}")
    n_tol = 1.1
    diff = utility.rel_diff(float(hits1_n * ea.efficiency), float(hits2_n))
    is_ok = utility.print_test(
        np.fabs(diff) < n_tol,
        f"Difference: {ea.efficiency}*{hits1_n} {hits2_n} {diff:.2f}% (tol = {n_tol:.2f})",
    )
    print(f"Reference tree: {hits1.keys()}")
    print(f"Current tree:   {hits2.keys()}")

    keys1, keys2, scalings, tols = utility.get_keys_correspondence(
        [
            "TotalEnergyDeposit",
            "KineticEnergy",
            "PostPosition_X",
            "PostPosition_Y",
            "PostPosition_Z",
            "TrackCreatorProcess",
            "GlobalTime",
            "TrackVolumeName",
            "RunID",
            "ThreadID",
            "TrackID",
        ]
    )
    is_ok = (
        utility.compare_trees(
            hits1,
            list(hits1.keys()),
            hits2,
            list(hits2.keys()),
            keys1,
            keys2,
            tols,
            [1] * len(scalings),
            scalings,
            False,
        )
        and is_ok
    )

    utility.test_ok(is_ok)
