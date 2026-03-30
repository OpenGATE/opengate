#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility

TARGET_AUTO_NAME = "target_auto"
TARGET_EXPLICIT_NAME = "target_explicit"
TARGET_EXPLICIT_CHILD_NAME = "target_explicit_child"
EXPLICIT_REGION_NAME = "dna_region_explicit"


def check_dna_regions(sim):
    hook_output = sim.user_hook_log[0]
    dna_regions = hook_output["dna_regions"]
    volume_regions = hook_output["volume_regions"]
    model_checks = sim.user_hook_log[1]

    target_auto_region = f"{TARGET_AUTO_NAME}_region"

    print("Checking configured DNA regions:")
    print(dna_regions)
    print("Checking volume-to-region association:")
    print(volume_regions)
    world_model = model_checks.get("world")

    checks = [
        (
            f"DNA region for {target_auto_region}",
            dna_regions.get(target_auto_region),
            "DNA_Opt2",
        ),
        (
            f"DNA region for {EXPLICIT_REGION_NAME}",
            dna_regions.get(EXPLICIT_REGION_NAME),
            "DNA_Opt4",
        ),
        (
            f"Region attached to {TARGET_AUTO_NAME}",
            volume_regions.get(TARGET_AUTO_NAME),
            target_auto_region,
        ),
        (
            f"Region attached to {TARGET_EXPLICIT_NAME}",
            volume_regions.get(TARGET_EXPLICIT_NAME),
            EXPLICIT_REGION_NAME,
        ),
        (
            f"Region attached to {TARGET_EXPLICIT_CHILD_NAME}",
            volume_regions.get(TARGET_EXPLICIT_CHILD_NAME),
            EXPLICIT_REGION_NAME,
        ),
        (
            "World DNA region remains unset",
            dna_regions.get("DefaultRegionForTheWorld"),
            None,
        ),
        (
            "World model remains standard/inactive",
            world_model,
            "None or DummyModel",
        ),
    ]

    is_ok = True
    print("Detailed DNA region checks:")
    for label, actual, expected in checks:
        if expected == "contains DNA":
            passed = actual is not None and "DNA" in str(actual)
        elif expected == "None or DummyModel":
            passed = actual is None or "DummyModel" in str(actual)
        else:
            passed = actual == expected
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {label}")
        print(f"    actual  : {actual}")
        print(f"    expected: {expected}")
        is_ok = is_ok and passed

    print("Diagnostic EM-model checks:")
    for volume_name, model_name in model_checks.items():
        print(f"  {volume_name}: {model_name}")

    return is_ok


def combined_dna_hook(simulation_engine):
    gate.userhooks.user_hook_dna_regions(simulation_engine)
    gate.userhooks.user_hook_dna_region_models(simulation_engine)


if __name__ == "__main__":
    sim = gate.Simulation()

    sim.g4_verbose = False
    sim.visu = False
    sim.random_engine = "MersenneTwister"
    sim.random_seed = 123456

    m = gate.g4_units.m
    cm = gate.g4_units.cm
    mm = gate.g4_units.mm
    MeV = gate.g4_units.MeV

    sim.world.size = [2 * m, 2 * m, 2 * m]

    target_auto = sim.add_volume("Box", TARGET_AUTO_NAME)
    target_auto.size = [2 * cm, 2 * cm, 2 * cm]
    target_auto.translation = [-4 * cm, 0, 0]
    target_auto.material = "G4_WATER"

    target_explicit = sim.add_volume("Box", TARGET_EXPLICIT_NAME)
    target_explicit.size = [2 * cm, 2 * cm, 2 * cm]
    target_explicit.translation = [4 * cm, 0, 0]
    target_explicit.material = "G4_WATER"

    target_explicit_child = sim.add_volume("Box", TARGET_EXPLICIT_CHILD_NAME)
    target_explicit_child.mother = target_explicit
    target_explicit_child.size = [1 * cm, 1 * cm, 1 * cm]
    target_explicit_child.material = "G4_WATER"

    sim.physics_manager.physics_list_name = "G4EmStandardPhysics"
    target_auto.set_dna_em_physics("DNA_Opt2")

    explicit_region = sim.physics_manager.add_region(EXPLICIT_REGION_NAME)
    explicit_region.associate_volume(target_explicit)
    explicit_region.associate_volume(target_explicit_child)
    sim.physics_manager.set_dna_em_physics_in_region(EXPLICIT_REGION_NAME, "DNA_Opt4")

    source = sim.add_source("GenericSource", "source")
    source.particle = "gamma"
    source.energy.mono = 1 * MeV
    source.position.type = "point"
    source.position.translation = [0, 0, 0]
    source.direction.type = "iso"
    source.n = 1

    sim.add_actor("SimulationStatisticsActor", "stats")

    sim.user_hook_after_init = combined_dna_hook

    sim.run(start_new_process=False)

    is_ok = check_dna_regions(sim)
    utility.test_ok(is_ok)
