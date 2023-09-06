#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate_core import G4RegionStore

if __name__ == "__main__":

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

    """
    The following line is only used for tests, it store the paths where the
    reference data are stored.
    """
    paths = gate.get_default_test_paths(__file__, "gate_test004_simulation_stats_actor")

    """
    Create a simulation object. The class is 'gate.Simulation'.
    The single object that will contain all parameters of the
    simulation is called 'sim' here.
    """
    sim = gate.Simulation()

    """
    Main global options.
    The 'sim' object contains a structure called 'user_info' that gather all global options.
    - For example here, the verbosity is set (verbosity means texts that are displayed during
    the simulation run, mostly for debug)
    - 'visu', if ON, display a windows with a QT view of the scene.
    - random_engine and random_seed control the pseudo random engine. We recommend MersenneTwister.
      A seed can be specified, e.g. 123456, for reproducible simulation. Or you can use 'auto', an random seed
      will be generated.
    """
    ui = sim.user_info
    ui.verbose_level = gate.DEBUG
    ui.running_verbose_level = gate.RUN
    ui.g4_verbose = False
    ui.g4_verbose_level = 1
    ui.visu = False
    ui.random_engine = "MersenneTwister"
    ui.random_seed = "auto"
    print(ui)

    """
    Units. Get some default units from G4. To define a value with a unit, e.g. do:
    x = 123 * cm
    """
    m = gate.g4_units("m")
    cm = gate.g4_units("cm")
    keV = gate.g4_units("keV")
    mm = gate.g4_units("mm")
    um = gate.g4_units("um")
    Bq = gate.g4_units("Bq")

    """
    Set the world size (like in the Gate macro). World is the only volume created by default.
    It is described by a dict-like structure, accessible by sim.world.
    The size is set here, as a 3D vector. Default material is G4_AIR.
    """
    world = sim.world
    world.size = [3 * m, 3 * m, 3 * m]
    world.material = "G4_AIR"

    """
    A simple waterbox volume is created. It is inserted into the simulation with 'add_volume'.
    This function return a dict-like structure (called 'waterbox' here) with various parameters
    (size, position in the world, material). Note that, like in Geant4, the coordinate system
    of all volumes is the one of the mother volume (here the world).
    """
    waterbox = sim.add_volume("Box", "Waterbox")
    waterbox.size = [40 * cm, 40 * cm, 40 * cm]
    waterbox.translation = [0 * cm, 0 * cm, 25 * cm]
    waterbox.material = "G4_WATER"

    """
    The physic list by default is 'QGSP_BERT_EMV' (see Geant4 doc).
    """
    sim.physics_manager.physics_list_name = "QGSP_BERT_EMV"
    global_cut = 700 * um
    sim.physics_manager.global_production_cuts.gamma = global_cut
    sim.physics_manager.global_production_cuts.electron = global_cut
    sim.physics_manager.global_production_cuts.positron = global_cut
    sim.physics_manager.global_production_cuts.proton = global_cut

    """
    Create a source, called 'Default'. The type of the source is 'Generic'.
    Several parameters (particle, energy, direction etc) are available in the
    dict-like structure.
    """
    source = sim.add_source("GenericSource", "Default")
    source.particle = "gamma"
    source.energy.mono = 80 * keV
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    source.n = 200000

    """
    Add a single scorer (called 'actor'), of type 'SimulationStatisticsActor'.
    This simple scorer store the number or Run/Events/Track/Steps of the simulation.
    We recommend to always add such actor.
    The flag 'track_types_flag' gives more detailed results about the tracks (particle type)
    """ ""
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.track_types_flag = True

    """
    Start the simulation ! You can relax and drink coffee.
    (The commented line indicates how to indicate to Geant4 to verbose during the simulation).
    """
    # sim.apply_g4_command("/run/verbose 1")
    sim.user_fct_after_init = check_production_cuts
    sim.run()

    """
    Now the simulation is terminated. The results are retrieved and can be displayed.
    """
    stats = sim.output.get_actor("Stats")
    print(stats)

    # Comparison with gate simulation
    # gate_test4_simulation_stats_actor
    # Gate mac/main.mac
    stats_ref = gate.read_stat_file(paths.gate_output / "stat.txt")
    is_ok = gate.assert_stats(stats, stats_ref, tolerance=0.01)

    gate.test_ok(is_ok)
