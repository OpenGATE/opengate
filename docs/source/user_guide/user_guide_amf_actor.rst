.. _amf-actor-label:

AMFActor
========

Microscopic energy-deposition fluctuations help describe radiation quality in
ion therapy, but resolving every interaction with track-structure transport is
costly. ``AMFActor`` couples ordinary Geant4 transport to an analytical
microdosimetric function (AMF), making voxel-wise lineal-energy spectra and
derived biological-model coefficients available without a separate microscopic
transport simulation at every location.

The method follows Sato et al., *Improvement of the hybrid approach between
Monte Carlo simulation and analytical function for calculating microdosimetric
probability densities in macroscopic matter*, Physics in Medicine & Biology
68 (2023) 155005, `doi:10.1088/1361-6560/ace14c
<https://doi.org/10.1088/1361-6560/ace14c>`_. Its application in TOPAS and
comparison with TOPAS-nBio are described by Hartzell, Parisi, Sato, Beltran and
Furutani, *Extending TOPAS with an analytical microdosimetric function:
application and benchmarking with nBio track structure simulations*, Physics
in Medicine & Biology 70 (2025) 105010, `doi:10.1088/1361-6560/adcfec
<https://doi.org/10.1088/1361-6560/adcfec>`_.

The actor evaluates analytical distributions using an external coefficient
table, particle charge, kinetic energy, target diameter and material stopping
power. It scores dose-weighted lineal-energy spectra, dose-mean lineal energy,
a saturation-corrected quantity, and alpha/beta coefficients for the Mayo Clinic
Florida microdosimetric kinetic model (MCF MKM). These coefficients have units
of inverse dose and inverse dose squared, respectively. RBE, cell survival,
ionization-cluster distributions and DNA damage are not actor outputs.

The published AMF coefficients describe microscopic water targets. A table
passing the parser is not evidence that it is physically appropriate for a
different material or study.

The ion AMF already represents secondary-electron contributions. Hartzell et al.
recommend suppressing secondary-electron production for its use with macroscopic
ion transport. Configure electron production cuts deliberately and check their
effect. OpenGATE's global ``all`` cut overrides the individual particle cuts;
set it to ``None`` when assigning an electron-specific cut.

Example
-------

Supply a coefficient table appropriate to the study. The default filename
``tsed.dat`` is relative to the working directory; a production table is not
automatically bundled or selected. This example illustrates configuration and
output access rather than a physically validated beam setup.

.. code-block:: python

   import itk
   import opengate as gate

   sim = gate.Simulation()
   sim.output_dir = "output"
   sim.random_seed = 123456789
   sim.world.size = [100, 100, 100]
   water = sim.add_volume("Box", "water")
   water.size = [10, 10, 10]
   water.material = "G4_WATER"
   sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option4"
   cuts = sim.physics_manager.global_production_cuts
   cuts.all = None
   cuts.gamma = cuts.positron = cuts.proton = 1 * gate.g4_units.mm
   cuts.electron = 1000 * gate.g4_units.mm  # study-dependent suppression

   beam = sim.add_source("GenericSource", "beam")
   beam.particle = "proton"
   beam.energy.mono = 100 * gate.g4_units.MeV
   beam.number_of_primaries = 100
   beam.position.type = "point"
   beam.position.translation = [0, 0, -4 * gate.g4_units.mm]
   beam.direction.type = "momentum"
   beam.direction.momentum = [0, 0, 1]

   amf = sim.add_actor("AMFActor", "amf")
   amf.attached_to = "water"
   amf.tsed_file_name = "/path/to/your/tsed.dat"
   amf.size = [5, 5, 5]
   amf.spacing = [2 * gate.g4_units.mm] * 3
   amf.hit_type = "middle"
   amf.DomainRadius = 0.3 * gate.g4_units.um
   amf.DoseAveragedLinealEnergy.active = True
   amf.output_filename = "amf.mhd"
   amf.dose.write_to_disk = True
   amf.microdosimetric_spectra.output_filename = "amf-spectrum.mhd"
   sim.run()

   dose = amf.dose.get_data()  # ITK scalar image, Gy
   yd = amf.DoseAveragedLinealEnergy.get_data()  # keV/um
   alpha = amf.Alpha_MCFMKM.get_data()  # Gy^-1
   beta = amf.Beta_MCFMKM.get_data()  # Gy^-2
   spectra = itk.array_from_image(amf.microdosimetric_spectra.get_data())
   # spectra.shape is (z, y, x, 400).
   labels = amf.GetHistogramLabels()  # lineal energy in keV/um

