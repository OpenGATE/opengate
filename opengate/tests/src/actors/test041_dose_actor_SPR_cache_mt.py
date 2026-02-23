#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from scipy.spatial.transform import Rotation
import matplotlib.pyplot as plt
from opengate.tests import utility

if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, "gate_test041_dose_actor_SPR_cache", "test041"
    )

    # create the simulation
    sim = gate.Simulation()

    # main options
    sim.g4_verbose = False
    sim.g4_verbose_level = 1
    sim.visu = False
    sim.random_seed = 123456
    sim.number_of_threads = 5
    sim.output_dir = paths.output

    # units
    m = gate.g4_units.m
    cm = gate.g4_units.cm
    mm = gate.g4_units.mm
    km = gate.g4_units.km
    MeV = gate.g4_units.MeV
    Bq = gate.g4_units.Bq
    kBq = 1000 * Bq

    # add a material database
    # sim.add_material_database(paths.gate_data / "HFMaterials2014.db")

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

    # Silicon scorer
    phantom_off = sim.add_volume("Box", "phantom_off")
    phantom_off.mother = phantom.name
    phantom_off.size = [100 * mm, 20 * mm, 20 * mm]
    phantom_off.translation = [0 * mm, 0 * mm, 0 * mm]
    phantom_off.material = "G4_Si"
    phantom_off.color = [0, 0, 1, 1]

    # physics
    sim.physics_manager.physics_list_name = "QGSP_BIC_EMY"
    sim.physics_manager.global_production_cuts.all = 1000 * km
    # sim.set_cut("world", "all", 1000 * km)

    # default source for tests
    source = sim.add_source("GenericSource", "mysource")
    source.energy.mono = 100 * MeV
    source.particle = "proton"
    source.position.type = "disc"  # pos = Beam, shape = circle + sigma
    # rotate the disc, equiv to : rot1 0 1 0 and rot2 0 0 1
    source.position.rotation = Rotation.from_euler("y", 90, degrees=True).as_matrix()
    # source.position.radius = 8 * mm
    source.position.sigma_x = 2 * mm
    source.position.sigma_y = 2 * mm
    source.position.translation = [0, 0, 0]
    source.direction.type = "momentum"
    source.direction.momentum = [-1, 0, 0]
    source.n = 1000

    # first actor scores dose to water on the fly -> reference
    dose_spr_on_the_fly = sim.add_actor("DoseActor", "dose_spr_on_the_fly")
    dose_spr_on_the_fly.attached_to = phantom_off
    dose_spr_on_the_fly.size = [1000, 1, 1]
    dose_spr_on_the_fly.spacing = [0.1, 20.0, 20.0]
    dose_spr_on_the_fly.dose.active = True
    dose_spr_on_the_fly.score_in = "G4_WATER"

    # second actor scores dose to water assuming SPR constant with energy
    dose_spr_const = sim.add_actor("DoseActor", "dose_spr_const")
    dose_spr_const.attached_to = phantom_off
    dose_spr_const.size = [1000, 1, 1]
    dose_spr_const.spacing = [0.1, 20.0, 20.0]
    dose_spr_const.dose.active = True
    dose_spr_const.score_in = "G4_WATER"
    dose_spr_const.assume_constant_SPR_per_material = True
    dose_spr_const.constant_energy_SPR = 10 * MeV

    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "stats")
    stats.track_types_flag = True

    # start simulation
    sim.run(start_new_process=True)

    # print results at the end
    print(stats)

    # ----------------------------------------------------------------------------------------------------------------
    # tests
    is_ok = utility.assert_images(
        dose_spr_on_the_fly.dose.get_output_path(),
        dose_spr_const.dose.get_output_path(),
        stats,
        tolerance=100,
        ignore_value_data2=0,
        axis="x",
    )
    utility.test_ok(is_ok)
    # x, d_on_the_fly = utility.get_image_1d_profile(dose_spr_on_the_fly.dose.get_output_path(), 'x')
    # x, d_spr_const = utility.get_image_1d_profile(dose_spr_const.dose.get_output_path(), 'x')
    # fig, ax = plt.subplots(2)
    # ax[0].plot(x,d_on_the_fly,label = 'ref')
    # ax[0].plot(x,d_spr_const,label = 'test')
    # ax[0].legend()
    # ax[0].set_ylabel('Dose2Water [Gy]')
    # ax[1].set_xlabel('x [mm]')
    # ax[1].set_ylabel('Dose2Water difference [Gy]')
    # ax[1].plot(x, d_spr_const-d_on_the_fly)
    # plt.savefig("diff.png")
