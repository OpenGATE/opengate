## Actors and Filters

The "Actors" are scorers can store information during simulation such as dose map or phase-space. They can also be used
to modify the behavior of a simulation, such as the `MotionActor` that allows to move volumes, this is why they are
called "actor".

### SimulationStatisticsActor

The SimulationStatisticsActor actor is a very basic tool that allow to count the number of runs, events, tracks and
steps that have been created during a simulation. Most of the simulation should include this actor as it gives very
basic but valuable information. Once the simulation ends, user can retrieve the values as follows:

```python
# during the initialisation: 
stats = sim.add_actor('SimulationStatisticsActor', 'Stats')
stats.track_types_flag = True

# (...)
sim.initialize()
sim.start()

# after the end of the simulation
stats = sim.get_actor('Stats')
print(stats)
stats.write('myfile.txt')
```

The `stats` object contains the `counts` dictionary that contains all numbers. In addition, the if the
flag `track_types_flag` is enabled, the `stats.counts.track_types` will contains a dictionary structure with all types
of particles that have been created during the simulation.. The start and end time of the whole simulation is also
available. Speeds are also computed (primary per sec, track per sec and step per sec). You can write all the data to a
file like in previous GATE, via `stats.write`. See [source](https://tinyurl.com/pygate/actor/SimulationStatisticsActor/)
.

### DoseActor

The DoseActor computes a 3D edep/dose map for deposited energy/absorbed dose in a given volume The dose map is a 3D
matrix parameterized with: dimension (number of voxels), spacing (voxel size), translation (according to the coordinate
system of the “attachedTo” volume). There is possibility to rotate this 3D matrix for the moment. By default, the matrix
is centered according to the volume center. The output dose map will thus have an offset 

- if the attachedTo volume is an Image AND the option “img_coord_system” is True:

the origin of the attachedTo image is used for the output dose. Hence, the dose can be superimposed with the attachedTo
volume

See test008:

https://github.com/OpenGATE/gam-gate/blob/master/gam_tests/src/test008_dose_actor.py

### PhaseSpaceActor

todo

### HitsCollectionActor + Hits related actors

todo

HitsAdderActor HitsEnergyWindowsActor HitsProjectionActor

### MotionVolumeActor

todo
