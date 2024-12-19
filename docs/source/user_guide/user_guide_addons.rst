Additional Functionalities
==========================

The command line tool ``opengate_info`` prints information about the current installation (Geant4 version, ITK version, etc.).

The command line tool ``opengate_tests`` runs all GATE tests. With the option ``-r``, only the last 10 tests and 1/4 of the remaining tests are run. With the option ``-i XX``, it runs the tests from XX. Each test dumps logs in the `tests/log` folder.

The command line tool ``opengate_user_info`` allows you to print all default and possible parameters for Volumes, Sources, Physics, and Actors elements. This is verbose but provides a dynamic documentation of everything currently available in the installed GATE version.
