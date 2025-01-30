#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from scipy.spatial.transform import Rotation
import opengate as gate
from opengate.tests import utility
import itk
import numpy as np

import matplotlib.pyplot as plt
from scipy.interpolate import interp1d
import sys
from pathlib import Path
from opengate.geometry import utility as gut
import math

red = [1, 0, 0, 1]
blue = [0, 0, 1, 1]
green = [0, 1, 0, 1]
yellow = [0.9, 0.9, 0.3, 1]
gray = [0.5, 0.5, 0.5, 1]
white = [1, 1, 1, 0.8]
transparent = [1, 1, 1, 0]


def add_rifi(sim, name="RiFi", mother_name="NozzleBox", rifi_rot=None, rifi_sad=361.6):

    mm = gate.g4_units.mm
    pmma_mat = "G4_LUCITE"

    rifix, rifiy, rifiz = [220 * mm, 220 * mm, 2.3 * mm]
    rifi = sim.add_volume("Box", name)
    rifi.mother = mother_name
    rifi.size = [rifiz, rifiy, rifix]
    rifi.translation = [0 * mm, 0 * mm, rifi_sad * mm]
    rot_rifi = Rotation.from_matrix(rifi_rot)
    rot_align = Rotation.from_euler("y", 90, degrees=True)
    rifi.rotation = (rot_rifi * rot_align).as_matrix()
    rifi.material = "G4_AIR"
    rifi.color = transparent

    rifi_element = sim.add_volume("Box", f"{name} Element")
    rifi_element.mother = name
    rifi_element.size = [rifiz, 1.0 * mm, rifix]
    rifi_element.translation = None
    rifi_element.rotation = None
    rifi_element.material = "G4_AIR"
    rifi_element.color = transparent

    rifi_wedge1 = add_wedge(
        sim,
        name=f"{name} Wedge1",
        wedge_x=2.0 * mm,
        wedge_narrowerx=0.4 * mm,
        wedge_y=0.451 * mm,
        wedge_z=rifix,
    )
    rifi_wedge1.mother = rifi_element.name
    rifi_wedge1.translation = [-0.4 * mm, 0.2655 * mm, 0 * mm]
    rifi_wedge1.material = pmma_mat
    rifi_wedge1.color = yellow

    rifi_wedge2 = add_wedge(
        sim,
        name=f"{name} Wedge2",
        wedge_x=2.0 * mm,
        wedge_narrowerx=0.4 * mm,
        wedge_y=0.451 * mm,
        wedge_z=rifix,
    )
    rifi_wedge2.mother = rifi_element.name
    rifi_wedge2.translation = [-0.4 * mm, -0.2655 * mm, 0 * mm]
    rifi_wedge2.rotation = Rotation.from_euler("x", 180, degrees=True).as_matrix()
    rifi_wedge2.material = pmma_mat
    rifi_wedge2.color = yellow

    rifi_flattop = sim.add_volume("Box", f"{name} Flattop")
    rifi_flattop.mother = rifi_element.name
    rifi_flattop.size = [2.0 * mm, 0.08 * mm, rifix]
    rifi_flattop.translation = [0 * mm, 0 * mm, 0 * mm]
    rifi_flattop.material = pmma_mat
    rifi_flattop.color = yellow

    rifi_flatbottom1 = sim.add_volume("Box", f"{name} Flatbottom1")
    rifi_flatbottom1.mother = rifi_element.name
    rifi_flatbottom1.size = [0.4 * mm, 0.009 * mm, rifix]
    rifi_flatbottom1.translation = [-0.8 * mm, 0.4955 * mm, 0 * mm]
    rifi_flatbottom1.material = pmma_mat
    rifi_flatbottom1.color = yellow

    rifi_flatbottom2 = sim.add_volume("Box", f"{name} Flatbottom2")
    rifi_flatbottom2.mother = rifi_element.name
    rifi_flatbottom2.size = [0.4 * mm, 0.009 * mm, rifix]
    rifi_flatbottom2.translation = [-0.8 * mm, -0.4955 * mm, 0 * mm]
    rifi_flatbottom2.material = pmma_mat
    rifi_flatbottom2.color = yellow

    translations = gut.get_grid_repetition([1, 220, 1], [0, 1.0 * mm, 0])
    rifi_element.translation = translations


