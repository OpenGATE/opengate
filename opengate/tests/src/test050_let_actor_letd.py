#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from scipy.spatial.transform import Rotation
import opengate as gate
from opengate.tests import utility

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "test050_let_actor_letd")

    ref_path = paths.output_ref

    # create the simulation
    sim = gate.Simulation()

    # main options
    ui = sim.user_info
    ui.g4_verbose = False
    ui.g4_verbose_level = 1
    ui.visu = False
    ui.random_seed = 12345678910

    numPartSimTest = 20000
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
    sim.physics_manager.physics_list_name = "QGSP_BIC_EMZ"
    # sim.set_production_cut("world", "all", 1000 * km)
    # FIXME need SetMaxStepSizeInRegion ActivateStepLimiter
    # now avialable
    # e.g.
    # sim.set_max_step_size(volume_name='phantom.name', max_step_size=1*mm)

    # default source for tests
    source = sim.add_source("GenericSource", "mysource")
    source.energy.mono = 80 * MeV
    # source.energy.type = 'gauss'
    # source.energy.sigma_gauss = 1 * MeV
    source.particle = "proton"
    source.position.type = "disc"
    source.position.rotation = Rotation.from_euler("y", 90, degrees=True).as_matrix()
    source.position.radius = 4 * mm
    source.position.translation = [0, 0, 0]
    source.direction.type = "momentum"
    source.direction.momentum = [-1, 0, 0]
    # print(dir(source.energy))
    source.n = numPartSimTest
    # source.activity = 100 * kBq

    # filter : keep proton
    # f = sim.add_filter("ParticleFilter", "f")
    # f.particle = "proton"

    size = [50, 1, 1]
    spacing = [2.0 * mm, 60.0 * mm, 60.0 * mm]

    doseActorName_IDD_d = "IDD_d"
    doseIDD = sim.add_actor("DoseActor", doseActorName_IDD_d)
    doseIDD.output = paths.output / ("test050-" + doseActorName_IDD_d + ".mhd")
    doseIDD.mother = phantom_off.name
    doseIDD.size = size
    doseIDD.spacing = spacing
    doseIDD.hit_type = "random"
    doseIDD.gray = False

    LETActorName_IDD_d = "LETActorOG_d"
    LETActor_IDD_d = sim.add_actor("LETActor", LETActorName_IDD_d)
    LETActor_IDD_d.output = paths.output / ("test050-" + LETActorName_IDD_d + ".mhd")
    LETActor_IDD_d.mother = phantom_off.name
    LETActor_IDD_d.size = size
    LETActor_IDD_d.spacing = spacing
    LETActor_IDD_d.hit_type = "random"
    LETActor_IDD_d.separate_output = True
    # both lines do the same thing,
    setattr(
        LETActor_IDD_d, "dose_average", True
    )  # usesful for looping over several options
    # LETActor_IDD_d.track_average = True ## same as above line

    LETActorName_IDD_t = "LETActorOG_t"
    LETActor_IDD_t = sim.add_actor("LETActor", LETActorName_IDD_t)
    LETActor_IDD_t.output = paths.output / ("test050-" + LETActorName_IDD_t + ".mhd")
    LETActor_IDD_t.mother = phantom_off.name
    LETActor_IDD_t.size = size
    LETActor_IDD_t.spacing = spacing
    LETActor_IDD_t.hit_type = "random"
    LETActor_IDD_t.track_average = True

    LETActorName_IDD_d2w = "LETActorOG_d2w"
    LETActor_IDD_d2w = sim.add_actor("LETActor", LETActorName_IDD_d2w)
    LETActor_IDD_d2w.output = paths.output / (
        "test050-" + LETActorName_IDD_d2w + ".mhd"
    )
    LETActor_IDD_d2w.mother = phantom_off.name
    LETActor_IDD_d2w.size = size
    LETActor_IDD_d2w.spacing = spacing
    LETActor_IDD_d2w.hit_type = "random"
    LETActor_IDD_d2w.other_material = "G4_WATER"
    setattr(LETActor_IDD_d2w, "dose_average", True)

    fName_ref_IDD = "IDD__Proton_Energy1MeVu_RiFiout-Edep.mhd"
    print(paths)
    # add stat actor
    s = sim.add_actor("SimulationStatisticsActor", "stats")
    s.track_types_flag = True
    # s.filters.append(f)

    print("Filters: ", sim.filter_manager)
    print(sim.filter_manager.dump())

    # start simulation
    sim.n = 10
    sim.run()

    # paths.gate_output

    # print results at the end
    stat = sim.output.get_actor("stats")
    print(stat)

    # ----------------------------------------------------------------------------------------------------------------
    # tests
    print()
    # gate.exception.warning("Tests stats file")
    # stats_ref = utility.read_stat_file(paths.gate_output / "stats.txt")
    # is_ok = utility.assert_stats(stat, stats_ref, 0.14)

    LETActorFPath_doseAveraged = sim.output.get_actor(
        LETActorName_IDD_d
    ).user_info.output
    LETActorFPath_trackAveraged = sim.output.get_actor(
        LETActorName_IDD_t
    ).user_info.output

    fNameIDD = "test050_IDD__Proton_Energy1MeVu_RiFiout-Edep.mhd"
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

    is_ok = utility.assert_filtered_imagesprofile1D(
        ref_filter_filename1=ref_path / fNameIDD,
        ref_filename1=ref_path
        / "test050_LET1D_noFilter__PrimaryProton-doseAveraged.mhd",
        filename2=LETActor_IDD_d.output,
        tolerance=15,
        plt_ylim=[0, 25],
    )

    is_ok = (
        utility.assert_filtered_imagesprofile1D(
            ref_filter_filename1=ref_path / fNameIDD,
            ref_filename1=ref_path
            / "test050_LET1D_noFilter__PrimaryProton-trackAveraged.mhd",
            filename2=LETActor_IDD_t.output,
            tolerance=8,
            plt_ylim=[0, 18],
        )
        and is_ok
    )

    utility.test_ok(is_ok)
