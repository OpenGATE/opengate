#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
from scipy.spatial.transform import Rotation
import numpy as np
from anytree import Node, RenderTree
import uproot


def test082_test(df):
    df = df[df["PDGCode"] == 22]
    nb_event = len(df["ParentID"])
    nb_event_to_interest = len(df["ParentID"][df["ParentID"] == 0])

    tab_vertex_ekin = df["TrackVertexKineticEnergy"]
    tab_ekin = df["KineticEnergy"]

    dz_diff = df["PreDirection_Z"][df["PreDirection_Z"] != -1]

    print("Number of photons undergoing at least one rayleigh process", len(dz_diff))
    if (nb_event_to_interest == nb_event) and (
        np.all(tab_ekin == tab_vertex_ekin) and len(dz_diff > 0)
    ):
        return True
    return False


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__)
    output_path = paths.output

    print(output_path)
    # create the simulation
    sim = gate.Simulation()

    # main options
    ui = sim.user_info
    ui.g4_verbose = False
    # ui.visu = True
    ui.visu_type = "vrml"
    ui.check_volumes_overlap = False
    # ui.running_verbose_level = gate.logger.EVENT
    ui.number_of_threads = 1
    ui.random_seed = "auto"

    # units
    m = gate.g4_units.m
    km = gate.g4_units.km
    mm = gate.g4_units.mm
    cm = gate.g4_units.cm
    nm = gate.g4_units.nm
    Bq = gate.g4_units.Bq
    MeV = gate.g4_units.MeV
    keV = gate.g4_units.keV
    sec = gate.g4_units.s
    gcm3 = gate.g4_units["g/cm3"]

    sim.volume_manager.material_database.add_material_weights(
        "Tungsten",
        ["W"],
        [1],
        19.3 * gcm3,
    )

    #  adapt world size
    world = sim.world
    world.size = [0.2 * m, 0.2 * m, 0.2 * m]
    world.material = "G4_Galactic"

    source = sim.add_source("GenericSource", "photon_source")
    source.particle = "gamma"
    source.position.type = "box"
    source.attached_to = world.name
    source.position.size = [1 * nm, 1 * nm, 1 * nm]
    source.position.translation = [0, 0, 10 * cm + 1 * mm]
    source.direction.type = "momentum"
    source.direction_relative_to_attached_volume = True
    # source1.direction.focus_point = [0*cm, 0*cm, -5 *cm]
    source.direction.momentum = [0, 0, -1]
    source.energy.type = "mono"
    source.energy.mono = 1 * MeV
    source.n = 100000

    tungsten = sim.add_volume("Box", "tungsten_box")
    tungsten.size = [3 * cm, 3 * cm, 1 * cm]
    tungsten.material = "Tungsten"
    tungsten.mother = world.name
    tungsten.color = [0.5, 0.9, 0.3, 1]

    kill_proc_act = sim.add_actor("KillAccordingProcessesActor", "kill_proc_act")
    kill_proc_act.attached_to = tungsten.name
    kill_proc_act.is_rayleigh_an_interaction = False
    kill_proc_act.processes_to_kill = ["all"]

    phsp_sphere = sim.add_volume("Sphere", "phsp_sphere")
    phsp_sphere.mother = world.name
    phsp_sphere.material = "G4_Galactic"
    phsp_sphere.rmin = 5 * cm
    phsp_sphere.rmax = 5 * cm + 1 * nm

    sim.output_dir = output_path
    phsp = sim.add_actor("PhaseSpaceActor", "PhaseSpace")
    phsp.attached_to = phsp_sphere.name
    phsp.attributes = [
        "ParentID",
        "EventID",
        "TrackID",
        "KineticEnergy",
        "TrackVertexKineticEnergy",
        "PreDirection",
        "PDGCode",
    ]
    name_phsp = "test082_" + phsp.name + "_all.root"
    phsp.output_filename = name_phsp

    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option3"
    sim.physics_manager.enable_decay = False
    sim.physics_manager.global_production_cuts.gamma = 1 * km
    sim.physics_manager.global_production_cuts.electron = 1 * km
    sim.physics_manager.global_production_cuts.positron = 1 * km

    # Mandatory for this actor, since gamma processes are encompassed in GammaGeneralProc without.
    s = f"/process/em/UseGeneralProcess false"
    sim.g4_commands_before_init.append(s)

    #
    # s = sim.add_actor("SimulationStatisticsActor", "Stats")
    # s.track_types_flag = True
    #
    # # go !
    sim.run()
    print(kill_proc_act)
    #
    phsp = uproot.open(
        str(output_path) + "/test082_PhaseSpace_all.root" + ":PhaseSpace"
    )

    df = phsp.arrays()
    is_ok = test082_test(df)
    #
    utility.test_ok(is_ok)
