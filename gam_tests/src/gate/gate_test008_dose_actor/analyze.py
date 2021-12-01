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
def plot(output_folder, a, filename):
    # 2D : output-gamma.mhd
    f = os.path.join(output_folder, filename)
    logger.info(f'Load {f}')
    img = itk.imread(f)

    # img spacing
    spacing = img.GetSpacing()
    print(spacing)

    # get data in np (warning Z and X inverted in np)
    data = itk.GetArrayViewFromImage(img)
    #print('data', data.shape)

    y = np.sum(data, 2)
    #print('y', y.shape)

    y = np.sum(y, 1)
    #print(y.shape)    
    #print(len(y))
    
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
    ncols=1
    nrows=1
    fig, ax = plt.subplots(ncols=ncols, nrows=nrows, figsize=(25, 10))

    a = phsp.fig_get_sub_fig(ax,0)
    for o in output_folders:
        plot(o, a, 'output-Edep.mhd')
    
    plt.savefig('output.pdf')
    plt.show()


# -----------------------------------------------------------------------------
if __name__ == '__main__':
    analyse()
