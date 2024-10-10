#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from scipy.spatial.transform import Rotation
import opengate as gate
from opengate.tests import utility


if __name__ == "__main__":
    do_debug = False
    paths = utility.get_default_test_paths(
        __file__, "test050_let_actor_letd", "test050"
    )
    ref_path = paths.output_ref

    # create the simulation
    sim = gate.Simulation()

    # main options
    sim.g4_verbose = False
    sim.g4_verbose_level = 1
    sim.visu = False
    sim.random_seed = 1234567891
    sim.number_of_threads = 1
    sim.output_dir = paths.output

    numPartSimTest = 4000 / sim.number_of_threads
    numPartSimRef = 1e5

    # units
    m = gate.g4_units.m
    cm = gate.g4_units.cm
    mm = gate.g4_units.mm
    mrad = gate.g4_units.mrad
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
    # sim.physics_manager.set_production_cut("world", "all", 1000 * km)
    # FIXME need SetMaxStepSizeInRegion ActivateStepLimiter
    # now available
    # e.g.
    # sim.physics_manager.set_max_step_size(volume_name='phantom', max_step_size=1*mm)

    # default source for tests
    source = sim.add_source("IonPencilBeamSource", "mysource1")
    source.energy.type = "gauss"
    source.energy.mono = 1440 * MeV
    source.particle = "ion 6 12"
    source.position.type = "disc"
    # rotate the disc, equiv to : rot1 0 1 0 and rot2 0 0 1
    source.direction.type = "momentum"
    source.position.rotation = Rotation.from_euler("y", -90, degrees=True).as_matrix()
    source.n = numPartSimTest
    # source.position.sigma_x = 8 * mm
    # source.position.sigma_y = 8 * mm
    source.direction.partPhSp_x = [
        2.3335754 * mm,
        2.3335754 * mrad,
        0.00078728 * mm * mrad,
        0,
    ]
    source.direction.partPhSp_y = [
        1.96433431 * mm,
        0.00079118 * mrad,
        0.00249161 * mm * mrad,
        0,
    ]

    size = [50, 1, 1]
    spacing = [2.0 * mm, 60.0 * mm, 60.0 * mm]

    doseActorName_IDD_d = "IDD_d"
    doseIDD = sim.add_actor("DoseActor", doseActorName_IDD_d)
    doseIDD.output_filename = "test050-" + doseActorName_IDD_d + ".mhd"
    doseIDD.attached_to = phantom_off
    doseIDD.size = size
    doseIDD.spacing = spacing
    doseIDD.hit_type = "random"
    doseIDD.dose.active = False

    RBEActorName_IDD_d = "RBEActorOG_d"
    RBEActor_IDD_d = sim.add_actor("RBEActor", RBEActorName_IDD_d)
    RBEActor_IDD_d.output_filename = "test_rbe-" + RBEActorName_IDD_d + ".mhd"
    RBEActor_IDD_d.attached_to = phantom_off
    RBEActor_IDD_d.size = size
    RBEActor_IDD_d.spacing = spacing
    RBEActor_IDD_d.hit_type = "random"
    RBEActor_IDD_d.rbe_model = "lemI"
    RBEActor_IDD_d.lookup_table_path = paths.data / 'NIRS_MKM_reduced_data.txt'
    
    print(paths)
    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "stats")
    stats.track_types_flag = True
    # stats.filters.append(f)

    print("Filters: ", sim.filter_manager)
    # print(sim.filter_manager.dump())

    # start simulation
    sim.run()

    # print results at the end
    print(stats)

    # ----------------------------------------------------------------------------------------------------------------
