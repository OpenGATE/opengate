#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import opengate_core as g4


def simulate(number_of_threads=1, start_new_process=False):
    # create the simulation
    energy = 200.0
    sim = gate.Simulation()
    sim.number_of_threads = number_of_threads

    # main options
    sim.g4_verbose = True
    sim.g4_verbose_level = 0
    sim.visu = False
    sim.random_engine = "MersenneTwister"

    cm = gate.g4_units.cm
    mm = gate.g4_units.mm
    MeV = gate.g4_units.MeV

    requested_stepsizes = {}
    requested_minekine = {}

    sim.physics_manager.set_user_limits_particles("gamma")

    # *** Step size in a single volume ***
    waterbox_A = sim.add_volume("Box", "waterbox_A")
    waterbox_A.size = [10 * cm, 10 * cm, 10 * cm]
    waterbox_A.translation = [0 * cm, 0 * cm, 11 * cm]
    waterbox_A.material = "G4_WATER"

    # Choose an "awkward" step size
    # which does not correspond to any of Geant4's
    # defaults to make the assertion (below) significant
    stepsize = 1.47 * mm
    min_ekine = 10.7 * MeV
    sim.physics_manager.set_max_step_size(waterbox_A.name, stepsize)
    sim.physics_manager.set_min_ekine(waterbox_A.name, min_ekine)
    requested_stepsizes[waterbox_A.name] = stepsize
    requested_minekine[waterbox_A.name] = min_ekine

    # *** Step sizes in individual volumes in nested volume structure ***
    waterbox_B = sim.add_volume("Box", "waterbox_B")
    waterbox_B.size = waterbox_A.size
    waterbox_B.translation = [
        0 * cm,
        0 * cm,
        waterbox_A.translation[2] + 1.1 * waterbox_B.size[2],
    ]
    waterbox_B.material = "G4_WATER"

    previous_mother = waterbox_B
    for i in range(6):
        new_insert = sim.add_volume("Box", f"insert_B_{i}")
        new_insert.size = [0.9 * s for s in previous_mother.size]
        new_insert.material = waterbox_B.material
        new_insert.mother = previous_mother.name
        previous_mother = new_insert
        # Set step in every second insert
        stepsize = 2.1 + i / 100.0 * mm
        min_ekine = 20.1 + i / 100.0 * MeV
        sim.physics_manager.set_max_step_size(new_insert.name, stepsize)
        sim.physics_manager.set_min_ekine(new_insert.name, min_ekine)
        requested_stepsizes[new_insert.name] = stepsize
        requested_minekine[new_insert.name] = min_ekine

    # *** Step sizes propagated to nested volumes ***
    waterbox_C = sim.add_volume("Box", "waterbox_C")
    waterbox_C.size = waterbox_A.size
    waterbox_C.translation = [
        0 * cm,
        0 * cm,
        waterbox_B.translation[2] + 1.1 * waterbox_C.size[2],
    ]
    waterbox_C.material = "G4_WATER"

    stepsize_C = 3.39 * mm
    min_ekine = 30.39 * MeV
    sim.physics_manager.set_max_step_size(waterbox_C.name, stepsize_C)
    sim.physics_manager.set_min_ekine(waterbox_C.name, min_ekine)
    requested_stepsizes[waterbox_C.name] = stepsize_C
    requested_minekine[waterbox_C.name] = min_ekine

    previous_mother = waterbox_C
    for i in range(6):
        new_insert = sim.add_volume("Box", f"insert_C_{i}")
        new_insert.size = [0.9 * s for s in previous_mother.size]
        new_insert.material = waterbox_C.material
        new_insert.mother = previous_mother.name
        previous_mother = new_insert
        requested_stepsizes[new_insert.name] = stepsize_C
        requested_minekine[new_insert.name] = min_ekine

    # *** Step size set via region object ***
    region_D = sim.physics_manager.add_region("region_D")
    region_D.max_step_size = 4.87 * mm
    region_D.min_ekine = 40.87 * MeV

    for i in range(4):
        new_box = sim.add_volume("Box", f"waterbox_D{i}")
        new_box.size = [1 * mm, 1 * mm, 1 * mm]
        new_box.translation = [
            i * 2 * cm,
            0 * cm,
            waterbox_C.translation[2] + 1.1 * waterbox_C.size[2],
        ]
        new_box.material = "G4_WATER"
        region_D.associate_volume(new_box)
        requested_stepsizes[new_box.name] = region_D.user_limits.max_step_size
        requested_minekine[new_box.name] = region_D.user_limits.min_ekine

    # Arbritrary source because we do not really need
    # the simulation, only the initialization
    source = sim.add_source("GenericSource", "Default")
    source.particle = "proton"
    source.energy.mono = energy * MeV
    source.position.radius = 1 * mm
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    source.n = 1e1

    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.track_types_flag = False

    # se = gate.SimulationEngine(sim)
    # Set the hook function user_fct_after_init
    # to the function defined below
    sim.user_hook_after_init = check_user_limit
    sim.run(start_new_process=start_new_process)

    # get results
    print("**** STATS ****")
    print(stats)
    print("track type", stats.counts.track_types)
    print("**** STATS END ****")

    print("Checking step limits:")
    for item in sim.user_hook_log:
        print(f"Volume {item[0]}:")
        value_dict = item[1]
        print(f"Requested max_step_size: {requested_stepsizes[item[0]]}")
        print(f"Found: {value_dict['max_step_size']}")
        print(f"Requested min_ekine: {requested_minekine[item[0]]}")
        print(f"Found: {value_dict['min_ekine']}")
        assert requested_stepsizes[item[0]] == value_dict["max_step_size"]
        assert requested_minekine[item[0]] == value_dict["min_ekine"]
    print("Test passed")


