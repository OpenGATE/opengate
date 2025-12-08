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


.. _user-limits-details-label:

User limits
===========


.. This last option is global, i.e. a step limit will be imposed on electrons in any volume in which you set a max step size.

`User Limits <https://geant4-userdoc.web.cern.ch/UsersGuides/ForApplicationDeveloper/html/TrackingAndPhysics/userLimits.html>`_



Acollinearity of Annihilation Photons (APA)
===========================================

Without modifications, most annihilation photon pairs from positron-electron annihilation will be collinear. For water between 20–30°C, the deviation of APA follows a 2D Gaussian distribution with a FWHM of 0.5° (`Colombino et al. 1965 <https://link.springer.com/article/10.1007/BF02748591>`_).

Ion or e+ source
----------------

To enable this behavior in a simulation, the user needs to set the `MeanEnergyPerIonPair` of all the materials where APA is desired to 0.5 eV (`Geant4 Release note <https://www.geant4.org/download/release-notes/notes-v10.7.0.html>`_).
This is done differently depending on whether the material is defined by Geant4, in `GateMaterials.db` or created dynamically.
Note: not all physics lists simulate APA (em_standard does but not Penelope).

Geant4 default material
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # First, get a reference to the material where APA is to be simulated.
    # This is done by providing the name of the materials, e.g., "G4_WATER", to the volume manager.
    mat = sim.volume_manager.find_or_build_material(material_of_interest)

    # Second, get a reference to the material ionisation property.
    # You can get the value of MeanEnergyPerIonPair of the materials with the command 'ionisation.GetMeanExcitationEnergy() / eV'
    # By default, MeanEnergyPerIonPair of a material is 0.0 eV
    ionisation = mat.GetIonisation()

    # Set the value of MeanEnergyPerIonPair to the desired value. Here, we use the recommended 5.0 eV.
    ionisation.SetMeanEnergyPerIonPair(5.0 * eV)


Material defined in `GateMaterials.db`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # Provide the location of GateMaterials.db to the volume manager.
    sim.volume_manager.add_material_database(path_to_gate_materials_db)

    # Set the MeanEnergyPerIonPair of the material in the physics manager
    # material_of_interest is the name of the material of interest, which should be defined in GateMaterials.db located at path_to_gate_materials_db
    sim.physics_manager.mean_energy_per_ion_pair[material_of_interest] = 5.0 * eV


Material created dynamically
~~~~~~~~~~~~~~~~~~~~~~~~~~~~


.. code-block:: python

    # Provide a description of the material to the volume manager
    # material_of_interest is the name of the material of interest
    sim.volume_manager.material_database.add_material_nb_atoms(material_of_interest, ex_elems, ex_nbAtoms, ex_density)

    # Set the MeanEnergyPerIonPair of the material in the physics manager
    # material_of_interest is the name of the material of interest, which should be defined in GateMaterials.db located at path_to_gate_materials_db
    sim.physics_manager.mean_energy_per_ion_pair[material_of_interest] = 5.0 * eV

**Further considerations**

The property needed to simulate APA, as expected in PET imaging, is defined at the level of materials, not at the volume level.
In other words, if one needs a water volume where annihilation photons will have acollinearity and another water volume without it in the simulation, two materials (e.g., water_aco and water_colin) need to be defined, with only the former using the code previously shown.

More recently, `[Shibuya et al. 2007] <https://iopscience.iop.org/article/10.1088/0031-9155/52/17/010>`_ have shown that the deviation of APA in a human subject follows a double Gaussian distribution with a combined FWHM of 0.55°.
While the double Gaussian distribution currently cannot be reproduced in GATE, setting the `MeanEnergyPerIonPair` of the material to 6.0 eV results in a 2D Gaussian with a FWHM of 0.55°.

**WARNING:** Currently, it is unknown if setting the `MeanEnergyPerIonPair` parameter to a non-zero value has an impact on other facets of Geant4 physics and thus on the GATE simulation.

Back-to-back source
-------------------

