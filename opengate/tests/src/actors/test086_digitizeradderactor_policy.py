#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import uproot
from opengate.actors.coincidences import coincidences_sorter
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

    is_ok = True
    exceptions = []
    paths = utility.get_default_test_paths(__file__, None, output_folder="test086")

    for adder_policy in ["EnergyWinnerPosition", "EnergyWeightedCentroidPosition"]:

        sim = gate.Simulation()
        sim.g4_verbose = False
        # sim.visu = False
        sim.visu_type = "vrml"
        sim.random_engine = "MersenneTwister"
        sim.random_seed = 1234
        sim.number_of_threads = 1
        sim.output_dir = paths.output
        create_materials(sim)

        sim.world.size = [200 * mm, 200 * mm, 200 * mm]
        sim.world.material = "G4_AIR"

        crystal = sim.add_volume("Box", "crystal")
        crystal.size = [50 * mm, 50 * mm, 50 * mm]
        crystal.translation = gate.geometry.utility.get_grid_repetition(
            [2, 1, 1], [60 * mm, 0, 0]
        )
        crystal.material = "LYSO"

        source = sim.add_source("GenericSource", "b2b")
        source.particle = "back_to_back"
        source.activity = 10 * Bq
        source.position.type = "sphere"
        source.position.radius = 0.5 * mm
        source.direction.type = "iso"
        source.direction.theta = [90, 90 * deg]
        source.direction.phi = [0, 0 * deg]

        sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option3"

        stats = sim.add_actor("SimulationStatisticsActor", "stats")

        hc = sim.add_actor("DigitizerHitsCollectionActor", "hits")
        hc.attached_to = crystal.name
        hc.authorize_repeated_volumes = True
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
        sc.policy = adder_policy
        sc.output_filename = hc.output_filename

        sim.run_timing_intervals = [[0, 1 * sec]]

        sim.run(start_new_process=True)

        root_file = uproot.open(hc.get_output_path())
        singles_tree = root_file["singles"]
        num_singles = int(singles_tree.num_entries)

        coincidences = coincidences_sorter(
            singles_tree,
            time_window=2 * ns,
            min_transaxial_distance=0 * mm,
            transaxial_plane="xy",
            max_axial_distance=60 * mm,
            policy="takeAllGoods",
            chunk_size=100000,
        )
        num_coincidences = len(coincidences["GlobalTime1"])
        print(f"{num_singles} single(s), {num_coincidences} coincidence(s)")

        if num_coincidences == 0:
            is_ok = False
            exceptions.append(
                GateImplementationError(
                    f"No coincidences were detected when using a DigitizerAdderActor with policy '{adder_policy}'"
                )
            )

    utility.test_ok(is_ok, exceptions=exceptions)
