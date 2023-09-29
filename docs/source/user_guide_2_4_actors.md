## Actors and Filters

The "Actors" are scorers can store information during simulation such as dose map or phase-space (like a "tally" in MCNPX). They can also be used to modify the behavior of a simulation, such as the `MotionActor` that allows to move volumes, this is why they are called "actor".

### SimulationStatisticsActor

The SimulationStatisticsActor actor is a very basic tool that allow to count the number of runs, events, tracks and steps that have been created during a simulation. Most of the simulations should include this actor as it gives valuable information. Once the simulation ends, the user can retrieve the values as follows:

```python
# during the initialisation:
stats = sim.add_actor('SimulationStatisticsActor', 'Stats')
stats.track_types_flag = True

# (...)
output = sim.start()

# after the end of the simulation
stats = output.get_actor('Stats')
print(stats)
stats.write('myfile.txt')
```

The `stats` object contains the `counts` dictionary that contains all numbers. In addition, if the flag `track_types_flag` is enabled, the `stats.counts.track_types` will contain a dictionary structure with all types of particles that have been created during the simulation. The start and end time of the whole simulation is also available. Speeds are also estimated (primary per sec, track per sec and step per sec). You can write all the data to a file like in the previous GATE, via `stats.write`. See [source](https://tinyurl.com/pygate/actor/SimulationStatisticsActor/).

### DoseActor

The DoseActor computes a 3D edep/dose map for deposited energy/absorbed dose in a given volume. The dose map is a 3D matrix parameterized with: dimension (number of voxels), spacing (voxel size), and translation (according to the coordinate system of the “attachedTo” volume). There is no possibility to rotate this 3D matrix for the moment. By default, the matrix is centered according to the volume center.

Like any image, the output dose map will have an origin. By default, it will consider the coordinate system of the volume it is attached to, so at the center of the image volume. The user can manually change the output origin, using the option `output_origin` of the DoseActor. Alternatively, if the option `img_coord_system` is set to `True` the final output origin will be automatically computed from the image the DoseActor is attached to. This option calls the function `get_origin_wrt_images_g4_position` to compute the origin. See the figure for details.

![](figures/image_coord_system.png)

Several tests depict usage of DoseActor: test008, test009, test021, test035, etc.

````python
dose = sim.add_actor("DoseActor", "dose")
dose.output = output_path / "test008-edep.mhd"
dose.mother = "waterbox"
dose.size = [99, 99, 99]
mm = gate.g4_units.mm
dose.spacing = [2 * mm, 2 * mm, 2 * mm]
dose.translation = [2 * mm, 3 * mm, -2 * mm]
dose.uncertainty = True
dose.hit_type = "random"
````

### PhaseSpaceActor

A PhaseSpaceActor stores any set of particles reaching a given volume during the simulation. The list of attributes that are kept for each stored particle can be specified by the user.

```python
phsp = sim.add_actor("PhaseSpaceActor", "PhaseSpace")
phsp.mother = plane.name
phsp.attributes = [
    "KineticEnergy",
    "Weight",
    "PostPosition",
    "PrePosition",
    "ParticleName",
    "PreDirection",
    "PostDirection",
    "TimeFromBeginOfEvent",
    "GlobalTime",
    "LocalTime",
    "EventPosition",
]
phsp.output = "test019_hits.root"
f = sim.add_filter("ParticleFilter", "f")
f.particle = "gamma"
phsp.filters.append(f)
```

In this example, the PhaseSpace will store all particles reaching the given plane. For each particle, some information will be stored, as shown in the attributes array: energy, position, name, time, etc. The list of available attributes name can be seen in the file : [GateDigiAttributeList.cpp](https://github.com/OpenGATE/opengate/blob/master/core/opengate_core/opengate_lib/digitizer/GateDigiAttributeList.cpp). Here is the current list:

```
TotalEnergyDeposit
PostKineticEnergy PreKineticEnergy KineticEnergy TrackVertexKineticEnergy EventKineticEnergy
LocalTime GlobalTime TimeFromBeginOfEvent TrackProperTime
Weight
TrackID ParentID EventID RunID ThreadID
TrackCreatorProcess ProcessDefinedStep
ParticleName
TrackVolumeName TrackVolumeCopyNo
PreStepVolumeCopyNo PostStepVolumeCopyNo TrackVolumeInstanceID
PreStepUniqueVolumeID PostStepUniqueVolumeID HitUniqueVolumeID
Position PostPosition PrePosition EventPosition TrackVertexPosition
Direction PostDirection PreDirection PreDirectionLocal TrackVertexMomentumDirection EventDirection
```

The output is a root file that contains a tree. It can be analysed for example with [uproot](https://uproot.readthedocs.io/).

### Hits-related actors (digitizer)

In legacy Gate, the digitizer module is a set of tools used to simulate the behaviour of the scanner detectors and signal processing chain. The tools consider a list of interactions occurring in the detector (e.g. in the crystal), named as "hits collections". Then, this collection of hits is processed and filtered by different modules to end up with a final digital value. To start a digitizer chain, we must start defining a `HitsCollectionActor`, explained in the next sections.

#### DigitizerHitsCollectionActor

The `DigitizerHitsCollectionActor` is an actor that collects hits occurring in a given volume (or one of its daughters). Every time a step occurs in the volume a list of attributes is recorded. The list of attributes is defined by the user as follows:

```python
hc = sim.add_actor('DigitizerHitsCollectionActor', 'Hits')
hc.mother = ['crystal1', 'crystal2']
hc.output = 'test_hits.root'
hc.attributes = ['TotalEnergyDeposit', 'KineticEnergy', 'PostPosition',
                 'CreatorProcess', 'GlobalTime', 'VolumeName', 'RunID', 'ThreadID', 'TrackID']
```

In this example, the actor is attached (`mother` option) to several volumes (`crystal1` and `crystal2` ) but most of the time, one single volume is sufficient. This volume is important: every time an interaction (a step) is occurring in this volume, a hit will be created. The list of attributes is defined with the given array of attribute names. The names of the attributes are as close as possible to the Geant4 terminology. They can be of a few types: 3 (ThreeVector), D (double), S (string), I (int), U (unique volume ID, see DigitizerAdderActor section). The list of available attributes is defined in the file `core/opengate_core/opengate_lib/GateDigiAttributeList.cpp` and can be printed with:

```python
import opengate_core as gate_core
am = gate_core.GateDigiAttributeManager.GetInstance()
print(am.GetAvailableDigiAttributeNames())
```
        Direction 3
        EventDirection 3
        EventID I
        EventKineticEnergy D
        EventPosition 3
        GlobalTime D
        HitUniqueVolumeID U
        KineticEnergy D
        LocalTime D
        ParticleName S
        Position 3
        PostDirection 3
        PostKineticEnergy D
        PostPosition 3
        PostStepUniqueVolumeID U
        PostStepVolumeCopyNo I
        PreDirection 3
        PreDirectionLocal 3
        PreKineticEnergy D
        PrePosition 3
        PreStepUniqueVolumeID U
        PreStepVolumeCopyNo I
        ProcessDefinedStep S
        RunID I
        ThreadID I
        TimeFromBeginOfEvent D
        TotalEnergyDeposit D
        TrackCreatorProcess S
        TrackID I
        TrackProperTime D
        TrackVertexKineticEnergy D
        TrackVertexMomentumDirection 3
        TrackVertexPosition 3
        TrackVolumeCopyNo I
        TrackVolumeInstanceID I
        TrackVolumeName S
        Weight D

Warning: KineticEnergy, Position and Direction are available for PreStep and for PostStep, and there is a "default" version corresponding to the legacy Gate.

| Pre version | Post version | default version         |
|-------------|--------------|-------------------------|
| PreKineticEnergy | PostKineticEnergy | KineticEnergy (**Pre**) |
| PrePosition | PostPosition | Position (**Post**)     |
| PreDirection | PostDirection | Direction (**Post**)    |


At the end of the simulation, the list of hits can be written as a root file and/or used by subsequent digitizer modules (see next sections). The Root output is optional, if the output name is `None` nothing will be written. Note that, like in Gate, every hit such with zero deposited energy is ignored. If you need them, you should probably use a PhaseSpaceActor. Several tests using `DigitizerHitsCollectionActor` are proposed: test025, test028, test035, etc.

The two basics actors used to convert some `hits` to one `digi` are "DigitizerHitsAdderActor" and "DigitizerReadoutActor" described in the next sections and illustrated in the figure:

![](figures/digitizer_adder_readout.png)


#### DigitizerHitsAdderActor

This actor groups the hits per different volumes according to the option `group_volume` (by default, this is the deeper volume that contains the hit). All hits (in the same event) occurring in the same volume are gathered into one single digi according to one of the two available policies:

- EnergyWeightedCentroidPosition:
  - the final energy ("TotalEnergyDeposit") is the sum of all deposited energy
  - the position ("PostPosition") is the energy-weighted centroid position
  - the time ("GlobalTime") is the time of the earliest hit

- EnergyWinnerPosition
  - the final energy ("TotalEnergyDeposit") is the energy of the hit with the largest deposited energy
  - the position ("PostPosition") is the position of the hit with the largest deposited energy
  - the time ("GlobalTime") is the time of the earliest hit

```python
sc = sim.add_actor("DigitizerAdderActor", "Singles")
sc.output = 'test_hits.root'
sc.input_digi_collection = "Hits"
sc.policy = "EnergyWeightedCentroidPosition"
# sc.policy = "EnergyWinnerPosition"
sc.group_volume = crystal.name
```

Note that this actor is only triggered at the end of an event, so the `mother` volume to which it is attached has no effect. Examples are available in test 037.

#### DigitizerReadoutActor

This actor is the same as the previous one (DigitizerHitsAdderActor) with one additional option: the resulting positions of the digi are set in the center of the defined volumes (discretized). We keep two different actors (Adder and Readout) to be close to the previous legacy GATE versions. The additional option `discretize_volume` indicates the volume name in which the discrete position will be taken.

```python
sc = sim.add_actor("HitsReadoutActor", "Singles")
sc.input_digi_collection = "Hits"
sc.group_volume = stack.name
sc.discretize_volume = crystal.name
sc.policy = "EnergyWeightedCentroidPosition"
```

Examples are available in test 037.

#### DigitizerGaussianBlurringActor

Digitizer module for blurring an attribute such as the time or the energy (single value only, not a vector). The blurring method can be "Gaussian", "InverseSquare" or "Linear" :

For Gaussian: the sigma or the FWHM should be given `blur_sigma` or `.blur_fwhm` options.

For InverseSquare: `blur_reference_value` and `blur_reference_value` EQUATION

For Linear: `blur_reference_value`, `blur_reference_value` and `blur_slope`  EQUATION


```python
bc = sim.add_actor("DigitizerBlurringActor", "Singles_with_blur")
bc.output = "output.root"
bc.input_digi_collection = "Singles_readout"
bc.blur_attribute = "GlobalTime"
bc.blur_method = "Gaussian"
bc.blur_fwhm = 100 * ns
```


#### DigitizerSpatialBlurringActor

(documentation TODO)

warning: if blur leads to point outside volume (keep_in_solid_limits option). Useful for monocrystal. Should probably not be used for pixelated crystal.

#### DigitizerEnergyWindowsActor

(documentation TODO)
for spect, test028

#### DigitizerProjectionActor

(documentation TODO)
for spect, test028

#### DigitizerEfficiencyActor

Digitizer module for simulating detection with lowered (non-100%) efficiency. It is initialized with a float number representing the probability of storing the hit. An efficiency of 0 means that absolutely nothing will be recorded, whereas a probability of 1 means that all digis will be stored.

For each digi the digitizer receives, a random float is uniformly shot between 0 and 1: if this random float is below the efficiency set when initializing the digitizer, then the digit is kept, otherwise, it is discarded.

As an example, a DigitizerEfficiencyActor with an efficiency of 0.3 can be initialized as follows:
```python
ea = sim.add_actor("DigitizerEfficiencyActor", "Efficiency")
ea.input_digi_collection = "Hits"
ea.efficiency = 0.3
```
A more detailed example can be found in [test 57](https://github.com/OpenGATE/opengate/blob/master/opengate/tests/src/test057_digit_efficiency.py).

### MotionVolumeActor

(documentation TODO)
test029

### ARFActor (and ARFTrainingDatasetActor)

(documentation TODO)
test043
The detector MUST be oriented such that the depth is Z dimension


### LETActor

(documentation TODO)
test050
