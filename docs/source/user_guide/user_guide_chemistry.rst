How to: Geant4-DNA chemistry
============================

This chapter explains how to run a Geant4-DNA chemistry simulation in GATE 10,
how to configure chemistry lists and track-structure EM physics, and how to
use chemistry actors.

The current chemistry support is built around the Geant4-DNA workflow:

- activate track-structure EM in the region where DNA physics should run;
- select a Geant4 chemistry list;
- optionally customize that chemistry list;
- add one or more chemistry-aware actors;
- read summary and counter results from actor outputs.


Minimal setup
-------------

A minimal chemistry simulation needs three ingredients:

1. a standard Geant4 physics list;
2. a Geant4-DNA chemistry list;
3. track-structure EM activated in the region of interest.

The smallest practical setup looks like this:

.. code-block:: python

    import opengate as gate

    sim = gate.Simulation()

    sim.physics_manager.physics_list_name = "G4EmStandardPhysics"
    sim.chemistry_manager.chemistry_list_name = "G4EmDNAChemistry_option3"
    sim.chemistry_manager.time_step_model = "IRT"

    water_box = sim.add_volume("Box", "water_box")
    water_box.material = "G4_WATER"
    water_box.size = [10 * gate.g4_units.um] * 3

    water_box.set_track_structure_em_physics("G4EmDNAPhysics_option2")

This does not yet add chemistry scoring, but it prepares the simulation so
that Geant4-DNA chemistry can run.


Track-structure EM physics
--------------------------

Chemistry requires track-structure EM physics in the relevant region. In GATE
10 this is configured with ``track_structure_em_physics``.

The recommended full Geant4 names are for example:

- ``G4EmDNAPhysics``
- ``G4EmDNAPhysics_option2``
- ``G4EmDNAPhysics_option4``
- ``G4EmDNAPhysics_option6``

The simplest way is to configure it directly on a volume:

.. code-block:: python

    target = sim.add_volume("Box", "target")
    target.material = "G4_WATER"
    target.size = [10 * gate.g4_units.um] * 3
    target.set_track_structure_em_physics("G4EmDNAPhysics_option2")

This creates or reuses the appropriate GATE region and activates Geant4-DNA
track-structure EM there.

You can also configure it explicitly through a region:

.. code-block:: python

    region = sim.physics_manager.add_region("dna_region")
    region.associate_volume(target)
    sim.physics_manager.set_track_structure_em_physics_in_region(
        "dna_region",
        "G4EmDNAPhysics_option4",
    )

If you use a chemistry actor, the actor may also request
``track_structure_em_physics`` for its attached volume. This is a convenience
feature, but configuring the region or volume explicitly is often clearer.


Choosing a chemistry list
-------------------------

The chemistry list is selected through ``ChemistryManager``:

.. code-block:: python

    sim.chemistry_manager.chemistry_list_name = "G4EmDNAChemistry_option3"

At the moment, one simulation must resolve to one coherent chemistry list.
This means:

- the manager can request a chemistry list;
- a chemistry actor can also request a chemistry list;
- all such requests must agree.

If multiple incompatible chemistry-list names are requested, GATE stops with a
fatal error.

Current built-in chemistry list names include:

- ``G4EmDNAChemistry``
- ``G4EmDNAChemistry_option1``
- ``G4EmDNAChemistry_option2``
- ``G4EmDNAChemistry_option3``


Chemistry time-step model
-------------------------

The chemistry time-step model is configured through:

.. code-block:: python

    sim.chemistry_manager.time_step_model = "IRT"

Current allowed values are:

- ``SBS``
- ``IRT``
- ``IRT_syn``

For many aqueous-radiolysis examples, ``IRT`` is a reasonable starting point.


Customizing the chemistry list
------------------------------

The active chemistry list is available as:

.. code-block:: python

    chem_list = sim.chemistry_manager.chemistry_list

You can extend the selected built-in Geant4 chemistry list with:

- additional chemical species;
- additional bimolecular reactions;
- additional dissociation channels.

