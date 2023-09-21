#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate_core as g4
import opengate as gate

if __name__ == "__main__":
    # get the attributes manager
    am = g4.GateDigiAttributeManager.GetInstance()

    # retrieve the list of attributes names
    nlist = am.GetAvailableDigiAttributeNames()

    # print
    print(f"List of all available attributes ({len(nlist)})")
    print(
        f"Types are: 3 (ThreeVector), D (double), S (string), I (int), U (unique volume ID)"
    )
    for a in nlist:
        att = am.GetDigiAttributeByName(a)
        print(att.GetDigiAttributeName(), att.GetDigiAttributeType())

    n = 44
    is_ok = len(nlist) == n

    gate.print_test(is_ok, f"Done for {n} attributes.")

    gate.test_ok(is_ok)
