#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
import opengate.contrib.linacs.elektasynergy as gate_linac
import gatetools.phsp as phsp
import matplotlib.pyplot as plt
from scipy.spatial.transform import Rotation

paths = utility.get_default_test_paths(
    __file__, "gate_test019_linac_phsp", output_folder="test019"
)


def init_test019(nt):
    # create the simulation
    sim = gate.Simulation()

    # main options
    sim.g4_verbose = False
    # sim.visu = True
    sim.visu_type = "vrml"
    sim.check_volumes_overlap = False
    sim.number_of_threads = nt
    sim.random_seed = 123456789
    sim.output_dir = paths.output
    print(sim)

    # units
    m = gate.g4_units.m
    mm = gate.g4_units.mm
    nm = gate.g4_units.nm
    Bq = gate.g4_units.Bq
    MeV = gate.g4_units.MeV

    #  adapt world size
    world = sim.world
    world.size = [1 * m, 1 * m, 1.3 * m]

    # add a linac
    linac = gate_linac.add_linac(sim, "linac")
    linac.translation = [0, 0, 0 * m]

    # virtual plane for phase space
    plane = sim.add_volume("Tubs", "phase_space_plane")
    plane.mother = linac.name
    plane.material = "G4_AIR"
    plane.rmin = 0
    plane.rmax = 70 * mm
    plane.dz = 1 * nm  # half height
    plane.translation = [0, 0, linac.size[2] / 2 - 300 * mm]
    plane.color = [1, 0, 0, 1]  # red

    # e- source
    source = sim.add_source("GenericSource", "Default")
    source.particle = "e-"
    source.mother = f"{linac.name}_target"
    source.energy.type = "gauss"
    source.energy.mono = 6.7 * MeV
    source.energy.sigma_gauss = 0.077 * MeV
    source.position.type = "disc"
    source.position.radius = 2 * mm  # FIXME not really similar to GATE need sigma etc
    source.position.translation = [0, 0, 0.5 * mm - 1 * nm]
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, -1]
    source.activity = 5000 * Bq / sim.number_of_threads

    # add stat actor
    s = sim.add_actor("SimulationStatisticsActor", "Stats")
    s.track_types_flag = True

    # PhaseSpace Actor
    ta2 = sim.add_actor("PhaseSpaceActor", "PhaseSpace")
    ta2.attached_to = plane.name
    ta2.attributes = [
        "KineticEnergy",
        "Weight",
        "PostPosition",
        "PrePosition",
        "PrePositionLocal",
        "ParticleName",
        "PreDirection",
        "PreDirectionLocal",
        "PostDirection",
        "TimeFromBeginOfEvent",
        "GlobalTime",
        "LocalTime",
        "EventPosition",
        "PDGCode",
    ]
    ta2.output_filename = "test019_hits.root"
    ta2.debug = False
    ta2.steps_to_store = "exiting"
    f = sim.add_filter("ParticleFilter", "f")
    f.particle = "gamma"
    ta2.filters.append(f)

    # phys
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option4"
    sim.physics_manager.enable_decay = False
    sim.physics_manager.global_production_cuts.gamma = 1 * mm
    sim.physics_manager.global_production_cuts.electron = 1 * mm
    sim.physics_manager.global_production_cuts.positron = 1 * mm

    return sim


