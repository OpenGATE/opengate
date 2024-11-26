#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from scipy.spatial.transform import Rotation
import opengate as gate
from opengate.tests import utility
import itk
import numpy as np
import matplotlib.pyplot as plt

from opengate.image import get_info_from_image, itk_image_from_array, write_itk_image


def get_1Dimg_data(fpath):
    img1 = itk.imread(fpath)
    info1 = get_info_from_image(img1)
    dx = info1.spacing[0]

    # check pixels contents, global stats

    data1 = np.squeeze(itk.GetArrayViewFromImage(img1).ravel())
    data1 = np.flip(data1)
    xV = np.arange(len(data1)) * info1.spacing[0] + 0.5 * info1.spacing[0]
    return xV, data1, info1


def run_simulation(stopping_or_production: str, x_source=0.0):

    do_debug = False
    paths = utility.get_default_test_paths(
        __file__, "test082_stopping_test1", "test082"
    )
    ref_path = paths.output_ref

    # create the simulation
    sim = gate.Simulation()

    # main options
    sim.g4_verbose = False
    sim.g4_verbose_level = 1
    sim.visu = False
    sim.random_seed = 1234567891
    sim.number_of_threads = 8
    sim.output_dir = paths.output

    numPartSimTest = 4e2 / sim.number_of_threads
    numPartSimRef = 1e5

    # units
    m = gate.g4_units.m
    cm = gate.g4_units.cm
    mm = gate.g4_units.mm
    km = gate.g4_units.km
    MeV = gate.g4_units.MeV
    Bq = gate.g4_units.Bq
    kBq = 1000 * Bq

    #  change world size
    world = sim.world
    world.size = [600 * cm, 500 * cm, 500 * cm]
    # world.material = "Vacuum"

    # waterbox
    phantom = sim.add_volume("Box", "phantom")
    phantom.size = [10 * cm, 10 * cm, 10 * cm]
    phantom.translation = [-5 * cm, 0, 0]
    phantom.material = "G4_WATER"
    phantom.color = [0, 0, 1, 1]

    test_material_name = "G4_WATER"
    phantom_off = sim.add_volume("Box", "phantom_off")
    phantom_off.mother = phantom.name
    phantom_off.size = [100 * mm, 60 * mm, 60 * mm]
    phantom_off.translation = [0 * mm, 0 * mm, 0 * mm]
    phantom_off.material = test_material_name
    phantom_off.color = [0, 0, 1, 1]

    # physics
    sim.physics_manager.physics_list_name = "QGSP_BIC_EMY"

    # default source for tests
    source = sim.add_source("GenericSource", "mysource")
    source.energy.mono = 60 * MeV
    source.particle = "proton"
    source.position.type = "disc"
    source.position.rotation = Rotation.from_euler("y", 90, degrees=True).as_matrix()
    source.position.radius = 4 * mm
    source.position.translation = [x_source, 0, 0]
    source.direction.type = "momentum"
    source.direction.momentum = [-1, 0, 0]
    source.n = numPartSimTest

    size = [100, 1, 1]
    spacing = [1.0 * mm, 60.0 * mm, 60.0 * mm]

    doseActorName_IDD_d = "IDD_d"
    doseIDD = sim.add_actor("DoseActor", doseActorName_IDD_d)
    doseIDD.output_filename = "test082-" + doseActorName_IDD_d + ".mhd"
    doseIDD.attached_to = phantom_off
    doseIDD.size = size
    doseIDD.spacing = spacing
    doseIDD.hit_type = "random"
    doseIDD.dose.active = False

    StoppingActor_depth_name = f"{stopping_or_production}_img"
    StoppingActor_depth = sim.add_actor(
        "ProductionAndStoppingActor", StoppingActor_depth_name
    )
    StoppingActor_depth.output_filename = "test082-" + StoppingActor_depth_name + ".mhd"
    StoppingActor_depth.attached_to = phantom_off
    StoppingActor_depth.size = size
    StoppingActor_depth.spacing = spacing
    StoppingActor_depth.hit_type = "random"
    StoppingActor_depth.method = (
        stopping_or_production  # "stopping" and "production" are allowed values
    )

    # # add dose actor, without e- (to check)
    fe = sim.add_filter("ParticleFilter", "f")
    fe.particle = "proton"
    fe.policy = "accept"
    StoppingActor_depth.filters.append(fe)

    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "stats")
    stats.track_types_flag = True
    # print("Filters: ", sim.filter_manager)
    sim.run(start_new_process=True)
    # print(stats)

    # ----------------------------------------------------------------------------------------------------------------
    x_source = (
        -1
    ) * x_source  # source is pointing in negative direction, therefore the dose actor image actuallypoints in negative direction; however instead we simply change sign in the source position to remain in positive position space for analysis
    idd_x, idd_d, idd_img_info = get_1Dimg_data(str(doseIDD.edep.get_output_path()))

    filename2 = StoppingActor_depth.production_stopping.get_output_path()
    stop_x, stop_v, stop_img_info = get_1Dimg_data(str(filename2))
    debug_level = 0
    if debug_level > 1:
        for x, y in zip(idd_x, idd_d):
            print(f"{x:.2f} {y:.2e}")
        print("=================")
        for x, y in zip(stop_x, stop_v):
            print(f"{x:.2f} {y:.2e}")

        _, ax = plt.subplots(ncols=1, nrows=2, figsize=(15, 15))

        utility.plot_profile(ax[0], idd_x, idd_img_info.spacing[0], "dose")
        plt.show()

    r50, d_r50 = utility.getRange(idd_x, idd_d, percentLevel=0.5)
    print(f"DoseActor: The range 50% of the peak is: {r50:.1f} mm")

    a = np.argmax(stop_v)
    peak_position_prodstop_img = stop_x[a]

    print(f"ProdAndStopActor: Peak position is at {peak_position_prodstop_img:.1f} mm")

    if stopping_or_production == "stopping":
        range_diff = r50 - peak_position_prodstop_img
    else:
        range_diff = x_source - peak_position_prodstop_img
    print(
        f"""The difference in range 50% of the depth dose profile
          and the mode position in the {stopping_or_production} particles image is: {range_diff:.2f} mm."""
    )
    print(f"The spacing and match condition is: { idd_img_info.spacing[0]} mm.")
    if np.abs(range_diff) < idd_img_info.spacing[0]:
        print("Yeah! Range difference smaller than tolerance! Pass.")
        is_ok = True
    else:
        is_ok = False

    return is_ok


if __name__ == "__main__":
    print("Going to evaluate the stopping particles functionality:")
    is_ok_stopping = run_simulation("stopping", x_source=0.0)
    print("")
    print("Going to evaluate the production particles functionality:")
    is_ok_production = run_simulation("production", x_source=-5.0)

    utility.test_ok(is_ok_stopping and is_ok_production)
