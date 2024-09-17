#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from scipy.spatial.transform import Rotation
import os, sys
import opengate as gate
from opengate.tests import utility

if __name__ == "__main__":
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    # import ../db.py

    # from sim_output_analysis import compareGaussParam, plot_edep

    paths = utility.get_default_test_paths(
        __file__, "gate_test044_pbs_unFocused", "test044_unfocused"
    )

    particle = "Carbon_"
    energy = "1440MeV_"
    beam_shape = "sourceShapePBS"
    folder = particle + energy + beam_shape

    output_path = paths.output
    ref_path = paths.gate_output

    # for for loop
    start = -500
    spacing = 100
    end = -start + spacing
    planePositionsV = range(start, end, spacing)

    # create the simulation
    sim = gate.Simulation()

    # main options
    sim.g4_verbose = False
    sim.g4_verbose_level = 1
    sim.visu = False
    sim.random_seed = 123654789
    sim.random_engine = "MersenneTwister"
    sim.output_dir = paths.output

    # units
    km = gate.g4_units.km
    cm = gate.g4_units.cm
    mm = gate.g4_units.mm
    um = gate.g4_units.um
    MeV = gate.g4_units.MeV
    Bq = gate.g4_units.Bq
    nm = gate.g4_units.nm
    deg = gate.g4_units.deg
    mrad = gate.g4_units.mrad

    # add a material database
    sim.volume_manager.add_material_database(paths.gate_data / "HFMaterials2014.db")

    #  change world size
    world = sim.world
    world.size = [600 * cm, 500 * cm, 500 * cm]

    # waterbox
    # translation and rotation like in the Gate macro
    waterbox = sim.add_volume("Box", "waterbox")
    waterbox.size = [10 * cm, 10 * cm, 100.2 * cm]
    waterbox.rotation = Rotation.from_euler("y", 90, degrees=True).as_matrix()
    waterbox.translation = [-50.1 * cm, 0 * cm, 0 * cm]
    waterbox.material = "Vacuum"
    waterbox.color = [0, 0, 1, 1]

    # Planes
    m = Rotation.identity().as_matrix()

    for i in planePositionsV:
        plane = sim.add_volume("Box", "planeNr" + str(i) + "a")
        plane.mother = "waterbox"
        plane.size = [100 * mm, 100 * mm, 2 * mm]
        plane.translation = [0 * mm, 0 * mm, i * mm]
        plane.rotation = m
        plane.material = "G4_AIR"
        plane.color = [1, 0, 1, 1]

    # physics
    sim.physics_manager.physics_list_name = "FTFP_INCLXX_EMZ"
    sim.physics_manager.global_production_cuts.all = 1000 * km

    # default source for tests (from test42)
    source = sim.add_source("IonPencilBeamSource", "mysource")
    source.energy.mono = 1440 * MeV
    source.particle = "ion 6 12"  # carbon
    source.position.type = "disc"  # pos = Beam, shape = circle + sigma
    source.position.translation = [0 * mm, 0 * mm, 0 * cm]
    source.position.rotation = Rotation.from_euler("y", -90, degrees=True).as_matrix()
    # rotate the disc, equiv to : rot1 0 1 0 and rot2 0 0 1
    source.direction.type = "momentum"
    source.direction.momentum = [-1, 0, 0]
    source.n = 20000
    source.direction.partPhSp_x = [
        2.3335754 * mm,
        2.3335754 * mrad,
        0.00078728 * mm * mrad,
        0,
    ]  # negative
    source.direction.partPhSp_y = [
        1.96433431 * mm,
        1.79118 * mrad,
        0.00249161 * mm * mrad,
        1,
    ]  # positive

    count = 0
    # add dose actors
    for i in planePositionsV:
        dose = sim.add_actor("DoseActor", "doseInYZ" + str(i))
        filename = "plane" + str(i) + "a.mhd"
        dose.output_filename = filename
        dose.attached_to = "planeNr" + str(i) + "a"
        dose.size = [250, 250, 1]
        dose.spacing = [0.4, 0.4, 2]
        dose.hit_type = "random"
        count += 1

    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.track_types_flag = True

    print(sim.source_manager.dump_sources())

    # create output dir, if it doesn't exist
    output_path.mkdir(parents=True, exist_ok=True)

    # start simulation
    sim.run()

    # print results at the end
    print(stats)

    print("Start to analyze data")
    override = False
    # if (not os.path.exists(ref_path / "sigma_values.txt")) or override:
    #     sigmasRef, musRef = utility.write_gauss_param_to_file(
    #         ref_path,
    #         planePositionsV,
    #         saveFig=False,
    #         fNamePrefix="plane",
    #         fNameSuffix="a_Carbon_1440MeV_sourceShapePBS-Edep.mhd",
    #     )
    override = True
    output_pathV = [
        sim.get_actor("doseInYZ" + str(i)).get_output_path("edep")
        for i in planePositionsV
    ]
    if (not os.path.exists(output_path / "sigma_values.txt")) or override:
        sigmasGam, musGam = utility.write_gauss_param_to_file(
            output_pathV, planePositionsV, saveFig=False
        )
    else:
        print("Some data are already available for analysis")

    # ----------------------------------------------------------------------------------------------------------------
    # tests

    # statistics
    stat_file = "SimulationStatistic_" + folder + ".txt"
    stats_ref = utility.read_stat_file(ref_path / stat_file)
    is_ok = utility.assert_stats(stats, stats_ref, 0.15)

    # energy deposition
    for i in planePositionsV:
        print("\nDifference for EDEP plane " + str(i))
        # mhd_gate = "plane" + str(i) + "a.mhd"
        mhd_gate = sim.get_actor("doseInYZ" + str(i)).get_output_path("edep")
        mhd_ref = "plane" + str(i) + "a_" + folder + "-Edep.mhd"
        is_ok = (
            utility.assert_images(
                ref_path / mhd_ref,
                output_path / mhd_gate,
                stats,
                tolerance=50,
                ignore_value=0,
            )
            and is_ok
        )
        """EdepColorMap = utlity.create_2D_Edep_colorMap(output_path / mhd_gate)
        img_name = 'Plane_'+str(i)+'ColorMap.png'
        EdepColorMap.savefig(output_path / img_name)
        plt.close(EdepColorMap)"""

    # beam shape
    print("Comparing sigma values")
    sigma_file = "sigma_values.txt"
    is_ok = (
        utility.compareGaussParamFromFile(
            output_path / sigma_file,
            ref_path / sigma_file,
            rel_tol=2,
            abs_tol=0.5,
            verb=True,
        )
        and is_ok
    )

    print("Comparing mu values")
    sigma_file = "mu_values.txt"
    is_ok = (
        utility.compareGaussParamFromFile(
            output_path / sigma_file,
            ref_path / sigma_file,
            rel_tol=2,
            abs_tol=0.5,
            verb=True,
        )
        and is_ok
    )

    utility.test_ok(is_ok)
