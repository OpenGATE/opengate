#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import uproot
import numpy as np
from opengate.tests import utility

# units
m = gate.g4_units.m
mm = gate.g4_units.mm
cm = gate.g4_units.cm
nm = gate.g4_units.nm
Bq = gate.g4_units.Bq
MeV = gate.g4_units.MeV
deg = gate.g4_units.deg


def is_test_ok(phsp_1, phsp_2):
    f1 = uproot.open(str(phsp_1) + ":PhaseSpace1")
    f2 = uproot.open(str(phsp_2) + ":PhaseSpace1")
    df1 = f1.arrays()
    df2 = f2.arrays()

    # print(df1.data,type(df1))
    for key in df1.fields:
        data_1 = df1[key]
        data_2 = df2[key]
        mean_data_1 = np.mean(data_1)
        mean_data_2 = np.mean(data_2)
        std_dev_data_1 = np.std(data_1, ddof=1)
        std_dev_data_2 = np.std(data_2, ddof=1)

        std_err = np.sqrt(
            (std_dev_data_1 / np.sqrt(len(data_1))) ** 2
            + (std_dev_data_2 / np.sqrt(len(data_2)) ** 2)
        )
        print("data 1 mean for " + key + " = " + str(mean_data_1))
        print("data 2 mean for " + key + " = " + str(mean_data_2))
        print("standard error for " + key + " = " + str(std_err))
        print("")
        if np.abs(mean_data_1 - mean_data_2) / std_err > 4:
            return False
    return True


def add_source(sim, plan_to_attach):
    source = sim.add_source("GenericSource", "GenSource")
    source.particle = "gamma"
    source.n = 10000
    source.position.type = "disc"
    radius = plan_to_attach.rmax
    source.position.radius = radius
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    source.energy.type = "mono"
    source.energy.mono = 1 * MeV
    source.attached_to = plan_to_attach.name


def add_source_2(sim, plan_to_attach):
    source = sim.add_source("GenericSource", "GenSource")
    source.particle = "gamma"
    source.n = 10000
    source.position.type = "disc"
    radius = plan_to_attach.rmax
    source.position.radius = radius
    source.direction.type = "iso"
    source.energy.type = "mono"
    source.energy.mono = 1 * MeV
    source.attached_to = plan_to_attach.name


def add_phsp_source(sim, plan_to_attach):
    source = sim.add_source("PhaseSpaceSource", "phsp_source_global")
    paths = utility.get_default_test_paths(__file__, "", "test060")
    source.phsp_file = paths.output / "test060_phsp_isotropic.root"
    source.isotropic_direction = True
    source.position_key = "PrePositionLocal"
    source.direction_key = "PreDirectionLocal"
    source.global_flag = True
    source.particle = "gamma"
    source.batch_size = 50000
    source.n = 10000
    source.verbose = False
    source.attached_to = plan_to_attach.name
    return source


def add_phsp_sphere_actor(sim, name):
    cm = gate.g4_units.cm
    nm = gate.g4_units.nm
    sphere = sim.volume_manager.add_volume("Sphere", "a_sphere")
    sphere.rmin = 50 * cm
    sphere.rmax = sphere.rmin + 1 * nm

    ta1 = sim.add_actor("PhaseSpaceActor", "PhaseSpace1")
    ta1.attached_to = sphere.name
    ta1.attributes = [
        "KineticEnergy",
        "Weight",
        "PrePosition",
        "PrePositionLocal",
        "PreDirection",
        "PreDirectionLocal",
        "PDGCode",
    ]
    ta1.output_filename = name


def add_phsp_actor(sim, plan_to_attach):
    ta1 = sim.add_actor("PhaseSpaceActor", "PhaseSpace1")
    ta1.attached_to = plan_to_attach.name
    ta1.attributes = [
        "KineticEnergy",
        "Weight",
        "PrePosition",
        "PrePositionLocal",
        "PreDirection",
        "PreDirectionLocal",
        "PDGCode",
    ]
    ta1.output_filename = "test060_phsp_isotropic.root"


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "", "test060")

    for i in range(3):
        sim = gate.Simulation()
        # main options
        sim.output_dir = paths.output
        print(sim.output_dir)
        sim.g4_verbose = False
        # sim.visu = True
        sim.visu_type = "vrml"
        sim.check_volumes_overlap = False
        # sim.running_verbose_level = gate.EVENT
        sim.number_of_threads = 1
        sim.random_seed = 987654321

        # units
        m = gate.g4_units.m
        cm = gate.g4_units.cm
        nm = gate.g4_units.nm
        MeV = gate.g4_units.MeV

        ##########################################################################################
        # geometry
        ##########################################################################################
        #  adapt world size
        world = sim.world
        world.size = [1 * m, 1 * m, 1 * m]
        world.material = "G4_Galactic"

        # virtual plane for phase space
        s_plane = sim.add_volume("Tubs", "source_plane")
        # plane.material = "G4_AIR"
        s_plane.material = "G4_Galactic"
        s_plane.rmin = 0
        s_plane.rmax = 30 * cm
        s_plane.dz = 1 * nm  # half height
        # plane.rotation = Rotation.from_euler("xy", [180, 30], degrees=True).as_matrix()
        s_plane.translation = [0 * mm, 0 * mm, 0 * mm]
        s_plane.color = [1, 0, 0, 1]  # red

        plane = sim.add_volume("Tubs", "phsp_actor_plane")
        # plane.material = "G4_AIR"
        plane.material = "G4_Galactic"
        plane.rmin = 0
        plane.rmax = 30 * cm
        plane.dz = 1 * nm  # half height
        # plane.rotation = Rotation.from_euler("xy", [180, 30], degrees=True).as_matrix()
        plane.translation = [0 * mm, 0 * mm, 1 * cm]
        plane.color = [1, 0, 0, 1]  # red

        ##########################################################################################
        # Actors
        ##########################################################################################
        # PhaseSpace Actor

        if i == 0:
            add_source(sim, s_plane)
            add_phsp_actor(sim, plane)
        if i == 1:
            add_source_2(sim, s_plane)
            add_phsp_sphere_actor(sim, "test060_phsp_actor_sphere_ref.root")

        if i == 2:
            add_phsp_source(sim, s_plane)
            add_phsp_sphere_actor(sim, "test060_phsp_actor_sphere_phsp.root")

        sim.run(start_new_process=True)

    is_ok = is_test_ok(
        paths.output / "test060_phsp_actor_sphere_ref.root",
        paths.output / "test060_phsp_actor_sphere_phsp.root",
    )
    utility.test_ok(is_test_ok)
