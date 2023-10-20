import itk
import numpy as np
import os
import random
import string
import colored
from box import Box, BoxList
import scipy
import pathlib
import uproot
import sys
import matplotlib.pyplot as plt

import gatetools.phsp as phsp

# from .helpers_log import colorlog
from ..utility import g4_units, check_filename_type
from ..exception import fatal, color_error, color_ok
from ..image import get_info_from_image, itk_image_view_from_array
from ..userinfo import UserInfo
from ..actors.miscactors import SimulationStatisticsActor


def test_ok(is_ok=False):
    if is_ok:
        s = "Great, tests are ok."
        s = "\n" + colored.stylize(s, color_ok)
        print(s)
        # sys.exit(0)
    else:
        s = "Error during the tests !"
        s = "\n" + colored.stylize(s, color_error)
        print(s)
        sys.exit(-1)


def read_stat_file(filename):
    p = os.path.abspath(filename)
    f = open(p, "r")
    r = "".join(random.choices(string.ascii_lowercase + string.digits, k=20))
    a = UserInfo("Actor", "SimulationStatisticsActor", r)
    stat = SimulationStatisticsActor(a)
    # stat.counts = Box()
    read_track = False
    for line in f:
        if "NumberOfRun" in line:
            stat.counts.run_count = int(line[len("# NumberOfRun    =") :])
        if "NumberOfEvents" in line:
            stat.counts.event_count = int(line[len("# NumberOfEvents = ") :])
        if "NumberOfTracks" in line:
            stat.counts.track_count = int(line[len("# NumberOfTracks =") :])
        if "NumberOfSteps" in line:
            stat.counts.step_count = int(line[len("# NumberOfSteps  =") :])
        sec = g4_units.s
        if "ElapsedTimeWoInit" in line:
            stat.counts.duration = float(line[len("# ElapsedTimeWoInit     =") :]) * sec
        if read_track:
            w = line.split()
            name = w[1]
            value = w[3]
            stat.counts.track_types[name] = value
        if "Track types:" in line:
            read_track = True
            stat.user_info.track_types_flag = True
            stat.counts.track_types = {}
        if "Date" in line:
            stat.date = line[len("# Date                       =") :]
    return stat


def print_test(b, s):
    if b:
        print(s)
    else:
        color = color_error
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
    print_test(b, f"Runs:         {stat1.counts.run_count} {stat2.counts.run_count} ")

    b = abs(event_d) <= tolerance * 100
    is_ok = b and is_ok
    st = f"(tol = {tolerance * 100:.2f} %)"
    print_test(
        b,
        f"Events:       {stat1.counts.event_count} {stat2.counts.event_count} : {event_d:+.2f} %  {st}",
    )

    b = abs(track_d) <= tolerance * 100
    is_ok = b and is_ok
    print_test(
        b,
        f"Tracks:       {stat1.counts.track_count} {stat2.counts.track_count} : {track_d:+.2f} %  {st}",
    )

    b = abs(step_d) <= tolerance * 100
    is_ok = b and is_ok
    print_test(
        b,
        f"Steps:        {stat1.counts.step_count} {stat2.counts.step_count} : {step_d:+.2f} %  {st}",
    )

    print_test(
        True,
        f"PPS:          {stat1.pps:.1f} {stat2.pps:.1f} : "
        f"{pps_d:+.1f}%    speedup = x{(pps_d + 100) / 100:.1f}",
    )
    print_test(
        True,
        f"TPS:          {stat1.tps:.1f} {stat2.tps:.1f} : "
        f"{tps_d:+.1f}%    speedup = x{(tps_d + 100) / 100:.1f}",
    )
    print_test(
        True,
        f"SPS:          {stat1.sps:.1f} {stat2.sps:.1f} : "
        f"{sps_d:+.1f}%    speedup = x{(sps_d + 100) / 100:.1f}",
    )

    # particles types (Track)
    if stat1.user_info.track_types_flag and stat2.user_info.track_types_flag:
        for item in stat1.counts.track_types:
            v1 = stat1.counts.track_types[item]
            if item in stat2.counts.track_types:
                v2 = stat2.counts.track_types[item]
            else:
                print_test(b, f"Track {item:8}{v1} 0")
                continue
            v_d = float(v1) / float(v2) * 100 - 100
            # b = abs(v_d) <= tolerance * 100
            # is_ok = b and is_ok
            print_test(b, f"Track {item:8}{v1} {v2} : {v_d:+.1f}%")
        for item in stat2.counts.track_types:
            v2 = stat2.counts.track_types[item]
            if item not in stat1.counts.track_types:
                print_test(b, f"Track {item:8}0 {v2}")

    # consistency check
    if stat1.user_info.track_types_flag:
        n = 0
        for t in stat1.counts.track_types.values():
            n += int(t)
        b = n == stat1.counts.track_count
        print_test(b, f"Tracks      : {stat1.counts.track_types}")
        if "track_types" in stat2.counts:
            print_test(b, f"Tracks (ref): {stat2.counts.track_types}")
        print_test(b, f"Tracks vs track_types : {stat1.counts.track_count} {n}")
        is_ok = b and is_ok

    return is_ok


def plot_img_axis(ax, img, label, axis="z"):
    if axis == "y":
        return plot_img_y(ax, img, label)
    if axis == "x":
        return plot_img_x(ax, img, label)
    return plot_img_z(ax, img, label)


def plot_img_z(ax, img, label):
    # get data in np (warning Z and X inverted in np)
    data = itk.GetArrayViewFromImage(img)
    y = np.sum(data, 2)
    y = np.sum(y, 1)
    x = np.arange(len(y)) * img.GetSpacing()[2]
    ax.plot(x, y, label=label)
    ax.legend()


def plot_img_y(ax, img, label):
    # get data in np (warning Z and X inverted in np)
    data = itk.GetArrayViewFromImage(img)
    y = np.sum(data, 2)
    y = np.sum(y, 0)
    x = np.arange(len(y)) * img.GetSpacing()[1]
    ax.plot(x, y, label=label)
    ax.legend()


def plot_img_x(ax, img, label):
    # get data in np (warning Z and X inverted in np)
    data = itk.GetArrayViewFromImage(img)
    y = np.sum(data, 1)
    y = np.sum(y, 0)
    x = np.arange(len(y)) * img.GetSpacing()[0]
    ax.plot(x, y, label=label)
    ax.legend()


