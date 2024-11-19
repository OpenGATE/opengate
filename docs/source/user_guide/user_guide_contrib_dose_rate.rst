Dose rate computation
=====================

Dose rate computations can be performed using Monte Carlo simulations, especially in the context of dosimetry for targeted radionuclide therapy. To run the simulations, you need to use the following command:

.. code:: python

    python dose_rate dose_rate_test1.json -o outputFolder/

The `dose_rate_test1.json` file contains the input parameters for the simulation: SPECT image, CT image, activity to simulate, radionuclide used, number of threads, and visualization settings.

.. code:: json

    {
      "# Input CT image": "",
      "ct_image": "./dose_rate_data/29_CT_5mm.mhd",
      "table_mat": "./dose_rate_data/Schneider2000MaterialsTable.txt",
      "table_density": "./dose_rate_data/Schneider2000DensitiesTable.txt",
      "density_tolerance_gcm3": 0.2,

      "# Input activity image": "",
      "activity_image": "./dose_rate_data/385_NM_5mm.mhd",

      "# Input radionuclide": "",
      "radionuclide": "Lu177",

      "# Input total simulated activity in the whole image, in Bq": "",
      "activity_bq": 1e6,

      "# Option: number of threads": "",
      "number_of_threads": 1,

      "# Option: visualisation (for debug)": "",
      "visu": false,

      "# verbosity": "",
      "verbose": true
    }

The SPECT and CT images provide information on the bio-distribution of the source as well as the density of the different materials. The simulated activity can be relatively low compared to the actual administered activity to reduce simulation times. For example, 10 MBq can be simulated, and then the dose rates can be scaled according to the actual injected activity. However, be aware that the choice of simulated activity affects the uncertainties, which may be acceptable at the organ level but not at the voxel level. In the latter case, the activity should be increased.
By default, the simulation times are set to 1 second. They can be modified by adding the time interval corresponding to the duration of the acquisition with the following line. More details in the section “Run and timing” of the page “Description of the simulation object”.

.. code:: python

    sim.run_timing_intervals = [[0, 3600 * sec]] for a total duration of one hour.

An alternative option is to account for radioactive decay by providing the radionuclide’s half-life. If the simulation starts at t=4s, with 10 MBq simulated, and the half-life of 4s, the simulation will consider 5 MBq instead of 10. The half-life can be added with the following line. More details in the section “Half-life and Time Activity Curve (TAC)” of the page “Source”.

.. code:: python

    source.half_life = 60 * sec

At present, only four radionuclides can be used in these simulations: 177Lu, 90Y, 111In, and 131I.
To speed up the calculations, it is possible to increase the number of threads used. More information in the section “Multithreading” in the page “Description of the simulation object”. However, you can look at the source code of this tool, the file `doserate.py <https://github.com/OpenGATE/opengate/blob/master/opengate/contrib/dose/doserate.py>`_ to create your own simulation.

The simulation generates five files: the dose rate map (`dose_edep.mhd`), the energy deposition map (`edep.mhd`), the uncertainties (`edep_uncertainty.mhd`), the labels of the CT image to material correspondance (labels.mhd), and the statistics from the simulation (`stats.txt`, simulation time, number of tracks, number of events, etc.).

