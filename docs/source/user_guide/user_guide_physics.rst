Physics
=======

The management of physics in Geant4 is rich and complex, with hundreds of options. OPENGATE proposes a subset of available options.

Physics List and Decay
----------------------

First, the user needs to select a physics list. A physics list contains a large set of predefined physics options, adapted to different problems. Please refer to the `Geant4 guide <https://geant4-userdoc.web.cern.ch/UsersGuides/PhysicsListGuide/html/physicslistguide.html>`_ for a detailed explanation. The user can select the physics list with the following:

.. code-block:: python

    # Assume that sim is a simulation
    sim.physics_manager.physics_list_name = 'QGSP_BERT_EMZ'

The default physics list is QGSP_BERT_EMV. The Geant4 standard physics lists are composed of a first part:

.. code-block:: text

    FTFP_BERT
    FTFP_BERT_TRV
    FTFP_BERT_ATL
    FTFP_BERT_HP
    FTFQGSP_BERT
    FTFP_INCLXX
    FTFP_INCLXX_HP
    FTF_BIC
    LBE
    QBBC
    QGSP_BERT
    QGSP_BERT_HP
    QGSP_BIC
    QGSP_BIC_HP
    QGSP_BIC_AllHP
    QGSP_FTFP_BERT
    QGSP_INCLXX
    QGSP_INCLXX_HP
    QGS_BIC
    Shielding
    ShieldingLEND
    ShieldingM
    NuBeam

And a second part with the electromagnetic interactions:

.. code-block:: text

    _EMV
    _EMX
    _EMY
    _EMZ
    _LIV
    _PEN
    __GS
    __SS
    _EM0
    _WVI
    __LE

The lists can change according to the Geant4 version (this list is for 10.7).

Additional physics lists are available:

.. code-block:: text

    G4EmStandardPhysics_option1
    G4EmStandardPhysics_option2
    G4EmStandardPhysics_option3
    G4EmStandardPhysics_option4
    G4EmStandardPhysicsGS
    G4EmLowEPPhysics
    G4EmLivermorePhysics
    G4EmLivermorePolarizedPhysics
    G4EmPenelopePhysics
    G4EmDNAPhysics
    G4OpticalPhysics

