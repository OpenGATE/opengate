#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import opengate.contrib.spect_ge_nm670 as gate_spect
import opengate.contrib.phantom_nema_iec_body as gate_iec
from scipy.spatial.transform import Rotation
from opengate_core import G4RegionStore

paths = gate.get_default_test_paths(
    __file__, "gate_test029_volume_time_rotation", "test029"
)


def check_production_cuts(simulation_engine):
    """Function to be called by opengate after initialization
    of the simulation, i.e. when G4 volumes and regions exist.
    The purpose is to check whether Geant4 has properly set
    the production cuts in the specific region.

    The value max_step_size is stored in the attribute hook_log
    which can be accessed via the output of the simulation.

    """
    print(f"Entered hook")
    rs = G4RegionStore.GetInstance()
    print("Known regions are:")
    for i in range(rs.size()):
        print("*****")
        print(f"{rs.Get(i).GetName()}")
        reg = rs.Get(i)
        pcuts = reg.GetProductionCuts()
        if pcuts is not None:
            cut_proton = pcuts.GetProductionCut("proton")
            cut_positron = pcuts.GetProductionCut("e+")
            cut_electron = pcuts.GetProductionCut("e-")
            cut_gamma = pcuts.GetProductionCut("gamma")
            print("Cuts in this region:")
            print(f"gamma: {cut_gamma}")
            print(f"electron: {cut_electron}")
            print(f"proton: {cut_proton}")
            print(f"positron: {cut_positron}")
        else:
            print("Found no cuts in this region")


