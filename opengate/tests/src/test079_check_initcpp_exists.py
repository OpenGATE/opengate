#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from opengate.devtools import check_classes_in_current_package
from opengate.base import GateObject
from opengate.exception import GateImplementationError

if __name__ == "__main__":
    warnings = check_classes_in_current_package(
        "__initcppp__",
        package_name="opengate",
        sub_package_name="actors",
        inherits_from="opengate.actors.base.ActorBase",
    )
    print(warnings)
    if len(warnings):
        raise GateImplementationError(
            "Some GateObjects do not implement a '__initcpp__' method: \n" f"{warnings}"
        )
