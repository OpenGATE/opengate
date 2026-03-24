#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate_core as g4

from opengate.managers import (
    PhysicsListManager,
    create_reference_physics_list_class,
    reference_physics_list_base_class_names,
)
from opengate.tests.utility import print_test, test_ok


def check_pybind_reference_classes_against_factory(factory):
    is_ok = True

    factory_names = set(factory.AvailablePhysLists())
    pybind_names = {
        name for name in reference_physics_list_base_class_names if hasattr(g4, name)
    }

    missing_pybind_names = sorted(factory_names - pybind_names)
    extra_pybind_names = sorted(pybind_names - factory_names)

    b = len(missing_pybind_names) == 0
    print_test(
        b,
        f"All Geant4 factory base physics lists are exposed via pybind. Missing: {missing_pybind_names}",
    )
    is_ok = b and is_ok

    b = len(extra_pybind_names) == 0
    print_test(
        b,
        f"Pybind does not expose unexpected reference physics-list classes. Extra: {extra_pybind_names}",
    )
    is_ok = b and is_ok

    for name in sorted(factory_names):
        b = hasattr(g4, name)
        print_test(b, f"Reference physics list '{name}' is bound in opengate_core")
        is_ok = b and is_ok
        if not b:
            continue

        cls = getattr(g4, name)
        b = issubclass(cls, g4.G4VModularPhysicsList)
        print_test(
            b,
            f"Reference physics list '{name}' inherits from G4VModularPhysicsList",
        )
        is_ok = b and is_ok

    return is_ok


def check_gate_reference_registry_against_factory(factory):
    is_ok = True

    for name in PhysicsListManager.available_g4_reference_physics_lists:
        b = factory.IsReferencePhysList(name)
        print_test(
            b,
            f"GATE reference physics list '{name}' is recognized by G4PhysListFactory",
        )
        is_ok = b and is_ok

    return is_ok


def check_gate_reference_classes_can_be_synthesized():
    is_ok = True

    for name in PhysicsListManager.available_g4_reference_physics_lists:
        try:
            cls = create_reference_physics_list_class(name)
            b = issubclass(cls, g4.G4VModularPhysicsList)
            print_test(
                b,
                f"GATE can synthesize a wrapped class for reference physics list '{name}'",
            )
            is_ok = b and is_ok
        except Exception as e:
            print_test(
                False,
                f"GATE failed to synthesize a wrapped class for reference physics list '{name}': {e}",
            )
            is_ok = False

    return is_ok


if __name__ == "__main__":
    factory = g4.G4PhysListFactory()

    is_ok = True
    is_ok = check_pybind_reference_classes_against_factory(factory) and is_ok
    is_ok = check_gate_reference_registry_against_factory(factory) and is_ok
    is_ok = check_gate_reference_classes_can_be_synthesized() and is_ok

    test_ok(is_ok)
