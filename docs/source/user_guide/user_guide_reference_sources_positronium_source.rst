.. _source-positronium-source:

Positronium source
==================

Description
-----------

The full theoretical description of the model, together with implementation details and tests, is available in `A Monte Carlo positronium decay source model with multiple annihilation channels in GATE <https://arxiv.org/abs/2605.14987>`_.

``PositroniumSource`` is a dedicated source model for positronium decays. It combines the standard source activity, time and position handling from ``GenericSource`` with an internal decay model that generates:

* a delayed 2-gamma or 3-gamma annihilation vertex,
* an optional prompt de-excitation gamma,
* an optional spatial shift of the annihilation point to model the mean positron range.

The source is configured component by component. Each component represents one positronium decay channel description with its own intensity, lifetime and prompt-gamma settings.

Creating a positronium source
-----------------------------

Create the source with the dedicated source type:

.. code:: python

    source = sim.add_source("PositroniumSource", "source")

As for other sources, the activity and the spatial or temporal distributions are configured with the standard source commands, for example:

.. code:: python

    source.n = 1000
    source.position.type = "sphere"
    source.position.radius = 20 * cm

The annihilation particles are generated internally by the positronium model, therefore there is no need to configure ``source.particle`` for the annihilation gammas.

Channel parameters
------------------

Required parameters
^^^^^^^^^^^^^^^^^^^

The channels can be defined either from positronium fractions and decay kinds, or derived from intensities and interaction types. Either the two parameters of ``source.channels_from_fractions`` or those of ``source.channels_from_intensities`` must be set. In all cases, the list of values provided to the parameters of the positronium source must always be of the same length.

- ``source.channels_from_fractions.fractions``: relative fractions. The implementation normalizes the vector internally, but the values should represent the intended relative fractions.
- ``source.channels_from_fractions.decay_kinds``: explicit annihilation channel selection for each channel. Allowed values are ``k2Gamma`` and ``k3Gamma``.
- ``source.channels_from_intensities.intensities``: intensities of each interaction type.
- ``source.channels_from_intensities.positron_interactions``: interaction type assigned to each channel. Allowed values are ``kParaPs``, ``kDirect`` and ``kOrthoPs``.
- ``source.positronium_lifetimes``: lifetime of each channel.
- ``source.prompt_gamma_probabilities``: probability of prompt-gamma emission for each channel.
- ``source.prompt_gamma_energies``: prompt-gamma energies for each channel.

Optional parameters
^^^^^^^^^^^^^^^^^^^

- ``source.electron_capture_probabilities``: probability that the positron is lost by electron capture and no annihilation vertex is produced for a given channel. If this command is omitted, all probabilities default to 0. Values are restricted to the [0, 1] range.
- ``source.mean_positron_range``: mean positron range for each channel. When this command is set, the annihilation vertex is shifted with an isotropic 3D Gaussian whose mean displacement matches the supplied range. If this command is omitted, all positron ranges default to 0.

Event timing and generated vertices
-----------------------------------

For each event, the source first samples the source time and position from the standard source configuration. Then the positronium model may generate up to two primary vertices:

- a prompt-gamma vertex at the sampled source time and position,
- an annihilation vertex delayed by an exponential law with the configured positronium lifetime.

If ``mean_positron_range`` is used, the annihilation vertex position is additionally smeared around the sampled source position.

If the electron-capture probability is very high and the prompt-gamma probability is very low, event generation can become inefficient because the source retries until at least one primary vertex is created. The code emits a warning when the probability of producing neither a prompt gamma nor an annihilation exceeds 90% for a component.

Examples
--------

- Defining the positronium channels using fractions:

.. code:: python

    source = sim.add_source("PositroniumSource", "source")
    source.positronium_fractions = [.5, .5]
    source.positronium_lifetimes = [0.122 * ns, 0.122 * ns]
    source.decay_kinds = ["k2Gamma", "k3Gamma"]
    source.prompt_photon_probabilities = [.25, .33]
    source.prompt_photon_energies = [1.244 * MeV, 1.244 * MeV]

- Defining the positronium channels using intensitites:

.. code:: python

    source = sim.add_source("PositroniumSource", "source")
    source.channels_from_intensities.intensities = [12, 4, 2, 2]
    source.positronium_lifetimes = [.4, 2., .125, 50.]
    source.prompt_gamma_probabilities = [5, 6, 7, 8]
    source.prompt_gamma_energies = [1., 2., 3., 4.]
    source.channels_from_intensities.positron_interactions = ["kDirect", "kOrthoPs", "kParaPs", "kOrthoPs"]


Reference
---------

.. autoclass :: opengate.sources.positroniumsources.PositroniumSource


