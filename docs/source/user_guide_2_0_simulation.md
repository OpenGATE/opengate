## Simulation


### Units values

The Geant4 physics units can be retrieved with the following:

```python
import opengate as gate

cm = gate.g4_units('cm')
eV = gate.g4_units('eV')
MeV = gate.g4_units('MeV')
x = 32 * cm
energy = 150 * MeV
print(f'The energy is {energy/eV} eV')
```

The units behave like in Geant4 [system of units](https://geant4.web.cern.ch/sites/default/files/geant4/collaboration/working_groups/electromagnetic/gallery/units/SystemOfUnits.html).

### Main Simulation object

Any simulation starts by defining the (unique) `Simulation` object. The generic options can be set with the `user_info` data structure (a kind of dictionary), as follows. You can print this `user_info` data structure to see all available options with the default value `print(sim.user_info)`.

```python
sim = gate.Simulation()
ui = sim.user_info
print(ui)
ui.verbose_level = gate.DEBUG
ui.running_verbose_level = gate.EVENT
ui.g4_verbose = False
ui.g4_verbose_level = 1
ui.visu = False
ui.visu_verbose = False
ui.random_engine = 'MersenneTwister'
ui.random_seed = 'auto'
ui.number_of_threads = 1
```

A simulation must contains 4 main elements that will define a complete simulation:

- **Geometry**: all geometrical elements that compose the scene, such as phantoms, detectors, etc.
- **Sources**: all sources of particles that will be created ex-nihilo. Each source may have different properties (location, direction, type of particles with their associated energy ,etc).
- **Physics**: describe the properties of the physical models that will be simulated. It describes models, databases, cuts etc.
- **Actors** : define what will be stored and output during the simulation. Typically, dose deposition or detected particles. This is the generic term for 'scorer'. Note that some `Actors` can not only store and output data, but also interact with the simulation itself (hence the name 'actor').

Also, you can use the command line ```opengate_user_info``` to print all default and possible parameters.

Each four elements will be described in the following sections. Once they have be defined, the simulation must be initialized and can be started. The initialization corresponds to the Geant4 step needed to create the scene, gather cross-sections, etc.

```python
output = sim.start()
```

#### Random Number Generator

The RNG can be set with `ui.random_engine = "MersenneTwister"`. The default one is "MixMaxRng" and not "MersenneTwister" because it is recommanded by Geant4 for MT.

The seed of the RNG can be set with `self.random_seed = 123456789`, with any number. If you run two times a simulation with the same seed, the results will be exactly the same. There are some exception to that behavior, for example when using PyTorch-based GAN. By default, it is set to "auto", which means that the seed is randomly chosen.

#### Run and timing

The simulation can be split into several runs, each of them with a given time duration. Geometry can only be modified between two runs, not within one. By default, the simulation has only one run with a duration of 1 second. In the following example, we defined 3 runs, the first has a duration of half a second and start at 0, the 2nd run goes from 0.5 to 1 second. The 3rd run starts latter at 1.5 second and lasts 1 second.

```python
sim.run_timing_intervals = [
    [ 0, 0.5 * sec],
    [ 0.5 * sec, 1.0 * sec],
    # Watch out : there is (on purpose) a 'hole' in the timeline
    [ 1.5 * sec, 2.5 * sec],
    ]
```

#### Verbosity (for debug)

The **verbosity**, i.e. the messages printed on the screen, are controlled via various parameters.

- `ui.verbose_level`: can be `DEBUG` or `INFO`. Will display more or less messages during initialization
- `ui.running_verbose_level`: can be `RUN` or `EVENT`. Will display message during simulation run
- `ui.g4_verbose`: (bool) enable or disable the Geant4 verbose system
- `ui.g4_verbose_level`: level of the Geant4 verbose system
- `ui.visu_verbose`: enable or disable Geant4 verbose during visualisation

#### Visualisation

**Visualisation** is enabled with `ui.visu = True`. It will start a Qt interface. By default, the Geant4 visualisation commands are the ones provided in the file `opengate\mac\default_visu_commands.mac`. It can be changed with `self.visu_commands = gate.read_mac_file_to_commands('my_visu_commands.mac')`.

The visualisation is still work in progress. First, it does not work on some linux systems (we don't know why yet). When a CT image is inserted in the simulation, every voxel should be drawn which is highly inefficient and cannot really be used.

#### Multithreading

**Multithreading** is enabled with `ui.number_of_threads = 4` (larger than 1). When MT is enabled, there will one run for each thread, running in parallel.

Warning, the speedup is far from optimal. First, it takes time to start a new thread. Second, if the simulation already contains several runs (for timing for example), all run will be synchronized, i.e. the master thread will wait for all threads to terminate the run before starting another one. This synchronisation takes times and may impact the speedup.

#### Starting and SimulationEngine

Once all simulation elements have been described (see next sections), the Geant4 engine must be initialized before the simulation can start. This is done by one single command:

    output = sim.start()

Geant4 engine is designed to be the only one instance of the engine, and thus prevent to run two simulations in the same process. In most of the cases, this is not an issue, but sometimes, for example in notebook, we want to run several simulations during the same process session. This can be achieved by setting the option that will start the Geant4 engine in a separate process and copy back the resulting output in the main process. This is the task of the `SimulationEngine` object.

    se = gate.SimulationEngine(sim, start_new_process=True)
    output = se.start()
    # or shorter :
    output = sim.start(start_new_process=True)


#### After the simulation

Once the simulation is terminated (after the `start()`), user can retrieve some actor outputs via the `output.get_actor` function. Note that output data cannot be all available when the simulation is run in a separate process. For the moment, G4 objects (ROOT output) and ITK images cannot be copied back to the main process, e.g. ITK images and ROOT files should be written on disk to be accessed back.

------------

```{include} user_guide_2_1_volumes.md
```

------------

```{include} user_guide_2_2_sources.md
```

------------

```{include} user_guide_2_3_physics.md
```

------------

```{include} user_guide_2_4_actors.md
```
