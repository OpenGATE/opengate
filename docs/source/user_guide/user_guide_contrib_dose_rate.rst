.. _dose_rate_vrt_label:

Dose rate computation
=====================

Dose rate computations can be performed using Monte Carlo simulations, especially in the context of internal dosimetry for targeted radionuclide therapy (TRT).

Command-line usage
------------------

To run the simulation from the command line, use the ``dose_rate`` executable with a JSON configuration file:

.. code-block:: bash

    dose_rate dose_rate_test1.json -o outputFolder/

The ``dose_rate_test1.json`` file contains the input parameters for the simulation: CT image, material/density calibration tables, activity image (e.g. from SPECT/PET), radionuclide, simulated activity, number of threads, and visualization settings.

.. code-block:: json

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

The SPECT/PET and CT images provide information on the bio-distribution of the source as well as the density and composition of patient tissues. The simulated activity can be lower than the actual administered activity to reduce computation times; the resulting dose rates can subsequently be scaled to the injected activity.
The SPECT/PET and CT images provide information on the bio-distribution of the source as well as the density and composition of patient tissues. Note that ``activity_image`` is used as a **relative spatial probability distribution**: it is internally normalized such that the sum of all voxel values is 1. The absolute total activity (in Bq) simulated across the entire volume is set independently by ``param.activity_bq`` (or ``source.activity``).

The simulated activity can be lower than the actual administered activity to reduce computation times; the resulting dose rates can subsequently be scaled linearly to the injected activity.

By default, the simulation duration is set to 1 second. It can be modified by setting the time intervals corresponding to the acquisition duration:

.. code-block:: python

    sim.run_timing_intervals = [[0, 3600 * sec]]  # for a total duration of 1 hour

Radioactive decay can also be accounted for by specifying the radionuclide half-life:

.. code-block:: python

    source.half_life = 60 * sec

Supported radionuclides in this helper currently include: ``Lu177``, ``Y90``, ``In111``, and ``I131``.

The simulation generates output files including:
- Dose rate map (``dose_edep.mhd``)
- Energy deposition map (``edep.mhd``)
- Statistical uncertainty map (``edep_uncertainty.mhd``)
- CT material labels (``labels.mhd``)
- Simulation statistics (``stats.txt``)


Python API usage
----------------

You can also set up and customize the dose rate simulation directly in Python using the helper module `opengate.contrib.dose.doserate <https://github.com/OpenGATE/opengate/blob/master/opengate/contrib/dose/doserate.py>`_ (see ``opengate/tests/src/source/test035a_dose_rate.py``):

.. code-block:: python

    from pathlib import Path
    from box import Box
    import opengate as gate
    from opengate.contrib.dose.doserate import create_simulation

    # Configure parameters
    param = Box()
    param.ct_image = "29_CT_5mm_crop.mhd"
    param.table_mat = "Schneider2000MaterialsTable.txt"
    param.table_density = "Schneider2000DensitiesTable.txt"
    param.activity_image = "activity_test_crop_4mm.mhd"
    param.radionuclide = "Lu177"
    param.activity_bq = 1e6
    param.number_of_threads = 4
    param.visu = False
    param.verbose = True
    param.density_tolerance_gcm3 = 0.05
    param.output_folder = "output_test035a"
    param.mode = ""  # standard full simulation

    # Create the simulation object
    sim = create_simulation(param)

    # You can customize any component before running
    sim.run(start_new_process=True)


Accelerated computation with Variance Reduction Techniques (VRT)
----------------------------------------------------------------

In standard analog simulations (``param.mode = ""``), radionuclide decay emits both electrons (:math:`\beta^-` / Auger / conversion electrons) and photons (:math:`\gamma` / X-rays) in the same tracking process. Because electrons have short ranges and deposit most of their energy locally, while photons travel long distances with low interaction probability per voxel, tracking both with analog Monte Carlo can be computationally demanding.

To significantly accelerate dose rate computations, a Variance Reduction Technique (VRT) approach is implemented (see ``opengate/tests/src/source/test035b_dose_rate_vrt.py``):

1. **Emission Decoupling**: The radionuclide decay is decoupled into separate simulations:
   - **Electron simulation** (``param.mode = "e-"``): Emits electrons sampled from the radionuclide beta spectrum. A high production cut (e.g. 1 m in the CT volume) is applied to deposit electron energy locally within the voxel where they originate, drastically speeding up electron scoring.
   - **Photon simulation** (``param.mode = "gamma"`` or ``param.mode = "gamma_tle"``): Emits photons sampled from the gamma spectrum. When using ``"gamma_tle"``, the simulation replaces stochastic photon dose deposition with a :class:`~.opengate.actors.doseactors.TLEDoseActor` (Track Length Estimator), achieving faster convergence with fewer simulated particles.

2. **Dose Map Recombination**: The dose/energy deposition maps from both runs are summed to obtain the total dose rate.

Example: running decoupled VRT simulations and combining results
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    import itk
    from box import Box
    import opengate as gate
    from opengate.contrib.dose.doserate import create_simulation

    def run_dose_rate(mode, output_folder, activity_bq=5e5):
        param = Box()
        param.ct_image = "29_CT_5mm_crop.mhd"
        param.table_mat = "Schneider2000MaterialsTable.txt"
        param.table_density = "Schneider2000DensitiesTable.txt"
        param.activity_image = "activity_test_crop_4mm.mhd"
        param.radionuclide = "Lu177"
        param.activity_bq = activity_bq
        param.number_of_threads = 4
        param.visu = False
        param.verbose = True
        param.density_tolerance_gcm3 = 0.05
        param.output_folder = output_folder
        param.mode = mode  # "e-", "gamma", or "gamma_tle"

        sim = create_simulation(param)
        sim.run(start_new_process=True)

    # 1. Run electron simulation (local deposition approximation)
    run_dose_rate(mode="e-", output_folder="output_vrt_e")

    # 2. Run gamma simulation (TLE or standard photon tracking)
    run_dose_rate(mode="gamma", output_folder="output_vrt_gamma")

    # 3. Sum the resulting energy deposition maps
    dose_e = itk.imread("output_vrt_e/edep_edep.mhd")
    dose_gamma = itk.imread("output_vrt_gamma/edep_edep.mhd")

    array_e = itk.GetArrayFromImage(dose_e)
    array_gamma = itk.GetArrayFromImage(dose_gamma)
    array_total = array_e + array_gamma

    dose_total = itk.GetImageFromArray(array_total)
    dose_total.CopyInformation(dose_e)
    itk.imwrite(dose_total, "output_total_vrt/edep_edep_vrt.mhd")

