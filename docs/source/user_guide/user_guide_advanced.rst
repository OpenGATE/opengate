****************
Details: Physics
****************


.. _physics-lists-details-label:

Physics lists
=============

The names of the Geant4 physics lists are composed of a first part concerning hadronic physics:

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

and a second part concerning electromagnetic interactions:

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

The second part in the name instructs let's Geant4 know which set of processes it should use for electromagnetic processes.

In GATE, you can also select the electromagnetic part of a physics list only, e.g.

.. code-block:: python

    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option4"

The simulation will then not consider any hadronic (nuclear) interactions. For the seasoned Geant4 users: Technically speaking, G4EmStandardPhysics_option4 is not a physics list in Geant4, but a PhysicsConstructor. GATE is implemented in a way that you can use it as if it were a phsyics list, which makes usage much easier.

Have a look at the `Geant4 guide <https://geant4-userdoc.web.cern.ch/UsersGuides/PhysicsListGuide/html/physicslistguide.html>`_ for more details.
Note that the Geant4 physics lists can change according to the Geant4 version (those above are for Geant4 10.7).


Radioactive Decay
=================

Under the hood, the setting ``sim.physics_manager.enable_decay = True`` will add two processes to the Geant4 list of processes: G4DecayPhysics and G4RadioactiveDecayPhysics. These processes are required particularly if a decaying generic ion (such as F18) is used as a source. Additional information can be found here:

- `Geant4 Particle Decay Process <https://geant4-userdoc.web.cern.ch/UsersGuides/ForApplicationDeveloper/html/TrackingAndPhysics/physicsProcess.html#particle-decay-process>`_
- `Geant4 Decay Physics <https://geant4-userdoc.web.cern.ch/UsersGuides/PhysicsReferenceManual/html/decay/decay.html>`_
- `Physics List <https://geant4-userdoc.web.cern.ch/UsersGuides/PhysicsListGuide/html/physicslistguide.html>`_
- `Nuclear Data Table <http://www.lnhb.fr/nuclear-data/nuclear-data-table/>`_


.. _production-cuts-details-label:
Production cuts
===============

`Geant4 User Guide: Tracking and Physics <https://geant4-userdoc.web.cern.ch/UsersGuides/ForApplicationDeveloper/html/TrackingAndPhysics/thresholdVScut.html>`_

`Cuts per Region <https://geant4-userdoc.web.cern.ch/UsersGuides/ForApplicationDeveloper/html/TrackingAndPhysics/cutsPerRegion.html>`_


Acollinearity of Annihilation Photons
=====================================

Without modifications, most annihilation photon pairs from positron-electron annihilation will be collinear. For water between 20–30°C, the acollinearity of annihilation photons follows a 2D Gaussian distribution with a FWHM of 0.5° (`Colombino et al. 1965 <https://link.springer.com/article/10.1007/BF02748591>`_).

Ion or e+ source
----------------

To enable this behavior in a simulation, the user needs to set the `MeanEnergyPerIonPair` of all the materials where acollinearity of annihilation photons is to be simulated to 0.5 eV (`Geant4 Release note <www.geant4.org/download/release-notes/notes-v10.7.0.html>`_).
This is done differently depending on whether the material is defined by Geant4, in `GateMaterials.db` or created dynamically.

Geant4 default material
-----------------------

.. code-block:: python

    # First, get a reference to the material where acollinearity of annihilation photons is to be simulated.
    # This is done by providing the name of the materials, e.g., "G4_WATER", to the volume manager.
    mat = sim.volume_manager.find_or_build_material(material_of_interest)

    # Second, get a reference to the material ionisation property.
    # You can get the value of MeanEnergyPerIonPair of the materials with the command 'ionisation.GetMeanExcitationEnergy() / eV'
    # By default, MeanEnergyPerIonPair of a material is 0.0 eV
    ionisation = mat.GetIonisation()

    # Set the value of MeanEnergyPerIonPair to the desired value. Here, we use the recommended 5.0 eV.
    ionisation.SetMeanEnergyPerIonPair(5.0 * eV)


Material defined in `GateMaterials.db`
--------------------------------------

.. code-block:: python

    # Provide the location of GateMaterials.db to the volume manager.
    sim.volume_manager.add_material_database(path_to_gate_materials_db)

    # Set the MeanEnergyPerIonPair of the material in the physics manager
    # material_of_interest is the name of the material of interest, which should be defined in GateMaterials.db located at path_to_gate_materials_db
    sim.physics_manager.mean_energy_per_ion_pair[material_of_interest] = 5.0 * eV


Material created dynamically
----------------------------


.. code-block:: python

    # Provide a description of the material to the volume manager
    # material_of_interest is the name of the material of interest
    sim.volume_manager.material_database.add_material_nb_atoms(material_of_interest, ex_elems, ex_nbAtoms, ex_density)

    # Set the MeanEnergyPerIonPair of the material in the physics manager
    # material_of_interest is the name of the material of interest, which should be defined in GateMaterials.db located at path_to_gate_materials_db
    sim.physics_manager.mean_energy_per_ion_pair[material_of_interest] = 5.0 * eV


**Back-to-back source**

Currently, simulating this behavior cannot (yet!) be reproduced with back-to-back source. This is work in progress.

**Further considerations**

The property needed to simulate acollinearity, as expected in PET imaging, is defined at the level of materials, not at the volume level.
In other words, if one needs a water volume with acollinearity and another water volume without acollinearity in the simulation, two materials (e.g., water_aco and water_colin) need to be defined, with only the former using the code previously shown.

More recently, `[Shibuya et al. 2007] <https://iopscience.iop.org/article/10.1088/0031-9155/52/17/010>`_ have shown that acollinearity of annihilation photons in a human subject follows a double Gaussian distribution with a combined FWHM of 0.55°.
While the double Gaussian distribution currently cannot be reproduced in GATE, setting the `MeanEnergyPerIonPair` of the material to 6.0 eV results in a 2D Gaussian with a FWHM of 0.55°.

**WARNING:** Currently, it is unknown if setting the `MeanEnergyPerIonPair` parameter to a non-zero value has an impact on other facets of Geant4 physics and thus on the GATE simulation.

OptiGAN
=======

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