def assert_images_properties(info1, info2):
    # check img info
    is_ok = True
    if not np.all(info1.size == info2.size):
        print_test(False, f"Sizes are different {info1.size} vs {info2.size} ")
        is_ok = False
    if not np.allclose(info1.spacing, info2.spacing):
        print_test(False, f"Spacing are different {info1.spacing} vs {info2.spacing} ")
        is_ok = False
    if not np.allclose(info1.origin, info2.origin):
        print_test(False, f"Origin are different {info1.origin} vs {info2.origin} ")
        is_ok = False
    if not np.all(info1.dir == info2.dir):
        print_test(False, f"Directions are different {info1.dir} vs {info2.dir} ")
        is_ok = False
    print_test(is_ok, f"Images with same size/spacing/origin/dir ? {is_ok}")

    print(f"Image1: {info1.size} {info1.spacing} {info1.origin} ")
    print(f"Image2: {info2.size} {info2.spacing} {info2.origin} ")

    return is_ok


def assert_images(
    ref_filename1,
    filename2,
    stats=None,
    tolerance=0,
    ignore_value=0,
    axis="z",
    fig_name=None,
    sum_tolerance=5,
    scaleImageValuesFactor=None,
):
    # read image and info (size, spacing etc)
    ref_filename1 = check_filename_type(ref_filename1)
    filename2 = check_filename_type(filename2)
    img1 = itk.imread(ref_filename1)
    img2 = itk.imread(filename2)
    info1 = get_info_from_image(img1)
    info2 = get_info_from_image(img2)

    is_ok = assert_images_properties(info1, info2)

    # check pixels contents, global stats
    data1 = itk.GetArrayViewFromImage(img1).ravel()
    data2 = itk.GetArrayViewFromImage(img2).ravel()

    if scaleImageValuesFactor:
        data2 *= scaleImageValuesFactor

    s1 = np.sum(data1)
    s2 = np.sum(data2)
    if s1 == 0 and s2 == 0:
        t = 0
    else:
        t = np.fabs((s1 - s2) / s1) * 100
    b = t < sum_tolerance
    print_test(b, f"Img sums {s1} vs {s2} : {t:.2f} %  (tol {sum_tolerance:.2f} %)")
    is_ok = is_ok and b

    print(f"Image1: {info1.size} {info1.spacing} {info1.origin} {ref_filename1}")
    print(f"Image2: {info2.size} {info2.spacing} {info2.origin} {filename2}")

    # do not consider pixels with a value of zero (data2 is the reference)
    d1 = data1[data2 != ignore_value]
    d2 = data2[data2 != ignore_value]

    # normalise by event
    if stats is not None:
        d1 = d1 / stats.counts.event_count
        d2 = d2 / stats.counts.event_count

    # normalize by sum of d1
    s = np.sum(d2)
    d1 = d1 / s
    d2 = d2 / s

    # sum of absolute difference (in %)
    sad = np.fabs(d1 - d2).sum() * 100
    is_ok = is_ok and sad < tolerance
    print_test(
        is_ok,
        f"Image diff computed on {len(data2 != 0)}/{len(data2.ravel())} \n"
        f"SAD (per event/total): {sad:.2f} % "
        f" (tolerance is {tolerance :.2f} %)",
    )

    # plot
    fig, ax = plt.subplots(ncols=1, nrows=1, figsize=(25, 10))
    plot_img_axis(ax, img1, "reference", axis)
    plot_img_axis(ax, img2, "test", axis)
    if fig_name is None:
        n = filename2.replace(".mhd", "_test.png")
    else:
        n = fig_name
    print("Save image test figure :", n)
    plt.savefig(n)

    return is_ok


def plot_hist(ax, data, label, bins=100):
    ax.hist(
        data,
        bins=bins,
        density=True,
        histtype="stepfilled",
        alpha=0.8,
        label=label,
    )
    ax.set_ylabel("Counts")
    ax.legend()


def plot_profile(ax, y, y_spacing=1, label=""):
    x = np.arange(len(y)) * y_spacing
    ax.plot(x, y, label=label)
    ax.legend()


def assert_filtered_imagesprofile1D(
    ref_filter_filename1,
    ref_filename1,
    filename2,
    stats=None,
    tolerance=0,
    ignore_value=0,
    fig_name=None,
    sum_tolerance=5,
    plt_ylim=None,
):
    # read image and info (size, spacing etc)
    ref_filter_filename1 = check_filename_type(ref_filter_filename1)
    ref_filename1 = check_filename_type(ref_filename1)
    filename2 = check_filename_type(filename2)
    filter_img1 = itk.imread(ref_filter_filename1)
    img1 = itk.imread(ref_filename1)
    img2 = itk.imread(filename2)
    info1 = get_info_from_image(img1)
    info2 = get_info_from_image(img2)

    is_ok = assert_images_properties(info1, info2)

    # check pixels contents, global stats

    filter_data = np.squeeze(itk.GetArrayViewFromImage(filter_img1).ravel())
    data1 = np.squeeze(itk.GetArrayViewFromImage(img1).ravel())
    data2 = np.squeeze(itk.GetArrayViewFromImage(img2).ravel())
    flipflag = True
    if flipflag:
        filter_data = np.flip(filter_data)
        data1 = np.flip(data1)
        data2 = np.flip(data2)
    max_ind = np.argmax(filter_data)
    L_filter = range(max_ind)
    d1 = data1[L_filter]
    d2 = data2[L_filter]

    s1 = np.sum(d1)
    s2 = np.sum(d2)
    print(
        f"Evaluate only data from entry up to peak position of reference filter image"
    )
    print(f"Going to evaluate {d1.size} elements out of {data1.size}")
    t = np.fabs((s1 - s2) / s1) * 100
    b = t < sum_tolerance
    print_test(b, f"Img sums {s1} vs {s2} : {t:.2f} %  (tol {sum_tolerance:.2f} %)")

    # do not consider pixels with a value of zero (data2 is the reference)
    # d1 = data1[data2 != ignore_value]
    # d2 = data2[data2 != ignore_value]

    # normalise by event
    if stats is not None:
        d1 = d1 / stats.counts.event_count
        d2 = d2 / stats.counts.event_count

    # normalize by sum of d1
    s = np.sum(d2)
    d1 = d1 / s
    d2 = d2 / s

    # sum of absolute difference (in %)
    sad = np.fabs(d1 - d2).sum() * 100
    is_ok = is_ok and sad < tolerance
    print_test(
        is_ok,
        f"Image diff computed on {len(data2 != 0)}/{len(data2.ravel())} \n"
        f"SAD (per event/total): {sad:.2f} % "
        f" (tolerance is {tolerance :.2f} %)",
    )
    filter_data_norm_au = filter_data / np.amax(filter_data) * np.amax(data1) * 0.7
    # plot
    fig, ax = plt.subplots(ncols=1, nrows=1, figsize=(25, 10))

    plot_profile(ax, filter_data_norm_au, info1.spacing[0], "filter")
    plot_profile(ax, data1, info1.spacing[0], "reference")
    plot_profile(ax, data2, info2.spacing[0], "test")
    ax.plot(max_ind * info1.spacing[0], filter_data_norm_au[max_ind], "o", label="p")

    if plt_ylim:
        ax.set_ylim(plt_ylim)
    # plt.show()

    if fig_name is None:
        n = filename2.replace(".mhd", "_test.png")
    else:
        n = fig_name
    print("Save image test figure :", n)
    plt.savefig(n)

    return is_ok


