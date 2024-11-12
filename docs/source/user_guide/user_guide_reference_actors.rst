Actors
======

SimulationStatisticsActor
--------------------------

Description
^^^^^^^^^^^

The SimulationStatisticsActor actor is a very basic tool that allows counting the number of runs, events, tracks, and steps that have been created during a simulation. Most simulations should include this actor as it gives valuable information. The `stats` object contains the `counts` dictionary that contains all results.

.. code-block:: python

   # ...
   stats = sim.add_actor('SimulationStatisticsActor', 'Stats')
   stats.track_types_flag = True
   # ...

   sim.run()
   print(stats)
   print(stats.counts)

 In addition, if the flag `track_types_flag` is enabled, the actor will save a dictionary structure with all types of particles that have been created during the simulation, which is available as `stats.counts.track_types`. The start and end time of the whole simulation are  available and speeds are estimated (primary per sec, track per sec, and step per sec).


Reference
^^^^^^^^^

.. autoclass:: opengate.actors.miscactors.SimulationStatisticsActor

DoseActor
---------

The DoseActor computes a 3D energy deposition (edep) or absorbed dose map in a given volume. The dose map is a 3D matrix parameterized with: dimension (number of voxels), spacing (voxel size), and translation (according to the coordinate system of the attached volume). By default, the matrix is centered according to the volume center.

Like any image, the output dose map will have an origin. By default, it will consider the coordinate system of the volume it is attached to, so at the center of the image volume. The user can manually change the output origin using the option `output_origin` of the DoseActor. Alternatively, if the option `img_coord_system` is set to `True`, the final output origin will be automatically computed from the image the DoseActor is attached to. This option calls the function `get_origin_wrt_images_g4_position` to compute the origin.

.. image:: ../figures/image_coord_system.png

Several tests depict the usage of DoseActor: test008, test009, test021, test035, etc.

.. code-block:: python

   dose = sim.add_actor("DoseActor", "dose")
   dose.output_filename = output_path / "test008-edep.mhd"
   dose.attached_to = "waterbox"
   dose.size = [99, 99, 99]
   mm = gate.g4_units.mm
   dose.spacing = [2 * mm, 2 * mm, 2 * mm]
   dose.translation = [2 * mm, 3 * mm, -2 * mm]
   dose.uncertainty = True
   dose.hit_type = "random"

PhaseSpaceActor
---------------

A PhaseSpaceActor stores any set of particles reaching a given volume during the simulation. The list of attributes that are kept for each stored particle can be specified by the user.

.. code-block:: python

   phsp = sim.add_actor("PhaseSpaceActor", "PhaseSpace")
   phsp.attached_to = plane.name
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
   phsp.output_filename = "test019_hits.root"
   f = sim.add_filter("ParticleFilter", "f")
   f.particle = "gamma"
   phsp.filters.append(f)

In this example, the PhaseSpaceActor will store all particles reaching the given plane. For each particle, some information will be stored, as shown in the attributes array: energy, position, name, time, etc. The list of available attribute names can be found in the file: `GateDigiAttributeList.cpp`.

The output is a ROOT file that contains a tree. It can be analyzed, for example, with `uproot`.

By default, the PhaseSpaceActor stores information about particles entering the volume. This behavior can be modified by the following options:

.. code-block:: python

   phsp.steps_to_store = "entering"  # this is the default
   phsp.steps_to_store = "entering exiting first"  # other options (combined)

Hits-related actors (digitizer)
-------------------------------

The digitizer module simulates the behavior of scanner detectors and signal processing chains. It processes and filters a list of interactions (hits) occurring in a detector to produce a final digital value. A digitizer chain begins with defining a `HitsCollectionActor`.

Common features of digitizer actors:

- Most digitizers have a ROOT output (except `DigitizerProjectionActor`, which outputs an image). The output can be written to disk with `my_digitizer.root_output.write_to_disk = True`.
- `authorize_repeated_volumes`: Set this to True to work with repeated volumes, such as in PET systems. However, for SPECT heads, you may want to avoid recording hits from both heads in the same file, in which case, set the flag to False.

DigitizerHitsCollectionActor
----------------------------

The `DigitizerHitsCollectionActor` collects hits occurring in a given volume (or its daughter volumes). Every time a step occurs in the volume, a list of attributes is recorded. The list of attributes is defined by the user:

