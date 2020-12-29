import itk
import numpy as np
import os
from box import Box
import gam
import matplotlib.pyplot as plt


def read_stat_file(filename):
    p = os.path.abspath(filename)
    f = open(p, 'r')
    stat2 = gam.SimulationStatisticsActor(filename)
    for line in f:
        if 'NumberOfRun' in line:
            stat2.set_run_count( int(line[len('# NumberOfRun    ='):]))
        if 'NumberOfEvents' in line:
            stat2.set_event_count(int(line[len('# NumberOfEvents = '):]))
        if 'NumberOfTracks' in line:
            stat2.set_track_count(int(line[len('# NumberOfTracks ='):]))
        if 'NumberOfSteps' in line:
            stat2.set_step_count(int(line[len('# NumberOfSteps  ='):]))
        sec = gam.g4_units('s')
        if 'ElapsedTimeWoInit' in line:
            stat2.duration = float(line[len('# ElapsedTimeWoInit     ='):])*sec
    return stat2


def assert_stats(stat1, stat2, tolerance=0):
    # stat2 = read_stat_file(stat_filename2)
    event_d = stat1.event_count() / stat2.event_count() * 100 - 100
    track_d = stat1.track_count() / stat2.track_count() * 100 - 100
    step_d = stat1.step_count() / stat2.step_count() * 100 - 100
    pps_d = stat1.pps / stat2.pps * 100 - 100
    print(f'Runs:   {stat1.run_count()} {stat2.run_count()} ')
    print(f'Events: {stat1.event_count()} {stat2.event_count()} : {event_d:+.2f} %')
    print(f'Tracks: {stat1.track_count()} {stat2.track_count()} : {track_d:+.2f} %')
    print(f'Steps:  {stat1.step_count()} {stat2.step_count()} : {step_d:+.2f} %')
    print(f'PPS:    {stat1.pps:.1f} {stat2.pps:.1f} : {pps_d:+.1f}% ')
    assert stat1.run_count() == stat2.run_count()
    assert abs(event_d) <= tolerance * 100
    assert abs(track_d) <= tolerance * 100


def plot_img_z(ax, img, label):
    # get data in np (warning Z and X inverted in np)
    data = itk.GetArrayViewFromImage(img)
    y = np.sum(data, 2)
    y = np.sum(y, 1)
    x = np.arange(len(y)) * img.GetSpacing()[2]
    ax.plot(x, y, label=label)
    ax.legend()


def assert_images(filename1, filename2, tolerance=0, plot=True):
    # read image and info (size, spacing etc)
    img1 = itk.imread(filename1)
    img2 = itk.imread(filename2)
    info1 = gam.get_img_info(img1)
    info2 = gam.get_img_info(img2)

    # check img info
    print(f'Image1: {info1.size} {info1.spacing} {info1.origin}')
    print(f'Image2: {info2.size} {info2.spacing} {info2.origin}')
    assert np.all(info1.size == info2.size)
    assert np.all(info1.spacing == info2.spacing)
    assert np.all(info1.origin == info2.origin)
    assert np.all(info1.dir == info2.dir)

    # check pixels contents, global stats
    data1 = itk.GetArrayViewFromImage(img1)
    data2 = itk.GetArrayViewFromImage(img2)
    # consider the diff only for pixels diff from zero in the second image
    # relative to the mean of those pixels
    diff = data1 - data2
    n = data2[data2 != 0].sum()
    sdiff = diff[data2 != 0].sum()
    diff = abs(sdiff / n * 100)
    print(f'Image sum abs diff: {sdiff:.2f}/{n:.2f} : {diff:.2f}%, tolerance is {(tolerance * 100):.2f}%')
    assert diff < tolerance * 100

    if not plot:
        return
    fig, ax = plt.subplots(ncols=1, nrows=1, figsize=(25, 10))
    plot_img_z(ax, img1, 'img1')
    plot_img_z(ax, img2, 'img2')
    fig.show()
