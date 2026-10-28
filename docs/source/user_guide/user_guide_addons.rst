Additional Functionalities
==========================

The command line tool ``opengate_info`` prints information about the current installation (Geant4 version, ITK version, etc.).

The command line tool ``opengate_tests`` runs all GATE tests. With the option ``-r``, only the last 10 tests and 1/4 of the remaining tests are run. With the option ``-i XX``, it runs the tests from XX. Each test dumps logs in the `tests/log` folder.

The command line tool ``dose_rate`` computes the 3D dose rate map from CT and activity distribution images (see :doc:`user_guide_contrib_dose_rate`).


