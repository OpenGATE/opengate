#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test 054c: Free Flight Biasing with Parallel Excluded Volumes

Objective:
Verify that the Gamma Free Flight (FF) biasing operator successfully synchronizes
with the Layered Mass Geometry parallel navigator to correctly toggle biasing states
when attached to the root world volume.

Setup:
- World (G4_AIR): Z = [-500 mm, +500 mm]. FF Operator attached.
- Box 1 (Mass World, G4_WATER): Z = [0 mm, +100 mm].
- Box 2 (Parallel World, G4_BONE_COMPACT_ICRU): Z = [+50 mm, +60 mm]. Excluded from FF.
- Source: 140 keV gammas fired along +Z.

Verification 1: Weight Modification (FF Active)
Validates that FF is actively biasing the track in the standard mass world.
At the Z=+50.0 mm boundary (entry to the excluded volume), the statistical
mean of the track weights MUST be strictly between 0.0 and 1.0.

Verification 2: Analog Energy Deposition (FF Disabled)
Validates that FF successfully disables itself upon entering the excluded
parallel volume. If FF remained erroneously active, steps would be forced
transparent (0 MeV). The total digitized energy deposition within the excluded
volume MUST be strictly greater than 0 MeV.
"""

import os

import uproot
import opengate as gate
from opengate.tests import utility
import numpy as np

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, None, "test054c")

    is_ok = True
    for nb_thread in range(1, 3):

        # no MT on windows
        if nb_thread > 1 and os.name == "nt":
            continue

        # Create the simulation
        sim = gate.Simulation()
        sim.visu_type = "qt"
        sim.number_of_threads = nb_thread

        # Units
        m = gate.g4_units.m
        cm = gate.g4_units.cm
        mm = gate.g4_units.mm
        keV = gate.g4_units.keV
        Bq = gate.g4_units.Bq
        sec = gate.g4_units.s

        # World
        sim.world.size = [1 * m, 1 * m, 1 * m]
        sim.world.material = "G4_AIR"

        # --- MASS WORLD VOLUME (Z = 0 to 100 mm) ---
        box1 = sim.add_volume("Box", "box1")
        box1.size = [10 * cm, 10 * cm, 10 * cm]
        box1.translation = [0, 0, 5 * cm]
        box1.material = "G4_WATER"
        box1.color = [0, 0, 1, 0.5]

        # --- PARALLEL WORLD VOLUME (Z = 50 to 60 mm) ---
        sim.add_parallel_world("world2")

        box2 = sim.add_volume("Box", "box2")
        box2.mother = "world2"
        box2.size = [10 * cm, 10 * cm, 1 * cm]
        box2.translation = [0, 0, 5.5 * cm]
        box2.material = "G4_BONE_COMPACT_ICRU"
        box2.color = [1, 0, 0, 1]

        # --- SOURCE ---
        source = sim.add_source("GenericSource", "source")
        source.particle = "gamma"
        source.energy.mono = 140 * keV
        source.position.type = "box"
        source.position.size = [2 * cm, 2 * cm, 1 * mm]
        source.position.translation = [0, 0, -5 * mm]
        source.direction.type = "momentum"
        source.direction.momentum = [0, 0, 1]

        sim.run_timing_intervals = [[0, 0.1 * sec]]
        source.activity = 2e5 * Bq

        # --- BIASING OPERATOR ---
        ff = sim.add_actor("GammaFreeFlightActor", "ff")
        ff.attached_to = "world"
        ff.exclude_volumes = ["box2"]

        # --- OUTPUTS ---
        phsp_mass = sim.add_actor("PhaseSpaceActor", "phsp_mass")
        phsp_mass.attached_to = "box1"
        phsp_mass.output_filename = paths.output / "box1_mass.root"
        phsp_mass.attributes = [
            "KineticEnergy",
            "Weight",
            "PrePosition",
            "PostPosition",
            "TotalEnergyDeposit",
        ]
        phsp_mass.steps_to_store = "all"

        digi_det = sim.add_actor("DigitizerHitsCollectionActor", "digi_det")
        digi_det.attached_to = "box2"
        digi_det.output_filename = paths.output / "box2_digi.root"
        digi_det.attributes = [
            "TotalEnergyDeposit",
            "PrePosition",
            "PostPosition",
        ]

        stats = sim.add_actor("SimulationStatisticsActor", "Stats")
        stats.track_types_flag = True

        # Physics
        sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option3"
        sim.physics_manager.set_production_cut("world", "all", 5000 * mm)
        s = f"/process/em/UseGeneralProcess false"
        if s not in sim.g4_commands_before_init:
            sim.g4_commands_before_init.append(s)

        # Run the simulation
        sim.run(start_new_process=True)
        print(stats)

        # ==========================================================
        # --- VERIFICATION BLOCK ---
        # ==========================================================

        print("\n=============================================")
        print("--- 1. ANALYZING FF TRACK WEIGHTS ---")
        print("=============================================")

        # Load Phase Space arrays
        with uproot.open(paths.output / "box1_mass.root") as f1:
            z_post = f1["phsp_mass"]["PostPosition_Z"].array(library="np")
            weight = f1["phsp_mass"]["Weight"].array(library="np")

        # V1: Check weight at the exact entry boundary to the excluded volume (Z = 50.0 mm)
        mask_boundary = np.isclose(z_post, 50.0, atol=1e-3)
        weights_at_boundary = weight[mask_boundary]

        mean_weight = (
            np.mean(weights_at_boundary) if len(weights_at_boundary) > 0 else 0.0
        )

        print(
            f"Steps arriving at excluded volume boundary (Z=50mm): {len(weights_at_boundary)}"
        )
        print(
            f"Mean Track Weight at boundary: {mean_weight:.4f} (Expected: 0.0 < W < 1.0)"
        )

        # Assertion 1: Weight must be modified (proving FF was active from Z=0 to 50)
        is_weight_ok = 0.0 < mean_weight < 1.0
        utility.print_test(is_weight_ok, "Check FF Weight Modification in Mass World")

        print("\n=============================================")
        print("--- 2. ANALYZING ANALOG SCORING IN EXCLUDED VOL ---")
        print("=============================================")

        # Load Digitizer arrays
        with uproot.open(paths.output / "box2_digi.root") as f2:
            edep_digi = f2["digi_det"]["TotalEnergyDeposit"].array(library="np")
            z_pre_digi = f2["digi_det"]["PrePosition_Z"].array(library="np")
            z_post_digi = f2["digi_det"]["PostPosition_Z"].array(library="np")

        # Midpoint filtering for safety
        z_mid_digi = (z_pre_digi + z_post_digi) / 2.0
        mask_overlap_digi = (z_mid_digi > 50.001) & (z_mid_digi < 59.999)

        total_edep_excluded = np.sum(edep_digi[mask_overlap_digi])
        hits_in_excluded = np.sum(mask_overlap_digi)

        print(f"Digitizer Hits in Excluded Volume: {hits_in_excluded}")
        print(f"Total Edep in Excluded Volume: {total_edep_excluded:.4f} MeV")

        # Assertion 2: Energy must be deposited (proving FF turned OFF)
        is_edep_ok = total_edep_excluded > 0.0
        utility.print_test(
            is_edep_ok, "Check Analog Energy Deposition in Excluded Parallel World"
        )
        is_ok = is_weight_ok and is_edep_ok and is_ok

    # Final Test Status
    utility.test_ok(is_ok)
