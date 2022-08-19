#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gatetools
import gatetools.phsp as phsp
import click
from matplotlib import pyplot as plt
import itk
import numpy as np
import os
import scipy


def compute_positions(phsp, keys, e_min):
    # get speed of light in mm/s
    c = scipy.constants.speed_of_light * 1000  # in mm

    # loop on x ; check energy
    positions = phsp[:, keys.index('PostPosition_X'):keys.index('PostPosition_Z') + 1]
    directions = phsp[:, keys.index('PostDirection_X'):keys.index('PostDirection_Z') + 1]
    # time is nanosecond so 1e9 to get in sec
    times = phsp[:, keys.index('TimeFromBeginOfEvent')] / 1e9
    energies = phsp[:, keys.index('KineticEnergy')]

    # filter according to E ?
    mask = energies > e_min
    positions = positions[mask]
    directions = directions[mask]
    times = times[mask]

    # normalise direction (not needed)
    # print('d', directions)
    # directions = directions / np.linalg.norm(directions, axis=1)
    # print('dn', directions)

    # output
    emissions = np.zeros_like(positions)

    # loop on event
    for pos, dir, t, E, p in zip(positions, directions, times, energies, emissions):
        # distance traveled according to time
        l = t * c
        # consider vector from position to dir
        # (+= is needed to keep initial pointer)
        p += pos + l * -dir

    return emissions


CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.argument('file_inputs', nargs=-1)
@click.option('--output', '-o', default='AUTO', help='output image (mhd)')
@click.option('--output_folder', '-f', default='.', help='output folder, auto image name (mhd)')
@click.option('-n', default='-1', help='Number of samples')
@click.option('--shuffle', '-s', is_flag=True, default=False, help='Shuffle the n samples (slow if file is large)')
def go(file_inputs, n, output, output_folder, shuffle):
    for file_input in file_inputs:
        go_one(file_input, n, output, output_folder, shuffle)


def go_one(file_input, n, output, output_folder, shuffle):
    n = int(float(n))

    # read phsp
    b, extension = os.path.splitext(file_input)
    phsp, keys, m = gatetools.phsp.load(file_input, nmax=n, shuffle=shuffle)
    if n == -1:
        n = m

    print(f'Load {file_input} {n}/{m}')
    print(f'Keys {keys}')

    # retrieve 3D position
    positions = compute_positions(phsp, keys, e_min=0)  # 0.14 for primary only

    # convert p from physical to pixel coordinates
    size = np.array((128, 128, 128)).astype(int)
    spacing = np.array((2, 2, 2))
    offset = -size * spacing / 2.0 + spacing / 2.0
    print(f'Image size, spacing, offset: {size} {spacing} {offset}')
    pix = np.rint((positions - offset) / spacing).astype(int)

    # remove values out of the image fov
    print(f'Number of events:                   {m}')
    print(f'Number of events after E selection: {len(pix)}')
    for i in [0, 1, 2]:
        pix = pix[(pix[:, i] < size[i]) & (pix[:, i] > i)]
    print(f'Number of events in the image FOV:  {len(pix)}')

    # output filename
    if output == 'AUTO':
        full_path = os.path.split(file_input)
        b, extension = os.path.splitext(full_path[1])
        if not output_folder:
            output_folder = '.'
        output = f'{b}.mhd'
        output = os.path.join(output_folder, output)
    print(f'Output file: {output}')

    # create the image
    a = np.zeros(size)
    for x in pix:
        a[x[0], x[1], x[2]] += 1
    img = itk.image_from_array(a)
    itk.imwrite(img, output)


# --------------------------------------------------------------------------
if __name__ == '__main__':
    go()
