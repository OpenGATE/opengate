#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate_core as g4
import opengate as gate
import subprocess
import sys
import textwrap
from unittest.mock import patch

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


def check_registry_alignment_warnings(factory):
    check = PhysicsListBuilder.check_reference_physics_list_registry
    mismatches = check(emit_warning=False)
    b = not mismatches
    print_test(b, f"Registry aligns with Geant4. Differences: {mismatches}")
    is_ok = b

    # A factory advertising exactly the supported options must produce no warning.
    with patch("opengate.physics.g4.G4PhysListFactory") as factory_class:
        advertised = factory_class.return_value
        advertised.AvailablePhysLists.return_value = list(factory.AvailablePhysLists())
        advertised.AvailablePhysListsEM.return_value = [
            "",
            *reference_physics_list_em_extensions,
        ]
        advertised.IsReferencePhysList.side_effect = factory.IsReferencePhysList
        with patch("opengate.physics.warnings.warn") as warn:
            b = check() == {} and not warn.called
            print_test(b, "Aligned registry does not warn")
            is_ok = b and is_ok

        with patch.dict(
            reference_physics_list_em_extensions, {"_FAKE": "MissingPhysicsConstructor"}
        ):
            with patch.object(
                PhysicsListBuilder,
                "available_g4_reference_physics_lists",
                [*PhysicsListBuilder.available_g4_reference_physics_lists, "Shielding"],
            ):
                mismatches = check(emit_warning=False)
                b = (
                    mismatches["GATE EM options unrecognized by Geant4"] == ["_FAKE"]
                    and mismatches["missing C++ bindings"]
                    == ["MissingPhysicsConstructor"]
                    and mismatches["duplicate registry names"] == ["Shielding"]
                )
                print_test(
                    b,
                    "Alignment check detects unknown EM options, missing bindings, and duplicates",
                )
                is_ok = b and is_ok

        # Reproduce the reported omission and introduce upstream API changes.
        names = [
            name
            for name in PhysicsListBuilder.available_g4_reference_physics_lists
            if name != "ShieldingLIQMD_EMZ"
        ] + ["NonexistentPhysicsList"]
        advertised.AvailablePhysLists.return_value.append("NewGeant4List")
        advertised.AvailablePhysListsEM.return_value.append("_NEW")
        with patch.object(
            PhysicsListBuilder, "available_g4_reference_physics_lists", names
        ):
            with patch("opengate.physics.warnings.warn") as warn:
                mismatches = check()
                b = (
                    "ShieldingLIQMD_EMZ" in mismatches["missing registry names"]
                    and "NewGeant4List" in mismatches["missing registry names"]
                    and mismatches["names unrecognized by Geant4"]
                    == ["NonexistentPhysicsList"]
                    and mismatches["Geant4 EM options unsupported by GATE"] == ["_NEW"]
                    and warn.call_count == 1
                    and "ShieldingLIQMD_EMZ" in warn.call_args.args[0]
                )
                print_test(
                    b,
                    "Registry drift warns, including missing special-builder suffixes",
                )
                is_ok = b and is_ok
    return is_ok


def check_builder_diagnostics():
    sim = gate.Simulation()
    builder = sim.physics_manager.physics_list_builder
    # Also verify diagnostics reflect the instantiated registry, not static metadata.
    builder.created_physics_list_classes.pop("ShieldingLIQMD_EMZ")
    with patch("opengate.physics.g4.G4PhysListFactory", side_effect=AssertionError):
        info = builder.dump_info_physics_lists()
        listed = set(info.splitlines()) & set(builder.created_physics_list_classes)
        b = listed == set(builder.created_physics_list_classes)
        b = "ShieldingLIQMD_EMZ" not in info and "_FAKE" not in info and b
        with patch("opengate.physics.fatal", side_effect=ValueError) as fatal:
            try:
                builder.create_physics_list("NonexistentPhysicsList")
            except ValueError:
                message = fatal.call_args.args[0]
                b = (
                    info in message
                    and "Unknown physics list: NonexistentPhysicsList" in message
                    and b
                )
            else:
                b = False
    print_test(
        b, "Diagnostics and unknown-name errors list the Builder's accepted names"
    )
    return b


def check_import_time_warning():
    code = textwrap.dedent(
        """
        import warnings
        import opengate_core as g4
        factory = g4.G4PhysListFactory()

        class ChangedFactory:
            def AvailablePhysLists(self):
                return [*factory.AvailablePhysLists(), "NewGeant4List"]

            def AvailablePhysListsEM(self):
                return factory.AvailablePhysListsEM()

            def IsReferencePhysList(self, name):
                return factory.IsReferencePhysList(name)

        g4.G4PhysListFactory = ChangedFactory
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            import opengate
            import opengate.physics
        registry_warnings = [w for w in caught if "PhysicsListBuilder registry" in str(w.message)]
        assert len(registry_warnings) == 1, registry_warnings
        assert registry_warnings[0].category is RuntimeWarning
        assert "NewGeant4List" in str(registry_warnings[0].message)
    """
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True
    )
    b = result.returncode == 0
    print_test(b, "Registry drift emits a warning during import in a fresh process")
    if not b:
        print(result.stdout, result.stderr)
    return b


if __name__ == "__main__":
    factory = g4.G4PhysListFactory()

    is_ok = True
    is_ok = check_pybind_reference_classes_against_factory(factory) and is_ok
    is_ok = check_gate_reference_registry_against_factory(factory) and is_ok
    is_ok = check_gate_reference_classes_can_be_synthesized() and is_ok
    is_ok = check_registry_alignment_warnings(factory) and is_ok
    is_ok = check_builder_diagnostics() and is_ok
    is_ok = check_import_time_warning() and is_ok
    b = not hasattr(factory, "GetReferencePhysList")
    print_test(b, "Obsolete GetReferencePhysList factory method is not bound")
    is_ok = b and is_ok
    is_ok = check_special_reference_lists_with_em_options() and is_ok

    test_ok(is_ok)
