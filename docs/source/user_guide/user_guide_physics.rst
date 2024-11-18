How to: Physics
===============

The management of physics in Geant4 is rich and complex, with hundreds of options. OPENGATE proposes a subset of available options.

Physics List and Decay
----------------------

With GATE, you can (and should) use Geant4 physics lists, i.e. pre-defined sets of physics processes. You can set the physics list via the `physics_manager` like this:

.. code-block:: python

    sim = gate.Simulation()
    # ...
    sim.physics_manager.physics_list_name = 'QGSP_BERT_EMZ'

The default physics list is QGSP_BERT_EMV. You find more details about physics lists and processes in the detailed part of this used guide in section :ref:`physics-lists-details-label` and in the `Geant4 guide <https://geant4-userdoc.web.cern.ch/UsersGuides/PhysicsListGuide/html/physicslistguide.html>`_.

You can use the following python command to get a list of all physics lists available in GATE:

.. code-block:: python

    print(sim.physics_manager.dump_available_physics_lists())


You can also activate additional sets of processes bundled in so-called "special physics constructors". To see which are available and which are active, use:

.. code-block:: python

    print(sim.physics_manager.special_physics_constructors)

If you want to activate one of them, say G4EmDNAPhysics, you add this line to your script:

.. code-block:: python

    sim.physics_manager.special_physics_constructors.G4EmDNAPhysics = True




Radioactive Decay
-----------------

Not all Geant4 physics lists include radioactive decay.
If you want to enable radioactive decay regardless of the list, use:

.. code-block:: python

    sim.physics_manager.enable_decay = True

.. important:: This will **not** turn off radioactive decay if the physics list actually includes it. Think of the option as a light switch that turns on the light, but does not turn it off.



Electromagnetic Parameters
--------------------------

Specific electromagnetic parameters can be turned on or off like this:

.. code-block:: python

    sim.physics_manager.em_parameters.fluo = True
    sim.physics_manager.em_parameters.auger = True
    sim.physics_manager.em_parameters.auger_cascade = True
    sim.physics_manager.em_parameters.pixe = True
    sim.physics_manager.em_parameters.deexcitation_ignore_cut = True

...


Production cuts
---------------

Geant4 allows you to tune the conditions under which it should actually produce anbd track secodnary particles, i.e. particles produced as the results of interactions of an existing particles with the target (or from fragmentation). More specifically, you can set the production cut in terms of range for a given particle. For example, a 10 mm cut applied to electrons means that secondary electrons are only produced if their energy gives them a range of at least 2 mm in the material where they are. As a rule of thumb: the higher the cut value the faster but also the less accurate the simulation.

You can set production cuts globally, i.e. apply them to the entire world, either like this:

.. code-block:: python

    sim.physics_manager.global_production_cuts.electron = 10 * gate.g4_units.mm

or like this:

.. code-block:: python

    sim.physics_manager.set_production_cut("world", "electron", 10 * gate.g4_units.mm)

Both of the above commands are equivalent.

If you want to apply a cut only to a certain volume, you can either do:

.. code-block:: python

    my_vol = sim.add_volume("SphereVolume", name="my_vol")
    sim.physics_manager.set_production_cut("my_vol", "electron", 10 * gate.g4_units.mm)

or set the cut via the volume like this:

.. code-block:: python

    my_vol = sim.add_volume("SphereVolume", name="my_vol")
    my_vol.set_production_cut("electron", 10 * gate.g4_units.mm)

Both of the above commands are equivalent.

.. important:: Geant4 only applies production cuts to electron, positrons, gammas, and protons. Use "all" instead of a specific particle to apply the cuts to all four particles.

Have a look at section :ref:`production-cuts-details-label` in the detailed part of this user guide for more information.


Limit the step size
-------------------

Geant4 automatically determines the best step size to be used in given circumstances while it transports a particle. Generally speaking, if interactions are not likely to occur close to the current position of the particle, Geant4 takes a large step. If a next interaction is likely to occur close by the current position, the step size will be small. Clearly, this not only depends on the particle properties, but also on the material, e.g. on its density.


You can impose a maximum step size that Geant4 may use, e.g. to guarantee a certain level of accuracy, in a specific volume in your simulation. There are two equivalent ways to achieve this. You can either do:

.. code-block:: python

    my_vol = sim.add_volume("SphereVolume", name="my_vol")
    sim.physics_manager.set_max_step_size(my_vol.name, 1 * gate.g4_units.mm)

or

.. code-block:: python

    my_vol = sim.add_volume("SphereVolume", name="my_vol")
    my_vol.set_max_step_size(1 * gate.g4_units.mm)

Additionally, you need to tell GATE to which particles you want to apply the step limit. To apply the 1 mm limit to electrons and positrons, you need this line:

.. code-block:: python

    sim.physics_manager.set_user_limits_particles(['electron', 'positron'])

There are other user limits like ''maximum track length'' and ''minimium kinetic energy'', that are used in analogy to the ''maximum step size''.
You can also use Regions if your geometry is complex. Have a look at the section :ref:`user-limits-details-label` in the detailed part of this user guide for more info.