def exponential_func(x, a, b):
    return a * np.exp(-b * x)


def Gauss(x, A, x0, sigma):
    return A * np.exp(-((x - x0) ** 2) / (2 * sigma**2))


def fit_exponential_decay(data, start, end):
    bin_heights, bin_borders = np.histogram(np.array(data), bins="auto", density=True)
    bin_widths = np.diff(bin_borders)
    bin_centers = bin_borders[:-1] + bin_widths / 2

    popt, pcov = scipy.optimize.curve_fit(exponential_func, bin_centers, bin_heights)
    xx = np.linspace(start, end, 100)
    yy = exponential_func(xx, *popt)
    hl = np.log(2) / popt[1]

    return hl, xx, yy


def get_new_key_name(key):
    # Correspondence between 1) gate root <-> opengate or 2) gate phsp <-> opengate
    # the third parameter is a scaling factor
    # the fourth is tolerance ?
    corres = [
        ["edep", "TotalEnergyDeposit", 1, 0.001],
        ["energy", "TotalEnergyDeposit", 1, 0.001],
        ["Ekine", "KineticEnergy", 1, 0.001],
        ["time", "GlobalTime", 1e-9, 0.02],
        ["posX", "PostPosition_X", 1, 1],
        ["posY", "PostPosition_Y", 1, 0.9],
        ["posZ", "PostPosition_Z", 1, 0.7],
        ["globalPosX", "PostPosition_X", 1, 0.7],
        ["globalPosY", "PostPosition_Y", 1, 0.7],
        ["globalPosZ", "PostPosition_Z", 1, 0.7],
        ["X", "PrePosition_X", 1, 0.8],
        ["Y", "PrePosition_Y", 1, 0.8],
        ["Z", "PrePosition_Z", 1, 0.8],
        ["dX", "PreDirection_X", 1, 0.01],
        ["dY", "PreDirection_Y", 1, 0.01],
        ["dZ", "PreDirection_Z", 1, 0.01],
        ["Weight", "Weight", 1, 0.01],
        ["trackID", "TrackID", 1, 0.05],
    ]
    for p in corres:
        if p[0] == key:
            return p[1], p[2], p[3]
    return None, None, None


def get_keys_correspondence(keys):
    keys1 = []
    keys2 = []
    scalings = []
    tols = []
    for k in keys:
        k2, s2, tol = get_new_key_name(k)
        if k2:
            keys1.append(k)
            keys2.append(k2)
            scalings.append(s2)
            tols.append(tol)
    return keys1, keys2, scalings, tols


def rel_diff(a, b):
    return np.divide(a - b, a, out=np.zeros_like(a), where=a != 0) * 100


def rel_diff_range(a, b):
    r = np.max(a) - np.min(a)
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

=> abort. REPLACE BY WASSERSTEIN DISTANCE

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


def compare_branches(
    tree1,
    keys1,
    tree2,
    keys2,
    key1,
    key2,
    tol=0.8,
    scaling1=1,
    scaling2=1,
    ax=False,
    nb_bins=200,
):
    """
    Compare with Wasserstein distance
    Works well, but not easy to set the tolerance value.
    """
    # get branches
    b1 = get_branch(tree1, keys1, key1) * scaling1
    b2 = get_branch(tree2, keys2, key2) * scaling2
    is_ok = compare_branches_values(b1, b2, key1, key2, tol, ax, nb_bins)
    return is_ok


def compare_branches_values(b1, b2, key1, key2, tol=0.8, ax=False, nb_bins=200):
    """
    Compare with Wasserstein distance
    Works well, but not easy to set the tolerance value.
    """

    # get ranges
    brange1 = np.max(b1) - np.min(b1)
    brange2 = np.max(b2) - np.min(b2)
    # mean
    m1 = np.mean(b1)
    m2 = np.mean(b2)
    n1 = np.size(b1)
    n2 = np.size(b2)
    # sum
    sum1 = np.sum(b1)
    sum2 = np.sum(b2)

    # Earth mover distance (Wasserstein)
    wass = scipy.stats.wasserstein_distance(b1, b2)
    ok = wass < tol
    oks = "pass"
    if not ok:
        oks = "fail"
    s = (
        f"N: {n1:7} vs {n2:7} -> means {m1:6.2f} vs {m2:6.2f} -> sums {sum1:6.2f} vs {sum2:6.2f}  -> ranges: {brange1:6.2f} vs {brange2:6.2f} "
        f" -> w:{wass:4.3f} vs {tol:4.3f}  \t {key1:<20} {key2:<20}  -> {oks} (tol {tol})"
    )
    print_test(ok, s)
    # figure ?
    if ax:
        nb_bins = nb_bins
        label = f" {key1} $\mu$={m1:.2f}"
        ax.hist(
            b1, nb_bins, density=True, histtype="stepfilled", alpha=0.5, label=label
        )
        label = f" {key2} $\mu$={m2:.2f}"
        ax.hist(
            b2, nb_bins, density=True, histtype="stepfilled", alpha=0.5, label=label
        )
        ax.set_ylabel("Counts")
        ax.legend()
    return ok