def run_test019(sim):
    # splitting
    linac = sim.volume_manager.get_volume("linac")
    region_linac = sim.physics_manager.add_region(name=f"{linac.name}_region")
    region_linac.associate_volume(linac)
    # FIXME: should be a user info in Region
    s = f"/process/em/setSecBiasing eBrem {region_linac.name} 100 100 MeV"
    print(s)
    sim.g4_commands_after_init.append(s)

    # start simulation
    sim.run()

    # print results
    stats = sim.get_actor("Stats")
    print(stats)

    h = sim.get_actor("PhaseSpace")
    print(h)

    # FIXME: missing features:
    # - missing several branch names in PhaseSpaceActor
    # - no local/global for position
    # - no policy options (all track single etc)

    # check stats
    print()
    stats_ref = utility.read_stat_file(paths.gate_output / "output-writePhS-stat.txt")
    print(f"Number of runs was {stats.counts.runs}. Set to 1 before comparison")
    stats.counts.runs = 1
    is_ok = utility.assert_stats(stats, stats_ref, 0.2)

    # compare the phsp tree
    print()
    fn1 = paths.gate_output / "output-PhS-g.root"
    fn2 = h.get_output_path()
    print("Reference gate tree : ", fn1)
    print("Checked Tree : ", fn2)
    data_ref, keys_ref, m_ref = phsp.load(fn1)
    data, keys, m = phsp.load(fn2)
    # find the good key's names
    keys1, keys2, scalings, tols = utility.get_keys_correspondence(keys_ref)
    keys1.remove("Z")
    keys2.remove("PrePosition_Z")
    # Do not check some keys
    tols[keys1.index("Weight")] = 0.001
    tols[keys1.index("Ekine")] = 0.1
    tols[keys1.index("Y")] = 2.0
    tols[keys1.index("X")] = 3.0
    # tols[keys1.index("Z")] = 0.2
    # perform the test
    is_ok = (
        utility.compare_trees(
            data_ref, keys_ref, data, keys, keys1, keys2, tols, scalings, scalings, True
        )
        and is_ok
    )

    # figure
    plt.suptitle(f"Values: {len(data_ref)} vs {len(data)}")
    # plt.show()
    fn = paths.output / "test019.png"
    plt.savefig(fn)
    print(f"Figure in {fn}")

    # this is the end, my friend
    utility.test_ok(is_ok)


def create_simu_test019_phsp_source(sim):
    # main options
    sim.g4_verbose = False
    # sim.visu = True
    sim.visu_type = "vrml"
    sim.check_volumes_overlap = False
    # sim.running_verbose_level = gate.logger.EVENT
    sim.number_of_threads = 1
    sim.random_seed = 987654321
    sim.output_dir = paths.output

    # units
    m = gate.g4_units.m
    mm = gate.g4_units.mm
    nm = gate.g4_units.nm

    #  adapt world size
    sim.world.size = [1 * m, 1 * m, 1 * m]

    # virtual plane for phase space
    plane = sim.add_volume("Tubs", "phase_space_plane")
    plane.material = "G4_AIR"
    plane.rmin = 0
    plane.rmax = 70 * mm
    plane.dz = 1 * nm  # half height
    plane.rotation = Rotation.from_euler("xy", [180, 30], degrees=True).as_matrix()
    plane.translation = [-5 * mm, 20 * mm, 33 * mm]
    plane.color = [1, 0, 0, 1]  # red

    plane2 = sim.add_volume("Tubs", "phase_space_plane2")
    plane2.material = "G4_AIR"
    plane2.rmin = 0
    plane2.rmax = 70 * mm
    plane2.dz = 1 * nm  # half height
    plane2.translation = [0 * mm, 0 * mm, -300.001 * mm]
    plane2.color = [1, 0, 0, 1]  # red

    # phsp source
    source = sim.add_source("PhaseSpaceSource", "phsp_source_local")
    source.mother = plane.name
    source.phsp_file = paths.output_ref / "test019_hits.root"
    source.position_key = "PrePositionLocal"
    source.direction_key = "PreDirectionLocal"
    source.global_flag = False
    source.particle = "gamma"
    source.particle = ""
    source.PDGCode_key = "PDGCode"
    source.n = 20000 / sim.number_of_threads
    source.batch_size = source.n

    # phsp source
    source = sim.add_source("PhaseSpaceSource", "phsp_source_global")
    source.mother = sim.world.name
    source.phsp_file = paths.output_ref / "test019_hits.root"
    source.position_key = "PrePosition"
    source.direction_key = "PreDirection"
    source.global_flag = True
    source.particle = None
    source.PDGCode_key = "PDGCode"
    source.n = 20000 / sim.number_of_threads
    source.batch_size = source.n
    source.verbose_batch = True

    # add stat actor
    s = sim.add_actor("SimulationStatisticsActor", "Stats")
    s.track_types_flag = True

    # PhaseSpace Actor
    ta1 = sim.add_actor("PhaseSpaceActor", "PhaseSpace1")
    ta1.attached_to = plane.name
    ta1.attributes = [
        "KineticEnergy",
        "Weight",
        "PostPosition",
        "PrePosition",
        "PrePositionLocal",
        "PostPositionLocal",
        "ParticleName",
        "PreDirection",
        "PreDirectionLocal",
        "PostDirection",
        "TimeFromBeginOfEvent",
        "GlobalTime",
        "LocalTime",
        "EventPosition",
    ]
    ta1.output_filename = "test019_hits_phsp_source_local.root"
    ta1.debug = False
    ta1.steps_to_store = "exiting"
    f = sim.add_filter("ParticleFilter", "f")
    f.particle = "gamma"
    ta1.filters.append(f)

    # PhaseSpace Actor
    ta2 = sim.add_actor("PhaseSpaceActor", "PhaseSpace2")
    ta2.attached_to = plane2.name
    ta2.attributes = [
        "KineticEnergy",
        "Weight",
        "PostPosition",
        "PrePosition",
        "PrePositionLocal",
        "ParticleName",
        "PreDirection",
        "PreDirectionLocal",
        "PostDirection",
        "TimeFromBeginOfEvent",
        "GlobalTime",
        "LocalTime",
        "EventPosition",
    ]
    ta2.output_filename = "test019_hits_phsp_source_global.root"
    ta2.debug = False
    f = sim.add_filter("ParticleFilter", "f2")
    f.particle = "gamma"
    ta2.filters.append(f)

    # phys
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option4"
    sim.physics_manager.enable_decay = False
    sim.physics_manager.global_production_cuts.gamma = 1 * mm
    sim.physics_manager.global_production_cuts.electron = 1 * mm
    sim.physics_manager.global_production_cuts.positron = 1 * mm


