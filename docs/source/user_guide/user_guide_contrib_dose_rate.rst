.. _dose_rate_vrt_label:

Dose rate computation
=====================

Dose rate computations can be performed using Monte Carlo simulations, especially in the context of internal dosimetry for targeted radionuclide therapy (TRT).
OpenGATE provides dedicated tools in `opengate.contrib.dose.doserate <https://github.com/OpenGATE/opengate/blob/master/opengate/contrib/dose/doserate.py>`_ and the command-line interface ``opengate_dose_rate``.

Command-line usage
------------------

To run the simulation from the command line, use the ``opengate_dose_rate`` executable (also available as ``dose_rate``) with a JSON configuration file:

.. code-block:: bash

    opengate_dose_rate dose_rate_param.json

CLI options
~~~~~~~~~~~

.. code-block:: text

    Usage: opengate_dose_rate [OPTIONS] [JSON_PARAM]

    Options:
      -m, --mode [vrt|analog|e-|gamma_tle|gamma]
                                      Simulation mode: vrt (runs e- and gamma_tle
                                      then merges), analog (full ion decay), e-,
                                      gamma_tle, gamma (default: from JSON or
                                      'vrt')
      -a, --activity FLOAT            Total simulated activity in Bq (overrides
                                      JSON). In vrt mode, this applies to gamma.
      -r, --radionuclide TEXT         Radionuclide name (e.g. Lu177, Y90, Ac225)
                                      or ion 'Z A' (e.g. '89 225') (overrides JSON).
      --e-factor FLOAT                In vrt mode, factor by which electron
                                      activity is reduced (default: from JSON or
                                      10.0).
      -t, --threads INTEGER           Number of threads (default: from JSON or 4,
                                      1 on Windows).
      -o, --output_folder PATH        Output folder. Default is auto-named based
                                      on mode (e.g. output_vrt, output_analog,
                                      output_e, output_gamma_tle).
      --visu                          Enable visualization (forces single thread).
      --merge-only DIR_E DIR_GAMMA    Merge precomputed electron and gamma
                                      simulation folders and exit.
      -h, --help                      Show this message and exit.

JSON configuration
~~~~~~~~~~~~~~~~~~

The JSON file contains the input parameters for the simulation:

.. code-block:: json

    {
      "ct_image": "./dose_rate_data/29_CT_5mm.mhd",
      "table_mat": "./dose_rate_data/Schneider2000MaterialsTable.txt",
      "table_density": "./dose_rate_data/Schneider2000DensitiesTable.txt",
      "density_tolerance_gcm3": 0.05,

      "activity_image": "./dose_rate_data/385_NM_5mm.mhd",
      "radionuclide": "Lu177",
      "activity_bq": 1e6,

      "mode": "vrt",
      "e_factor": 10.0,
      "number_of_threads": 4,
      "visu": false,
      "verbose": true
    }

Parameter descriptions:

- **ct_image**: Patient CT image providing the geometry and tissue distribution.
- **table_mat**, **table_density**: Calibration tables mapping Hounsfield Units (HU) to materials and mass densities (e.g., Schneider 2000).
- **density_tolerance_gcm3**: Tolerance for grouping voxels with similar densities into discrete material definitions (default: 0.05 g/cm³).
- **activity_image**: 3D spatial activity distribution (from SPECT or PET). Used as a **relative spatial probability distribution** (internally normalized so that the sum of all voxel values is 1).
- **radionuclide**: Radionuclide identifier (see below).
- **activity_bq**: Total simulated activity across the whole volume in Becquerels (Bq).
- **mode**: Simulation mode:
  - ``"vrt"``: Runs decoupled electron and gamma-TLE simulations and merges them automatically (default for beta/gamma emitters).
  - ``"analog"``: Full ion radioactive decay simulation (default for alpha emitters and custom ions).
  - Single-component modes: ``"e-"``, ``"gamma_tle"``, or ``"gamma"``.
- **e_factor** (or ``e-factor``): In VRT mode, the reduction factor for electron histories (``activity_e = activity / e_factor``, default: 10.0).
- **number_of_threads**: Number of worker threads (default: 4 on Linux/macOS, 1 on Windows).
- **visu**: Set to ``true`` to generate a VRML visualization for debugging (forces 1 thread).

Radionuclide specification
~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``radionuclide`` parameter accepts several flexible formats:

1. **Standard isotope names**:
   - Built-in: ``"Lu177"``, ``"Y90"``, ``"In111"``, ``"I131"``, ``"Ac225"``, ``"Ra223"``, ``"Bi213"``, ``"Pb212"``, ``"Tb161"``.
   - Dynamic: Any valid isotope name (e.g. ``"Sm153"``, ``"Re186"``, ``"Cu67"``) is dynamically resolved to its atomic number :math:`Z` and mass :math:`A` using the Geant4 NIST database.

2. **Generic ion specification ("Z A")**:
   - Space/comma/hyphen separated: ``"89 225"``, ``"ion 89 225"``, ``"89, 225"``, ``"89-225"``.
   - List: ``[89, 225]``.
   - Optional excitation energy :math:`E` can be provided: ``"ion 89 225 0"``.
   This allows simulating any ion without requiring database entries.

.. note::
   - **Beta/gamma emitters** (such as Lu-177, Y-90, I-131, In-111) can run in either accelerated ``vrt`` mode or ``analog`` mode.
   - **Alpha emitters** (such as Ac-225, Ra-223) and generic ions (``"89 225"``) do not have a beta spectrum and should be run in ``analog`` mode (``source.particle = "ion"`` with full radioactive decay enabled). When an alpha emitter or generic ion is detected, ``opengate_dose_rate`` automatically selects ``analog`` mode.