def compare_trees(
    tree1,
    allkeys1,
    tree2,
    allkeys2,
    keys1,
    keys2,
    tols,
    scalings1,
    scalings2,
    fig=False,
    nb_bins=200,
):
    if fig:
        nb_fig = len(keys1)
        nrow, ncol = phsp.fig_get_nb_row_col(nb_fig)
        f, ax = plt.subplots(nrow, ncol, figsize=(25, 10))
    is_ok = True
    n = 0
    print("Compare branches with Wasserstein distance")
    for i in range(len(keys1)):
        if fig:
            a = phsp.fig_get_sub_fig(ax, i)
            n += 1
        else:
            a = False
        ia = compare_branches(
            tree1,
            allkeys1,
            tree2,
            allkeys2,
            keys1[i],
            keys2[i],
            tols[i],
            scalings1[i],
            scalings2[i],
            a,
            nb_bins=nb_bins,
        )
        is_ok = ia and is_ok
    if fig:
        phsp.fig_rm_empty_plot(nb_fig, n, ax)
    return is_ok


def get_default_test_paths(f, gate_folder=None, output_folder=None):
    p = Box()
    p.current = pathlib.Path(f).parent.resolve()
    # data
    p.data = p.current / ".." / "data"
    # gate
    if gate_folder:
        p.gate = p.current / ".." / "data" / "gate" / gate_folder
        p.gate_output = p.gate / "output"
        p.gate_data = p.gate / "data"
    # output
    p.output = p.current / ".." / "output"
    if output_folder is not None:
        p.output = p.output / output_folder
        if not pathlib.Path.is_dir(p.output):
            pathlib.Path.mkdir(p.output)
    # output ref
    p.output_ref = p.current / ".." / "data" / "output_ref"
    if output_folder is not None:
        p.output_ref = p.output_ref / output_folder
        if not pathlib.Path.is_dir(p.output_ref):
            pathlib.Path.mkdir(p.output_ref)
    return p


def compare_root2(root1, root2, branch1, branch2, keys, img_filename, n_tol=3):
    if not os.path.isfile(root1):
        fatal(f"Cannot open root file '{root1}'")
    hits1 = uproot.open(root1)[branch1]
    hits1_n = hits1.num_entries
    hits1 = hits1.arrays(library="numpy")

    if not os.path.isfile(root2):
        fatal(f"Cannot open root file '{root2}'")
    hits2 = uproot.open(root2)[branch2]
    hits2_n = hits2.num_entries
    hits2 = hits2.arrays(library="numpy")

    print(f"Reference tree: {os.path.basename(root1)} n={hits1_n}")
    print(f"Current tree:   {os.path.basename(root2)} n={hits2_n}")
    diff = rel_diff(float(hits1_n), float(hits2_n))
    is_ok = print_test(
        np.fabs(diff) < n_tol,
        f"Difference: {hits1_n} {hits2_n} {diff:.2f}% (tol = {n_tol:.2f})",
    )
    print(f"Reference tree: {hits1.keys()}")
    print(f"Current tree:   {hits2.keys()}")

    keys = BoxList(keys)
    keys1 = [k.k1 for k in keys]
    keys2 = [k.k2 for k in keys]
    scalings = [k.scaling for k in keys]
    tols = [k.tol for k in keys]
    is_ok = (
        compare_trees(
            hits1,
            list(hits1.keys()),
            hits2,
            list(hits2.keys()),
            keys1,
            keys2,
            tols,
            [1] * len(scalings),
            scalings,
            True,
        )
        and is_ok
    )

    # figure
    plt.suptitle(
        f"Values: ref {os.path.basename(root1)} {os.path.basename(root2)} "
        f"-> {hits1_n} vs {hits2_n}"
    )
    plt.savefig(img_filename)
    print(f"Figure in {img_filename}")

    return is_ok


def compare_root(root1, root2, branch1, branch2, checked_keys, img):
    hits1 = uproot.open(root1)[branch1]
    hits1_n = hits1.num_entries
    hits1 = hits1.arrays(library="numpy")

    hits2 = uproot.open(root2)[branch2]
    hits2_n = hits2.num_entries
    hits2 = hits2.arrays(library="numpy")

    print(f"Reference tree: {os.path.basename(root1)} n={hits1_n}")
    print(f"Current tree:   {os.path.basename(root2)} n={hits2_n}")
    diff = rel_diff(float(hits1_n), float(hits2_n))
    is_ok = print_test(
        np.fabs(diff) < 6, f"Difference: {hits1_n} {hits2_n} {diff:.2f}%"
    )
    print(f"Reference tree: {hits1.keys()}")
    print(f"Current tree:   {hits2.keys()}")

    keys1, keys2, scalings, tols = get_keys_correspondence(checked_keys)
    is_ok = (
        compare_trees(
            hits1,
            list(hits1.keys()),
            hits2,
            list(hits2.keys()),
            keys1,
            keys2,
            tols,
            [1] * len(scalings),
            scalings,
            True,
        )
        and is_ok
    )

    # figure
    plt.suptitle(
        f"Values: ref {os.path.basename(root1)} {os.path.basename(root2)} "
        f"-> {hits1_n} vs {hits2_n}"
    )
    plt.savefig(img)
    print(f"Figure in {img}")

    return is_ok


