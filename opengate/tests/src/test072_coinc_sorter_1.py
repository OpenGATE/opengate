#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import opengate.contrib.pet.siemensbiograph as pet_biograph
from opengate.tests import utility

if __name__ == "__main__":
    # test paths
    paths = utility.get_default_test_paths(
        __file__, output_folder="test72_coinc_sorter"
    )

    # create the simulation
    sim = gate.Simulation()

    # main options
    sim.g4_verbose = False
    sim.g4_verbose_level = 1
    sim.visu_type = "vrml"
    # sim.visu = True

    # units
    cm = gate.g4_units.cm
    Bq = gate.g4_units.Bq
    MeV = gate.g4_units.MeV
    sec = gate.g4_units.second
    minute = gate.g4_units.minute
    keV = gate.g4_units.keV

    # add a PET Biograph
    # (when sim.visu is on, the number of crystal is reduced to allow fast visualization)
    pet = pet_biograph.add_pet(sim, "pet", visu_debug=sim.visu)

    # get some volumes
    crystal = sim.volume_manager.volumes[f"{pet.name}_crystal"]
    block = sim.volume_manager.volumes[f"{pet.name}_block"]
    ring = sim.volume_manager.volumes[f"{pet.name}_ring"]

    # hits collection
    output_filename = paths.output / "test72_output_1.root"
    hc = sim.add_actor("DigitizerHitsCollectionActor", "hits")
    hc.mother = crystal.name
    hc.output = output_filename
    hc.attributes = [
        "PostPosition",
        "TotalEnergyDeposit",
        "PreStepUniqueVolumeID",
        "GlobalTime",
    ]

    # singles collection
    ro = sim.add_actor("DigitizerReadoutActor", "readout")
    ro.mother = crystal.name
    ro.input_digi_collection = hc.name
    ro.group_volume = block.name
    ro.discretize_volume = crystal.name
    ro.policy = "EnergyWeightedCentroidPosition"
    ro.output = hc.output

    # No energy blurring, no spatial blurring, no noise, no efficiency ...

    # EnergyWindows
    ew = sim.add_actor("DigitizerEnergyWindowsActor", f"singles")
    ew.mother = crystal.name
    ew.output = output_filename
    ew.input_digi_collection = ro.name
    ew.channels = [{"name": ew.name, "min": 435 * keV, "max": 585 * keV}]

    # source
    total_yield = gate.sources.generic.get_rad_yield("F18")
    source = sim.add_source("GenericSource", "src")
    source.energy.type = "F18"
    source.particle = "e+"
    source.position.type = "sphere"
    source.position.radius = 1 * cm
    source.position.translation = [0, 0, 0]
    source.activity = 1e5 * Bq * total_yield
    source.direction.type = "iso"
    source.half_life = 109.7 * minute

    # add stat actor
    s = sim.add_actor("SimulationStatisticsActor", "stats")
    s.track_types_flag = True

    # time run
    sim.run_timing_intervals = [(0, 1 * sec)]

    # start simulation
    sim.run()

    # print stats
    stats = sim.output.get_actor("stats")
    print(stats)
    print(f"Output root file is {output_filename}")
