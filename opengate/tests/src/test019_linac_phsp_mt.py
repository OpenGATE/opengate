#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import test019_linac_phsp_helpers as test019

if __name__ == "__main__":
    sim = test019.init_test019(3)
    test019.run_test019(sim)
