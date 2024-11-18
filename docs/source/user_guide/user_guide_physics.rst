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

**Ion or e+ source.**

To enable this behavior in a simulation, the user needs to set the `MeanEnergyPerIonPair` of all the materials where acollinearity of annihilation photons is to be simulated to 0.5 eV (`Geant4 Release note <www.geant4.org/download/release-notes/notes-v10.7.0.html>`_).
This is done differently depending on whether the material is defined by Geant4, in `GateMaterials.db` or created dynamically.

**Geant4 default material.**

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


**Material defined in `GateMaterials.db`**

.. code-block:: python

    # Provide the location of GateMaterials.db to the volume manager.
    sim.volume_manager.add_material_database(path_to_gate_materials_db)

    # Set the MeanEnergyPerIonPair of the material in the physics manager
    # material_of_interest is the name of the material of interest, which should be defined in GateMaterials.db located at path_to_gate_materials_db
    sim.physics_manager.mean_energy_per_ion_pair[material_of_interest] = 5.0 * eV


**Material created dynamically**


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


Managing Cuts and Limits
------------------------

TODO

`Geant4 User Guide: Tracking and Physics <https://geant4-userdoc.web.cern.ch/UsersGuides/ForApplicationDeveloper/html/TrackingAndPhysics/thresholdVScut.html>`_

`Cuts per Region <https://geant4-userdoc.web.cern.ch/UsersGuides/ForApplicationDeveloper/html/TrackingAndPhysics/cutsPerRegion.html>`_

`User Limits <https://geant4-userdoc.web.cern.ch/UsersGuides/ForApplicationDeveloper/html/TrackingAndPhysics/userLimits.html>`_