.. code-block:: python

   hc = sim.add_actor('DigitizerHitsCollectionActor', 'Hits')
   hc.attached_to = ['crystal1', 'crystal2']
   hc.output_filename = 'test_hits.root'
   hc.attributes = ['TotalEnergyDeposit', 'KineticEnergy', 'PostPosition',
                    'CreatorProcess', 'GlobalTime', 'VolumeName', 'RunID', 'ThreadID', 'TrackID']

The names of the attributes align with Geant4 terminology. The list of available attributes is defined in the file `GateDigiAttributeList.cpp` and can be printed with:

.. code-block:: python

   import opengate_core as gate_core
   am = gate_core.GateDigiAttributeManager.GetInstance()
   print(am.GetAvailableDigiAttributeNames())

Attributes correspondence with Gate 9.X for Hits and Singles:

+------------------------+-------------------------+
| Gate 9.X               | Gate 10                 |
+========================+=========================+
| edep or energy         | TotalEnergyDeposit       |
+------------------------+-------------------------+
| posX/Y/Z of globalPosX/Y/Z | PostPosition_X/Y/Z    |
+------------------------+-------------------------+
| time                   | GlobalTime              |
+------------------------+-------------------------+

The list of hits can be written to a ROOT file at the end of the simulation. Like in Gate, hits with zero energy are ignored. If zero-energy hits are needed, use a PhaseSpaceActor.

The actors used to convert some `hits` to one `digi` are `DigitizerHitsAdderActor` and `DigitizerReadoutActor` (see next sections).

.. image:: ../figures/digitizer_adder_readout.png


DigitizerHitsAdderActor
-----------------------

This actor groups the hits per different volumes according to the option `group_volume` (by default, this is the deeper volume that contains the hit). All hits occurring in the same event in the same volume are gathered into one single digi according to one of two available policies:

- **EnergyWeightedCentroidPosition**:
  - The final energy (`TotalEnergyDeposit`) is the sum of all deposited energy.
  - The position (`PostPosition`) is the energy-weighted centroid position.
  - The time (`GlobalTime`) is the time of the earliest hit.

- **EnergyWinnerPosition**:
  - The final energy (`TotalEnergyDeposit`) is the energy of the hit with the largest deposited energy.
  - The position (`PostPosition`) is the position of the hit with the largest deposited energy.
  - The time (`GlobalTime`) is the time of the earliest hit.

.. code-block:: python

   sc = sim.add_actor("DigitizerAdderActor", "Singles")
   sc.output_filename = 'test_hits.root'
   sc.input_digi_collection = "Hits"
   sc.policy = "EnergyWeightedCentroidPosition"
   # sc.policy = "EnergyWinnerPosition"
   sc.group_volume = crystal.name

Note that this actor is only triggered at the end of an event, so the `attached_to` volume has no effect. Examples are available in test 037.

DigitizerReadoutActor
---------------------

This actor is similar to `DigitizerHitsAdderActor`, with one additional option: the resulting positions of the digi are set at the center of the defined volumes (discretized). The option `discretize_volume` indicates the volume name where the discrete position will be taken.

.. code-block:: python

   sc = sim.add_actor("HitsReadoutActor", "Singles")
   sc.input_digi_collection = "Hits"
   sc.group_volume = stack.name
   sc.discretize_volume = crystal.name
   sc.policy = "EnergyWeightedCentroidPosition"

Examples are available in test 037.

DigitizerGaussianBlurringActor
------------------------------

This module applies blurring to an attribute, such as time or energy. The method can be Gaussian, InverseSquare, or Linear:

For Gaussian blurring, specify the sigma or FWHM with `blur_sigma` or `blur_fwhm`.

For InverseSquare blurring, use `blur_reference_value` and `blur_reference_value` (equation TBD).

For Linear blurring, specify `blur_reference_value`, `blur_slope`, and `blur_reference_value` (equation TBD).

.. code-block:: python

   bc = sim.add_actor("DigitizerBlurringActor", "Singles_with_blur")
   bc.output_filename = "output.root"
   bc.input_digi_collection = "Singles_readout"
   bc.blur_attribute = "GlobalTime"
   bc.blur_method = "Gaussian"
   bc.blur_fwhm = 100 * ns

DigitizerSpatialBlurringActor
-----------------------------

.. warning::
   This documentation is still TODO. Blurring may cause points to fall outside the volume (use the `keep_in_solid_limits` option). This is useful for monocrystals but should not be used for pixelated crystals.

DigitizerEnergyWindowsActor
---------------------------

The `DigitizerEnergyWindowsActor` is used in both PET and SPECT simulations to define energy windows, which filter particles by energy range. This helps to reduce noise and select relevant events.

