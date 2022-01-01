import itk
import numpy as np
import os
import gam_gate as gam
import matplotlib.pyplot as plt
import colored
from box import Box
import scipy
from scipy import optimize
from scipy import stats
import gatetools.phsp as phsp


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
    return b


def assert_stats(stat1, stat2, tolerance=0, is_ok=True):
    if stat2.counts.event_count != 0:
        event_d = stat1.counts.event_count / stat2.counts.event_count * 100 - 100
    else:
        event_d = 100
    if stat2.counts.track_count != 0:
        track_d = stat1.counts.track_count / stat2.counts.track_count * 100 - 100
    else:
        track_d = 100
    if stat2.counts.step_count != 0:
        step_d = stat1.counts.step_count / stat2.counts.step_count * 100 - 100
    else:
        step_d = 100
    if stat2.pps != 0:
        pps_d = stat1.pps / stat2.pps * 100 - 100
    else:
        pps_d = 100

    if stat2.tps != 0:
        tps_d = stat1.tps / stat2.tps * 100 - 100
    else:
        tps_d = 100

    if stat2.sps != 0:
        sps_d = stat1.sps / stat2.sps * 100 - 100
    else:
        sps_d = 100

    b = stat1.counts.run_count == stat2.counts.run_count
    is_ok = b and is_ok
    print_test(b, f'Runs:         {stat1.counts.run_count} {stat2.counts.run_count} ')

    b = abs(event_d) <= tolerance * 100
    is_ok = b and is_ok
    print_test(b, f'Events:       {stat1.counts.event_count} {stat2.counts.event_count} : {event_d:+.2f} %')

    b = abs(track_d) <= tolerance * 100
    is_ok = b and is_ok
    print_test(b, f'Tracks:       {stat1.counts.track_count} {stat2.counts.track_count} : {track_d:+.2f} %')

    b = abs(step_d) <= tolerance * 100
    is_ok = b and is_ok
    print_test(b, f'Steps:        {stat1.counts.step_count} {stat2.counts.step_count} : {step_d:+.2f} %')

    print_test(True, f'PPS:          {stat1.pps:.1f} {stat2.pps:.1f} : {pps_d:+.1f}% ')
    print_test(True, f'TPS:          {stat1.tps:.1f} {stat2.tps:.1f} : {tps_d:+.1f}% ')
    print_test(True, f'SPS:          {stat1.sps:.1f} {stat2.sps:.1f} : {sps_d:+.1f}% ')

    # particles types (Track)
    if stat1.user_info.track_types_flag and stat2.user_info.track_types_flag:
        for item in stat1.counts.track_types:
            v1 = stat1.counts.track_types[item]
            if item in stat2.counts.track_types:
                v2 = stat2.counts.track_types[item]
            else:
                print_test(b, f'Track {item:8}{v1} 0')
                continue
            v_d = float(v1) / float(v2) * 100 - 100
            # b = abs(v_d) <= tolerance * 100
            # is_ok = b and is_ok
            print_test(b, f'Track {item:8}{v1} {v2} : {v_d:+.1f}%')
        for item in stat2.counts.track_types:
            v2 = stat2.counts.track_types[item]
            if item not in stat1.counts.track_types:
                print_test(b, f'Track {item:8}0 {v2}')

    # consistency check
    if stat1.user_info.track_types_flag:
        n = 0
        for t in stat1.counts.track_types.values():
            n += t
        b = (n == stat1.counts.track_count)
        print_test(b, f'Tracks      : {stat1.counts.track_types}')
        if 'track_types' in stat2.counts:
            print_test(b, f'Tracks (ref): {stat2.counts.track_types}')
        print_test(b, f'Tracks vs track_types : {stat1.counts.track_count} {n}')
        is_ok = b and is_ok

    return is_ok


def plot_img_z(ax, img, label):
    # get data in np (warning Z and X inverted in np)
    data = itk.GetArrayViewFromImage(img)
    y = np.sum(data, 2)
    y = np.sum(y, 1)
    x = np.arange(len(y)) * img.GetSpacing()[2]
    ax.plot(x, y, label=label)
    ax.legend()