def compare_root3(
    root1,
    root2,
    branch1,
    branch2,
    keys1,
    keys2,
    tols,
    scalings1,
    scalings2,
    img,
    hits_tol=6,
    nb_bins=200,
):
    hits1 = uproot.open(root1)[branch1]
    hits1_n = hits1.num_entries
    hits1 = hits1.arrays(library="numpy")

    hits2 = uproot.open(root2)[branch2]
    hits2_n = hits2.num_entries
    hits2 = hits2.arrays(library="numpy")

    print(f"Reference tree: {os.path.basename(root1)} n={hits1_n}")
    print(f"Current tree:   {os.path.basename(root2)} n={hits2_n}")
    diff = rel_diff(float(hits1_n), float(hits2_n))
    b = np.fabs(diff) < hits_tol
    is_ok = print_test(b, f"Difference: {hits1_n} {hits2_n} {diff:.2f}%")
    print(f"Reference tree: {hits1.keys()}")
    print(f"Current tree:   {hits2.keys()}")

    if scalings1 is None:
        scalings1 = [1] * len(keys1)
    if scalings2 is None:
        scalings2 = [1] * len(keys2)

    # keys1, keys2, scalings, tols = get_keys_correspondence(checked_keys)
    is_ok = (
        compare_trees(
            hits1,
            list(hits1.keys()),
            hits2,
            list(hits2.keys()),
            keys1,
            keys2,
            tols,
            scalings1,
            scalings2,
            True,
            nb_bins=nb_bins,
        )
        and is_ok
    )

    # figure
    plt.suptitle(
        f"Values: ref {os.path.basename(root1)} {os.path.basename(root2)} "
        f"-> {hits1_n} vs {hits2_n}"
    )
    plt.savefig(img)
    print(f"Figure in {img}")

    return is_ok


def open_root_as_np(root_file, tree_name):
    a = uproot.open(root_file)[tree_name]
    n = a.num_entries
    a = a.arrays(library="numpy")
    return a, n


# https://stackoverflow.com/questions/4527942/comparing-two-dictionaries-and-checking-how-many-key-value-pairs-are-equal
def dict_compare(d1, d2):
    d1_keys = set(d1.keys())
    d2_keys = set(d2.keys())
    shared_keys = d1_keys.intersection(d2_keys)
    added = d1_keys - d2_keys
    removed = d2_keys - d1_keys
    modified = {o: (d1[o], d2[o]) for o in shared_keys if d1[o] != d2[o]}
    same = set(o for o in shared_keys if d1[o] == d2[o])
    return added, removed, modified, same


# Edit by Andreas and Martina
def write_gauss_param_to_file(
    outputdir, planePositionsV, saveFig=False, fNamePrefix="plane", fNameSuffix="a.mhd"
):
    # create output dir, if it doesn't exist
    if not os.path.isdir(outputdir):
        os.mkdir(outputdir)

    print("fNameSuffix", fNameSuffix)
    print("write mu and sigma file to dir: ")
    print(outputdir)

    # Extract gauss param along the two dim of each plane
    sigma_values = []
    mu_values = []
    for i in planePositionsV:
        filename = fNamePrefix + str(i) + fNameSuffix
        filepath = outputdir / filename

        # Get data from file
        data, spacing, shape = read_mhd(filepath)

        # Figure output is saved only if fig names are provided
        fig_name = None
        if saveFig:
            fig_name = str(outputdir) + "/Plane_" + str(i) + fNameSuffix + "_profile"

        # Get relevant gauss param
        sigma_x, mu_x, sigma_y, mu_y = get_gauss_param_xy(
            data, spacing, shape, filepath=fig_name, saveFig=saveFig
        )
        sigma_values.append([i, sigma_x, sigma_y])
        mu_values.append([i, mu_x, mu_y])

    np.savetxt(
        outputdir / "sigma_values.txt",
        sigma_values,
        header="Plane_nr sigma_x sigma_y",
        comments="",
    )
    np.savetxt(
        outputdir / "mu_values.txt", mu_values, header="Plane_nr mu_x mu_y", comments=""
    )

    return sigma_values, mu_values


def get_gauss_param_xy(data, spacing, shape, filepath=None, saveFig=False):
    # Parameters along x
    parameters_x, img_x, _ = extract_gauss_param_1D(
        data, shape[2], spacing[0], axis=1, createFig=saveFig
    )
    sigma_x = parameters_x[2]
    mu_x = parameters_x[1]

    # Parameters along y
    parameters_y, img_y, _ = extract_gauss_param_1D(
        data, shape[1], spacing[1], axis=2, createFig=saveFig
    )
    sigma_y = parameters_y[2]
    mu_y = parameters_y[1]

    # Save plots
    if filepath is not None:
        img_x.savefig(filepath + "_x.png")
        img_y.savefig(filepath + "_y.png")
        plt.close(img_x)
        plt.close(img_y)

    return sigma_x, mu_x, sigma_y, mu_y


def extract_gauss_param_1D(data, length, spacing, axis=1, createFig=False):
    poseVec = create_position_vector(length, spacing)
    dose = np.squeeze(np.sum(data, axis=axis))  # integrate dose along axis
    parameters, fit = gaussian_fit(poseVec, dose)

    fig = None
    if createFig:
        fig = plot_gauss_fit(poseVec, dose, fit, show=False)

    return parameters, fig, max(fit)


def plot_gauss_fit(positionVec, dose, fit, show=False):
    fig, a = plt.subplots()
    a.plot(positionVec, dose, "o", label="data")
    a.plot(positionVec, fit, "-", label="fit")
    a.set_xlabel("Depth [mm]")
    a.set_ylabel("Dose")
    if show:
        plt.show()

    return fig


def create_position_vector(length, spacing, centered=True):
    # cretae position vector, with origin in the image plane's center
    width = length * spacing
    if centered:
        positionVec = np.arange(0, width, spacing) - width / 2 + spacing / 2
    else:
        positionVec = np.arange(0, width, spacing)

    return positionVec


def Gauss(x, A, x0, sigma):
    return A * np.exp(-((x - x0) ** 2) / (2 * sigma**2))


def gaussian_fit(positionVec, dose):
    # Fit data with Gaussian func
    mean = sum(positionVec * dose) / sum(dose)
    sigma = np.sqrt(sum(dose * (positionVec - mean) ** 2) / sum(dose))
    parameters, covariance = scipy.optimize.curve_fit(
        Gauss, positionVec, dose, p0=[max(dose), mean, sigma]
    )
    fit = Gauss(positionVec, parameters[0], parameters[1], parameters[2])

    return parameters, fit


def read_mhd(filename):
    img = itk.imread(str(filename))
    data = itk.GetArrayViewFromImage(img)
    spacing = img.GetSpacing()
    shape = data.shape
    return data, spacing, shape


def plot2D(twodarray, label, show=False):
    fig = plt.figure(figsize=(20, 20))
    ax = fig.add_subplot(111)
    ax.set_title(label)
    plt.imshow(twodarray)
    ax.set_aspect("equal")
    plt.colorbar(orientation="vertical")
    if show:
        plt.show()
    return fig


