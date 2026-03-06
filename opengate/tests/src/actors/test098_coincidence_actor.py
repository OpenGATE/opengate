#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import opengate.tests.utility as utility
import opengate.contrib.pet.philipsvereos as vereos
from opengate.actors.coincidences import coincidences_sorter
from test098_coincidence_helpers import compare_coincidences
import uproot

if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, gate_folder="", output_folder="test098_coincidence_actor"
    )
    root_filename = paths.output / "output_singles.root"

    # units
    m = gate.g4_units.m
    cm = gate.g4_units.cm
    Bq = gate.g4_units.Bq
    sec = gate.g4_units.s

    # options
    sim = gate.Simulation()
    sim.random_seed = 1234
    sim.number_of_threads = 1
    sim.output_dir = paths.output
    sim.verbose_level = gate.logger.NONE

    # world
    world = sim.world
    world.size = [1.5 * m, 1.5 * m, 1.5 * m]
    world.material = "G4_AIR"

    # Pet
    pet = vereos.add_pet(sim, "pet")
    crystal = sim.volume_manager.get_volume("pet_crystal")

    # Point source
    source = sim.add_source("GenericSource", "source")
    source.particle = "back_to_back"
    source.activity = 1e6 * Bq / sim.number_of_threads
    source.position.type = "point"
    source.position.translation = [0 * cm, 0 * cm, 0 * cm]
    source.direction.type = "iso"

    # Hits
    hc = sim.add_actor("DigitizerHitsCollectionActor", "hits")
    hc.attached_to = crystal.name
    hc.authorize_repeated_volumes = True
    hc.attributes = [
        "EventID",
        "PostPosition",
        "TotalEnergyDeposit",
        "PreStepUniqueVolumeID",
        "GlobalTime",
    ]

    # Singles
    sc = sim.add_actor("DigitizerAdderActor", "singles")
    sc.attached_to = hc.attached_to
    sc.authorize_repeated_volumes = True
    sc.input_digi_collection = hc.name
    sc.policy = "EnergyWeightedCentroidPosition"
    sc.group_volume = crystal.name
    sc.output_filename = root_filename

    # Coincidence sorter
    cc = sim.add_actor("CoincidenceSorterActor", "coincidences")
    cc.input_digi_collection = sc.name
    cc.window = 1e-9 * sec
    cc.output_filename = root_filename

    sim.run_timing_intervals = [[0, 0.001 * sec]]

    for policy in [
        "RemoveMultiples",
        "TakeAllGoods",
        "TakeWinnerOfGoods",
        "TakeIfOnlyOneGood",
        "TakeWinnerIfIsGood",
        "TakeWinnerIfAllAreGoods",
    ]:
        cc.multiples_policy = policy

        sim.run(start_new_process=True)

        # Calculate the coincidences using the Python implementation.
        root_file = uproot.open(root_filename)
        singles_tree = root_file["singles"]

        coincidences_python = coincidences_sorter(
            singles_tree,
            1e-9 * sec,
            # The policy names in the Python version start with lowercase.
            policy[0].lower() + policy[1:],
            0.0,
            "xy",
            1 * m,
            chunk_size=1000000,
            return_type="pd",
        )

        print(coincidences_python[coincidences_python["EventID1"] == 55])

        # Check that the coincidences from the CoincidenceSorterActor are identical.
        identical = compare_coincidences(coincidences_python, str(root_filename))
        if identical:
            print(f"Policy '{policy}': OK")
        else:
            print(f"Policy '{policy}': not OK")
            utility.test_ok(False)

    utility.test_ok(True)