def assert_images(filename1, filename2, stats, tolerance=0, ignore_value=0):
    # read image and info (size, spacing etc)
    filename1 = gam.check_filename_type(filename1)
    filename2 = gam.check_filename_type(filename2)
    img1 = itk.imread(filename1)
    img2 = itk.imread(filename2)
    info1 = gam.get_image_info(img1)
    info2 = gam.get_image_info(img2)

    # check img info
    is_ok = True
    is_ok = is_ok and np.all(info1.size == info2.size)
    is_ok = is_ok and np.all(info1.spacing == info2.spacing)
    is_ok = is_ok and np.all(info1.origin == info2.origin)
    is_ok = is_ok and np.all(info1.dir == info2.dir)

    # check pixels contents, global stats
    data1 = itk.GetArrayViewFromImage(img1).ravel()
    data2 = itk.GetArrayViewFromImage(img2).ravel()

    print(f'Image1: {info1.size} {info1.spacing} {info1.origin} sum={np.sum(data1):.2f} {filename1}')
    print(f'Image2: {info2.size} {info2.spacing} {info2.origin} sum={np.sum(data2):.2f} {filename2}')

    # dont consider pixels with a value of zero (data2 is the reference)
    d1 = data1[data2 != ignore_value]
    d2 = data2[data2 != ignore_value]

    # normalise by event
    d1 = d1 / stats.counts.event_count
    d2 = d2 / stats.counts.event_count

    # normalize by sum of d1
    s = np.sum(d2)
    d1 = d1 / s
    d2 = d2 / s

    # sum of absolute difference (in %)
    sad = np.fabs(d1 - d2).sum() * 100
    is_ok = is_ok and sad < tolerance
    print_test(is_ok, f'Image diff computed on {len(data2 != 0)}/{len(data2.ravel())} \n'
                      f'SAD (per event/total): {sad:.2f} % '
                      f' (tolerance is {tolerance :.2f} %)')

    # plot
    fig, ax = plt.subplots(ncols=1, nrows=1, figsize=(25, 10))
    plot_img_z(ax, img1, 'img1')
    plot_img_z(ax, img2, 'reference')
    n = filename1.replace('.mhd', '_test.png')
    print('Save image test figure :', n)
    plt.savefig(n)

    return is_ok


def exponential_func(x, a, b):
    return a * np.exp(-b * x)


def fit_exponential_decay(data, start, end):
    bin_heights, bin_borders = np.histogram(np.array(data), bins='auto', density=True)
    bin_widths = np.diff(bin_borders)
    bin_centers = bin_borders[:-1] + bin_widths / 2

    popt, pcov = scipy.optimize.curve_fit(exponential_func, bin_centers, bin_heights)
    xx = np.linspace(start, end, 100)
    yy = exponential_func(xx, *popt)
    hl = np.log(2) / popt[1]

    return hl, xx, yy


def get_new_key_name(key):
    # Correspondence between 1) gate root <-> gam or 2) gate phsp <-> gam
    # the third parameter is a scaling factor
    corres = [['edep', 'TotalEnergyDeposit'],
              ['time', 'GlobalTime', 1e-9],
              ['posX', 'PostPosition_X'],
              ['posY', 'PostPosition_Y'],
              ['posZ', 'PostPosition_Z'],
              ['Ekine', 'KineticEnergy'],
              ['X', 'PostPosition_X'],
              ['Y', 'PostPosition_Y'],
              ['Z', 'PostPosition_Z'],
              ['dX', 'PostDirection_X'],
              ['dY', 'PostDirection_Y'],
              ['dZ', 'PostDirection_Z'],
              ['Weight', 'Weight'],
              ]
    for p in corres:
        if p[0] == key:
            s = 1
            if len(p) > 2:
                s = p[2]
            return p[1], s
    return None, None


def get_keys_correspondence(keys):
    keys1 = []
    keys2 = []
    scalings = []
    for k in keys:
        k2, s2 = gam.get_new_key_name(k)
        if k2:
            keys1.append(k)
            keys2.append(k2)
            scalings.append(s2)
    return keys1, keys2, scalings


def rel_diff(a, b):
    return np.divide(np.fabs(a - b), a, out=np.zeros_like(a), where=a != 0) * 100


