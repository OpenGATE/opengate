#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
from scipy.spatial.transform import Rotation
import numpy as np
from anytree import Node, RenderTree
import uproot


def test074_test(entry_data, exit_data_1, exit_data_2):
    liste_ekin = []
    liste_evtID = []
    liste_trackID = []
    evt_ID_entry_data = entry_data["EventID"]
    j = 0
    i = 0
    while i < len(evt_ID_entry_data):
        if (
            j < len(exit_data_1["EventID"])
            and evt_ID_entry_data[i] == exit_data_1["EventID"][j]
        ):
            TID_entry = entry_data["TrackID"][i]
            TID_exit = exit_data_1["TrackID"][j]
            Ekin_entry = entry_data["KineticEnergy"][i]
            Ekin_exit = exit_data_1["KineticEnergy"][j]

            if (TID_entry == TID_exit) and (Ekin_exit == Ekin_entry):
                liste_ekin.append(exit_data_1["KineticEnergy"][j])
                liste_evtID.append(exit_data_1["EventID"][j])
                liste_trackID.append(exit_data_1["TrackID"][j])
            if (j < len(exit_data_1["EventID"]) - 1) and (
                exit_data_1["EventID"][j] == exit_data_1["EventID"][j + 1]
            ):
                i = i - 1
            j += 1
        i += 1
    liste_ekin = np.asarray(liste_ekin)
    print("Number of tracks to kill =", len(liste_ekin))
    print(
        "Number of killed tracks =",
        (len(exit_data_1["EventID"]) - len(exit_data_2["EventID"])),
    )

    return len(liste_ekin) == (
        len(exit_data_1["EventID"]) - len(exit_data_2["EventID"])
    )


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
    world.size = [1 * m, 1 * m, 1 * m]
    world.material = "G4_AIR"

    big_box = sim.add_volume("Box", "big_box")
    big_box.mother = world.name
    big_box.material = "G4_AIR"
    big_box.size = [0.8 * m, 0.8 * m, 0.8 * m]

    actor_box = sim.add_volume("Box", "actor_box")
    actor_box.mother = big_box.name
    actor_box.material = "G4_AIR"
    actor_box.size = [0.6 * m, 0.6 * m, 0.6 * m]
    actor_box.translation = [0, 0, -0.1 * m]

    source = sim.add_source("GenericSource", "photon_source")
    source.particle = "gamma"
    source.position.type = "box"
    source.mother = world.name
    source.position.size = [6 * cm, 6 * cm, 6 * cm]
    source.position.translation = [0, 0, 0.3 * m]
    source.direction.type = "momentum"
    source.force_rotation = True
    # source1.direction.focus_point = [0*cm, 0*cm, -5 *cm]
    source.direction.momentum = [0, 0, -1]
    source.energy.type = "mono"
    source.energy.mono = 6 * MeV
    source.n = 1000

    tungsten_leaves = sim.add_volume("Box", "tungsten_leaves")
    tungsten_leaves.mother = actor_box
    tungsten_leaves.size = [0.6 * m, 0.6 * m, 0.3 * cm]
    tungsten_leaves.material = "Tungsten"
    liste_translation_W = []
    for i in range(7):
        liste_translation_W.append([0, 0, 0.25 * m - i * 6 * cm])
    tungsten_leaves.translation = liste_translation_W
    tungsten_leaves.color = [0.9, 0.0, 0.4, 0.8]

    kill_No_int_act = sim.add_actor("KillNonInteractingParticleActor", "killact")
    kill_No_int_act.mother = actor_box.name

    entry_phase_space = sim.add_volume("Box", "entry_phase_space")
    entry_phase_space.mother = big_box
    entry_phase_space.size = [0.8 * m, 0.8 * m, 1 * nm]
    entry_phase_space.material = "G4_AIR"
    entry_phase_space.translation = [0, 0, 0.21 * m]
    entry_phase_space.color = [0.5, 0.9, 0.3, 1]

    exit_phase_space_1 = sim.add_volume("Box", "exit_phase_space_1")
    exit_phase_space_1.mother = actor_box
    exit_phase_space_1.size = [0.6 * m, 0.6 * m, 1 * nm]
    exit_phase_space_1.material = "G4_AIR"
    exit_phase_space_1.translation = [0, 0, -0.3 * m + 1 * nm]
    exit_phase_space_1.color = [0.5, 0.9, 0.3, 1]

    exit_phase_space_2 = sim.add_volume("Box", "exit_phase_space_2")
    exit_phase_space_2.mother = world.name
    exit_phase_space_2.size = [0.6 * m, 0.6 * m, 1 * nm]
    exit_phase_space_2.material = "G4_AIR"
    exit_phase_space_2.translation = [0, 0, -0.4 * m - 1 * nm]
    exit_phase_space_2.color = [0.5, 0.9, 0.3, 1]

    # print(sim.volume_manager.dump_volume_tree())
    liste_phase_space_name = [
        entry_phase_space.name,
        exit_phase_space_1.name,
        exit_phase_space_2.name,
    ]
    for name in liste_phase_space_name:

        phsp = sim.add_actor("PhaseSpaceActor", "PhaseSpace_" + name)
        phsp.mother = name
        phsp.attributes = ["EventID", "TrackID", "KineticEnergy"]
        name_phsp = "test074_" + name + ".root"
        phsp.output = output_path / name_phsp

    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option3"
    sim.physics_manager.enable_decay = False
    sim.physics_manager.global_production_cuts.gamma = 1 * mm
    sim.physics_manager.global_production_cuts.electron = 1 * mm
    sim.physics_manager.global_production_cuts.positron = 1 * mm

    s = sim.add_actor("SimulationStatisticsActor", "Stats")
    s.track_types_flag = True

    # go !
    sim.run()
    output = sim.output
    stats = sim.output.get_actor("Stats")
    print(stats)

    entry_phsp = uproot.open(
        str(output_path)
        + "/test074_"
        + liste_phase_space_name[0]
        + ".root"
        + ":PhaseSpace_"
        + liste_phase_space_name[0]
    )
    exit_phase_space_1 = uproot.open(
        str(output_path)
        + "/test074_"
        + liste_phase_space_name[1]
        + ".root"
        + ":PhaseSpace_"
        + liste_phase_space_name[1]
    )
    exit_phase_space_2 = uproot.open(
        str(output_path)
        + "/test074_"
        + liste_phase_space_name[2]
        + ".root"
        + ":PhaseSpace_"
        + liste_phase_space_name[2]
    )

    df_entry = entry_phsp.arrays()
    df_exit_1 = exit_phase_space_1.arrays()
    df_exit_2 = exit_phase_space_2.arrays()

    is_ok = test074_test(df_entry, df_exit_1, df_exit_2)

    utility.test_ok(is_ok)