def create_2D_Edep_colorMap(filepath, show=False, axis="z"):
    img = itk.imread(str(filepath))
    data = itk.GetArrayViewFromImage(img)

    fig = plt.figure(figsize=(20, 20))
    ax = fig.add_subplot(111)
    ax.set_title("colorMap")
    if axis == "z":
        plt.imshow(data[0, :, :])
    elif axis == "x":
        plt.imshow(data[:, :, 0])
    else:
        plt.imshow(data[:, 0, :])
    ax.set_aspect("equal")
    plt.colorbar(orientation="vertical")
    if show:
        plt.show()

    return fig


def compareGaussParamFromFile(sigma, ref, rel_tol=0, abs_tol=0, verb=False):
    if rel_tol == 0 and abs_tol == 0:
        print("\033[91m Please provide non-zero tolerance\033[0m")

    with open(sigma, "r") as c1:
        lines1 = np.asarray(c1.readlines()[1:])

    with open(ref, "r") as c2:
        lines_ref = np.asarray(c2.readlines()[1:])

    is_ok = True

    for l, l_r in np.stack((lines1, lines_ref), axis=-1):
        sig_x = float(l.split(" ")[1])
        sig_y = float(l.split(" ")[2])
        plane = float(l.split(" ")[0])

        sig_x_r = float(l_r.split(" ")[1])
        sig_y_r = float(l_r.split(" ")[2])

        diff_x = abs(sig_x - sig_x_r)
        diff_y = abs(sig_y - sig_y_r)

        reldiff_x = (abs(sig_x - sig_x_r) / sig_x_r) * 100
        reldiff_y = (abs(sig_y - sig_y_r) / sig_y_r) * 100

        if verb:
            print(
                "Plane {0}: value x is {1}mm, value x ref is {2}mm ".format(
                    plane, round(sig_x, 2), round(sig_x_r, 2)
                )
            )
            print(
                "Plane {0}: value y is {1}mm, value y ref is {2}mm ".format(
                    plane, round(sig_y, 2), round(sig_y_r, 2)
                )
            )

        if diff_x > abs_tol and reldiff_x > rel_tol:
            print(
                "\033[91m Plane {0}:  rel difference along x is {1}%, threshold is {2}% \033[0m".format(
                    plane, round(reldiff_x, 2), round(rel_tol, 2)
                )
            )
            print(
                "\033[91m Plane {0}:  abs difference along x is {1}mm, threshold is {2}mm \033[0m".format(
                    plane, round(diff_x, 2), round(abs_tol, 2)
                )
            )
            is_ok = False
        else:
            print("Plane " + str(plane) + " along x is ok")

        if diff_y > abs_tol and reldiff_y > rel_tol:
            print(
                "\033[91m Plane {0}:  rel difference along y is {1}%, threshold is {2}% \033[0m".format(
                    plane, round(reldiff_y, 2), round(rel_tol, 2)
                )
            )
            print(
                "\033[91m Plane {0}:  abs difference along y is {1}mm, threshold is {2}mm \033[0m".format(
                    plane, round(diff_y, 2), round(abs_tol, 2)
                )
            )
            is_ok = False
        else:
            print("Plane " + str(plane) + " along y is ok")

    if is_ok:
        print("differences below threshold")
    else:
        print("\033[91m differences NOT OK \033[0m")

    return is_ok


def compareGaussParamArrays(paramTestV, paramRefV, rel_tol=0, abs_tol=0, verb=False):
    if rel_tol == 0 and abs_tol == 0:
        print("\033[91m Please provide non-zero tolerance\033[0m")

    is_ok = True

    for l in np.column_stack((paramTestV, paramRefV)):
        plane = l[0]
        pTest_x = l[1]
        pTest_y = l[2]
        pRef_x = l[4]
        pRef_y = l[5]

        diff_x = abs(pTest_x - pRef_x)
        diff_y = abs(pTest_y - pRef_y)

        reldiff_x = (abs(pTest_x - pRef_x) / pRef_x) * 100
        reldiff_y = (abs(pTest_y - pRef_y) / pRef_y) * 100

        if verb:
            print(
                "Plane {0}: value x is {1}mm, value x ref is {2}mm ".format(
                    plane, round(pTest_x, 2), round(pRef_x, 2)
                )
            )
            print(
                "Plane {0}: value y is {1}mm, value y ref is {2}mm ".format(
                    plane, round(pTest_y, 2), round(pRef_y, 2)
                )
            )

        if diff_x > abs_tol and reldiff_x > rel_tol:
            print(
                "\033[91m Plane {0}:  rel difference along x is {1}%, threshold is {2}% \033[0m".format(
                    plane, round(reldiff_x, 2), round(rel_tol, 2)
                )
            )
            print(
                "\033[91m Plane {0}:  abs difference along x is {1}mm, threshold is {2}mm \033[0m".format(
                    plane, round(diff_x, 2), round(abs_tol, 2)
                )
            )
            is_ok = False
        else:
            print("Plane " + str(plane) + " along x is ok")

        if diff_y > abs_tol and reldiff_y > rel_tol:
            print(
                "\033[91m Plane {0}:  rel difference along y is {1}%, threshold is {2}% \033[0m".format(
                    plane, round(reldiff_y, 2), round(rel_tol, 2)
                )
            )
            print(
                "\033[91m Plane {0}:  abs difference along y is {1}mm, threshold is {2}mm \033[0m".format(
                    plane, round(diff_y, 2), round(abs_tol, 2)
                )
            )
            is_ok = False
        else:
            print("Plane " + str(plane) + " along y is ok")

    if is_ok:
        print("differences below threshold")
    else:
        print("\033[91m differences NOT OK \033[0m")

    return is_ok


def test_weights(expected_ratio, mhd_1, mhd_2, thresh=0.1):
    img1 = itk.imread(str(mhd_1))
    img2 = itk.imread(str(mhd_2))
    data1 = itk.GetArrayViewFromImage(img1).ravel()
    data2 = itk.GetArrayViewFromImage(img2).ravel()

    sum1 = np.sum(data1)
    sum2 = np.sum(data2)
    ratio = sum2 / sum1

    print("\nSum energy dep for phantom 1: ", sum1)
    print("MSum energy dep for phantom 2: ", sum2)
    print("Ratio is: ", ratio)
    print("Expected ratio is: ", expected_ratio)

    is_ok = False
    if abs(ratio - expected_ratio) < thresh:
        is_ok = True
    else:
        print("\033[91m Ratio not as expected \033[0m")

    return is_ok


