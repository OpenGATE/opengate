#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import pathlib
import os

pathFile = pathlib.Path(__file__).parent.resolve()

cmd = os.path.join(pathFile, 'test022_half_life.py') + ' 3'
r = os.system(cmd)

sys.exit(r)