def rel_diff_range(a, b):
    r = np.max(a) - np.min(a)
    print(r)
    return np.divide(np.fabs(a - b), r, out=np.zeros_like(a), where=r != 0) * 100


def get_branch(tree, keys, key):
    """
    Return a branch whether it is a numpy or a uproot tree
    """
    try:
        index = keys.index(key)
        return tree[:, index]
    except:
        return tree[key]


"""
Previous trial with Two-sample Kolmogorov-Smirnov test
- works well for small samples size
- but not clear how to set "alpha" (tolerance) for large set like root tree

=> abort.

        Two-sample K–S test
        https://en.wikipedia.org/wiki/Kolmogorov%E2%80%93Smirnov_test
        https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.kstest.html#scipy.stats.kstest

    Two-sample Kolmogorov-Smirnov test
    two-sided: The null hypothesis is that the two distributions are identical,
    F(x)=G(x) for all x; the alternative is that they are not identical.       
    If the KS statistic is small or the p-value is high, then we cannot 
    reject the null hypothesis in favor of the alternative.
    
    https://stackoverflow.com/questions/10884668/two-sample-kolmogorov-smirnov-test-in-python-scipy
    
    Results can be interpreted as following:
    - You can either compare the statistic value given by python to the KS-test 
    critical value table according to your sample size. When statistic value is higher 
    than the critical value, the two distributions are different.

    - Or you can compare the p-value to a level of significance a, usually a=0.05 or 0.01 
    (you decide, the lower a is, the more significant). If p-value is lower than a, then it 
    is very probable that the two distributions are different.

"""


def compare_branches(tree1, keys1, tree2, keys2, key1, key2, tol=0.8, scaling=1, ax=False):
    """
        Compare with Wasserstein distance
        Works well, but not easy to set the tolerance value.
    """
    # get branches
    b1 = get_branch(tree1, keys1, key1)
    b2 = get_branch(tree2, keys2, key2) * scaling
    # get ranges
    brange1 = np.max(b1) - np.min(b1)
    brange2 = np.max(b2) - np.min(b2)
    # mean
    m1 = np.mean(b1)
    m2 = np.mean(b2)
    n1 = np.size(b1)
    n2 = np.size(b2)

    # Earth mover distance (Wasserstein)
    wass = stats.wasserstein_distance(b1, b2)
    ok = wass < tol
    oks = 'pass'
    if not ok:
        oks = 'fail'
    s = f'N: {n1:7} vs {n2:7} -> means {m1:6.2f} vs {m2:6.2f} -> ranges: {brange1:6.2f} vs {brange2:6.2f} ' \
        f' -> w:{wass:4.3f} vs {tol:4.3f}  \t {key1:<20} {key2:<20}  -> {oks} '
    print_test(ok, s)
    # figure ?
    if ax:
        nb_bins = 100
        label = f' {key1} $\mu$={m1:.2f}'
        ax.hist(b1, nb_bins, density=True,
                histtype='stepfilled', alpha=0.5, label=label)
        label = f' {key2} $\mu$={m2:.2f}'
        ax.hist(b2, nb_bins, density=True,
                histtype='stepfilled', alpha=0.5, label=label)
        ax.set_ylabel('Counts')
        ax.legend()
    return ok


def compare_trees(tree1, allkeys1, tree2, allkeys2,
                  keys1, keys2, tols, scalings, fig=False):
    if fig:
        nb_fig = len(keys1)
        nrow, ncol = phsp.fig_get_nb_row_col(nb_fig)
        f, ax = plt.subplots(nrow, ncol, figsize=(25, 10))
    is_ok = True
    n = 0
    print('Compare branches with Wasserstein distance')
    for i in range(len(keys1)):
        if fig:
            a = phsp.fig_get_sub_fig(ax, i)
            n += 1
        else:
            a = False
        is_ok = compare_branches(tree1, allkeys1, tree2, allkeys2,
                                 keys1[i], keys2[i], tols[i], scalings[i], a) and is_ok
    if fig:
        phsp.fig_rm_empty_plot(nb_fig, n, ax)
    return is_ok
