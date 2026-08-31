#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import uproot
import opengate as gate
from opengate.tests import utility

"""
Test 054b: Parallel Navigation and Layered Mass Geometry (LMG) Verification

Objective:
Verify the synchronization of particle tracking and energy scoring between
the mass world and a parallel world using Layered Mass Geometry.

Setup:
- Box 1 (Mass World, G4_WATER): Z = [-50 mm, +50 mm]
- Box 2 (Parallel World, G4_BONE_COMPACT_ICRU): Z = [0 mm, +100 mm]
- Overlapping Region: Z = [0 mm, +50 mm]

Verification 1: Navigator Track Slicing (PhaseSpaceActor)
Validates that parallel navigators correctly force step limitations across
dimensions. Geant4 must artificially truncate tracking steps exactly at the
intersection boundaries (Z=0.0 mm in Box 1, and Z=+50.0 mm in Box 2).

Verification 2: Step Broadcasting (DigitizerHitsCollectionActor)
Validates that physical energy deposition, calculated using the overriding
LMG material (Bone), is symmetrically broadcast to the `UserSteppingAction`
of sensitive volumes in both the mass and parallel worlds without data loss
or double-counting.
"""

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, None, "test054b")

    # Create the simulation
    sim = gate.Simulation()
    # sim.visu = True
    sim.visu_type = "qt"
    sim.number_of_threads = 1
    # sim.random_seed = 123456

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

    # --- MASS WORLD VOLUME ---
    box1 = sim.add_volume("Box", "box1")
    box1.size = [10 * cm, 10 * cm, 10 * cm]
    box1.translation = [0, 0, 0]
    box1.material = "G4_WATER"
    box1.color = [0, 1, 0, 1]

    # --- PARALLEL WORLD VOLUME ---
    sim.add_parallel_world("world2")

    box2 = sim.add_volume("Box", "box2")
    box2.mother = "world2"  # not a daughter of Box1
    box2.size = [10 * cm, 10 * cm, 10 * cm]
    box2.translation = [0, 0, 5 * cm]
    box2.material = "G4_BONE_COMPACT_ICRU"
    box2.color = [1, 0, 0, 1]

    # --- SOURCE ---
    # A broad beam shooting straight through both overlapping boxes
    source = sim.add_source("GenericSource", "source")
    source.particle = "gamma"
    source.energy.mono = 500 * keV
    source.position.type = "box"
    source.position.size = [5 * cm, 5 * cm, 1 * mm]
    source.position.translation = [0, 0, -15 * cm]
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]

    sim.run_timing_intervals = [[0, 0.1 * sec]]
    source.activity = 1e5 * Bq

    # --- PHASE SPACE OUTPUTS ---
    phsp1 = sim.add_actor("PhaseSpaceActor", "phsp1")
    phsp1.attached_to = "box1"
    phsp1.output_filename = paths.output / "box1_phsp.root"
    phsp1.attributes = [
        "KineticEnergy",
        "PrePosition",
        "PostPosition",
        "TotalEnergyDeposit",
    ]
    phsp1.steps_to_store = "all"

    phsp2 = sim.add_actor("PhaseSpaceActor", "phsp2")
    phsp2.attached_to = "box2"
    phsp2.output_filename = paths.output / "box2_phsp.root"
    phsp2.attributes = phsp1.attributes
    phsp2.steps_to_store = "all"

    # --- DIGITIZER OUTPUTS ---
    d1 = sim.add_actor("DigitizerHitsCollectionActor", "d1")
    d1.attached_to = "box1"
    d1.output_filename = paths.output / "box1_digi.root"
    d1.attributes = [
        "TotalEnergyDeposit",
        "PrePosition",
        "PostPosition",
    ]

    d2 = sim.add_actor("DigitizerHitsCollectionActor", "d2")
    d2.attached_to = "box2"
    d2.output_filename = paths.output / "box2_digi.root"
    d2.attributes = d1.attributes

    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.track_types_flag = True

    # no secondaries
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option3"
    sim.physics_manager.set_production_cut("world", "all", 5000 * mm)

    # Run the simulation
    sim.run()
    print(stats)

    # --- VERIFICATION ---
    import numpy as np

    print("\n=============================================")
    print("--- 1. ANALYZING PHASE SPACE BOUNDARIES ---")
    print("=============================================")

    # Load PostPosition_Z arrays
    with uproot.open(paths.output / "box1_phsp.root") as f1:
        z_post_1_phsp = f1["phsp1"]["PostPosition_Z"].array(library="np")

    with uproot.open(paths.output / "box2_phsp.root") as f2:
        z_post_2_phsp = f2["phsp2"]["PostPosition_Z"].array(library="np")

    # Prove step limitations
    hits_sliced_at_0 = np.sum(np.isclose(z_post_1_phsp, 0.0, atol=1e-3))
    hits_sliced_at_50 = np.sum(np.isclose(z_post_2_phsp, 50.0, atol=1e-3))

    print(f"Total steps in Mass World (box1): {len(z_post_1_phsp)}")
    print(f"Steps artificially sliced at Z=0.0 mm in box1: {hits_sliced_at_0}")
    print(f"\nTotal steps in Parallel World (box2): {len(z_post_2_phsp)}")
    print(f"Steps artificially sliced at Z=+50.0 mm in box2: {hits_sliced_at_50}")

    is_ok = hits_sliced_at_0 > 100 and hits_sliced_at_50 > 100
    utility.print_test(
        is_ok, "Check Both navigators sliced tracks at the intersection boundaries."
    )

    print("\n=============================================")
    print("--- 2. ANALYZING PHASE SPACE ENERGY EDEP ---")
    print("=============================================")

    # Load Edep, PrePosition, and PostPosition
    with uproot.open(paths.output / "box1_phsp.root") as f1:
        edep1_phsp = f1["phsp1"]["TotalEnergyDeposit"].array(library="np")
        z1_pre_phsp = f1["phsp1"]["PrePosition_Z"].array(library="np")

    with uproot.open(paths.output / "box2_phsp.root") as f2:
        edep2_phsp = f2["phsp2"]["TotalEnergyDeposit"].array(library="np")
        z2_pre_phsp = f2["phsp2"]["PrePosition_Z"].array(library="np")

    # Midpoint filtering
    z1_mid_phsp = (z1_pre_phsp + z_post_1_phsp) / 2.0
    z2_mid_phsp = (z2_pre_phsp + z_post_2_phsp) / 2.0

    mask1_overlap_phsp = (z1_mid_phsp > 0) & (z1_mid_phsp < 50)
    mask2_overlap_phsp = (z2_mid_phsp > 0) & (z2_mid_phsp < 50)

    total_edep1_overlap_phsp = np.sum(edep1_phsp[mask1_overlap_phsp])
    total_edep2_overlap_phsp = np.sum(edep2_phsp[mask2_overlap_phsp])

    steps_in_1_phsp = np.sum(mask1_overlap_phsp)
    steps_in_2_phsp = np.sum(mask2_overlap_phsp)

    b1_phsp = steps_in_1_phsp == steps_in_2_phsp
    utility.print_test(b1_phsp, "Check PHSP steps in overlapping region")
    print(f"PHSP Steps inside overlap (box1): {steps_in_1_phsp}")
    print(f"PHSP Steps inside overlap (box2): {steps_in_2_phsp}")

    b2_phsp = total_edep1_overlap_phsp == total_edep2_overlap_phsp
    utility.print_test(b2_phsp, "Check PHSP energy deposition in overlapping region")
    print(
        f"Total PHSP Edep in box1 (Overlap Region): {total_edep1_overlap_phsp:.4f} MeV"
    )
    print(
        f"Total PHSP Edep in box2 (Overlap Region): {total_edep2_overlap_phsp:.4f} MeV"
    )

    print("\n=============================================")
    print("--- 3. ANALYZING DIGITIZER ENERGY EDEP ---")
    print("=============================================")

    # Load Edep, PrePosition, and PostPosition from the Digitizer roots
    with uproot.open(paths.output / "box1_digi.root") as f1:
        edep1_digi = f1["d1"]["TotalEnergyDeposit"].array(library="np")
        z1_pre_digi = f1["d1"]["PrePosition_Z"].array(library="np")
        z1_post_digi = f1["d1"]["PostPosition_Z"].array(library="np")

    with uproot.open(paths.output / "box2_digi.root") as f2:
        edep2_digi = f2["d2"]["TotalEnergyDeposit"].array(library="np")
        z2_pre_digi = f2["d2"]["PrePosition_Z"].array(library="np")
        z2_post_digi = f2["d2"]["PostPosition_Z"].array(library="np")

    # Midpoint filtering
    z1_mid_digi = (z1_pre_digi + z1_post_digi) / 2.0
    z2_mid_digi = (z2_pre_digi + z2_post_digi) / 2.0

    mask1_overlap_digi = (z1_mid_digi > 0) & (z1_mid_digi < 50)
    mask2_overlap_digi = (z2_mid_digi > 0) & (z2_mid_digi < 50)

    total_edep1_overlap_digi = np.sum(edep1_digi[mask1_overlap_digi])
    total_edep2_overlap_digi = np.sum(edep2_digi[mask2_overlap_digi])

    steps_in_1_digi = np.sum(mask1_overlap_digi)
    steps_in_2_digi = np.sum(mask2_overlap_digi)

    b1_digi = steps_in_1_digi == steps_in_2_digi
    utility.print_test(b1_digi, "Check DIGI hits in overlapping region")
    print(f"DIGI Hits inside overlap (box1): {steps_in_1_digi}")
    print(f"DIGI Hits inside overlap (box2): {steps_in_2_digi}")

    # Note: Using np.isclose for float comparison to avoid arbitrary precision failures
    b2_digi = np.isclose(total_edep1_overlap_digi, total_edep2_overlap_digi, rtol=1e-5)
    utility.print_test(b2_digi, "Check DIGI energy deposition in overlapping region")
    print(
        f"Total DIGI Edep in box1 (Overlap Region): {total_edep1_overlap_digi:.4f} MeV"
    )
    print(
        f"Total DIGI Edep in box2 (Overlap Region): {total_edep2_overlap_digi:.4f} MeV"
    )

    is_ok_steps = b1_phsp and b2_phsp and b1_digi and b2_digi
    utility.test_ok(is_ok and is_ok_steps)
