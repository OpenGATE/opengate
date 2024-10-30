#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from opengate.devtools import find_unprocessed_gateobject_classes
from opengate.exception import GateImplementationError
import opengate.tests.utility as utility


if __name__ == "__main__":
    is_ok = True
    exceptions = []

    unprocessed_classes = find_unprocessed_gateobject_classes()
    if len(unprocessed_classes) > 0:
        is_ok = False
        s = "\n".join([f"{i}) {w}" for i, w in enumerate(unprocessed_classes)])
        exceptions.append(
            GateImplementationError(
                f"{len(unprocessed_classes)} GateObjects are not processed upon import: \n{s}"
            )
        )
    else:
        print("All classes inheriting from GateObject are properly processed .")
    utility.test_ok(is_ok, exceptions=exceptions)
