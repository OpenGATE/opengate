#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from opengate.userhooks import check_production_cuts
from opengate.tests.utility import (
    get_default_test_paths,
    read_stat_file,
    assert_stats,
    test_ok,
)
from opengate.utility import g4_units
from opengate.logger import DEBUG, RUN
from opengate.managers import Simulation

if __name__ == "__main__":
    """
    The following line is only used for tests, it store the paths where the
    reference data are stored.
    """
    paths = get_default_test_paths(__file__, "gate_test004_simulation_stats_actor")

    """
    Create a simulation object. The class is 'gate.Simulation'.
    The single object that will contain all parameters of the
    simulation is called 'sim' here.
    """
    sim = Simulation()

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
    sim.verbose_level = DEBUG
    sim.running_verbose_level = RUN
    sim.g4_verbose = False
    sim.g4_verbose_level = 1
    sim.visu = False
    sim.random_engine = "MersenneTwister"
    sim.random_seed = "auto"
    print(sim)

    """
    Units. Get some default units from G4. To define a value with a unit, e.g. do:
    x = 123 * cm
    """
    m = g4_units.m
    cm = g4_units.cm
    keV = g4_units.keV
    mm = g4_units.mm
    um = g4_units.um
    Bq = g4_units.Bq

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
    (The commented line indicates how to indicate to Geant4 to verbose during the simulation,
    if the flag sim.g4_verbose is True).
    """
    # sim.g4_commands_after_init.append("/run/verbose 1")
    sim.user_hook_after_init = check_production_cuts
    sim.run()

    """
    Now the simulation is terminated. The results are retrieved and can be displayed.
    """
    print(stats)

    # Comparison with gate simulation
    # gate_test4_simulation_stats_actor
    # Gate mac/main.mac
    stats_ref = read_stat_file(paths.gate_output / "stat.txt")
    is_ok = assert_stats(stats, stats_ref, tolerance=0.01)

    test_ok(is_ok)
