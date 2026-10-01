.. _amdm-actor-label:

AMDMActor
=========

``AMDMActor`` scores energy-weighted AMDM delta and gamma values on a voxel
grid. Gamma (also called yd in the table) is expressed in keV/µm; delta is
dimensionless. The actor uses the material and particle transport of the
simulation without changing the physics model.

Discussion
----------

The abridged microdosimetric distribution methodology (AMDM) was published by
Parisi, Beltran and Furutani in `10.1002/acm2.14049
<https://doi.org/10.1002/acm2.14049>`_. It was subsequently used in OpenGATE10
by Fuchs et al. to study the influence of carbon-ion nozzle configurations on
microdosimetric spectra and RBE in `10.1016/j.zemedi.2025.04.004
<https://doi.org/10.1016/j.zemedi.2025.04.004>`_.

AMDM is intended to retain compact summaries of the microdosimetric spectra
in each voxel for carbon-ion transport studies and subsequent RBE calculations.
Storing bin-wise dose fractions and dose-mean lineal energies allows later
evaluation with a microdosimetric model, such as the Mayo Clinic Florida
microdosimetric kinetic model (MCF MKM), using the chosen cell-line parameters.
The actor generates the physical quantities; the biological-model calculation
is performed separately.

To use the generated data, read the paired normalized ``delta`` and ``gamma``
images, either through ``amdm.delta.get_data()`` and ``amdm.gamma.get_data()``
after the simulation or from their MetaImage files with ITK. For each voxel,
delta gives the dose fraction in each LUT bin and gamma gives its dose-mean
lineal energy in keV/µm. Keep the voxel geometry and LUT bin definitions with
the images when passing these values to a microdosimetric model. When combining
independent simulations, sum restricted energy, raw delta and raw gamma before
normalizing; enable ``storeMergingData`` to save those raw sums.

Example
-------

Supply a LUT appropriate to the particles, energy range and microdosimetric bin
definitions of your study, and set ``LUTfilename`` to its location. A production
LUT is not bundled at the repository root or automatically installed there.
The development table is retained separately as a test fixture.

.. code-block:: python

   import opengate as gate

   sim = gate.Simulation()
   sim.output_dir = "output"
   sim.world.size = [100, 100, 100]
   sim.world.material = "G4_WATER"
   sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option3"
   source = sim.add_source("GenericSource", "carbon")
   source.particle = "ion 6 12"
   source.energy.mono = 60 * gate.g4_units.MeV
   source.number_of_primaries = 100
   source.position.type = "point"
   source.direction.type = "momentum"
   source.direction.momentum = [0, 0, 1]
   amdm = sim.add_actor("AMDMActor", "amdm")
   amdm.attached_to = "world"
   amdm.LUTfilename = "/path/to/your/AMDM_LUT.txt"
   amdm.AMDM_Bins = 10
   amdm.size = [5, 5, 5]
   amdm.spacing = [10 * gate.g4_units.mm] * 3
   amdm.output_filename = "amdm.mhd"
   amdm.storeMergingData = True
   amdm.user_output.amdm.keep_data_per_run = True
   sim.run()
   delta = amdm.delta.get_data()                  # merged normalized 4D image
   gamma = amdm.gamma.get_data()                  # merged normalized 4D image
   restricted = amdm.restrictedEdep.get_data()    # merged weighted MeV, 3D

Configuration
-------------

All lengths use OpenGATE internal units (mm) and can be specified by
multiplication with ``gate.g4_units``. Rotations and voxel/bin counts are
unitless. The three spatial components are ordered x, y, z. The AMDM parameters
retain their historical capitalization.

