.. _source-fasty90-source:

Fast Y-90 source
================

Description
-----------

``FastY90Source`` ports the GATE 9.4.1 fastY90 model and its numerical tables.
It generates bremsstrahlung photons directly from a precomputed water kernel,
avoiding transport of the beta electrons. Photon energy, distance from the
decay position, and angle between displacement and momentum follow the GATE 9
distributions. The source also generates the internal pair-production
positron branch, with a default yield of 0.00003186 per decay. Geant4 transports
these positrons and their annihilation photons. The 2.186 MeV gamma branch is
absent, as in GATE 9.

.. code:: python

   import opengate as gate

   sim = gate.Simulation()
   sim.world.size = [100 * gate.g4_units.mm] * 3
   sim.world.material = "G4_WATER"
   source = sim.add_source("FastY90Source", "y90")
   source.activity = 1e6 * gate.g4_units.Bq
   source.position.type = "sphere"
   source.position.radius = 5 * gate.g4_units.mm
   source.min_brem_energy = 50 * gate.g4_units.keV
   sim.run()

Activity and timing
-------------------

``activity`` specifies Y-90 decays per second. The event rate is the activity
multiplied by the sum of the bremsstrahlung yield above the effective cutoff
and ``positron_probability``. Half-life and time-activity curves use the same
decay activity convention. GATE 10 handles the division among worker threads.
Set the total activity once, without manually applying the emission yield.

Alternatively, ``number_of_primaries`` specifies a fixed number of transported
emissions, each consisting of one photon or one positron. It does not count
decays. The source uses the simulation's Geant4 random engine and seed.

``min_brem_energy`` must be finite and in [0, 2 MeV). The kernel rounds it down
to a 10 keV boundary, so 59 keV has the same effect as 50 keV. It changes both
the bremsstrahlung spectrum and its yield, leaving the positron yield
unchanged. ``positron_probability`` must be finite and in [0, 1]; zero disables
the positron branch. A configuration with zero total emission yield is rejected.

Decay positions
---------------

Use the usual ``GenericSource`` position shapes, translations, rotations and
``attached_to`` volume. Confinement applies to the decay position; photon
emission positions can extend up to 12 mm beyond it.

For a voxelized decay distribution, set ``source.image`` to an activity image
readable by ITK, such as MetaImage. Weights must be finite,
nonnegative, three-dimensional and have a positive sum. They are normalized
internally. The voxel grid is centered in source coordinates using its spacing;
``position.rotation`` and ``position.translation`` place it relative to
``attached_to``. Image origin and direction are ignored; use the source's
translation and rotation to place the grid. Confinement cannot be combined
with an image.

.. code:: python

   source.image = "activity.mhd"
   source.position.translation = [0, 0, 20 * gate.g4_units.mm]

Leave ``particle``, ``energy``, ``direction`` and ``polarization`` at their
defaults. The kernel determines these properties. Angular acceptance and
forced directions are unsupported because they would change the kernel's
displacement and direction relation.

Model validity
--------------

The kernel was computed in water and extends to a radius of 12 mm. Use it for
sources surrounded by water or materials with similar density and effective
atomic number, with sufficient surrounding material to contain the kernel.
This source is intended for PET and bremsstrahlung SPECT imaging. It does not
score the omitted beta-electron energy deposition for dosimetry.

The upstream algorithm and tables are available in the
`GATE 9.4.1 source <https://github.com/OpenGATE/Gate/blob/v9.4.1/source/physics/src/GateSourceFastY90.cc>`_
and `table file <https://github.com/OpenGATE/Gate/blob/v9.4.1/source/physics/src/GateSourceFastY90Tables.cc>`_.

Reference
---------

.. autoclass:: opengate.sources.fasty90.FastY90Source