def test_tps_spot_size_positions(data, ref, spacing, thresh=0.1, abs_tol=0.3):
    if not np.array_equal(data.size, ref.size):
        print("Images do not have the same size")
        return False
    ok = True
    # beam along x
    size = data.shape
    # get gaussian fit of Edep only around the i-th spot
    param_y_out, _, _ = extract_gauss_param_1D(data, size[1], spacing[1], axis=0)
    param_y_ref, _, _ = extract_gauss_param_1D(ref, size[1], spacing[1], axis=0)

    param_z_out, _, _ = extract_gauss_param_1D(data, size[0], spacing[2], axis=1)
    param_z_ref, _, _ = extract_gauss_param_1D(ref, size[0], spacing[2], axis=1)

    # check positions
    print("Check position of the spot")
    print(f"   opengate: ({param_y_out[1]:.2f},{param_z_out[1]:.2f})")
    print(f"   gate:     ({param_y_ref[1]:.2f},{param_z_ref[1]:.2f})")

    diffmY = param_y_out[1] - param_y_ref[1]  # / param_y_ref[1]
    diffmZ = param_z_out[1] - param_z_ref[1]  # / param_z_ref[1]
    mean_diff = np.mean([diffmY, diffmZ])

    if (
        (abs(diffmY) > 2 * abs_tol)
        or (abs(diffmZ) > 2 * abs_tol)
        or (abs(mean_diff) > abs_tol)
    ):
        print(
            f"\033[91m Position error above threshold. DiffX={diffmY:.2f}, diffY={diffmZ:.2f}, threshold is 0.3mm \033[0m"
        )
        ok = False

    # check sizes
    print("Check size of the spot")
    print(f"   opengate: ({param_y_out[2]:.2f},{param_z_out[2]:.2f})")
    print(f"   gate:     ({param_y_ref[2]:.2f},{param_z_ref[2]:.2f})")

    diffsY = (param_y_out[2] - param_y_ref[2]) / param_y_ref[2]
    diffsZ = (param_z_out[2] - param_z_ref[2]) / param_z_ref[2]

    if (diffsY > thresh) or (diffsZ > thresh):
        print("\033[91m Size error above threshold \033[0m")
        ok = False

    return ok


def scale_dose(path, scaling, outpath):
    img_mhd_in = itk.imread(path)
    data = itk.GetArrayViewFromImage(img_mhd_in)
    dose = data * scaling
    spacing = img_mhd_in.GetSpacing()
    img = itk_image_view_from_array(dose)
    img.SetSpacing(spacing)
    itk.imwrite(img, outpath)
    return outpath


def check_dose_grid_geometry(dose_mhd_path, dose_actor):
    img = itk.imread(dose_mhd_path)
    data = itk.GetArrayViewFromImage(img)
    shape = data.shape
    spacing = img.GetSpacing()
    shape_ref = tuple(np.flip(dose_actor.size))
    spacing_ref = dose_actor.spacing

    ok = True
    if shape != shape_ref:
        print(f"{shape=} not the same as {shape_ref=}!")
        ok = False

    if spacing != spacing_ref:
        print(f"{spacing=} not the same as {spacing_ref=}!")
        ok = False

    return ok


def arangeDx(dx, xV, includeUB=False, lb=[], ub=[]):
    if not lb:
        lb = np.amin(xV)
    if not ub:
        ub = np.amax(xV)
    if includeUB:
        x_int = np.arange(lb, ub + dx / 10, dx)
    else:
        x_int = np.arange(lb, ub, dx)
    return x_int


def interpolate1Dprofile(xV, dV, dx=0.01, interpolMethod="cubic"):
    f = scipy.interpolate.interp1d(
        xV, dV, kind=interpolMethod, fill_value="extrapolate"
    )
    xVfine = arangeDx(dx, xV, includeUB=True, lb=np.amin(xV), ub=np.amax(xV))
    dVfine = f(xVfine)
    return xVfine, dVfine


def getRange(xV, dV, percentLevel=0.8):
    dx = 0.01
    xVfine, dVfine = interpolate1Dprofile(xV, dV, dx, "cubic")

    indMaxFine = np.argmax(dVfine)
    indR80 = np.argmax(
        np.logical_and(
            xVfine > xVfine[indMaxFine], dVfine <= percentLevel * dVfine[indMaxFine]
        )
    )
    r80 = xVfine[indR80]
    dAtR80 = dVfine[indR80]

    return (r80, dAtR80)


def get_range_from_image(volume, shape, spacing, axis="y"):
    x1, d1 = get_1D_profile(volume, shape, spacing, axis=axis)
    r, _ = getRange(x1, d1)

    return r


def compareRange(
    volume1,
    volume2,
    shape1,
    shape2,
    spacing1,
    spacing2,
    axis1="y",
    axis2="y",
    thresh=2.0,
):
    ok = True
    x1, d1 = get_1D_profile(volume1, shape1, spacing1, axis=axis1)
    x2, d2 = get_1D_profile(volume2, shape2, spacing2, axis=axis2)

    print("---RANGE80---")
    r1, _ = getRange(x1, d1)
    r2, _ = getRange(x2, d2)
    print(r1)
    print(r2)
    diff = abs(r2 - r1)

    if diff > thresh:
        print(f"\033[91mRange difference is {diff}mm, threshold is {thresh}mm \033[0m")
        ok = False

    return ok


def get_1D_profile(data, shape, spacing, axis="z"):
    if axis == "x":
        d1 = np.sum(np.sum(data, 1), 0)
        x1 = create_position_vector(shape[2], spacing[0], centered=False)

    if axis == "y":
        d1 = np.sum(np.sum(data, 2), 0)
        x1 = create_position_vector(shape[1], spacing[1], centered=False)

    if axis == "z":
        d1 = np.sum(np.sum(data, 2), 1)
        x1 = create_position_vector(shape[0], spacing[2], centered=False)

    return x1, d1


