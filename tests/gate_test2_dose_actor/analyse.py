#!/usr/bin/env python3

import gatetools as gt
import gatetools.phsp as phsp
import itk
import click
import sys
import os
import numpy as np
import logging
import matplotlib.pyplot as plt
logger=logging.getLogger(__name__)

# -----------------------------------------------------------------------------
def plot(output_folder, a, filename, axis):
    # 2D : output-gamma.mhd
    f = os.path.join(output_folder, filename)
    logger.info(f'Load {f}')
    img = itk.imread(f)

    # img spacing
    spacing = img.GetSpacing()

    # get data in np
    data = itk.GetArrayViewFromImage(img)

    #y = data[0,0,:]
    y = np.sum(data, axis)
    y = np.sum(y, axis)
    print(y.shape)
    x = np.arange(len(y)) * spacing[2]
    a.plot(x,y, label=output_folder)
    a.legend()

# -----------------------------------------------------------------------------
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])
@click.command(context_settings=CONTEXT_SETTINGS)
@click.argument('output_folders',
                nargs=-1,
                required=True,
                type=click.Path(exists=True, file_okay=False, dir_okay=True))
@gt.add_options(gt.common_options)
def analyse(output_folders, **kwargs):
    '''
    TODO
    '''

    # logger
    gt.logging_conf(**kwargs)

    # plot
    ncols=2
    nrows=1
    fig, ax = plt.subplots(ncols=ncols, nrows=nrows, figsize=(25, 10))

    a = phsp.fig_get_sub_fig(ax,0)
    for o in output_folders:
        plot(o, a, 'output-Edep.mhd', 0)
    a = phsp.fig_get_sub_fig(ax,1)
    for o in output_folders:
        plot(o, a, 'output-Edep.mhd', 1)
    plt.savefig('output.pdf')
    plt.show()


# -----------------------------------------------------------------------------
if __name__ == '__main__':
    analyse()
