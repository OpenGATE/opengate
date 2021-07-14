#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from os import listdir
from os.path import isfile, join
from gam.helpers import *

mypath = '.'
onlyfiles = [f for f in listdir(mypath) if isfile(join(mypath, f))]

files = []
for f in onlyfiles:
    if 'WIP' in f:
        continue
    if 'visu' in f:
        continue
    if 'test' not in f:
        continue
    if '.py' not in f:
        continue
    if '.log' in f:
        continue
    if 'all_tes' in f:
        continue
    if '_base' in f:
        continue
    files.append(f)

files = sorted(files)

print(f'Running {len(files)} tests')

for f in files:
    print(f'-' * 70)
    print(f'Running: {f}', end='')
    r = os.system('./' + f + f'> log/{f}.log')
    if r == 0:
        print(colored.stylize(' OK', color_ok), end='')
    else:
        print(colored.stylize(' FAILED !', color_error), end='')
    print(f' logfile : log/{f}.log')
