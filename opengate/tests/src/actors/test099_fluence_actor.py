#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
import numpy as np
import uproot
import itk
import pandas as pd



def std_dev_img_calculation(N,sum_E,squared_sum_E):
    return( np.sqrt((1/(N-1)) * ((squared_sum_E/N) - (sum_E/N)**2)))



def img_generation_from_phsp(nb_pixel_x,nb_pixel_y,dim_x,dim_y,df,type = "E"):
    x_edges = np.linspace(-dim_x / 2, dim_x / 2, nb_pixel_x + 1)
    y_edges = np.linspace(-dim_y / 2, dim_y / 2, nb_pixel_y + 1)
    spacing = np.array([x_edges[1] - x_edges[0],y_edges[1] - y_edges[0]])
    origin = np.array([x_edges[0],y_edges[0]])

    df[["PrePositionLocal_X","PrePositionLocal_Y"]] = (df[["PrePositionLocal_X","PrePositionLocal_Y"]] - origin)/spacing
    df[["PrePositionLocal_X","PrePositionLocal_Y"]]  = df[["PrePositionLocal_X","PrePositionLocal_Y"]] .astype(int)
    if type == "E":
        df["KineticEnergy"] = df["KineticEnergy"] * df["Weight"]
    elif type == "C" :
        df["KineticEnergy"] = df["Weight"]


    df_merge_evt = df.groupby(["EventID","PrePositionLocal_X","PrePositionLocal_Y"]).agg(KineticEnergy=("KineticEnergy", "sum")).reset_index()
    size = int(df_merge_evt.size/4)
    df_merge_evt[["PrePositionLocal_X","PrePositionLocal_Y"]] = (df_merge_evt[["PrePositionLocal_X","PrePositionLocal_Y"]].astype(float) + np.random.random(size =(size,2)))*spacing +origin
    df_squared = df_merge_evt.copy()
    df_squared["KineticEnergy"] = df_squared["KineticEnergy"]**2

    H,_,_ = np.histogram2d(df_merge_evt["PrePositionLocal_Y"], df_merge_evt["PrePositionLocal_X"], bins=[x_edges, y_edges], weights=df_merge_evt["KineticEnergy"])
    H2,_,_ = np.histogram2d(df_squared["PrePositionLocal_Y"], df_squared["PrePositionLocal_X"], bins=[x_edges, y_edges], weights=df_squared["KineticEnergy"])

    return H,H2


if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, "gate_test099_fluence_actor", "test099"
    )

    # create the simulation
    sim = gate.Simulation()

    # main options
    sim.g4_verbose = False
    sim.g4_verbose_level = 1
    # sim.visu = True
    sim.random_seed = 123456
    sim.output_dir = paths.output
    ui = sim.user_info
    # ui.running_verbose_level = gate.logger.EVENT

    # units
    m = gate.g4_units.m
    cm = gate.g4_units.cm
    mm = gate.g4_units.mm
    nm = gate.g4_units.nm
    MeV = gate.g4_units.MeV
    Bq = gate.g4_units.Bq

    #  change world size
    world = sim.world
    world.material = "G4_AIR"
    world.size = [0.5 * m, 0.5 * m, 0.5 * m]

    # waterbox
    fluence_plane = sim.add_volume("Box", "air_plane")
    fluence_plane.size = [10 * cm, 10 * cm, 1*nm]
    fluence_plane.material = "G4_AIR"
    fluence_plane.color = [0, 0, 1, 1]

    # physics
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option3"
    sim.physics_manager.global_production_cuts.all = 1 * mm

    # default source for tests
    source = sim.add_source("GenericSource", "mysource")
    source.energy.type = "gauss"
    source.energy.mono = 5 * MeV
    source.energy.sigma_gauss = 2* MeV
    source.particle = "gamma"
    source.position.type = "disc"
    source.position.radius = 1 * cm
    source.position.translation = [0, 0, -80 * mm]
    source.direction.type = "iso"
    source.n = 30000

    # add fluence actor
    fluence_actor = sim.add_actor("FluenceActor", "fluence_actor")
    # let the actor score other quantities additional to edep (default)
    fluence_actor.counts_uncertainty.active = True
    fluence_actor.counts_squared.active = True
    fluence_actor.energy.active = True
    fluence_actor.energy_uncertainty.active = True
    fluence_actor.energy_squared.active = True
    fluence_actor.output_filename = "test099.mhd"
    fluence_actor.attached_to = fluence_plane
    fluence_actor.size = [10,10,1]
    mm = gate.g4_units.mm
    ts = [10* cm, 10* cm, 1* nm]
    fluence_actor.spacing = [x / y for x, y in zip(ts, fluence_actor.size)]
    fluence_actor.hit_type = "random"


    ##add phase space actor

    phsp = sim.add_actor("PhaseSpaceActor", "PhaseSpace")
    phsp.attached_to = fluence_plane.name
    phsp.attributes = [
        "KineticEnergy",
        "EventID",
        "Weight",
        "PrePositionLocal",
        "ParticleName",
    ]
    phsp.output_filename = f"test099.root"

    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.track_types_flag = True

    # start simulation
    sim.run(start_new_process=False)
    print(stats)

    with uproot.open(f"{sim.output_dir}/{phsp.output_filename}:PhaseSpace") as tree:
        df = tree.arrays(library="pd")


    l_is_ok = np.zeros(2)
    for i,type in enumerate(("E","C")):
        tab, s_tab = img_generation_from_phsp(fluence_actor.size[0], fluence_actor.size[1], fluence_plane.size[0], fluence_plane.size[1], df.copy(),type = type)
        std_dev_tab = std_dev_img_calculation(source.n, tab, s_tab)
        rel_err_tab_phsp = np.divide(std_dev_tab,(tab / source.n))

        if type == "E" :
            rel_err_img = itk.imread(f"{sim.output_dir}/test099_energy_uncertainty.mhd")
        elif type =="C":
            rel_err_img = itk.imread(f"{sim.output_dir}/test099_counts_uncertainty.mhd")
        rel_err_tab_img = itk.GetArrayFromImage(rel_err_img)
        numpy_column_order = [2, 1, 0]
        rel_err_tab_img = np.transpose(rel_err_tab_img, numpy_column_order)
        rel_err_tab_img = rel_err_tab_img.reshape((rel_err_tab_img.shape[0], rel_err_tab_img.shape[1]))
        rel_err_tab_img = rel_err_tab_img.transpose()

        diff = np.round((rel_err_tab_img - rel_err_tab_phsp),6)
        is_ok = (np.all(diff == 0))
        l_is_ok[i] = is_ok
        if is_ok:
            if type =='E':
                print(f"No differences regarding errors on registered kinetic energy")
            else :
                print(f"No differences regarding errors on registered counts")
    is_ok = np.all(l_is_ok)
    utility.test_ok(is_ok)
