#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from opengate.devtools import check_if_class_has_attribute, apply_class_check_to_package
from opengate.base import GateObject
from opengate.exception import GateImplementationError
import opengate.tests.utility as utility

if __name__ == "__main__":
    is_ok = True
    exceptions = []

    # check if all actors implement an __initcpp__ method as they should
    attribute_name = "__initcpp__"
    warnings = apply_class_check_to_package(
        check_if_class_has_attribute,
        package_name="opengate",
        sub_package_name="actors",
        inherits_from="opengate.actors.base.ActorBase",
        func_kwargs={"attribute_name": attribute_name, "attribute_type": "method"},
    )
    if len(warnings):
        is_ok = False
        s = "\n".join([f"{i}) {w}" for i, w in enumerate(warnings)])
        exceptions.append(
            GateImplementationError(
                f"{len(warnings)} GateObjects do not implement a '{attribute_name}' method: \n{s}"
            )
        )

    # test the check function by performing a check that should fail!
    warnings_test = apply_class_check_to_package(
        check_if_class_has_attribute,
        package_name="opengate",
        sub_package_name="actors",
        inherits_from="opengate.actors.base.ActorBase",
        func_kwargs={"attribute_name": attribute_name, "attribute_type": "property"},
    )
    # so there should be warnings!
    if len(warnings_test) == 0:
        is_ok = False
        exceptions.append(
            GateImplementationError(
                "A class check should have issued a warning, but it has not. "
                "The class check looked for actor classes "
                "which do not implement an '__initcpp__ PROPERTY', and indeed "
                "no actor class should really do that. "
            )
        )

    utility.test_ok(is_ok, exceptions=exceptions)