Configuration
-------------

Lengths use OpenGATE units; express radii with ``gate.g4_units.um`` and voxel
spacing with ``gate.g4_units.mm``. Biological coefficients require dose units.
Parameter names retain their historical capitalization.

.. list-table:: AMF configuration
   :header-rows: 1
   :widths: 28 25 47

   * - Parameter
     - Default
     - Meaning and validation
   * - ``tsed_file_name``
     - ``"tsed.dat"``
     - Readable str or pathlib.Path; exactly 576 rows of nine coefficients.
   * - ``DomainRadius``
     - 0.3 um
     - Finite spherical target radius, 0.0015 to 0.5 um inclusive. Also used
       as the biological domain radius.
   * - ``NucleusRadius``
     - 4.5 um
     - Finite positive biological nuclear radius.
   * - ``AlphaNot``
     - 0.117 Gy^-1
     - Finite nonnegative alpha0 in the biological model.
   * - ``BetaRef``
     - 0.0615 Gy^-2
     - Finite positive reference beta; also used for saturation correction.
   * - ``AlphaRef``
     - 0.217 Gy^-1
     - Finite nonnegative compatibility parameter; unused in the calculation.
   * - ``MicrodosimetricSpectra``
     - True
     - Boolean spectrum enablement. The spectrum interface must also be active.
   * - ``microdosimetric_spectra_file_name``
     - ``"microdosimetric_spectra.dat"``
     - Legacy filename parameter. The unchanged default maps to
       ``microdosimetric_spectra.mhd``. An explicit value overrides the
       spectrum interface filename and must use a supported image extension.

Inherited settings include ``attached_to`` (one volume, default ``"world"``),
``size`` (three positive integer voxel counts, default [10, 10, 10]),
``spacing`` (three finite positive lengths, default [1, 1, 1] mm),
``translation`` (grid-center offset in the volume frame, default [0, 0, 0] mm)
and ``rotation`` (proper orthonormal 3x3 matrix, default identity).
``hit_type`` accepts ``"pre"``, ``"post"``, ``"middle"`` or ``"random"``
(default); the last samples uniformly along the step segment. The current
``filter`` interface selects accepted steps. Use ``attached_to``, ``filter``
and ``output_filename`` in place of the deprecated ``mother``, ``filters``
and ``output`` parameters.

Configure each output through its ``active``, ``write_to_disk`` and
``output_filename`` attributes. ``amf.output_filename`` sets a shared basename;
individual filenames may then be assigned as in the example.
``amf.write_to_disk = False`` disables all image writes and the spectrum label
file. Output data remain available in memory by default. The output settings
``keep_data_per_run``, ``merge_data_after_simulation`` and ``keep_data_in_memory``
default to False, True and True respectively. If automatic merging is disabled,
enable per-run retention to retain results. These controls do not enable
multiple AMF run intervals or merging independent jobs.

The tsed.dat coefficient file
------------------------------

``tsed.dat`` is an input table of fitted microscopic distributions, not a
macroscopic dose profile or an output of ``AMFActor``. Its filename can be
changed through ``tsed_file_name``. Each row contains nine whitespace-separated
coefficients in the order ``A0 A1 A2 A3 A4 A5 A6 A7 A8``. There is no header,
key column or units column; row order defines the grid:

.. code-block:: text

   diameter (um): 0.003, 0.01, 0.03, 0.1, 0.2, 0.3, 0.5, 1
   energy (MeV/u): 1, 2, 3, 5, 7, 10, 20, 30, 50, 100, 300, 999
   atomic number: 1, 2, 6, 10, 14, 26
   zero-based row = charge_index * 96 + energy_index * 8 + diameter_index

Exactly 576 nonempty rows with nine finite numbers each are required. Blank
lines and whitespace are accepted; comments and extra columns are not.
A0, A3 and A6 must be nonnegative, with at least one positive amplitude per row.
Active components require A1/A2 > 0, A4/A5 > 0 or A7 > 1 respectively.
Unused coefficients of inactive components may be negative but must be finite.
Missing or malformed input raises an initialization error.

Meaning of the coefficients
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Let x be the number of ionizations in the microscopic target, and let
``b = deposited_energy_proxy_eV / A8``. For positive stopping power the
calculator evaluates the following three-component distribution before
interpolation and normalization:

