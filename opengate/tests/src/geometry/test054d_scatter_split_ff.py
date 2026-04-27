#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test 054d: Scatter Splitting + Free Flight in Parallel Geometries

Objective:
Verify that the ScatterSplittingFreeFlightActor correctly splits Compton/Rayleigh
scattered gammas, applies Free Flight attenuation to the secondary tracks, and
successfully restores analog physics when the split tracks enter an excluded
parallel volume.

Setup:
- World (G4_AIR): Z = [-500 mm, +500 mm]. Biasing Operator attached.
- Phantom (Mass World, G4_WATER): Z = [0 mm, +100 mm]. Scattering medium.
- Detector (Parallel World, G4_BONE_COMPACT_ICRU): Z = [+150 mm, +160 mm]. Excluded.
- Source: 500 keV gammas fired along +Z.

Verification 1: Internal Splitting Statistics
Validates that the number of secondary tracks generated exactly matches the
number of splits multiplied by the requested `compton_splitting_factor`.

Verification 2: Compound Variance Reduction (Weight)
Validates that the split tracks underwent both initial splitting weight reduction
(W_initial / Factor) and subsequent Free Flight attenuation. The mean weight
of tracks reaching the detector must be strictly < (1.0 / splitting_factor).

Verification 3: Analog Energy Deposition
Validates that the biased secondary tracks successfully disable Free Flight
upon entering the parallel detector, allowing for valid analog energy scoring.
"""

import uproot
import opengate as gate
from opengate.tests import utility
import numpy as np
import os

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, None, "test054d")

    is_ok = True
    for nb_thread in range(1, 3):

        # no MT on windows
        if nb_thread > 1 and os.name == "nt":
            continue

        # Create the simulation
        sim = gate.Simulation()
        sim.visu_type = "qt"
        # sim.visu = True
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

        # --- MASS WORLD VOLUME (Phantom) ---
        phantom = sim.add_volume("Box", "phantom")
        phantom.size = [10 * cm, 10 * cm, 10 * cm]
        phantom.translation = [0, 0, 5 * cm]  # Z: 0 to 100 mm
        phantom.material = "G4_WATER"
        phantom.color = [0, 0, 1, 0.5]

        # --- PARALLEL WORLD VOLUME (Detector) ---
        sim.add_parallel_world("world2")

        detector = sim.add_volume("Box", "detector")
        detector.mother = "world2"
        detector.size = [10 * cm, 10 * cm, 1 * cm]
        detector.translation = [0, 0, 15.5 * cm]  # Z: 150 to 160 mm
        detector.material = "G4_BONE_COMPACT_ICRU"
        detector.color = [1, 0, 0, 1]

        # --- SOURCE ---
        source = sim.add_source("GenericSource", "source")
        source.particle = "gamma"
        source.energy.mono = 500 * keV
        source.position.type = "box"
        source.position.size = [2 * cm, 2 * cm, 1 * mm]
        source.position.translation = [0, 0, -5 * mm]
        source.direction.type = "momentum"
        source.direction.momentum = [0, 0, 1]

        sim.run_timing_intervals = [[0, 0.1 * sec]]
        source.activity = 5e5 * Bq
        source.activity = 5000 * Bq
        if sim.visu:
            source.activity = 100 * Bq

        # --- BIASING OPERATOR ---
        split_factor = 10

        bias = sim.add_actor("ScatterSplittingFreeFlightActor", "bias")
        bias.attached_to = "world"
        bias.exclude_volumes = ["detector"]
        bias.kill_interacting_in_volumes = ["detector"]
        bias.compton_splitting_factor = split_factor
        bias.rayleigh_splitting_factor = split_factor
        bias.max_compton_level = 1
        # bias.debug = True # very verbose !

        # --- OUTPUTS ---
        phsp_det = sim.add_actor("PhaseSpaceActor", "phsp_det")
        phsp_det.attached_to = "detector"
        phsp_det.output_filename = paths.output / "detector_phsp.root"
        phsp_det.attributes = [
            "KineticEnergy",
            "Weight",
            "PrePosition",
            "PostPosition",
        ]
        phsp_det.steps_to_store = "all"

        digi_det = sim.add_actor("DigitizerHitsCollectionActor", "digi_det")
        digi_det.attached_to = "detector"
        digi_det.output_filename = paths.output / "detector_digi.root"
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

        # Disable General Process for biasing compatibility
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
        print("--- 1. ANALYZING INTERNAL SPLITTING STATS ---")
        print("=============================================")

        # Extract internal actor statistics
        split_info = bias.user_output["info"].split_info

        nb_splits = split_info.nb_compt_splits
        nb_tracks = split_info.nb_compt_tracks

        print(f"Recorded Compton Splits: {nb_splits}")
        print(f"Generated Secondary Tracks: {nb_tracks}")

        is_split_logic_ok = (nb_splits > 0) and (nb_tracks == nb_splits * split_factor)
        utility.print_test(
            is_split_logic_ok,
            f"Check exact splitting factor ({split_factor}x) multiplication",
        )

        print("\n=============================================")
        print("--- 2. ANALYZING COMPOUND TRACK WEIGHTS ---")
        print("=============================================")

        with uproot.open(paths.output / "detector_phsp.root") as f1:
            z_pre = f1["phsp_det"]["PrePosition_Z"].array(library="np")
            z_post = f1["phsp_det"]["PostPosition_Z"].array(library="np")
            weight = f1["phsp_det"]["Weight"].array(library="np")

        # Isolate steps entering the detector boundary (Z = 150.0 mm)
        # Using midpoint filtering to capture the active track weight within the volume
        z_mid = (z_pre + z_post) / 2.0
        mask_inside = (z_mid > 150.001) & (z_mid < 159.999)
        weights_inside = weight[mask_inside]

        max_expected_weight = 1.0 / split_factor
        mean_weight = np.mean(weights_inside) if len(weights_inside) > 0 else 0.0
        max_weight = np.max(weights_inside) if len(weights_inside) > 0 else 0.0

        print(f"Steps recorded inside detector: {len(weights_inside)}")
        print(
            f"Max Track Weight: {max_weight:.4f} (Must be <= {max_expected_weight:.4f})"
        )
        print(
            f"Mean Track Weight: {mean_weight:.4f} (Must be < {max_expected_weight:.4f} due to FF)"
        )

        is_weight_ok = (
            (len(weights_inside) > 0)
            and (max_weight <= max_expected_weight)
            and (mean_weight < max_expected_weight)
        )
        utility.print_test(
            is_weight_ok, "Check Compound Variance Reduction (Split + FF)"
        )

        print("\n=============================================")
        print("--- 3. ANALYZING ANALOG SCORING (DIGITIZER) ---")
        print("=============================================")

        with uproot.open(paths.output / "detector_digi.root") as f2:
            edep_digi = f2["digi_det"]["TotalEnergyDeposit"].array(library="np")
            z_pre_digi = f2["digi_det"]["PrePosition_Z"].array(library="np")
            z_post_digi = f2["digi_det"]["PostPosition_Z"].array(library="np")

        z_mid_digi = (z_pre_digi + z_post_digi) / 2.0
        mask_overlap_digi = (z_mid_digi > 150.001) & (z_mid_digi < 159.999)

        total_edep_excluded = np.sum(edep_digi[mask_overlap_digi])
        hits_in_excluded = np.sum(mask_overlap_digi)

        print(f"Digitizer Hits in Excluded Volume: {hits_in_excluded}")
        print(f"Total Edep in Excluded Volume: {total_edep_excluded:.4f} MeV")

        is_edep_ok = total_edep_excluded > 0.0
        utility.print_test(is_edep_ok, "Check Analog Energy Deposition of Split Tracks")

        is_ok = is_split_logic_ok and is_weight_ok and is_edep_ok and is_ok

    # Final Test Status
    utility.test_ok(is_ok)
