
All notable changes to this project will be documented in this file.
The format is based on Keep a [Changelog](https://keepachangelog.com/en/1.1.0/).
Keep newer changes at the top.


## Version [10.beta00] - 2023-03-20

This is the first official release of Gate10, as a "beta" version. We list below the main available features and the still non-available ones.

### Added features (only main ones)

**Installation**
- install via pip on Linux + OSX (both M1 and Intel CPUs)
- automatic Geant4 data download
- opengate_info
- opengate_tests: more than 90 tests
- opengate_visu


**Main Simulation system**
- random engine and seed
- multithreading
- visualisation: QT, GDML, VRML.
- verbose: Geant4, running
- run time intervals management
- SimulationEngine system to run in a separate process (useful for notebooks)


**Geometry**
- Box, Sphere, Cons, Hexagon, Polyhedra, Trd, Trap
- Image volume : voxelized
- Boolean volumes: associate some solids
- RepeatParametrised volumes
- Material files are compatible with GateMaterial.db from the legacy Gate


**Physics**
- all EM, Hadronic, RadioactiveDecay Geant4 physics lists
- production cuts can be set for any volumes


**Sources**
- Generic Source (roughly like the Geant4 GPS source)
- acceptance angle is available as an option in the Generic Source
- Voxels Source
- PencilBeam Source (for protontherapy)
- GAN sources (conditional or not ; also with pairs for PET ; also voxelized)
- positron energy spectra for various ion (F18, Ga68, Zr89 etc)


**Actors**
- SimulationStatistics actor (should be use in most of the simulation as a log)
- Dose actor
- LET actor (several options)
- PhaseSpace actor
- ARF actor (Angular Response Function for SPECT, with neural network)
- motion volume actor : to move a volume between simulation runs
- Digitizer HitsCollection
- Digitizer Adder
- Digitizer Readout
- Digitizer SpatialBlurring
- Digitizer Blurring (energy or time)
- Digitizer EnergyWindows
- Digitizer Projection
- Filters: particle, kinetic energy, track creator process

**Additional features**
- dose_rate binary executable
- voxelize_iec_phantom



### Not yet available features

We list here important features that are available in legacy Gate 9.xx, but not yet in Gate 10.beta:

- phase space as a source
- user cuts (step limiters, etc)
- coincidences sorter
- STL volumes
- optical photon management
- EM fields
- FFD actor
