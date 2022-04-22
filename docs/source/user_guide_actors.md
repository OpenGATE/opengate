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
is centered according to the volume center. 

Like any image, the output dose map will have an origin. By default, it will consider the coordinate system of the volume it is attached to so at the center of the image volume. The user can manually change the output origin, using the option `output_origin` of the DoseActor.  Alternatively, if the option `img_coord_system` is set to `True` the final output origin will be automatically computed from the image the DoseActor is attached to. This option call the function `get_origin_wrt_images_g4_position` to compute the origin. See the figure for details. 


![](figures/image_coord_system.png)

Several tests depict usage of DoseActor: test008, test009, test021, test035, etc.

### PhaseSpaceActor

todo

### HitsCollectionActor + Hits related actors

todo

HitsAdderActor HitsEnergyWindowsActor HitsProjectionActor

### MotionVolumeActor

todo
