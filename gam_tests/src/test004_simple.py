#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam_gate as gam
import gam_g4 as g4
import pathlib
import os

pathFile = pathlib.Path(__file__).parent.resolve()

"""
Create a simulation object. The class is 'gam.Simulation'. 
The single object that will contain all parameters of the 
simulation is called 'sim' here.
"""
sim = gam.Simulation()

"""
Main global options. 
The 'sim' object contains a structure called 'user_info' that gather all global options. 
- For example here, the verbosity is set (verbosity means texts that are displayed during 
the simulation run, mostly for debug)
- 'visu', if ON, display a windows with a QT view of the scene.
- random_engine and random_seed control the pseudo random engine. We recommand MersenneTwister. 
  A seed can be specified, e.g. 123456, for reproducible simulation. Or you can use 'auto', an random seed
  will be generated.
"""
ui = sim.user_info
ui.verbose_level = gam.DEBUG
ui.running_verbose_level = gam.RUN
ui.g4_verbose = False
ui.g4_verbose_level = 1
ui.visu = False
ui.random_engine = 'MersenneTwister'
ui.random_seed = 'auto'
print(ui)

"""
Units. Get some default units from G4. To define a value with a unit, e.g. do:
x = 123 * cm
"""
m = gam.g4_units('m')
cm = gam.g4_units('cm')
keV = gam.g4_units('keV')
mm = gam.g4_units('mm')
Bq = gam.g4_units('Bq')

"""
Set the world size (like in the Gate macro). World is the only volume created by default. 
It is described by a dict-like structure, accessible by sim.world. 
The size is set here, as a 3D vector. Default material is G4_AIR.
"""
world = sim.world
world.size = [3 * m, 3 * m, 3 * m]
world.material = 'G4_AIR'

"""
A simple waterbox volume is created. It is inserted into the simulation with 'add_volume'.
This function return a dict-like structure (called 'waterbox' here) with various parameters
(size, position in the world, material). Note that, like in Geant4, the coordinate system 
of all volumes is the one of the mother volume (here the world).
"""
waterbox = sim.add_volume('Box', 'Waterbox')
waterbox.size = [40 * cm, 40 * cm, 40 * cm]
waterbox.translation = [0 * cm, 0 * cm, 25 * cm]
waterbox.material = 'G4_WATER'

"""
The physic list by default is 'QGSP_BERT_EMV' (see Geant4 doc).
"""
p = sim.get_physics_user_info()
p.physics_list_name = 'QGSP_BERT_EMV'
cuts = p.production_cuts
um = gam.g4_units('um')
cuts.world.gamma = 700 * um
cuts.world.electron = 700 * um
cuts.world.positron = 700 * um
cuts.world.proton = 700 * um

"""
Create a source, called 'Default'. The type of the source is 'Generic'. 
Several parameters (particle, energy, direction etc) are available in the
dict-like structure. 
"""
source = sim.add_source('Generic', 'Default')
source.particle = 'gamma'
source.energy.mono = 80 * keV
source.direction.type = 'momentum'
source.direction.momentum = [0, 0, 1]
source.n = 200000

"""
Add a single scorer (called 'actor'), of type 'SimulationStatisticsActor'. 
This simple scorer store the number or Run/Events/Track/Steps of the simulation.
We recommand to always add such actor. 
The flag 'track_types_flag' gives more detailed results about the tracks (particle type)
"""""
stats = sim.add_actor('SimulationStatisticsActor', 'Stats')
stats.track_types_flag = True

"""
Create G4 objects, like in conventional Geant4 simulation.
"""
sim.initialize()

"""
Start the simulation ! You can relax and drink coffee.
(The commented line indicates how to indicate to Geant4 to verbose during the simulation).
"""
# sim.apply_g4_command("/run/verbose 1")
sim.start()

"""
Now the simulation is terminated. The results is retrieved and can be displayed.
"""
stats = sim.get_actor('Stats')
print(stats)

# Comparison with gate simulation
# gate_test4_simulation_stats_actor
# Gate mac/main.mac
stats_ref = gam.read_stat_file(
    pathFile / '..' / 'data' / 'gate' / 'gate_test004_simulation_stats_actor' / 'output' / 'stat.txt')
is_ok = gam.assert_stats(stats, stats_ref, tolerance=0.01)

gam.test_ok(is_ok)