def analyse_test019_phsp_source(sim):
    # print results
    stats = sim.get_actor("Stats")
    print(stats)

    # print source phsp info
    s1 = sim.source_manager.get_source_info("phsp_source_local").particle_generator
    print(f"Source local :  {s1.num_entries} elements, {s1.cycle_count} cycle")
    s2 = sim.source_manager.get_source_info("phsp_source_global").particle_generator
    print(f"Source global : {s2.num_entries} elements, {s2.cycle_count} cycle")

    # --------------------------------------------------------------
    # Test LOCAL position
    print()
    print("Test LOCAL position")
    fn1 = paths.output_ref / "test019_hits.root"
    ta1 = sim.get_actor("PhaseSpace1")
    fn2 = ta1.get_output_path()
    print("Reference gate tree : ", fn1)
    print("Checked Tree : ", fn2)
    data, keys, _ = phsp.load(fn2, "PhaseSpace1")
    data_ref, keys_ref, _ = phsp.load(fn1, nmax=len(data))

    keys1 = [
        "PrePositionLocal_X",
        "PrePositionLocal_Y",
        "PrePositionLocal_Z",
        "KineticEnergy",
        "Weight",
    ]
    keys2 = keys1
    tols = [0.01] * len(keys1)
    scalings = [1.0] * len(keys1)
    is_ok = utility.compare_trees(
        data_ref, keys_ref, data, keys, keys1, keys2, tols, scalings, scalings, True
    )

    # figure
    plt.suptitle(f"Values: {len(data_ref)} vs {len(data)}")
    # plt.show()
    fn = paths.output / "test019_source_local.png"
    plt.savefig(fn)
    print(f"Figure in {fn}")

    # --------------------------------------------------------------
    # Test GLOBAL position
    print()
    print("Test GLOBAL position")
    fn1 = paths.output_ref / "test019_hits.root"
    ta2 = sim.get_actor("PhaseSpace2")
    fn2 = ta2.get_output_path()
    print("Reference gate tree : ", fn1)
    print("Checked Tree : ", fn2)
    data, keys, _ = phsp.load(fn2, "PhaseSpace2")
    data_ref, keys_ref, _ = phsp.load(fn1, nmax=len(data))

    keys1 = [
        "PrePosition_X",
        "PrePosition_Y",
        "PrePosition_Z",
        "KineticEnergy",
        "Weight",
    ]
    keys2 = keys1
    tols = [0.01] * len(keys1)
    scalings = [1.0] * len(keys1)
    is_ok = (
        utility.compare_trees(
            data_ref, keys_ref, data, keys, keys1, keys2, tols, scalings, scalings, True
        )
        and is_ok
    )

    # figure
    plt.suptitle(f"Values: {len(data_ref)} vs {len(data)}")
    # plt.show()
    fn = paths.output / "test019_source_global.png"
    plt.savefig(fn)
    print(f"Figure in {fn}")

    return is_ok
