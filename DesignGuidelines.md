## OBSOLETE! Will be updated soon.

* Classes should use dictionaries of the form {name:object} to register series of objects, e.g. volumes in the VolumeManager. They should **not** use lists.
* Initialize methods should **not** take any arguments. All parameters should be set explicitly before calling initialize.
* Initialize methods should be called either privately by the class itself or from the associated engine. They should not be called by the user.
* Gate objects should be created via create functions of the respective managers, not by directly calling the constructor of the object's class. The create method should take care of setting up the object correctly and registering the required managers
* Geant4 object belonging to an opengate class should be created at the initialization stage. The class should take care that all required g4 objects exist (via flags, Exception handling).
* GateObjects should be constructable without mandatory arguments to the __init__ method, except for the name. Parameters are to be set explicitly after object creation. That makes creation of dummy objects easy.
* Geant4 objects defined in python should have a preceding "g4_" to inform the developer about their nature.
* If a G4 object is represented by a Gate object, e.g. Region, then the reference to the G4 object should be stored as attribute of that Gate object. E.g.: Region.g4_region. Other objects should prefer to define properties to retrieve this reference across the simulation hierarchy, to avoid having many references to G4 objects spread across the code.
* Engine to not have user_infos because they are not made for user interaction
* All user info should be set in Manager classes. All G4 objects should be initialized in Engines. Not the contrary.
* Managers are responsible for checking the user input. Engines may assume the input is valid (type, size, etc.).
