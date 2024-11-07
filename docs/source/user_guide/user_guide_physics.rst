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

Managing Cuts and Limits
------------------------

WARNING: this part is work in progress. DO NOT USE YET.

`Geant4 User Guide: Tracking and Physics <https://geant4-userdoc.web.cern.ch/UsersGuides/ForApplicationDeveloper/html/TrackingAndPhysics/thresholdVScut.html>`_

`Cuts per Region <https://geant4-userdoc.web.cern.ch/UsersGuides/ForApplicationDeveloper/html/TrackingAndPhysics/cutsPerRegion.html>`_

`User Limits <https://geant4-userdoc.web.cern.ch/UsersGuides/ForApplicationDeveloper/html/TrackingAndPhysics/userLimits.html>`_
