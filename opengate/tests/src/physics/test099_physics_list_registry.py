#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate_core as g4
import opengate as gate

from opengate.physics import (
    PhysicsListBuilder,
    create_reference_physics_list_class,
    reference_physics_list_base_class_names,
    reference_physics_list_em_extensions,
    reference_physics_list_special_builders,
)
from opengate.tests.utility import print_test, test_ok


def check_pybind_reference_classes_against_factory(factory):
    is_ok = True

    factory_names = {str(name) for name in factory.AvailablePhysLists()}
    expected_bound_names = set(reference_physics_list_base_class_names)
    pybind_names = {name for name in expected_bound_names if hasattr(g4, name)}

    missing_pybind_names = sorted(expected_bound_names - pybind_names)
    extra_pybind_names = sorted(pybind_names - factory_names)

    b = len(missing_pybind_names) == 0
    print_test(
        b,
        f"All expected base reference physics lists are exposed via pybind. Missing: {missing_pybind_names}",
    )
    is_ok = b and is_ok

    b = len(extra_pybind_names) == 0
    print_test(
        b,
        f"Pybind does not expose unexpected reference physics-list classes. Extra: {extra_pybind_names}",
    )
    is_ok = b and is_ok

    for name in sorted(expected_bound_names):
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

    registered_names = set(PhysicsListBuilder.available_g4_reference_physics_lists)
    expected_names = {
        f"{base_name}{suffix}"
        for base_name in factory.AvailablePhysLists()
        for suffix in ("", *reference_physics_list_em_extensions)
    }
    missing_names = sorted(expected_names - registered_names)
    b = len(missing_names) == 0
    print_test(
        b,
        f"GATE registers all factory reference lists with supported EM options. Missing: {missing_names}",
    )
    is_ok = b and is_ok

    for name in PhysicsListBuilder.available_g4_reference_physics_lists:
        b = factory.IsReferencePhysList(name)
        print_test(
            b,
            f"GATE reference physics list '{name}' is recognized by G4PhysListFactory",
        )
        is_ok = b and is_ok

    return is_ok


def check_gate_reference_classes_can_be_synthesized():
    is_ok = True

    for name in PhysicsListBuilder.available_g4_reference_physics_lists:
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


def check_special_reference_lists_with_em_options():
    # Shielding sets particle cuts in its constructor and needs the default region.
    run_manager = g4.G4RunManager()
    sim = gate.Simulation()
    sim.g4_verbose_level = 0
    is_ok = True
    for base, spec in reference_physics_list_special_builders.items():
        for suffix in ("", *reference_physics_list_em_extensions):
            name = f"{base}{suffix}"
            try:
                physics_list = (
                    sim.physics_manager.physics_list_builder.create_physics_list(name)
                )
                b = isinstance(physics_list, getattr(g4, spec["base"]))
                em_constructor = reference_physics_list_em_extensions.get(suffix)
                if em_constructor:
                    b = (
                        isinstance(
                            physics_list.GetPhysics(0), getattr(g4, em_constructor)
                        )
                        and b
                    )
                if spec.get("ctor_args", (None, None, False))[2]:
                    b = physics_list.GetPhysics("LightIonQMD") is not None and b
                if spec.get("add_thermal_neutrons"):
                    b = physics_list.GetPhysics("ThermalNeutrons") is not None and b
                print_test(b, f"GATE constructs '{name}' with the requested physics")
                is_ok = b and is_ok
            except Exception as e:
                print_test(False, f"GATE failed to construct '{name}': {e}")
                is_ok = False
    del run_manager
    return is_ok


if __name__ == "__main__":
    factory = g4.G4PhysListFactory()

    is_ok = True
    is_ok = check_pybind_reference_classes_against_factory(factory) and is_ok
    is_ok = check_gate_reference_registry_against_factory(factory) and is_ok
    is_ok = check_gate_reference_classes_can_be_synthesized() and is_ok

    is_ok = check_special_reference_lists_with_em_options() and is_ok

    test_ok(is_ok)