For PET, the window is centered around the 511 keV annihilation photon:

.. code-block:: python

   # EnergyWindows for PET
   ew = sim.add_actor("DigitizerEnergyWindowsActor", "EnergyWindows")
   ew.attached_to = hc.attached_to
   ew.input_digi_collection = "Singles"
   ew.channels = [{"name": ew.name, "min": 425 * keV, "max": 650 * keV}]  # 511 keV window
   ew.output_filename = root_name

For SPECT, the windows can be more complex, with multiple channels:

.. code-block:: python

   # EnergyWindows for SPECT
   ew = sim.add_actor("DigitizerEnergyWindowsActor", "EnergyWindows")
   ew.attached_to = hc.attached_to
   ew.input_digi_collection = "Singles"
   ew.channels = [
       {"name": "scatter", "min": 114 * keV, "max": 126 * keV},
       {"name": "peak140", "min": 126 * keV, "max": 154.55 * keV},  # Tc-99m
   ]
   ew.output_filename = hc.output_filename

For PET, refer to test037; for SPECT, refer to test028.

DigitizerProjectionActor
------------------------

The `DigitizerProjectionActor` generates 2D projections from digitized particle hits in SPECT or PET simulations. It takes input collections and creates a projection image based on predefined grid spacing and size.

.. code-block:: python

   proj = sim.add_actor("DigitizerProjectionActor", "Projection")
   proj.attached_to = hc.attached_to  # Attach to crystal volume
   proj.input_digi_collections = ["scatter", "peak140", "Singles"]  # Use multiple energy channels
   proj.spacing = [4.41806 * mm, 4.41806 * mm]  # Set pixel spacing in mm
   proj.size = [128, 128]  # Image size in pixels (128x128)
   proj.origin_as_image_center = False  # Origin is not at image center
   proj.output_filename = 'projection.mhd'

Refer to test028 for SPECT examples.

DigitizerEfficiencyActor
-------------------------

This module simulates detection with non-100% efficiency, which can be set as a float between 0 and 1 (where 1 means all digis are stored). For each digi, a random number determines if the digi is kept.

.. code-block:: python

   ea = sim.add_actor("DigitizerEfficiencyActor", "Efficiency")
   ea.input_digi_collection = "Hits"
   ea.efficiency = 0.3

Refer to test057 for more details.

Coincidences Sorter
-------------------

.. note::
   The current version of the Coincidence sorter is still a work in progress. It is only available for offline use.

The Coincidence Sorter finds pairs of coincident singles within a defined time window and groups them into coincidence events. Various policies are available for handling multiple coincidences:

.. code-block:: python

   singles_tree = root_file["Singles_crystal"]
   ns = gate.g4_units.nanosecond
   time_window = 3 * ns
   policy = "keepAll"
   minSecDiff = 1  # NOT YET IMPLEMENTED

   # Apply coincidence sorter
   coincidences = coincidences_sorter(singles_tree, time_window, policy, minDistanceXY, maxDistanceZ, chunk_size=1000000)

The following policies are supported:

- **takeAllGoods**: Each good pair is considered.
- **takeWinnerOfGoods**: Only the pair with the highest energy is considered.
- **takeWinnerIfIsGood**: If the highest energy pair is good, take it; otherwise, kill the event.
- **keepIfOnlyOneGood**: If exactly one good pair exists, keep the multicoincidence.
- **removeMultiples**: No multiple coincidences are accepted, even if there are good pairs.

Refer to test072 for more details.

ARFActor and ARFTrainingDatasetActor
------------------------------------

The Angular Response Function (ARF) is a method designed to accelerate SPECT simulations by replacing full particle tracking within the SPECT head (collimator and crystal) with an analytical function. This function provides the detection probability of a photon across all energy windows based on its direction and energy. Specifically, ARF estimates the probability that an incident photon will interact with or pass through the collimator and reach the detector plane at a specified energy window. By approximating the SPECT head’s behavior in this manner, ARF allows for faster planar and SPECT simulations. Using ARF involves three steps:

1.	Create a training dataset.
2.	Build the ARF function.
3.	Apply the trained ARF to enhance simulation efficiency.

.. warning::

Ensure that torch and garf (Gate ARF) packages are installed prior to use. Install them with: `pip install torch gaga_phsp garf`

