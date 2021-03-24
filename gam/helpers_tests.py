import itk
import numpy as np
import os
import gam
import matplotlib.pyplot as plt
import colored
from box import Box


def read_stat_file(filename):
    p = os.path.abspath(filename)
    f = open(p, 'r')
    a = gam.UserInfo('Actor', 'SimulationStatisticsActor', filename)
    stat = gam.SimulationStatisticsActor(a)
    stat.counts = Box()
    read_track = False
    for line in f:
        if 'NumberOfRun' in line:
            stat.counts.run_count = int(line[len('# NumberOfRun    ='):])
        if 'NumberOfEvents' in line:
            stat.counts.event_count = int(line[len('# NumberOfEvents = '):])
        if 'NumberOfTracks' in line:
            stat.counts.track_count = int(line[len('# NumberOfTracks ='):])
        if 'NumberOfSteps' in line:
            stat.counts.step_count = int(line[len('# NumberOfSteps  ='):])
        sec = gam.g4_units('s')
        if 'ElapsedTimeWoInit' in line:
            stat.counts.duration = float(line[len('# ElapsedTimeWoInit     ='):]) * sec
        if read_track:
            w = line.split()
            name = w[1]
            value = w[3]
            stat.counts.track_types[name] = value
        if 'Track types:' in line:
            read_track = True
            stat.user_info.track_types_flag = True
            stat.counts.track_types = {}
    return stat


def print_test(b, s):
    if b:
        print(s)
    else:
        color = gam.color_error
        print(colored.stylize(s, color))


def assert_stats(stat1, stat2, tolerance=0, is_ok=True):
    if stat2.counts.event_count != 0:
        event_d = stat1.counts.event_count / stat2.counts.event_count * 100 - 100
    else:
        event_d = 100
    if stat2.counts.track_count != 0:
        track_d = stat1.counts.track_count / stat2.counts.track_count * 100 - 100
    else:
        track_d = 100
    if stat2.counts.event_count != 0:
        step_d = stat1.counts.event_count / stat2.counts.event_count * 100 - 100
    else:
        step_d = 100
    if stat2.pps != 0:
        pps_d = stat1.pps / stat2.pps * 100 - 100
    else:
        pps_d = 100

    b = stat1.counts.run_count == stat2.counts.run_count
    is_ok = b and is_ok
    print_test(b, f'Runs:   {stat1.counts.run_count} {stat2.counts.run_count} ')

    b = abs(event_d) <= tolerance * 100
    is_ok = b and is_ok
    print_test(b, f'Events: {stat1.counts.event_count} {stat2.counts.event_count} : {event_d:+.2f} %')

    b = abs(track_d) <= tolerance * 100
    is_ok = b and is_ok
    print_test(b, f'Tracks: {stat1.counts.track_count} {stat2.counts.track_count} : {track_d:+.2f} %')

    b = abs(step_d) <= tolerance * 100
    is_ok = b and is_ok
    print_test(b, f'Steps:  {stat1.counts.event_count} {stat2.counts.event_count} : {step_d:+.2f} %')

    print_test(True, f'PPS:    {stat1.pps:.1f} {stat2.pps:.1f} : {pps_d:+.1f}% ')

    # particles types (Track)
    if stat1.user_info.track_types_flag and stat2.user_info.track_types_flag:
        for item in stat1.counts.track_types:
            v1 = stat1.counts.track_types[item]
            if item in stat2.counts.track_types:
                v2 = stat2.counts.track_types[item]
            else:
                print_test(b, f'Track {item}: {v1} 0')
                continue
            v_d = float(v1) / float(v2) * 100 - 100
            # b = abs(v_d) <= tolerance * 100
            # is_ok = b and is_ok
            print_test(b, f'Track {item}: {v1} {v2} : {v_d:+.1f}%')
        for item in stat2.counts.track_types:
            v2 = stat2.counts.track_types[item]
            if item not in stat1.counts.track_types:
                print_test(b, f'Track {item}: 0 {v2}')
    return is_ok


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
    is_ok = True
    is_ok = is_ok and np.all(info1.size == info2.size)
    is_ok = is_ok and np.all(info1.spacing == info2.spacing)
    is_ok = is_ok and np.all(info1.origin == info2.origin)
    is_ok = is_ok and np.all(info1.dir == info2.dir)

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
    is_ok = is_ok and diff < tolerance * 100

    if not plot:
        return is_ok

    fig, ax = plt.subplots(ncols=1, nrows=1, figsize=(25, 10))
    plot_img_z(ax, img1, 'img1')
    plot_img_z(ax, img2, 'reference')
    fig.show()

    return is_ok