def check_user_limit(simulation_engine):
    """Function to be called by opengate after initialization
    of the simulation, i.e. when G4 volumes and regions exist.
    The purpose is to check whether Geant4 has properly set
    the step limit in the specific region.

    The value max_step_size is stored in the attribute hook_log
    which can be accessed via the output of the simulation.

    """
    print(f"Entered hook")
    for (
        volume_name,
        volume,
    ) in simulation_engine.simulation.volume_manager.volumes.items():
        # print(volume_name, g4_volume.g4_region)
        if volume.g4_region is not None:
            region_name = volume.g4_region.GetName()
            print(f"In hook: found volume {volume_name} with region {region_name}")
            user_limits = volume.g4_region.GetUserLimits()
            print(f"In hook: found UserLimit {user_limits}")

            ul = volume.g4_region.GetUserLimits()
            # UserLimit is None for the DefaultWorldRegion
            if ul is not None:
                max_step_size = volume.g4_region.GetUserLimits().GetMaxAllowedStep(
                    g4.G4Track()
                )
                min_ekine = volume.g4_region.GetUserLimits().GetUserMinEkine(
                    g4.G4Track()
                )
                simulation_engine.user_hook_log.append(
                    (
                        volume_name,
                        {"max_step_size": max_step_size, "min_ekine": min_ekine},
                    )
                )
                print(f"In hook: found max_step_size {max_step_size}")
            else:
                print("UserLimits is None")

    # Check whether the particle 'gamma' actually has
    # the requested processes attached to it
    p_name = "gamma"
    g4_particle_table = g4.G4ParticleTable.GetParticleTable()
    particle = g4_particle_table.FindParticle(particle_name=p_name)
    # FindParticle returns nullptr if particle name was not found
    if particle is None:
        raise Exception(f"Something went wrong. Could not find particle {p_name}.")
    pm = particle.GetProcessManager()
    p = pm.GetProcess("StepLimiter")
    # GetProcess returns nullptr if the requested process was not found
    if p is None:
        raise Exception(
            f"Could not find the StepLimiter process for particle {p_name}."
        )
    else:
        print(f"Hooray, I found the process StepLimiter for the particle {p_name}!")
    p = pm.GetProcess("UserSpecialCut")
    if p is None:
        raise Exception(
            f"Could not find the UserSpecialCut process for particle {p_name}."
        )
    else:
        print(f"Hooray, I found the process UserSpecialCut for the particle {p_name}!")


# --------------------------------------------------------------------------
if __name__ == "__main__":
    # simulate(number_of_threads=1, start_new_process=False)
    # simulate(number_of_threads=2, start_new_process=False)
    # simulate(number_of_threads=1, start_new_process=True)
    simulate(number_of_threads=2, start_new_process=True)
