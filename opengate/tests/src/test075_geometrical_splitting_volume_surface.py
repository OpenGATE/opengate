#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
from scipy.spatial.transform import Rotation
import numpy as np
from anytree import Node, RenderTree
import uproot


def test075(entry_data, exit_data, splitting_factor):
    splitted_particle_data_entry = entry_data[
        entry_data["TrackCreatorProcess"] == "none"
    ]

    splitted_particle_data_exit = exit_data[exit_data["TrackCreatorProcess"] == "none"]

    array_weight_1 = splitted_particle_data_entry["Weight"]
    array_weight_2 = splitted_particle_data_exit["Weight"]

    if (np.round(np.sum(array_weight_1), 3) == 1) and len(
        array_weight_1
    ) == splitting_factor:
        if (np.round(np.sum(array_weight_2), 3) == 1) and len(
            array_weight_2
        ) == splitting_factor:
            return True
        else:
            return False
    else:
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

    #  adapt world size
    world = sim.world
    world.size = [1 * m, 1 * m, 1 * m]
    world.material = "G4_Galactic"

    big_box = sim.add_volume("Box", "big_box")
    big_box.mother = world.name
    big_box.material = "G4_Galactic"
    big_box.size = [0.8 * m, 0.8 * m, 0.8 * m]

    actor_box = sim.add_volume("Box", "actor_box")
    actor_box.mother = big_box.name
    actor_box.material = "G4_Galactic"
    actor_box.size = [0.6 * m, 0.6 * m, 0.6 * m]
    actor_box.translation = [0, 0, -0.1 * m]

    source_1 = sim.add_source("GenericSource", "elec_source_1")
    source_1.particle = "e-"
    source_1.position.type = "box"
    source_1.mother = big_box.name
    source_1.position.size = [1 * cm, 1 * cm, 1 * cm]
    source_1.position.translation = [0, 0.35 * m, 0]
    source_1.direction.type = "momentum"
    source_1.direction.momentum = [0, -1, 0]
    source_1.energy.type = "mono"
    source_1.energy.mono = 10 * MeV
    source_1.n = 1

    source_2 = sim.add_source("GenericSource", "elec_source_2")
    source_2.particle = "e-"
    source_2.position.type = "box"
    source_2.mother = big_box.name
    source_2.position.size = [1 * cm, 1 * cm, 1 * cm]
    source_2.position.translation = [0, 0, -0.39 * m]
    source_2.direction.type = "momentum"
    source_2.direction.momentum = [0, 0, -1]
    source_2.energy.type = "mono"
    source_2.energy.mono = 10 * MeV
    source_2.n = 1

    geom_splitting = sim.add_actor("SurfaceSplittingActor", "splitting_act")
    geom_splitting.mother = actor_box.name
    geom_splitting.splitting_factor = 10
    geom_splitting.weight_threshold = 1
    geom_splitting.split_entering_particles = True
    geom_splitting.split_exiting_particles = True

    entry_phase_space = sim.add_volume("Box", "entry_phase_space")
    entry_phase_space.mother = actor_box
    entry_phase_space.size = [0.6 * m, 1 * nm, 0.6 * m]
    entry_phase_space.material = "G4_Galactic"
    entry_phase_space.translation = [0, 0.3 * m - 0.5 * nm, 0]
    entry_phase_space.color = [0.5, 0.9, 0.3, 1]

    exit_phase_space = sim.add_volume("Box", "exit_phase_space")
    exit_phase_space.mother = world.name
    exit_phase_space.size = [0.6 * m, 0.6 * m, 1 * nm]
    exit_phase_space.material = "G4_Galactic"
    exit_phase_space.translation = [0, 0, -0.4 * m - 1 * nm]
    exit_phase_space.color = [0.5, 0.9, 0.3, 1]

    # # print(sim.volume_manager.dump_volume_tree())
    liste_phase_space_name = [
        entry_phase_space.name,
        exit_phase_space.name,
    ]
    for name in liste_phase_space_name:

        phsp = sim.add_actor("PhaseSpaceActor", "PhaseSpace_" + name)
        phsp.mother = name
        phsp.attributes = [
            "EventID",
            "TrackID",
            "Weight",
            "PDGCode",
            "TrackCreatorProcess",
        ]
        name_phsp = "test075_" + name + ".root"
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

    #
    entry_phsp = uproot.open(
        str(output_path)
        + "/test075_"
        + liste_phase_space_name[0]
        + ".root"
        + ":PhaseSpace_"
        + liste_phase_space_name[0]
    )
    exit_phase_space = uproot.open(
        str(output_path)
        + "/test075_"
        + liste_phase_space_name[1]
        + ".root"
        + ":PhaseSpace_"
        + liste_phase_space_name[1]
    )

    #
    df_entry = entry_phsp.arrays()
    df_exit = exit_phase_space.arrays()
    #

    is_ok = test075(df_entry, df_exit, geom_splitting.splitting_factor)

    utility.test_ok(is_ok)
