#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Test 136 (2/2): outputs of the actors with quotient images (LET, RE, RBE), with 2 threads, 2 runs (data kept
per run) and a merge of 2 split jobs (issue #993). See test136_voxel_actors_helpers.py.
"""

from test136_voxel_actors_helpers import run_test

if __name__ == "__main__":
    run_test(
        __file__,
        ["LETActor", "REActor", "RBEActor"],
    )
