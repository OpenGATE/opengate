#!/usr/bin/env python3
"""Multithreaded fastY90 emission and activity scheduling regression."""

import opengate_core as g4

from opengate.tests import utility
from opengate.tests.src.source import test115_fasty90

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, output_folder="test115_mt")
    tables = g4.GateFastY90Kernel.GetTables()
    test115_fasty90.check_fixed_count(paths.output / "multi", 3, tables)
    test115_fasty90.check_activity(paths.output / "activity", tables, threads=2)
    utility.test_ok(True)