.. code-block:: text

   Fermi(x) = A0 * 2*x / ((b*A2)**2 * (exp(A1*(x - b*A2)) + 1))
   normal(x) = A3 * exp(-abs(x - A4)**A5 / (2*A4))
   power(x) = A6 / (A7 - 1) * ((A7 - 1)/A7)**x
   f(x) = Fermi(x) + normal(x) + power(x)

The implementation caps the first two exponential arguments at 50 and discards
corner-distribution values at or below 1e-10. A zero amplitude disables that
component. For zero stopping power, the first component instead uses
``A0 * exp(-min(50, abs(x-A1)**A2 / (2*A1)))`` when active.

The column meanings follow directly from these expressions:

.. list-table:: Coefficient columns
   :header-rows: 1
   :widths: 15 55 30

   * - Column
     - Role
     - Relation to Sato (2023), equations (1)-(4)
   * - A0
     - Fermi amplitude
     - a1
   * - A1
     - Inverse Fermi transition width
     - 1/a5
   * - A2
     - Scale of the Fermi endpoint relative to b
     - a4
   * - A3
     - Normal-component amplitude, including its normalization factor
     - a2 / sqrt(2*pi*a6)
   * - A4
     - Normal-component location and denominator scale
     - a6
   * - A5
     - Normal-component shape exponent
     - a7
   * - A6
     - Power-component amplitude
     - a3
   * - A7
     - Power-component decay parameter
     - a8
   * - A8
     - Mean deposited energy per ionization, w, in eV
     - w

Thus the actor's zero-based A0,...,A8 columns are not the paper's a1,...,a8
parameters copied in numerical order. A8 supplies the energy conversion in
addition to the eight fitted parameters. For a spherical target of diameter c,
``energy_eV = x*A8`` and ``y_keV_per_um = energy_eV / (1000 * 2*c/3)``.
The value of w must be consistent with the track-structure model and its
definition of ionization events; it is not the material's mean excitation
energy used by a macroscopic stopping-power model.

Generating the coefficients
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Sato (2023), sections 2.1-2.2 and Supplementary Material A, describes generating
the underlying data from track-structure simulations in water. The ion model
uses primary-ion tracks and their secondary-electron tracks. The published
work used ITSART and ETS-PHITS. The procedure is:

1. Simulate tracks for the six charge groups and twelve nominal energies above,
   recording ionization-event coordinates from the primary and its secondaries.
   Keep the primary energy near its nominal value when collecting a track
   segment. Use the microscopic interaction definitions and transport settings
   of the chosen track-structure model consistently.
2. Sample spherical target sites around the tracks for each of the eight target
   diameters. Count ionizations per site and construct the single-event
   ionization-count distribution. Follow the sampling and normalization
   prescription in Sato's Supplementary Material A; a histogram of macroscopic
   voxel energy deposits is not this distribution.
3. Evaluate electronic stopping power S and mean deposited energy per ionization
   w with the same track-structure model. In the published fit, the expected
   central-crossing count is ``nc = S*c/w`` with S in eV/um, c in um and w in eV.
4. Fit the eight parameters of Sato's three-component ion function by least
   squares. The paper describes optimizing the ionization-weighted distribution
   ``x*f(x)``. Transform the fitted parameters into A0,...,A7 using the table
   above and append w as A8. Alternatively, fit the actor's expressions directly
   with the same target distribution and coefficient constraints.
5. Export all 576 rows with diameter varying fastest, energy next and charge
   slowest. Compare reconstructed distributions and their moments with the
   track-structure inputs at grid points and between them. When exporting
   paper-derived fits, also check the actor's exponential caps and tail cutoff.

The fitting calculation is performed outside OpenGATE; this actor loads and
interpolates the resulting table. There is no coefficient-generation command
in the actor, and a PHITS ``[t-sed]`` spectrum tally is not itself the required
nine-column coefficient file. An existing AMF table from the method's authors
can be used instead of repeating the fits, provided its parameter convention,
grid and model revision match this format.

For an already calculated array ``coefficients`` with shape
``(6, 12, 8, 9)`` in [charge, energy, diameter, coefficient] order, export it as:

.. code-block:: python

   import numpy as np

   # coefficients contains fitted parameters, not scored spectra.
   assert coefficients.shape == (6, 12, 8, 9)
   assert np.isfinite(coefficients).all()
   np.savetxt("tsed.dat", coefficients.reshape(576, 9), fmt="%.17g")

