#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
import uproot

if __name__ == "__main__":

    f = "../output/test077_scatter_order/test077_scatter_order.root"

    file = uproot.open(f)
    branch = file["phsp"]
    print(branch)