def add_wedge(
    sim, name="wedge", wedge_x=200, wedge_narrowerx=40, wedge_y=45.1, wedge_z=100
):

    deg = gate.g4_units.deg
    wedge = sim.add_volume("Trap", name)
    wedge.dz = 0.5 * wedge_z
    wedge.dy1 = 0.5 * wedge_y
    wedge.dy2 = wedge.dy1
    wedge.dx1 = wedge.dx3 = 0.5 * wedge_x
    wedge.dx2 = wedge.dx4 = 0.5 * wedge_narrowerx
    talp = 0.5 * (wedge_narrowerx - wedge_x) / wedge_y
    wedge.alp1 = wedge.alp2 = math.degrees(math.atan(talp)) * deg
    wedge.theta = wedge.phi = 0

    return wedge


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "test_087")
    print(paths)
    ref_path = paths.output_ref / "test087"
    mkm_lq_fpath = ref_path / "mkm_nirs_LQparameters_SURVIVAL.csv"
    #    df = pd.read_csv(mkm_lq_fpath)
    # create the simulation
    sim = gate.Simulation()

    # main options
    ui = sim.user_info
    ui.g4_verbose = False
    ui.g4_verbose_level = 1
    ui.visu = False
    ui.random_seed = 12345678910
    ui.number_of_threads = 16

    numPartSimTest = 1e3 / ui.number_of_threads
    numPartSimRef = 1e4

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
    phantom.size = [50 * mm, 10 * cm, 10 * cm]
    phantom.translation = [-35 * cm, 0, 0]
    phantom.material = "G4_WATER"
    phantom.color = [0, 0, 1, 1]

    test_material_name = "G4_WATER"
    phantom_off = sim.add_volume("Box", "phantom_off")
    phantom_off.mother = phantom.name
    phantom_off.size = [50 * mm, 10 * mm, 10 * mm]
    phantom_off.translation = [0 * mm, 0 * mm, 0 * mm]
    phantom_off.material = test_material_name
    phantom_off.color = [0, 0, 1, 1]

    NozzleBox = sim.add_volume("Box", "NozzleBox")
    #    NozzleBox.mother = phantom.name
    NozzleBox.size = [220 * mm, 220 * mm, 10 * mm]
    NozzleBox.translation = [0 * mm, 0 * mm, 0 * mm]
    NozzleBox.material = "G4_AIR"
    NozzleBox.color = [0, 0, 1, 1]
    #    sys.path.append('/opt/share/IDEAL-1_2refactored/ideal/nozzle/')
    #    import rifi
    add_rifi(
        sim,
        name="RiFi",
        mother_name="NozzleBox",
        rifi_rot=Rotation.identity().as_matrix(),
        rifi_sad=0,
    )

    rot_align = Rotation.from_euler("z", -90, degrees=True)
    NozzleBox.rotation = rot_align.as_matrix()
    # physics
    sim.physics_manager.physics_list_name = "QGSP_BIC_EMZ"

    # default source for tests
    source = sim.add_source("GenericSource", "mysource")
    source.energy.mono = 1424 * MeV
    # source.energy.type = 'gauss'
    # source.energy.sigma_gauss = 1 * MeV
    source.particle = "ion 6 12"
    source.position.type = "disc"
    source.position.rotation = Rotation.from_euler("y", 90, degrees=True).as_matrix()
    source.position.radius = 4 * mm
    source.position.translation = [-10 * mm, 0, 0]
    source.direction.type = "momentum"
    source.direction.momentum = [-1, 0, 0]
    # print(dir(source.energy))
    source.n = numPartSimTest
    # source.activity = 100 * kBq

    size = [50, 1, 1]
    spacing = [1.0 * mm, 100.0 * mm, 100.0 * mm]

    doseActorName_IDD_d = "IDD_d"
    doseIDD = sim.add_actor("DoseActor", doseActorName_IDD_d)
    doseIDD.output_filename = paths.output / ("test087-" + doseActorName_IDD_d + ".mhd")
    #    print(f'actor: {paths.output / ("test087-" + doseActorName_IDD_d + ".mhd")}')
    doseIDD.attached_to = phantom_off.name
    doseIDD.size = size
    doseIDD.spacing = spacing
    doseIDD.hit_type = "random"
    doseIDD.dose.active = False
    #
    #    RBE = "RBE"
    #    RBE_act = sim.add_actor("BeamQualityActor", RBE)
    #    RBE_act.output_filename = paths.output / ("test087-" + RBE + ".mhd")
    #    RBE_act.attached_to = phantom_off.name
    #    RBE_act.size = size
    #    RBE_act.spacing = spacing
    #    RBE_act.hit_type = "random"
    ##    RBE_act.other_material = 'G4_Alanine'
    #    # both lines do the same thing,
    ##    RBE_act.dose_average = False
    ##    RBE_act.enable_rbe = True
    ##    RBE_act.is_energy_per_nucleon = False
    ##    RBE_act.fclin = 1.0
    ##    RBE_act.lookup_table_path = (
    ##        "/opt/GATE/GateRTion-1.1/install/data/RE_Alanine/RE_Alanine_RBEstyle.txt"
    ##    )
    ##    RBE_act.lookup_table_path = (
    ##        "/home/ideal/0_Data/21_RBE/01_Tables/NIRS_MKM_reduced_data.txt"
    ##    )
    #    RBE_act.lookup_table_path = ref_path / "RE_Alanine_RBEstyle.txt"

    RBE = "RBE"
    RBE_act = sim.add_actor("RBEActor", "RBE_act")
    RBE_act.output_filename = paths.output / ("test087-" + RBE + ".mhd")
    RBE_act.attached_to = phantom_off.name
    RBE_act.size = size
    RBE_act.spacing = spacing
    RBE_act.hit_type = "random"
    RBE_act.model = "mMKM"
    RBE_act.r_nucleus = 3.9
    #    RBE_act.model = "LEM1lda"
    #    RBE_act.score_in = "G4_WATER"

    #    RBE_act.energy_per_nucleon = False
    #    RBE_act.lookup_table_path = mkm_lq_fpath

    RBE_act.energy_per_nucleon = False
    RBE_act.lookup_table_path = ref_path / "mkm_nirs_LQparameters_SURVIVAL.csv"

    #    RBE_act.lookup_table_path = '/users/aresch/Documents/RBE/LEM1_RS.txt'
    # add stat actor
    s = sim.add_actor("SimulationStatisticsActor", "stats")
    s.track_types_flag = True

    sim.run()
    rs_fpath = ref_path / "mMKM line dose IDEAL_water_AbsDose_2D_IR2HBLc28Jan2025.csv"
    rs_fpath_phys = (
        ref_path
        / "mMKM line physical dose IDEAL_water_AbsDose_2D_IR2HBLc 28 Jan 2025.csv"
    )
    data = np.loadtxt(rs_fpath, delimiter=";", skiprows=12)
    data_phys = np.loadtxt(rs_fpath_phys, delimiter=";", skiprows=12)
    # Extract the first and fourth columns
    x = (data[:-1, 0] - 28.049) * (-10)  # First column
    y = data[:-1, 3] / data_phys[:, 3]  # Fourth column

    #    fName = paths.output / doseIDD.r.get_output_path()
    #    img1 = itk.imread(fName)
    #    data1 = np.squeeze(itk.GetArrayViewFromImage(img1).ravel())
    #    y_prime = np.flip(data1)

    fName = paths.output / RBE_act.rbe.get_output_path()
    img1 = itk.imread(fName)
    data1 = np.squeeze(itk.GetArrayViewFromImage(img1).ravel())
    y_prime = np.flip(data1)
    x_test = np.arange(0, len(y_prime)) + 0.5
    x_prime = x_test
    interpolator = interp1d(x, y, kind="linear", fill_value="extrapolate")
    y_interpolated = interpolator(x_prime)

    # Calculate residuals
    residuals = y_prime - y_interpolated
    #    print(f"{residuals = }")
    #    print(f'{ref_data = }')

    # Plotting
    plt.figure(figsize=(10, 6))

    # Original and interpolated data
    plt.plot(x, y, "o-", label="Original (x, y)")
    plt.plot(x_prime, y_prime, "x-", label="Target (x', y')")
    plt.plot(x_prime, y_interpolated, "--", label="Interpolated (x', y_interp)")

    # Residuals
    plt.scatter(x_prime, residuals, color="red", label="Residuals", zorder=5)

    # Formatting
    plt.axhline(0, color="gray", linestyle="--", linewidth=0.8)
    plt.title("Interpolation and Residuals")
    plt.xlabel("x or x'")
    plt.ylabel("y, y' or residuals")
    plt.legend()
    plt.grid()
    plt.savefig("test.png")

    # ----------------------------------------------------------------------------------------------------------------
    #    print(RBE_act)

    fNameIDD = doseIDD.user_info.output
    """
    is_ok = utility.assert_images(
        ref_path / fNameIDD,
        doseIDD.output,
        stat,
        tolerance=100,
        ignore_value=0,
        axis="x",
        scaleImageValuesFactor=numPartSimRef / numPartSimTest,
    )

    """
    ref_fpath = ref_path / "test087-RBE_rbe.mhd"
    ref_fpath = ref_path / "test087-alpha_mix_rbe.mhd"
    #    print(f"{doseIDD.dose.get_output_path()=}")
    is_ok = utility.assert_filtered_imagesprofile1D(
        ref_filter_filename1=doseIDD.edep.get_output_path(),
        ref_filename1=ref_fpath,
        filename2=paths.output / RBE_act.rbe.get_output_path(),
        tolerance=20,
        eval_quantity="RBE",
        #        plt_ylim=[0, 2],
    )

    # )
    # is_ok = (
    #     utility.assert_filtered_imagesprofile1D(
    #         ref_filter_filename1=ref_path / fNameIDD,
    #         ref_filename1=ref_path / "test050_LET1D_Z1__PrimaryProton-doseAveraged.mhd",
    #         filename2=paths.output / LETActor_primaries.user_info.output,
    #         tolerance=8,
    #         plt_ylim=[0, 25],
    #     )
    #     and is_ok
    # )

    utility.test_ok(is_ok)