Add a reaction
~~~~~~~~~~~~~~

This is the most common customization pattern:

.. code-block:: python

    dm3_per_mole_s = (
        1e-3 * gate.g4_units.m3 / (gate.g4_units.mole * gate.g4_units.s)
    )

    chem_list.add_reaction(
        reactant_a="H",
        reactant_b="H",
        rate_constant=0.503e10 * dm3_per_mole_s,
        products=["H2"],
        reaction_type=0,
    )

Reactions are appended to the Geant4-DNA reaction table after the selected
built-in chemistry list has created its default content.

Add a species
~~~~~~~~~~~~~

You can add or modify a species by name:

.. code-block:: python

    chem_list.add_chemical_species(
        name="MySpecies",
        charge=0,
        diffusion_coefficient=1.0e-9 * gate.g4_units.m2 / gate.g4_units.s,
    )

If the molecular configuration already exists, GATE updates its configurable
properties. Otherwise it creates the necessary Geant4 molecule definition and
configuration.

Add a dissociation channel
~~~~~~~~~~~~~~~~~~~~~~~~~~

You can also add a dissociation channel:

.. code-block:: python

    chem_list.add_chemical_dissociation(
        parent="H2O2",
        products=["°OH", "°OH"],
        probability=1.0,
    )

Current model
~~~~~~~~~~~~~

The current model is additive:

- start from one built-in Geant4 chemistry list;
- then append species, reactions, and dissociations in GATE.

If you customize species, reactions, or dissociations, make sure a valid base
chemistry list is still selected.


Adding a chemistry actor
------------------------

The current reference chemistry actor is ``ChemicalCountingActor``.

It provides:

- chem6-like energy-loss and LET bookkeeping;
- chemistry-time species sampling;
- reaction counting;
- dedicated molecule and reaction counter outputs.

A typical setup looks like this:

.. code-block:: python

    chem_actor = sim.add_actor("ChemicalCountingActor", "chem_actor")
    chem_actor.attached_to = target
    chem_actor.number_of_time_bins = 50

The actor must be attached to a volume. This volume defines the local region
for the actor logic.

If you want the actor to request DNA EM on its attached volume itself, you can
do:

.. code-block:: python

    chem_actor.track_structure_em_physics = "G4EmDNAPhysics_option2"

If you have already configured track-structure EM explicitly on the volume or
region, you can leave this as ``None``.

The actor also supports:

- ``track_only_primary``
- ``primary_pdg_code``
- ``energy_loss_min``
- ``energy_loss_max``
- ``min_kinetic_energy``
- ``let_cutoff``
- ``times_to_record``
- ``number_of_time_bins``

Example:

.. code-block:: python

    chem_actor.track_only_primary = True
    chem_actor.primary_pdg_code = 11
    chem_actor.number_of_time_bins = 50


Chemistry confinement
---------------------

Chemistry confinement is configured globally through ``ChemistryManager``, not
per actor.

If you want chemistry tracks starting outside a given volume subtree to be
killed before chemistry processing continues, configure:

.. code-block:: python

    sim.chemistry_manager.confine_chemistry_to_volume = target

where ``target`` can be either a volume object or a volume name.

This is a simulation-wide chemistry-control policy. It is intentionally kept
outside chemistry actors so that chemistry actors can remain focused on
probing and scoring.


Chemistry actor outputs
-----------------------

``ChemicalCountingActor`` currently exposes three outputs:

- ``results``
- ``molecule_counter``
- ``reaction_counter``

Summary output
~~~~~~~~~~~~~~

The ``results`` output contains actor-level summary quantities such as:

- ``recorded_events``
- ``chemistry_starts``
- ``chemistry_stages``
- ``pre_time_step_calls``
- ``post_time_step_calls``
- ``reaction_count``
- ``killed_particles``
- ``aborted_events``
- ``accumulated_primary_energy_loss``
- ``total_energy_deposit``
- ``mean_restricted_let``
- ``std_restricted_let``
- ``species``
- ``times_to_record``