Note that EMV, EMX, EMY, EMZ corresponds to option1, 2, 3, 4 (don't ask us why).

Radioactive Decay
-----------------

The decay process, if needed, must be added explicitly. This is done with:

.. code-block:: python

    sim.physics_manager.enable_decay(True)

Under the hood, this will add two processes to the Geant4 list of processes: G4DecayPhysics and G4RadioactiveDecayPhysics. These processes are required particularly if a decaying generic ion (such as F18) is used as a source. Additional information can be found here:

- `Geant4 Particle Decay Process <https://geant4-userdoc.web.cern.ch/UsersGuides/ForApplicationDeveloper/html/TrackingAndPhysics/physicsProcess.html#particle-decay-process>`_
- `Geant4 Decay Physics <https://geant4-userdoc.web.cern.ch/UsersGuides/PhysicsReferenceManual/html/decay/decay.html>`_
- `Physics List <https://geant4-userdoc.web.cern.ch/UsersGuides/PhysicsListGuide/html/physicslistguide.html>`_
- `Nuclear Data Table <http://www.lnhb.fr/nuclear-data/nuclear-data-table/>`_

Acollinearity of Annihilation Photons
-------------------------------------

Without modifications, most annihilation photon pairs from positron-electron annihilation will be collinear. For water between 20–30°C, the acollinearity of annihilation photons follows a 2D Gaussian distribution with a FWHM of 0.5° (`Colombino et al. 1965 <https://link.springer.com/article/10.1007/BF02748591>`_).

...

[Content continues here following the structured format]

...

Electromagnetic Parameters
--------------------------

Electromagnetic parameters are managed by a specific Geant4 object called G4EmParameters. It is available with the following:

.. code-block:: python

    sim.physics_manager.em_parameters.fluo = True
    sim.physics_manager.em_parameters.auger = True
    sim.physics_manager.em_parameters.auger_cascade = True
    sim.physics_manager.em_parameters.pixe = True
    sim.physics_manager.em_parameters.deexcitation_ignore_cut = True

...

OptiGAN
========

Refer to this `testcase <https://github.com/OpenGATE/opengate/blob/6cd98d3f7d76144889b1615e28a00873ebc28f81/opengate/tests/src/test081_simulation_optigan_with_random_seed.py>`_ for a simulation example.

In the default optical simulations of Gate v10, each optical photon generated is treated as a separate track, which can be quite resource-intensive. For instance, approximately one second is required to simulate the spatial distribution of optical photons detected from a single 511 keV gamma ray interaction in a 20 mm thick layer of bismuth germanate (BGO), which has a light yield of about 8500 photons per MeV. Recent advancements in Monte Carlo simulations using deep learning, particularly with Generative Adversarial Networks (GANs), have shown significant potential in reducing simulation times. We have adopted a specific type of GAN known as Wasserstein GAN to enhance the efficiency of generating optical photons in scintillation crystals, which we have named OptiGAN. For more detailed information, you can refer to this `research paper <https://iopscience.iop.org/article/10.1088/2632-2153/acc782>`_.

The OptiGAN model trained with 3 x 3 x 3 mm\ :sup:`3` BGO crystal is already included with Gate 10. More models will be added in the future.

Users can utilize OptiGAN in two ways: they can integrate it into the simulation file, or they can use it after running the simulation.

Method 1 - Running OptiGAN with Simulation
------------------------------------------

.. code-block:: python

    optigan = OptiGAN(input_phsp_actor=phsp_actor)

Method 2 - Running OptiGAN After Simulation
-------------------------------------------

.. code-block:: python

    optigan = OptiGAN(root_file_path=hc.get_output_path())

Method 1 can be used when a user wants to run OptiGAN within the same simulation file. The ``input_phsp_actor`` parameter must be set to the phase space actor attached to the crystal in the simulation. The output will then be saved in the folder specified by ``sim.output_dir``.

Method 2 can be used when a user wants to use OptiGAN in a file outside their main simulation file. In this case, the ``root_file_path`` must be set to the path of the root file obtained from the simulation.

Workflow of OptiGAN Module in Gate 10
-------------------------------------

OptiGAN requires two pieces of input information: the position of gamma interaction in the crystal and the number of optical photons emitted. This information is automatically parsed from the root files when users utilize OptiGAN.

- **Position of gamma interaction:** This refers to the coordinate information of gamma interaction with the scintillation crystal.

- **Number of optical photons emitted:** This indicates the total number of optical photons emitted per gamma event.

Obtaining the number of optical photons emitted without modifying Geant4 is challenging. As a workaround for now, we ask users to use a kill actor and add a filter in the test case to eliminate optical photons.

.. code-block:: python

    # filter : remove opticalphoton
    fe = sim.add_filter("ParticleFilter", "fe")
    fe.particle = "opticalphoton"
    fe.policy = "reject"

    # add a kill actor to the crystal
    ka = sim.add_actor("KillActor", "kill_actor2")
    ka.attached_to = crystal
    ka.filters.append(fe)

NOTE: Using a kill actor still creates optical photons, but it terminates the track after the first step. This approach provides us with the required information (number of optical photons emitted) as an input for OptiGAN, while also saving tracking time by terminating the photons early.

.. image:: ../figures/kill_actor.png

NOTE: The analysis of computation time gained by using OptiGAN in Gate 10 is still in works by the team at UC Davis.

Managing Cuts and Limits
------------------------

WARNING: this part is work in progress. DO NOT USE YET.

`Geant4 User Guide: Tracking and Physics <https://geant4-userdoc.web.cern.ch/UsersGuides/ForApplicationDeveloper/html/TrackingAndPhysics/thresholdVScut.html>`_

`Cuts per Region <https://geant4-userdoc.web.cern.ch/UsersGuides/ForApplicationDeveloper/html/TrackingAndPhysics/cutsPerRegion.html>`_

`User Limits <https://geant4-userdoc.web.cern.ch/UsersGuides/ForApplicationDeveloper/html/TrackingAndPhysics/userLimits.html>`_