def create_simulation(sim, aa_flag):
    # main options
    ui = sim.user_info
    ui.g4_verbose = False
    # ui.visu = True
    # ui.visu_type = 'vrml'
    ui.number_of_threads = 1
    ui.random_seed = 3456789

    # units
    m = gate.g4_units("m")
    cm = gate.g4_units("cm")
    cm3 = gate.g4_units("cm3")
    keV = gate.g4_units("keV")
    mm = gate.g4_units("mm")
    Bq = gate.g4_units("Bq")
    sec = gate.g4_units("second")
    BqmL = Bq / cm3

    sim.user_fct_after_init = check_production_cuts

    # world size
    world = sim.world
    world.size = [2 * m, 2 * m, 2 * m]
    world.material = "G4_AIR"

    # spect head (no collimator)
    spect, crystal = gate_spect.add_ge_nm67_spect_head(
        sim, "spect", collimator_type=False, debug=False
    )
    # will be overriden by MotionActor
    """initial_rot = Rotation.from_euler("X", 90, degrees=True)
    t, rot = gate.get_transform_orbiting([0, 25 * cm, 0], "Z", 0)
    rot = Rotation.from_matrix(rot)
    spect.translation = t
    spect.rotation = (rot * initial_rot).as_matrix()"""

    # iec phantom
    gate_iec.add_iec_phantom(sim)

    # two sources (no background yet)
    activity_concentration = 5000 * BqmL / ui.number_of_threads
    ac = activity_concentration
    sources = gate_iec.add_spheres_sources(
        sim,
        "iec",
        "iec_source",
        [10, 13, 17, 22, 28, 37],
        [ac, ac, ac, ac, ac, ac],
        verbose=True,
    )

    for s in sources:
        s.particle = "gamma"
        s.energy.type = "mono"
        s.energy.mono = 140 * keV
        # WARNING : to speed up, this is not a iso source,
        # s.direction.type = "iso"
        s.direction.type = "momentum"
        s.direction.momentum = [0, 1, 0]
        s.direction.acceptance_angle.volumes = ["spect"]
        s.direction.acceptance_angle.intersection_flag = aa_flag
        s.direction.acceptance_angle.skip_policy = "ZeroEnergy"

    sources = gate_iec.add_spheres_sources(
        sim,
        "iec",
        "iec_source2",
        [10, 13, 17, 22, 28, 37],
        [ac, ac, ac, ac, ac, ac],
        verbose=True,
    )

    for s in sources:
        s.particle = "gamma"
        s.energy.type = "mono"
        s.energy.mono = 140 * keV
        # WARNING : to speed up, this is not a iso source,
        # s.direction.type = "iso"
        s.direction.type = "momentum"
        s.direction.momentum = [1, 0, 0]
        s.direction.acceptance_angle.volumes = ["spect"]
        s.direction.acceptance_angle.intersection_flag = aa_flag
        s.direction.acceptance_angle.skip_policy = "ZeroEnergy"

    # physic list
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option4"

    # either set global cuts like this:
    # sim.physics_manager.global_production_cuts.all = 10 * mm

    # ... or like this
    sim.set_production_cut(
        volume_name="world",
        particle_name="all",
        value=10 * mm,
    )

    sim.set_production_cut(
        volume_name="spect",
        particle_name="all",
        value=1 * mm,
    )

    # add stat actor
    stat = sim.add_actor("SimulationStatisticsActor", "Stats")
    stat.output = paths.output / "stats029.txt"

    # hits collection
    hc = sim.add_actor("DigitizerHitsCollectionActor", "Hits")
    hc.mother = "spect_crystal"
    hc.output = ""  # No output
    hc.attributes = [
        "PostPosition",
        "TotalEnergyDeposit",
        "PreStepUniqueVolumeID",
        "GlobalTime",
    ]

    # singles collection
    sc = sim.add_actor("DigitizerAdderActor", "Singles")
    sc.mother = hc.mother
    sc.input_digi_collection = "Hits"
    sc.policy = "EnergyWeightedCentroidPosition"
    sc.output = hc.output

    # EnergyWindows
    cc = sim.add_actor("DigitizerEnergyWindowsActor", "EnergyWindows")
    cc.mother = hc.mother
    cc.input_digi_collection = "Singles"
    cc.channels = [
        {"name": "scatter", "min": 114 * keV, "max": 126 * keV},
        {"name": "peak140", "min": 126 * keV, "max": 154.55 * keV},
    ]
    cc.output = hc.output

    # projections
    proj = sim.add_actor("DigitizerProjectionActor", "Projection")
    proj.mother = hc.mother
    proj.input_digi_collections = ["Singles", "scatter", "peak140"]
    proj.spacing = [4.41806 * mm, 4.41806 * mm]
    proj.size = [128, 128]
    proj.origin_as_image_center = False
    proj.output = paths.output / "proj029.mhd"

    # motion of the spect, create also the run time interval
    motion = sim.add_actor("MotionVolumeActor", "Move")
    motion.mother = spect.name
    motion.translations = []
    motion.rotations = []
    n = 9
    sim.run_timing_intervals = []
    gantry_rotation = -90
    start_t = 0
    end = 1 * sec / n
    initial_rot = Rotation.from_euler("X", 90, degrees=True)
    for r in range(n):
        t, rot = gate.get_transform_orbiting([0, 30 * cm, 0], "Z", gantry_rotation)
        rot = Rotation.from_matrix(rot)
        rot = rot * initial_rot
        rot = rot.as_matrix()
        motion.translations.append(t)
        motion.rotations.append(rot)
        sim.run_timing_intervals.append([start_t, end])
        gantry_rotation += 10
        start_t = end
        end += 1 * sec / n

    # Warning : we set the initial position for the spect
    # is it not really used (because the motion actor) but needed to test overlap
    spect.translation = motion.translations[0]
    spect.rotation = motion.rotations[0]

    print(f"Run {len(sim.run_timing_intervals)} intervals: {sim.run_timing_intervals}")

    # check actor priority: the MotionVolumeActor must be first
    l = [l for l in sim.actor_manager.user_info_actors.values()]
    sorted_actors = sorted(l, key=lambda d: d.priority)
    print(f"Actors order: ", [[l.name, l.priority] for l in sorted_actors])
