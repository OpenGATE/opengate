#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import uproot
from opengate.exception import GateImplementationError
import opengate.tests.utility as utility


g_cm3 = gate.g4_units.g_cm3
mm = gate.g4_units.mm
Bq = gate.g4_units.Bq
keV = gate.g4_units.keV
sec = gate.g4_units.second
ns = gate.g4_units.nanosecond
deg = gate.g4_units.degree


def create_materials(sim):
    sim.volume_manager.material_database.add_material_nb_atoms(
        "LYSO", ["Lu", "Y", "Si", "O"], [18, 2, 10, 50], 7.1 * g_cm3
    )


if __name__ == "__main__":

    paths = utility.get_default_test_paths(__file__, output_folder="test086")

    sim = gate.Simulation()
    sim.g4_verbose = False
    sim.visu = False
    sim.visu_type = "vrml"
    sim.random_engine = "MersenneTwister"
    sim.random_seed = 1234
    sim.output_dir = paths.output
    sim.number_of_threads = 1
    create_materials(sim)

    sim.world.size = [200 * mm, 200 * mm, 200 * mm]
    sim.world.material = "G4_AIR"

    block_size = 50 * mm

    # Two blocks of LYSO, created separately without repetition, symmetrically along the x-axis.
    crystal_no_repeat1 = sim.add_volume("Box", "crystal_no_repeat1")
    crystal_no_repeat1.size = [block_size] * 3
    crystal_no_repeat1.translation = [-block_size * 1.1, 0, 0]
    crystal_no_repeat1.material = "LYSO"
    crystal_no_repeat2 = sim.add_volume("Box", "crystal_no_repeat2")
    crystal_no_repeat2.size = [block_size] * 3
    crystal_no_repeat2.translation = [block_size * 1.1, 0, 0]
    crystal_no_repeat2.material = "LYSO"

    # Two blocks of LYSO, created with repetition, symmetrically along the y-axis.
    crystal_repeat = sim.add_volume("Box", "crystal_repeat")
    crystal_repeat.size = [block_size] * 3
    crystal_repeat.translation = gate.geometry.utility.get_grid_repetition(
        [1, 2, 1], [0, 2 * block_size * 1.1, 0]
    )
    crystal_repeat.material = "LYSO"

    # Gamma 511 keV source, radiating in the x-y plane.
    source = sim.add_source("GenericSource", "source")
    source.particle = "gamma"
    source.activity = 100 * Bq
    source.energy.type = "mono"
    source.energy.mono = 511 * keV
    source.position.type = "sphere"
    source.position.radius = 0.5 * mm
    source.direction.type = "iso"
    source.direction.theta = [90 * deg, 90 * deg]

    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option3"

    stats = sim.add_actor("SimulationStatisticsActor", "stats")

    hc = sim.add_actor("DigitizerHitsCollectionActor", "hits")
    hc.attached_to = [crystal_no_repeat1.name, crystal_no_repeat2, crystal_repeat]
    hc.output_filename = "sim.root"
    hc.attributes = [
        "EventID",
        "PreStepUniqueVolumeID",
        "TrackVolumeName",
        "PostPosition",
        "TotalEnergyDeposit",
        "GlobalTime",
    ]

    sc = sim.add_actor("DigitizerAdderActor", "singles")
    sc.attached_to = hc.attached_to
    sc.input_digi_collection = hc.name
    sc.policy = "EnergyWinnerPosition"
    sc.output_filename = hc.output_filename

    sim.run_timing_intervals = [[0, 1 * sec]]

    sim.run()

    root_file = uproot.open(paths.output / hc.output_filename)
    singles_tree = root_file["singles"]

    unique_volume_ids = set(singles_tree["PreStepUniqueVolumeID"].array())
    num_unique_hit_volumes = len(unique_volume_ids)
    print(f"{num_unique_hit_volumes} volumes have been hit: {unique_volume_ids}")

    is_ok = True
    exceptions = []

    expected_num_volumes = 4
    if num_unique_hit_volumes < expected_num_volumes:
        is_ok = False
        exceptions.append(
            GateImplementationError(
                f"Hits have been recorded for only {num_unique_hit_volumes} out of {expected_num_volumes} volumes: {unique_volume_ids}"
            )
        )
    utility.test_ok(is_ok, exceptions=exceptions)