def compare_dose_at_points(
    pointsV,
    dose1,
    dose2,
    shape1,
    shape2,
    spacing1,
    spacing2,
    axis1="z",
    axis2="z",
    rel_tol=0.03,
):
    ok = True
    s1 = 0
    s2 = 0
    x1, doseV1 = get_1D_profile(dose1, shape1, spacing1, axis=axis1)
    x2, doseV2 = get_1D_profile(dose2, shape2, spacing2, axis=axis2)
    # plt.plot(x1, doseV1)
    # plt.plot(x2, doseV2)
    # plt.show()
    for p in pointsV:
        # get dose at the position p [mm]
        cp1 = min(x1, key=lambda x: abs(x - p))
        d1_p = doseV1[np.where(x1 == cp1)]

        cp2 = min(x2, key=lambda x: abs(x - p))
        d2_p = doseV2[np.where(x2 == cp2)]

        s1 += d1_p
        s2 += d2_p

    print(abs(s1 - s2) / s2)

    # print(f"Dose difference at {p} mm is {diff_pc}%")
    if abs(s1 - s2) / s2 > rel_tol:
        print(f"\033[91mDose difference above threshold \033[0m")
        ok = False
    return ok


def assert_img_sum(img1, img2, sum_tolerance=5):
    data1 = itk.GetArrayViewFromImage(img1).ravel()
    data2 = itk.GetArrayViewFromImage(img2).ravel()

    s1 = np.sum(data1)
    s2 = np.sum(data2)
    if s1 == 0 and s2 == 0:
        t = 0
    else:
        t = np.fabs((s1 - s2) / s1) * 100
    b = t < sum_tolerance
    print_test(b, f"Img sums {s1} vs {s2} : {t:.2f} %  (tol {sum_tolerance:.2f} %)")
    return b


def check_diff(value1, value2, tolerance, txt):
    diff = np.fabs(value1 - value2) / value1 * 100
    t = diff < tolerance
    s = f"{txt} {value1:.2f} vs {value2:.2f} -> {diff:.2f}% (tol={tolerance}%)"
    print_test(t, s)
    return t


def check_diff_abs(value1, value2, tolerance, txt):
    diff = np.fabs(value1 - value2)
    t = diff < tolerance
    s = f"{txt} {value1:.2f} vs {value2:.2f} -> {diff:.2f} (tol={tolerance})"
    print_test(t, s)
    return t


def root_compare_param_tree(filename, tree_name, keys):
    p = Box()
    p.root_file = filename
    p.tree_name = tree_name
    p.the_keys = keys
    p.scaling = [1.0] * len(keys)
    p.mins = [None] * len(keys)
    p.maxs = [None] * len(keys)
    return p


def root_compare_param(keys, fig):
    p = Box()
    p.tols = [1.0] * len(keys)
    p.fig = fig
    p.hits_tol = 6
    p.nb_bins = 300
    return p


def root_compare4(p1, p2, param):
    """
    Compare two root trees.

    p1 and p2 contain = the root filename, the tree name, a list of branch names
    (see root_compare_param_tree)
    Also, each branch can be scaled and clip to a min/max range.

    param contains: the tolerance values (for all branches), the fig name,
    the nb of bins of the histograms, the tolerance for the nb of hits
    (see root_compare_param)
    """

    # read reference tree
    hits1 = uproot.open(p1.root_file)[p1.tree_name]
    hits1_n = hits1.num_entries
    hits1 = hits1.arrays(library="numpy")

    # read tree
    hits2 = uproot.open(p2.root_file)[p2.tree_name]
    hits2_n = hits2.num_entries
    hits2 = hits2.arrays(library="numpy")

    print(f"Reference tree: {os.path.basename(p1.root_file)} n={hits1_n}")
    print(f"Current tree:   {os.path.basename(p2.root_file)} n={hits2_n}")
    diff = rel_diff(float(hits2_n), float(hits1_n))
    b = np.fabs(diff) < param.hits_tol
    is_ok = print_test(b, f"Difference: {hits1_n} {hits2_n} {diff:+.2f}%")
    print(f"Reference tree: {hits1.keys()}")
    print(f"Current tree:   {hits2.keys()}")

    # compare the given tree
    p1.tree = hits1
    p2.tree = hits2
    is_ok = compare_trees4(p1, p2, param) and is_ok

    # figure
    plt.suptitle(
        f"Values: ref {os.path.basename(p1.root_file)} {os.path.basename(p2.root_file)} "
        f"-> {hits1_n} vs {hits2_n}"
    )
    plt.savefig(param.fig)
    print(f"Figure in {param.fig}")

    return is_ok


def compare_trees4(p1, p2, param):
    nb_fig = 0
    ax = None
    if param.fig:
        nb_fig = len(p1.the_keys)
        nrow, ncol = phsp.fig_get_nb_row_col(nb_fig)
        f, ax = plt.subplots(nrow, ncol, figsize=(25, 10))
    is_ok = True
    n = 0
    print("Compare branches with Wasserstein distance")
    for i in range(len(p2.the_keys)):
        if param.fig:
            a = phsp.fig_get_sub_fig(ax, i)
            n += 1
        else:
            a = False
        b1 = p1.tree[p1.the_keys[i]] * p1.scaling[i]
        b2 = p2.tree[p2.the_keys[i]] * p2.scaling[i]
        if p1.mins[i] is not None:
            b1 = b1[b1 > p1.mins[i]]
        if p1.maxs[i] is not None:
            b1 = b1[b1 < p1.maxs[i]]
        if p2.mins[i] is not None:
            b2 = b2[b2 > p2.mins[i]]
        if p2.maxs[i] is not None:
            b2 = b2[b2 < p2.maxs[i]]
        is_ok = (
            compare_branches_values(
                b1, b2, p1.the_keys[i], p2.the_keys[i], param.tols[i], a, param.nb_bins
            )
            and is_ok
        )

    if param.fig:
        phsp.fig_rm_empty_plot(nb_fig, n, ax)
    return is_ok


def get_gpu_mode():
    """
    return "auto" except if the test runs with macos and github actions
    On macos and github actions, mps is detected but not usable and lead to errors. So choose "cpu" in such a case
    """
    if "GITHUB_WORKSPACE" in os.environ and sys.platform == "darwin":
        print("Detection of Github actions and MacOS -> Use CPU")
        return "cpu"
    return "auto"
