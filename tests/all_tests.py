#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from os import listdir
from os.path import isfile, join

mypath = '.'
onlyfiles = [f for f in listdir(mypath) if isfile(join(mypath, f))]
print(onlyfiles)

for f in onlyfiles:
    if 'WIP' in f:
        continue
    if 'visu' in f:
        continue
    if 'test' not in f:
        continue
    if '.py' not in f:
        continue
    print(f'-' * 50, f)
    # exec(open(f).read())
    os.system('./'+f)
    print(f'-' * 50, f)
