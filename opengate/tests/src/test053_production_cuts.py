#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate

# Physics list default range cut for protons, e+, e-, gamma
# defined in GEANT4/source/run/src/G4VUserPhysicsList.cc
DEFAULT_CUT = 1.0


def simulate(number_of_threads=1, start_new_process=False):
    # create the simulation
    energy = 200.0
    sim = gate.Simulation()
    sim.number_of_threads = number_of_threads

    # main options
    sim.g4_verbose = True
    sim.g4_verbose_level = 1
    sim.visu = False
    sim.random_engine = "MersenneTwister"

    cm = gate.g4_units.cm
    mm = gate.g4_units.mm
    MeV = gate.g4_units.MeV

    sim.physics_manager.physics_list_name = "G4EmStandardPhysics"
    global_cut = 1.34 * mm
    sim.physics_manager.global_production_cuts.electron = global_cut

    requested_cuts_proton = {}

    # *** Production cuts in a single volume ***
    waterbox_A = sim.add_volume("Box", "waterbox_A")
    waterbox_A.size = [10 * cm, 10 * cm, 10 * cm]
    waterbox_A.translation = [0 * cm, 0 * cm, 11 * cm]
    waterbox_A.material = "G4_WATER"

    # Choose an "awkward" cut
    # which does not corrispond to any of Geant4's
    # defaults to make the assertion (below) significant
    cut_proton = 10.7 * mm
    sim.physics_manager.set_production_cut(waterbox_A.name, "proton", cut_proton)
    requested_cuts_proton[waterbox_A.name] = cut_proton

    # *** Production cuts in individual volumes in nested volume structure ***
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
        # Set cut in every second insert
        if i % 2 == 0:
            cut_proton = 2.1 + i / 100.0 * mm
            sim.physics_manager.set_production_cut(
                new_insert.name, "proton", cut_proton
            )
            requested_cuts_proton[new_insert.name] = cut_proton

    # *** Production cuts propagated to nested volumes ***
    waterbox_C = sim.add_volume("Box", "waterbox_C")
    waterbox_C.size = waterbox_A.size
    waterbox_C.translation = [
        0 * cm,
        0 * cm,
        waterbox_B.translation[2] + 1.1 * waterbox_C.size[2],
    ]
    waterbox_C.material = "G4_WATER"

    cut_proton = 3.39 * mm
    sim.physics_manager.set_production_cut(waterbox_C.name, "proton", cut_proton)
    requested_cuts_proton[waterbox_C.name] = cut_proton

    previous_mother = waterbox_C
    for i in range(6):
        new_insert = sim.add_volume("Box", f"insert_C_{i}")
        new_insert.size = [0.9 * s for s in previous_mother.size]
        new_insert.material = waterbox_C.material
        new_insert.mother = previous_mother.name
        previous_mother = new_insert
        requested_cuts_proton[new_insert.name] = cut_proton

    # *** Production cuts set via region object ***
    region_D = sim.physics_manager.add_region("region_D")
    region_D.production_cuts.proton = 4.87 * mm

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
        requested_cuts_proton[new_box.name] = region_D.production_cuts.proton

    # Arbritrary source because we do not really need
    # the simulation, only the initialization
    source = sim.add_source("GenericSource", "Default")
    source.particle = "proton"
    source.energy.mono = energy * MeV
    source.position.radius = 1 * mm
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    source.n = 1e1

    print(sim.physics_manager.dump_production_cuts())

    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.track_types_flag = True

    # Set the hook function user_fct_after_init
    # to the function defined below
    sim.user_hook_after_init = check_production_cuts
    sim.run(start_new_process=start_new_process)

    # get results
    print(stats)
    print("track type", stats.counts.track_types)

    print("Checking production cuts:")
    retrieved_global_cut_proton = None
    for item in sim.user_hook_log:
        if item[0] == "world":
            retrieved_global_cut_proton = item[1]["proton"]
            retrieved_global_cut_positron = item[1]["positron"]
            retrieved_global_cut_electron = item[1]["electron"]
            retrieved_global_cut_gamma = item[1]["gamma"]

            print("retrieved_global_cut_positron")
            print(retrieved_global_cut_positron)

            # Verify that cuts are global cuts in volumes beloging to DefaultWorldRegion
            # global cut has been set for electron
            assert retrieved_global_cut_electron == global_cut
            # but not for the others, so the physics list default is applied
            assert retrieved_global_cut_proton == DEFAULT_CUT
            assert retrieved_global_cut_positron == DEFAULT_CUT
            assert retrieved_global_cut_gamma == DEFAULT_CUT

    for item in sim.user_hook_log:
        print(f"Volume {item[0]}:")
        value_dict = item[1]
        if item[0] != "world":
            if item[0] in requested_cuts_proton.keys():
                print(
                    f"Requested production cut for protons: {requested_cuts_proton[item[0]]}"
                )
                print(f"Found: {value_dict['proton']}")
                assert requested_cuts_proton[item[0]] == value_dict["proton"]
            else:
                print(
                    f"Found production cut for protons, {value_dict['proton']}, but no requested cut."
                )
                if value_dict["proton"] == retrieved_global_cut_proton:
                    print(
                        "... but don't worry, this is just the global cut as expected."
                    )
                else:
                    print(
                        "... and that is strange because it does not match the global cut. "
                    )
                    # raise Exception("Found unexpected production cut")
            # NB: because region cuts were only set for protons
            # we should find the user-specified global cut for electrons
            assert value_dict["electron"] == global_cut
            # # and the physics list default (= 1.0) for the others
            assert value_dict["positron"] == DEFAULT_CUT
            assert value_dict["gamma"] == DEFAULT_CUT
            print(value_dict)

    print("Test passed")


def check_production_cuts(simulation_engine):
    """Function to be called by opengate after initialization
    of the simulation, i.e. when G4 volumes and regions exist.
    The purpose is to check whether Geant4 has properly set
    the production cuts in the specific region.

    The information is stored in the attribute hook_log
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

            pc = volume.g4_region.GetProductionCuts()
            cut_proton = pc.GetProductionCut("proton")
            # Note: G4 particle names != Gate names for e+ and e-
            cut_positron = pc.GetProductionCut("e+")
            cut_electron = pc.GetProductionCut("e-")
            cut_gamma = pc.GetProductionCut("gamma")
            simulation_engine.user_hook_log.append(
                (
                    volume_name,
                    {
                        "proton": cut_proton,
                        "positron": cut_positron,
                        "electron": cut_electron,
                        "gamma": cut_gamma,
                    },
                )
            )
            print(f"In hook: found production cut for protons {cut_proton}")


# --------------------------------------------------------------------------
if __name__ == "__main__":
    simulate(number_of_threads=1, start_new_process=False)
    # simulate(number_of_threads=2, start_new_process=False)
    # simulate(number_of_threads=1, start_new_process=True)
    # simulate(number_of_threads=2, start_new_process=True)