.. list-table:: AMDM and inherited configuration
   :header-rows: 1
   :widths: 20 22 58

   * - Parameter
     - Type and default
     - Units, supported values and validation
   * - ``name``
     - str, required
     - Unique actor name supplied through ``sim.add_actor``.
   * - ``LUTfilename``
     - str or pathlib.Path, ``"AMDM_LUT.txt"``
     - Nonempty readable table path, relative to the working directory or
       absolute. Marked as an input file for archiving. Missing/malformed tables
       raise an exception during initialization. The default is a relative
       filename, not a bundled table; set this parameter to your own LUT path.
   * - ``AMDM_Bins``
     - int, 10
     - Positive bin count, excluding booleans. Must match the exact column count
       ``2 + 2 * AMDM_Bins``. Counts must fit the C++ integer range.
   * - ``storeMergingData``
     - bool, False
     - Activates the raw delta/gamma file interfaces. In-memory merging and
       thread safety work with either value. Individual ``write_to_disk``
       controls still apply.
   * - ``attached_to``
     - volume or str, ``"world"``
     - One existing volume only; a list of volumes is unsupported. Daughters
       use the same scoring grid. The volume may move between runs.
   * - ``size``
     - three integers, [10, 10, 10]
     - Positive spatial voxel counts. ``"like_image_volume"`` uses an attached
       ImageVolume's grid; incompatible volume types raise an exception.
   * - ``spacing``
     - three numbers, [1, 1, 1] mm
     - Finite positive spatial voxel sizes. ``"like_image_volume"`` uses the
       attached image spacing.
   * - ``translation``
     - three numbers, [0, 0, 0] mm
     - Finite offset of the scoring-grid center in the attached volume frame.
   * - ``rotation``
     - 3x3 matrix, identity
     - Finite proper orthonormal rotation of the grid within the volume.
   * - ``repeated_volume_index``
     - int, 0
     - Selects the attached physical volume when copies exist. The inherited
       physical-volume lookup reports unavailable indices.
   * - ``hit_type``
     - str, ``"random"``
     - ``"pre"``, ``"post"``, ``"middle"`` or ``"random"``. The latter samples
       uniformly along the pre/post position segment, as in the source actor.
   * - ``output_coordinate_system``
     - str or None, ``"local"``
     - ``"local"``: attached-volume coordinates; ``"global"``: world coordinates;
       ``"attached_to_image"``: native attached ImageVolume coordinates;
       None: centered image with identity direction. The image option requires
       an ImageVolume. This changes output coordinates, not transport scoring.
   * - ``filter``
     - filter object or None, None
     - Current OpenGATE step filter; accepted steps alone are scored.
   * - ``priority``
     - int, 100
     - Inherited callback ordering; lower values run earlier.
   * - ``track_structure_em_physics``
     - str or None, None
     - Inherited region-physics request. Supported values are the constructors
       in ``Region.available_track_structure_em_physics``; requires one volume.
   * - ``output``, ``img_coord_system``, ``mother``, ``filters``
     - deprecated, None
     - Existing framework deprecation errors. Use ``output_filename``,
       ``output_coordinate_system``, ``attached_to`` and ``filter`` respectively.
   * - ``filters_boolean_operator``
     - deprecated, ``"and"``
     - Use the current filter-composition API.

The output interfaces are ``restrictedEdep``, ``raw_delta``, ``raw_gamma``,
``delta`` and ``gamma``. Set ``amdm.output_filename`` to configure the shared
basename, or set an interface's ``output_filename`` (str or Path, default
``"auto"``) to configure its actual filename. The actor-wide getter returns the
configured delta filename. Filenames of the AMDM images use ``.mhd`` when the
actor-wide basename is set, regardless of the requested final extension.

All interfaces support the current ``active`` and ``write_to_disk`` boolean
controls. Restricted energy and normalized images are active by default;
``storeMergingData`` controls activation of the two raw interfaces during
initialization. Writing defaults to True on all interfaces; inactive raw
interfaces produce no files. ``amdm.write_to_disk = False`` suppresses all image
writes, including raw files with ``storeMergingData=True``. Disabling an output
interface does not remove raw denominators needed by the other outputs.

The shared output ``amdm.user_output.amdm`` supports
``keep_data_per_run`` (bool, False), ``merge_data_after_simulation`` (bool, True)
and ``keep_data_in_memory`` (bool, True). Set ``keep_data_per_run=True`` to retain
and write separately indexed runs. With merging disabled, enable per-run data
retention to keep results. Set ``keep_data_in_memory=False`` to release the
outputs at simulation close; use the files thereafter. Set output filenames to
None or an empty string only with the corresponding disk writes disabled.

Lookup and scoring
------------------

The LUT has two key columns (positive integral charge and positive energy in
MeV/n), then one gamma/yd column per bin in keV/µm, then one dimensionless delta
column per bin. All entries must be finite numbers. Charge groups must be
ordered; energy keys must be unique and strictly increasing within each group.
Groups may have different sizes and energy ranges, including a single entry.
Blank lines, whitespace, and comments starting with ``#`` are accepted.
Validation checks the schema; it does not require a particular gamma/delta
model or force the delta values to sum to one.

Bin values interpolate linearly in energy within the particle's charge group.
Values below/above its energy range clamp to that group's first/last row.
Missing charges contribute neither to the restricted energy nor to the bins.

For compatibility with the source actor, the LUT query uses the track's kinetic
energy at the scoring callback (post-step energy), divided by its baryon number.
It does not use mean pre/post energy. Track weight multiplies the deposited
energy in MeV. Only strictly positive integer-converted PDG charges contribute.
The source's unusual zero-baryon behavior is retained explicitly: a positive
kinetic energy with zero baryon number samples that charge's upper endpoint;
zero kinetic energy with zero baryon number contributes nothing. Thus positive
ions are the intended use, but positive-charge zero-baryon particles are not
silently removed as a scientific-model change.