For a source defined as a `back_to_back` particle, activation of APA is straightforward:
.. code-block:: python

  # Assuming that 'your_source' is a source defined as a 'back_to_back' particle
  your_source.direction.accolinearity_flag = True

By default, the deviation of APA is defined as a 2D Gaussian distribution with a FWHM of 0.5°.
If the user desire to modify the FWHM of the APA deviation, it can be done with the following:
.. code-block:: python

  # Assuming that 'your_source' is a source defined as a 'back_to_back' particle
  your_source.direction.accolinearity_flag = True
  # Assuming that a FWHM of 0.55 deg is desired
  your_source.direction.accolinearity_fwhm = 0.55 * deg

**WARNING:** The implementation of APA for `back_to_back` sources is based on assuming that its deviation follows a 2D Gaussian distribution.
This is a simplification of the true physical process.

Material Ionisation Potential
=============================
The ionisation potential is the energy required to remove an electron to an atom or a molecule. By default, the ionization potential is calculated thanks to the Bragg’s additivity rule.
Users can modify the `MeanExcitationEnergy` of a material, and therefore the material's ionisation potential, similarly to how described for the `MeanEnergyPerIonPair`.
**WARNING:** changing this value for G4_WATER will not affect the simulation, as the default value will be used.

.. code-block:: python

    # Provide the location of GateMaterials.db to the volume manager.
    sim.volume_manager.add_material_database(path_to_gate_materials_db)

    # Set the MeanExcitationEnergy of the material in the physics manager
    # material_of_interest is the name of the material of interest, which should be defined in GateMaterials.db located at path_to_gate_materials_db
    sim.physics_manager.material_ionisation_potential[material_of_interest] =  75.0 * eV

Background information on physics lists in Geant4 and GATE
==========================================================

This section provides you with background information on the way GATE and Geant4 handle physics lists. To go in depth, you can also read the [guide from Geant4](https://geant4.web.cern.ch/documentation/dev/plg_html/PhysicsListGuide/physicslistguide.html).

Geant4 knows "processes" as the basic concept (C++ class) that handles physics interactions. It groups processes that describe logically related interactions into so-called Physics Constructors. G4EmStandardPhysics is such a constructor. It groups processes that describe electromagnetic interactions. G4OpticalPhysics is another such grouping. There are also constructors related to hadron physics, or nuclear decay, etc.

A physics list is a grouping at yet another logical level. It combines physics constructors, and it provides the user with functionality to combine them while attempting to keep to whole list coherent. There can only be 1 physics list per simulation. Internally, Geant4 distinguishes between physics constructors in terms of physics type and mutually excludes constructors with the same physics type. For example: a physics list can only contain physics constructor for elastic hadron physics (physics type 5). There are, however, physics constructors that can be added to a list without requiring another constructor to be removed, e.g. Optical physics, because the processes grouped in the constructor do not compete with processes from another constructor. Constructors that do not impose a compatibility check have physics type 0. Mutually exclusive constructors have physics type >0, e.g. bHadronElastic = 5, bHadronInelastic = 6, etc.

Now to GATE:
Geant4 pre-implements reference physics lists with different hadron physics constructors, and with and without additional electronic magnetic constructors (see above). It does not, however, pre-implement pure electromagnetic physics lists. To allow users to say:

.. code-block:: python

    sim.physics_manager.physics_list_name = "G4EmStandardPhysics"

GATE dynamically creates a physics list class around the G4EmStandardPhysics physics constructor.
Additionally, GATE allows users to add other physics constructors to the physics list, e.g. "G4OpticalPhysics".
So technically, when you write:

.. code-block:: python

    sim.physics_manager.physics_list_name = "G4EmStandardPhysics"
    sim.physics_manager.special_physics_constructors = ["G4OpticalPhysics"],

You get a physics list created based on G4EmStandardPhysics extended by the processes from the G4OpticalPhysics constructor.

If you write

.. code-block:: python

    sim.physics_manager.physics_list_name = "G4OpticalPhysics"

You get a physics list created based on G4OpticalPhysics, that's it. No process from G4EmStandardPhysics, unless also present in the G4OpticalPhysics constructor.