Keep the track-structure code/version, interaction settings, target-sampling
method, stopping-power and w calculations, fit settings and table checksum
with the generated file. The table is independent of the actor's cell-line
parameters ``AlphaNot``, ``BetaRef`` and ``NucleusRadius``.

Scoring
-------

Corner distributions interpolate with logarithmic diameter and energy weights
and linear charge weights. Queries outside the table range clamp to its
endpoints. The actor nevertheless restricts scoring to particles with positive
atomic mass and atomic number 1 through 18, mean step energy at least
0.025 MeV/u, positive weighted deposited dose, and a selected hit inside the
grid. Primary and secondary eligible ions are included; electrons and neutral
particles do not contribute to the AMF dose denominator.

Both interpolation and Geant4 ``ComputeTotalDEDX`` use the mean of pre/post
kinetic energy; interpolation divides it by atomic mass. Stopping power uses
the pre-step material and includes total, rather than electronic-only, DEDX.
For target diameter c, the energy-deposit proxy is
``min(DEDX * c, ion kinetic energy)`` with consistent units. The weighted dose
for each eligible step is ``track_weight * deposited_energy / voxel_mass``.
The reported dose is the accumulated dose for the simulated histories, without
division by the number of primaries. Score a separate ``DoseActor`` to obtain
all-particle absorbed dose or its uncertainty.

Lineal-energy bin edges are ``10**(-3 + 0.02*i)`` keV/um, i=0,...,400;
labels are arithmetic midpoints of adjacent edges. The 400-component spectrum
is q(y)=y*d(y), a density with respect to ln(y), not a list of bin probabilities.
In nonempty voxels its sum times ``ln(10)/50`` is one. Obtain labels in full
precision with ``GetHistogramLabels()``; the label file uses six significant
digits. Dose-mean lineal energy is evaluated from the first and second moments
of the underlying frequency distribution.

Workers accumulate additive dose, dose-weighted spectra and scalar numerators.
The master merges these raw sums before normalization. For steps s:

.. code-block:: text

   dose = sum(D_s)
   spectrum = sum(D_s * q_s) / dose
   yD = sum(D_s * yD_s) / dose
   yS = sum(D_s * yS_s) / dose
   alpha = sum(D_s * alpha_s) / dose
   beta = (sum(D_s * sqrt(beta_s)) / dose)**2

Empty voxels return zero for every output. Finalized alpha, beta and spectra
cannot be added or averaged directly to combine independent simulations.

Coordinates and files
---------------------

All images use double precision and three spatial dimensions. Scalars have
NumPy/ITK array order [z, y, x]; spectra use [z, y, x, component]. The spectrum
is a 3D vector image with 400 channels, rather than a 4D scalar image.

.. list-table:: Outputs
   :header-rows: 1
   :widths: 44 16 20 20

   * - Interface
     - Units
     - Active by default
     - Disk writes by default
   * - ``dose``
     - Gy
     - True
     - False
   * - ``DoseAveragedLinealEnergy``
     - keV/um
     - False
     - True
   * - ``DoseAveragedLinealEnergySaturationCorrected``
     - keV/um
     - False
     - True
   * - ``Alpha_MCFMKM``
     - Gy^-1
     - True
     - True
   * - ``Beta_MCFMKM``
     - Gy^-2
     - True
     - True
   * - ``microdosimetric_spectra``
     - Dimensionless q(y)
     - True
     - True

Paths resolve through the current actor-output interfaces relative to
``sim.output_dir``. Use ``amf.<interface>.get_output_path()`` to inspect the
resolved filename. Spectrum filenames support ``.mhd``, ``.mha`` and ``.nrrd``.
Keep a MetaImage ``.mhd`` together with its referenced binary payload. Image
sample-count JSON sidecars follow the framework conventions. When spectra are
written, a sibling ``<spectrum-stem>_histo_x_labels.txt`` records the 400 labels
in keV/um. Units are documented here rather than encoded as standard MetaImage
fields.

Spatial origins refer to the first voxel center, including translation,
rotation and the half-voxel shift. ``output_coordinate_system`` is ``"local"``
by default, using attached-volume coordinates. ``"global"`` uses world
coordinates; ``"attached_to_image"`` requires an ImageVolume and uses its
native image coordinates. None produces a centered image with identity
direction. Scalar and spectrum outputs use the same spatial metadata.

.. autoclass:: opengate.actors.doseactors.AMFActor