For each accepted step and bin b, with weighted deposit e:

.. code-block:: text

   restrictedEdep += e
   raw_delta[b] += delta_LUT[b] * e
   raw_gamma[b] += gamma_LUT[b] * delta_LUT[b] * e
   delta[b] = raw_delta[b] / restrictedEdep
   gamma[b] = raw_gamma[b] / raw_delta[b]

The result is zero wherever the corresponding denominator is zero, including
empty voxels and zero-weight bins. Raw sums are never normalized in place.
Per-run and merged normalized images are views derived from raw sums;
normalized run images are never averaged directly. In-memory merging through
``merge_data_from_actor_output`` retains this rule.

Threads share read-only lookup data and use an actor-owned mutex for accumulator
and event-count updates. Run initialization, image copying, normalization and
writing occur on the master after the appropriate worker boundaries. Both
single-thread and multithread execution are supported. The coarse lock favors
correctness and minimal changes; throughput scaling depends on scoring load.

Coordinates and files
---------------------

The spatial origin uses the center of the first voxel, with its half-voxel
shift, translation and rotation. Geometry attachment is recomputed each run.
The fourth axis is the LUT bin axis, with spacing 1, origin 0 and independent
identity direction. Bin order follows the columns of the LUT. ITK/NumPy arrays
are ordered [bin, z, y, x]; the MetaImage size is [x, y, z, bin].

For ``amdm.output_filename = "result.mhd"``, filenames relative to
``sim.output_dir`` are:

.. list-table:: Image outputs
   :header-rows: 1

   * - Filename
     - Scalar type / dimension
     - Quantity and units
   * - ``result-delta.mhd``
     - double / 4D
     - Normalized delta, dimensionless
   * - ``result-gamma.mhd``
     - double / 4D
     - Normalized gamma, keV/µm
   * - ``result-restrictedEdep.mhd``
     - double / 3D
     - Restricted weighted deposited energy, MeV
   * - ``result-unprocessedForMergingOnly-delta.mhd``
     - double / 4D
     - Raw delta numerator, MeV (dimensionless delta and weight)
   * - ``result-unprocessedForMergingOnly-gamma.mhd``
     - double / 4D
     - Raw gamma numerator, MeV·keV/µm

Each ``.mhd`` references its binary payload, normally the corresponding
``.raw``. Preserve both files. The framework also writes
``<image-stem>-samples.mhd.json`` with the number of events; units are documented
here rather than represented as standard MetaImage fields. Per-run filenames
append ``-run0``, ``-run1``, etc. immediately before ``.mhd``. These run suffixes
and sample sidecars follow the current framework. The four legacy 4D basename
patterns and double scalar representation are preserved. Restricted energy now
has an explicitly resolved filename; the old wrapper's fluence callback did
not provide a functioning legacy output path.

For moving geometry, outputs are merged by voxel index in the grid attached to
the volume, following current actor conventions. A merged global image has the
first contributing run's coordinates; it is not a resampling of all runs into a
fixed world grid. Retain per-run outputs to inspect their individual poses.

Validation and migration
------------------------

Use ``sim.add_actor("AMDMActor", "amdm")`` and ``attached_to``. Replace obsolete
``output`` with ``output_filename`` and ``sim.output_dir``. Initialization and
callbacks use the current framework; wrong fluence references, duplicate LUT
allocation, unchecked endpoint iterators, process-exit errors and destructive
normalization were repaired. Zero denominators now explicitly yield zero.

Tests in ``tests/src/actors/test110_amdm_*.py`` exercise independently known
constant-bin results, interpolation and malformed tables, full output headers
and payloads, zero bins, coordinates, track weights, unequal run contributions,
raw-first merging and single/multithread aggregates. The supplied-LUT test uses
the development fixture ``tests/src/actors/fixtures/test110_amdm/AMDM_LUT.txt``
with SHA-256
``93d42113b9f48e3ec069000f5983e4568f7bca2e873d1cb06186d08f949771ab``;
it compares the ten raw bins to independently recorded PhaseSpaceActor steps
and NumPy interpolation. This is analytical/transport-step acceptance evidence.
No independently trusted legacy output image was found for a legacy numerical
comparison. The fixture is a test input, not a generated output reference or a
production LUT selected automatically by the actor. The original root-level
development file is not required to run the tests.

.. autoclass:: opengate.actors.doseactors.AMDMActor