Step 1: Creating the Training Dataset
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The initial step involves creating a dataset for training. This can be implemented by following the example in `test043_garf_training_dataset.py`. Configure a simplified simulation to emit photons across the expected energy range (e.g., slightly above 140.5 keV for Tc99m) through the SPECT head, recording detected counts. The `ARFTrainingDatasetActor` is utilized here, with input from a detector plane positioned directly in front of the collimator. This actor stores detected counts per energy window in a ROOT file. For efficiency, a Russian roulette technique reduces the data size for photons with low detection probabilities due to large incident angles. Users must specify energy windows by referencing the name of the `DigitizerEnergyWindowsActor` associated with the SPECT system.

.. code-block:: python

    # arf actor for building the training dataset
    arf = sim.add_actor("ARFTrainingDatasetActor", "my_arf_actor")
    arf.attached_to = detector_plane.name
    arf.output_filename = "arf_training_dataset.root"
    arf.energy_windows_actor = ene_win_actor.name
    arf.russian_roulette = 50


Step 2: Training the ARF Model
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

After generating the dataset, train the ARF model using garf_train, which trains a neural network to represent the ARF function. This requires the previous dataset as input, with training options specified in a JSON configuration file (e.g., `train_arf_v058.json` in `tests/data/test043`). A suitable GPU is recommended for training. The output is a .pth file containing the trained model and its associated weights.

.. code-block:: bash

    garf_train  train_arf_options.json arf_training_dataset.root arf.pth

Step 3: Using the Trained ARF Model in Simulation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


With the trained model (.pth file), you can now substitute direct photon tracking in the SPECT head with the ARF model. This is accomplished with the `ARFActor`, which takes the trained .pth file, consider a detector plane, and generates a 2D projection image with estimated detection counts. Note that the values represent probabilities rather than integer counts, as this is a variance reduction method. Although the computation time per particle is comparable to full tracking, ARF accelerates convergence towards the mean counts across all pixels. Consequently, an ARF-based simulation can achieve the same noise level as a traditional simulation but with up to 5-10 times fewer particles. The `distance_to_crystal` parameter defines the spacing between the detector plane and the crystal center, allowing for positional correction in the 2D projection.

.. code-block:: python

    arf = sim.add_actor("ARFActor", "arf")
    arf.attached_to = detector_plane
    arf.output_filename = "projection.mhd"
    arf.image_size = [128, 128]
    arf.image_spacing = [4.41806 * mm, 4.41806 * mm]
    arf.verbose_batch = True
    arf.distance_to_crystal = 74.625 * mm
    arf.pth_filename = "arf.pth"
    arf.batch_size = 2e5
    arf.gpu_mode = "auto"


The source code for garf is here : https://github.com/OpenGATE/garf
The associated publication is:

    Learning SPECT detector angular response function with neural network for accelerating Monte-Carlo simulations. Sarrut D, Krah N, Badel JN, Létang JM. Phys Med Biol. 2018 Oct 17;63(20):205013. doi: 10.1088/1361-6560/aae331.  https://www.ncbi.nlm.nih.gov/pubmed/30238925


LETActor
--------

.. note::
   Documentation TODO. Refer to test050 for current examples.

ComptonSplittingActor
---------------------

This actor generates N particles with reduced weight whenever a Compton process occurs. The options include:

- **splitting factor**: Number of splits.
- **Russian Roulette**: Option for selective elimination based on angle and probability.
- **Minimum Track Weight**: Avoids splitting very low-weight particles.

.. code-block:: python

   compt_splitting_actor = sim.add_actor("ComptSplittingActor", "ComptSplitting")
   compt_splitting_actor.attached_to = W_tubs.name
   compt_splitting_actor.splitting_factor = nb_split
   compt_splitting_actor.russian_roulette = True
   compt_splitting_actor.rotation_vector_director = True
   compt_splitting_actor.vector_director = [0, 0, -1]

Refer to test071 for more details.

.. code-block:: python

  compt_splitting_actor = sim.add_actor("ComptSplittingActor", "ComptSplitting")
  compt_splitting_actor.attached_to = W_tubs.name
  compt_splitting_actor.splitting_factor = nb_split
  compt_splitting_actor.russian_roulette = True
  compt_splitting_actor.rotation_vector_director = True
  compt_splitting_actor.vector_director = [0, 0, -1]

The options include:

- the splitting Number: Specifies the number of splits to create.
- A Russian Roulette to activate : Enables selective elimination based on a user-defined angle, with a probability of 1/N.
- A Minimum Track Weight: Determines the minimum weight a track must possess before undergoing subsequent Compton splitting. To mitigate variance fluctuations or too low-weight particles, I recommend to set the minimum weight to the average weight of your track multiplied by 1/N², with N depending on your application.
