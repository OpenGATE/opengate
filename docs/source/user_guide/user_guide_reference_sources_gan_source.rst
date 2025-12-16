.. _source-gan-source:

GAN sources (Generative Adversarial Network)
============================================

Description
-----------

A Phase-Space (phsp) source typically uses a large file containing particle properties (e.g., energy, position, direction, time) to generate primary events in a simulation. This traditional phsp source can be replaced by a neural network-based particle generator that replicates similar distribution probabilities in a more compact form. GAN sources utilize Generative Adversarial Networks (GANs) trained to reproduce these particle properties based on an initial phsp. This approach, proposed in `[Sarrut et al, PMB, 2019] <https://doi.org/10.1088/1361-6560/ab3fc1>`__, can be applied across various applications:

- Linac phsp: `test034 <https://github.com/OpenGATE/opengate/tree/master/opengate/tests/src/source>`_ `[Sarrut et al, PMB, 2019] <https://doi.org/10.1088/1361-6560/ab3fc1>`__
- SPECT: `test038 <https://github.com/OpenGATE/opengate/tree/master/opengate/tests/src/source>`_ and `test047 <https://github.com/OpenGATE/opengate/tree/master/opengate/tests/src/source>`_ `[Sarrut et al, PMB, 2021] <https://doi.org/10.1088/1361-6560/abde9a>`_ and `[Saporta et al, PMB, 2022] <https://doi.org/10.1088/1361-6560/aca068>`_
- PET: `test040 <https://github.com/OpenGATE/opengate/tree/master/opengate/tests/src/source>`_ `[Sarrut et al, PMB, 2023] <https://doi.org/10.1088/1361-6560/acdfb1>`_

Installation Requirements
^^^^^^^^^^^^^^^^^^^^^^^^^

To use GAN sources, first install the required `torch` and `gaga_phsp` libraries with:

.. code:: bash

    pip install torch gaga_phsp

The `gaga_phsp` library provides tools for training and using GAN models: https://github.com/OpenGATE/gaga-phsp.

Workflow Overview
^^^^^^^^^^^^^^^^^

The workflow to use a GAN source involves three main steps:

1. Generate the training dataset.
2. Train the GAN model.
3. Use the GAN model as a source in GATE.

For Linac applications, a conventional Linac phsp can serve as the training dataset. In SPECT or PET applications, a conditional GAN is used to generate particles exiting the patient, conditioned on the activity distribution within the patient. In this case, the training dataset must include not only the particle properties at the patient exit (e.g., position and direction in a spheroid or cylinder around the patient) but also the initial emission point inside the patient (using `EventPosition` and `EventDirection`). An example can be found in `test038_gan_phsp_spect_training_dataset_mt.py <https://github.com/OpenGATE/opengate/blob/master/opengate/tests/src/source/test038_gan_phsp_spect_training_dataset_mt.py>`_.

Training the GAN
^^^^^^^^^^^^^^^^

Once the training data is generated, train the GAN model outside of GATE using `gaga_phsp`. Example command:

.. code:: bash

    gaga_train my_phsp.root gaga_train_options.json -pi epoch 50 -o gan_source.pth

A sample JSON file for GAN options, `train_gaga_v124.json`, can be found in the `tests/data/test038` folder. Training can be resource-intensive, typically requiring a GPU and several hours. The resulting generator model is saved as a compact `.pth` file, containing the neural network weights (generally a few tens of MB).

Using the GAN Source in GATE
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Once trained, the generator can be used as a source in GATE using the ``GANSource`` type, as in the example below:

.. code:: python

    gsource = sim.add_source("GANSource", "my_gan_source")
    gsource.particle = "gamma"
    gsource.activity = 1 * MBq
    gsource.pth_filename = "gan_source.pth"

    gsource.position_keys = ["PrePosition_X", "PrePosition_Y", "PrePosition_Z"]
    gsource.direction_keys = ["PreDirection_X", "PreDirection_Y", "PreDirection_Z"]
    gsource.energy_key = "KineticEnergy"
    gsource.time_key = None
    gsource.weight_key = None

    gsource.energy_min_threshold = 10 * keV
    gsource.backward_distance = 5 * cm
    # Use ZeroEnergy policy to avoid altering event counts
    gsource.skip_policy = "ZeroEnergy"

    gsource.batch_size = 5e4
    gsource.verbose_generator = True
    gsource.gpu_mode = "auto"

    cond_gen = gate.sources.gansources.VoxelizedSourceConditionGenerator("myactivity.mhd")
    cond_gen.compute_directions = True
    gen = gate.sources.gansources.GANSourceConditionalGenerator(gsource, cond_gen.generate_condition)
    source.generator = gen

In this example, the GAN source emits 10 MBq of gamma particles with position and direction distributions learned by the GAN. Each attribute of the particles (e.g., position, direction, energy) corresponds to a key in the GAN file. The `energy_min_threshold` parameter defines a lower limit for energy; particles with energy below this threshold can either be skipped (`skip_policy = "SkipEvents"`) or assigned zero energy (`skip_policy = "ZeroEnergy"`), meaning they are not tracked.

The GAN operates in batches, with the size defined by `batch_size`. In this case, a conditional GAN is used to control the emitted particles based on an internal activity distribution provided by a voxelized source (`myactivity.mhd` file). This approach can efficiently replicate complex spatial dependencies in the particle emission process.

The GAN-based source is an experimental feature in GATE. While it offers promising advantages in terms of reduced file size and simulation speed, users are encouraged to approach it cautiously. We strongly recommend thoroughly reviewing the associated publications `[Sarrut et al, PMB, 2019] <https://doi.org/10.1088/1361-6560/ab3fc1>`_, `[Sarrut et al, PMB, 2021] <https://doi.org/10.1088/1361-6560/abde9a>`_, and `[Saporta et al, PMB, 2022] <https://doi.org/10.1088/1361-6560/aca068>`_ to understand the method’s assumptions, limitations, and best practices. This method is best suited for research purposes and may not yet be appropriate for clinical or regulatory applications without extensive validation.


Reference
---------

.. autoclass:: opengate.sources.gansources.GANSource
.. autoclass:: opengate.sources.gansources.GANPairsSource
