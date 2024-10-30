## Actors and Filters

The "Actors" are scorers that can store information during simulation, such as dose map or phase-space (like a "tally" in MCNPX). They can also be used to modify the behavior of a simulation, such as the `KillActor` that allows to stop tracking particles when they reach some defined regions, this is why they are called "actors" rather than "scorers".