You can read it like this:

.. code-block:: python

    sim.run()
    results = chem_actor.results.get_data()
    print(results.reaction_count)
    print(results.mean_restricted_let)

Counter outputs
~~~~~~~~~~~~~~~

The detailed chemistry histories live on the dedicated counter outputs:

- ``chem_actor.molecule_counter``
- ``chem_actor.reaction_counter``

Both follow the same in-memory structure:

- a dictionary;
- keys are molecule or reaction labels;
- each value is a structured NumPy array with fields ``time`` and ``count``.

Example:

.. code-block:: python

    molecule_data = chem_actor.molecule_counter.get_data()
    reaction_data = chem_actor.reaction_counter.get_data()

    for molecule_name, series in molecule_data.items():
        print(molecule_name)
        print(series["time"])
        print(series["count"])

The counts are cumulative.

Activating and deactivating outputs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

By default, the predefined counter outputs are active. You can deactivate them
through the normal actor-output interface:

.. code-block:: python

    chem_actor.molecule_counter.active = False
    chem_actor.reaction_counter.active = False

The same can also be controlled through the actor-owned counter objects:

.. code-block:: python

    chem_actor.counters.molecule_counter.active = False
    chem_actor.counters.reaction_counter.active = False

For most user scripts, using the actor output interface directly is the
clearest choice.


Complete example
----------------

This combines the main pieces in one small script:

.. code-block:: python

    import opengate as gate

    sim = gate.Simulation()
    um = gate.g4_units.um
    keV = gate.g4_units.keV

    sim.world.material = "G4_WATER"
    sim.world.size = [1 * gate.g4_units.km] * 3

    sim.physics_manager.physics_list_name = "G4EmStandardPhysics"
    sim.chemistry_manager.chemistry_list_name = "G4EmDNAChemistry_option3"
    sim.chemistry_manager.time_step_model = "IRT"

    target = sim.add_volume("Box", "chem_box")
    target.material = "G4_WATER"
    target.size = [10 * um, 10 * um, 10 * um]
    target.set_track_structure_em_physics("G4EmDNAPhysics_option2")
    sim.chemistry_manager.confine_chemistry_to_volume = target

    source = sim.add_source("GenericSource", "source")
    source.particle = "e-"
    source.energy.mono = 2 * keV
    source.position.type = "point"
    source.position.translation = [0, 0, 0]
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    source.n = 1

    chem_actor = sim.add_actor("ChemicalCountingActor", "chem_actor")
    chem_actor.attached_to = target
    chem_actor.number_of_time_bins = 50

    sim.run()

    results = chem_actor.results.get_data()
    species = chem_actor.molecule_counter.get_data()
    reactions = chem_actor.reaction_counter.get_data()

    print(results.reaction_count)
    print(species.keys())
    print(reactions.keys())


Current limitations
-------------------

The chemistry support on this branch is already usable, but a few constraints
are worth keeping in mind:

- one simulation currently needs one coherent chemistry list;
- one simulation currently has at most one global GATE-side chemistry
  confinement policy;
- chemistry counter writing to disk is not implemented yet on the python side;
- chemistry counter merged data currently uses a simple successive-run merge;
- ``ChemicalCountingActor`` currently assumes at most one molecule counter for its
  built-in species-sampling path.

These are implementation limits, not usage mistakes.


Practical tips
--------------

- Start with ``G4EmStandardPhysics`` plus regional
  ``track_structure_em_physics`` rather than trying to replace the whole
  physics list with a DNA-only list.
- Configure DNA EM only where you need it. Track-structure physics is much more
  expensive than standard condensed-history EM.
- Keep the chemistry list request consistent across the simulation and all
  chemistry actors.
- Use ``sim.chemistry_manager.confine_chemistry_to_volume`` if you want to
  restrict chemistry spatially at the GATE level.
- If you only need summary chemistry information, ``chem_actor.results`` is the
  easiest entry point.
- If you need time-resolved species or reaction histories, use the dedicated
  counter outputs.
