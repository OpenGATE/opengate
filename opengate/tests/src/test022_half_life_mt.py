#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import pathlib
import os

if __name__ == "__main__":
    pathFile = pathlib.Path(__file__).parent.resolve()

    cmd = "python " + os.path.join(pathFile, "test022_half_life.py") + " 3"
    r = os.system(cmd)

    sys.exit(r)
