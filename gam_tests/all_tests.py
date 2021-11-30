#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from os import listdir
from os.path import isfile, join
import time
from gam_gate.helpers import *

mypath = 'src/'
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
print(f'-' * 70)

failure = False

for f in files:
    start = time.time()
    print(f'Running: {f:<40}  ', end='')
    cmd = f'./src/{f}'
    log = f'log/{f}.log'
    r = os.system(f'{cmd} > {log}')
    # subprocess.run(cmd, stdout=f, shell=True, check=True)
    if r == 0:
        print(colored.stylize(' OK', color_ok), end='')
    else:
        print(colored.stylize(' FAILED !', color_error), end='')
        failure = True
    end = time.time()
    log = f'log/{f}.log'
    print(f' {log:<45}  {end - start:0.1f} s')

print(not failure)