Simulation outputs
~~~~~~~~~~~~~~~~~~

The simulation generates the following files in the output directory:

- **output_dose.mhd**: Absorbed dose rate map (in Gy).
- **output_edep.mhd**: Energy deposition map (in MeV).
- **output_dose_uncertainty.mhd**: Statistical relative uncertainty map (:math:`u = \sigma(D) / D`).
- **labels.mhd**: Material labels segmented from the CT image.
- **stats.txt**: Detailed runtime statistics (histories, tracks, steps, computation duration).


Accelerated computation with Variance Reduction Techniques (VRT)
----------------------------------------------------------------

In standard analog simulations (``mode = "analog"``), radionuclide decay simulates the parent ion and tracks all decay products (electrons, alphas, gammas, X-rays) in the same process. Because electrons have short ranges and deposit their energy locally, while photons travel long distances with low interaction probability per voxel, tracking both with analog Monte Carlo can be computationally demanding.

To significantly accelerate dose rate computations for beta/gamma emitters, an automated VRT pipeline is available:

1. **Emission Decoupling**:
   - **Electron simulation** (``mode = "e-"``): Simulates electrons sampled from the radionuclide beta spectrum. A 1 m production cut in the CT volume deposits electron energy locally in the voxel of emission. Because electron dose is deposited locally with high efficiency, far fewer histories are needed (:math:`A_e = A / \text{e\_factor}`, default reduction factor 10).
   - **Photon simulation** (``mode = "gamma_tle"``): Simulates photons sampled from the gamma spectrum using a :class:`~.opengate.actors.doseactors.TLEDoseActor` (Track Length Estimator). TLE analytically scores dose along photon paths in every voxel traversed, achieving smooth dose distributions with low uncertainty without tracking rare secondary electrons.

2. **Automated Merging**:
   The ``merge_vrt_dose_rate`` function combines the dose maps:

   .. math::

       D_{\text{total}} = F \cdot D_{e} + D_{\gamma}

   where :math:`F` is the ``e_factor``.
   Because the electron and gamma simulations are statistically independent, the combined relative uncertainty is computed rigorously via error propagation:

   .. math::

       u_{\text{total}} = \frac{\sqrt{(F \cdot u_e \cdot D_e)^2 + (u_\gamma \cdot D_\gamma)^2}}{F \cdot D_e + D_\gamma}

   where :math:`u_e` and :math:`u_\gamma` are the relative uncertainties from each run.

3. **Performance Gain**:
   Compared to an analog simulation, the VRT approach with TLE and :math:`F=10` typically achieves an efficiency speedup (:math:`\epsilon = 1 / (t^2 \cdot \text{variance})`) of **10x to 30x** for equivalent statistical precision.


Python API usage
----------------

Standard simulation (Analog)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To set up an analog simulation directly in Python (see ``opengate/tests/src/source/test035a_dose_rate.py``):

.. code-block:: python

    from box import Box
    from opengate.contrib.dose.doserate import create_simulation

    # Configure parameters
    param = Box()
    param.ct_image = "29_CT_5mm_crop.mhd"
    param.table_mat = "Schneider2000MaterialsTable.txt"
    param.table_density = "Schneider2000DensitiesTable.txt"
    param.activity_image = "activity_test_crop_4mm.mhd"
    param.radionuclide = "Lu177"  # or "Ac225", "89 225", etc.
    param.activity_bq = 1e6
    param.number_of_threads = 4
    param.visu = False
    param.verbose = True
    param.density_tolerance_gcm3 = 0.05
    param.output_folder = "output_analog"
    param.mode = ""  # standard full simulation

    # Create and run simulation
    sim = create_simulation(param)
    sim.run(start_new_process=True)


VRT simulation and merging
~~~~~~~~~~~~~~~~~~~~~~~~~~

To run decoupled VRT simulations and merge their results (see ``opengate/tests/src/source/test035b_dose_rate_vrt.py``):

.. code-block:: python

    from box import Box
    from opengate.contrib.dose.doserate import create_simulation, merge_vrt_dose_rate

    activity = 1e6
    e_factor = 10.0

    # Common parameters
    base_param = Box()
    base_param.ct_image = "29_CT_5mm_crop.mhd"
    base_param.table_mat = "Schneider2000MaterialsTable.txt"
    base_param.table_density = "Schneider2000DensitiesTable.txt"
    base_param.activity_image = "activity_test_crop_4mm.mhd"
    base_param.radionuclide = "Lu177"
    base_param.number_of_threads = 4
    base_param.density_tolerance_gcm3 = 0.05

    # 1. Run electron simulation with reduced statistics
    param_e = base_param.copy()
    param_e.mode = "e-"
    param_e.activity_bq = int(activity / e_factor)
    param_e.output_folder = "output_e"
    sim_e = create_simulation(param_e)
    sim_e.run(start_new_process=True)

    # 2. Run photon simulation with TLE
    param_g = base_param.copy()
    param_g.mode = "gamma_tle"
    param_g.activity_bq = activity
    param_g.output_folder = "output_gamma_tle"
    sim_g = create_simulation(param_g)
    sim_g.run(start_new_process=True)

    # 3. Merge outputs and calculate combined uncertainty
    merged_files = merge_vrt_dose_rate(
        folder_e="output_e",
        folder_gamma="output_gamma_tle",
        output_folder="output_vrt",
        e_factor=e_factor,
    )
    print("Merged outputs:", merged_files)
