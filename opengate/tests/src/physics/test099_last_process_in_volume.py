#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from opengate.tests.utility import *
from opengate.managers import Simulation
from opengate.actors.digitizers import *
import uproot
import numpy as np
import pandas as pd


def test099(df, l_att):
    nb_processes_layer_0 = df[l_att[1]] + df[l_att[2]]
    nb_processes_layer_1 = df[l_att[3]] + df[l_att[4]]
    nb_processes_tot = nb_processes_layer_0 + nb_processes_layer_1
    df_selec = df[
        (nb_processes_layer_0 <= 1)
        & (nb_processes_layer_1 <= 1)
        & (nb_processes_tot == 2)
    ]
    last_process = df_selec[l_att[0]].to_numpy()
    last_process_int = np.zeros(len(last_process))
    for i in range(len(last_process_int)):
        if last_process[i] == "compt":
            last_process_int[i] = 1
    compt_layer_1 = df_selec[l_att[3]]
    process_recorded = np.zeros(len(last_process))
    process_recorded[compt_layer_1 == 1] = 1
    print(
        f"Difference between recorded event using the process defined step and the last occuring process : {np.sum(process_recorded - last_process_int)}"
    )
    if np.sum(process_recorded - last_process_int) == 0:
        return True
    return False


if __name__ == "__main__":
    paths = get_default_test_paths(__file__, None, "test099")

    # units
    m = g4_units.m
    mm = g4_units.mm
    nm = g4_units.nm
    cm = g4_units.cm
    keV = g4_units.keV

    # simulation
    sim = Simulation()
    world = sim.world
    world.size = [50 * cm, 50 * cm, 20 * cm]
    world.material = "G4_Galactic"

    # sim.progress_bar = True
    # sim.visu = True
    sim.visu_type = "vrml"
    sim.output_dir = paths.output
    sim.random_seed = 32145987

    # add a volume
    vacuum_box = sim.add_volume("Box", "Vacuum_box")
    vacuum_box.size = [20 * cm, 20 * cm, 10 * cm]
    vacuum_box.translation = [0 * cm, 0 * cm, 0 * cm]
    vacuum_box.material = "G4_Galactic"
    vacuum_box.mother = world.name

    detector_plan = sim.add_volume("Box", "plan_phsp")
    detector_plan.size = [world.size[0], world.size[1], 1 * nm]
    detector_plan.translation = [0, 0, 9.9 * cm]
    detector_plan.color = [0.8, 0.6, 0.4, 0.4]

    phsp = sim.add_actor("PhaseSpaceActor", "PhaseSpace")
    phsp.attached_to = detector_plan.name
    att = LastProcessDefinedStepInVolumeAttribute(sim, vacuum_box.name)

    l_att = []
    l_att.append(att.name)
    for i in range(2):
        layer = sim.add_volume("Box", f"layer_{i}")
        layer.material = "G4_WATER"
        layer.mother = vacuum_box.name
        if i == 0:
            layer.size = [1 * nm, 1 * nm, 2 * cm]
        else:
            layer.size = [20 * cm, 20 * cm, 2 * cm]
        layer.translation = [0, 0, -vacuum_box.size[2] / 2 + 4.5 * (i + 1) * cm]
        layer.color = [0.9, 0.7, 0.8, 0.1]
        att1 = ProcessDefinedStepInVolumeAttribute(sim, "compt", layer.name)
        att2 = ProcessDefinedStepInVolumeAttribute(sim, "Rayl", layer.name)
        l_att.append(att1.name)
        l_att.append(att2.name)

    l_all_attributes = ["EventID", "TrackID"] + l_att
    phsp.attributes = l_all_attributes

    print(phsp.attributes)

    # source 1
    source = sim.add_source("GenericSource", "low_energy")
    source.particle = "gamma"
    source.energy.mono = 45 * keV
    source.position.type = "sphere"
    source.position.radius = 0.1 * nm
    source.position.translation = [0 * cm, 0 * cm, -6 * cm]
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    source.n = 10000

    # add a stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.track_types_flag = True

    # needed for Rayl !
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option3"
    phsp.output_filename = "phsp_test.root"

    # go
    sim.run()
    #
    # # check
    # ref_root = paths.output_ref / "phsp.root"
    test_root = paths.output / "phsp_test.root"
    f = uproot.open(f"{test_root}:PhaseSpace")
    df = f.arrays(library="pd")
    is_ok = test099(df, l_att)
    test_ok(is_ok)
