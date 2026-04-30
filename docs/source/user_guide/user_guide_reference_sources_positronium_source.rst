.. _source-positronium-source:

Positronium source
==================

Description
-----------

A positronium source can be created as follows:

.. code:: python

   source = sim.add_source("PositroniumSource", "source")
    source.positronium_fractions = [0.4, 0.3, 0.2, 0.1]
    source.positronium_lifetimes = [0.122 * ns, 2 * ns, 5 * ns, 12 * ns]
    source.decay_kinds = ["k2Gamma", "k2Gamma", "k3Gamma", "k2Gamma"]
    source.prompt_photon_probabilities = [0.1, 1., 1., 0.5]
    source.prompt_photon_energies = [1.244 * MeV, 1 * MeV, 1.2 * MeV, 2 * MeV]

This code create a positronium source. The source defines several decay channels, represented by the list given to the parameters ``positronium_fractions``, ``positronium_lifetimes``, ``decay_kinds``, ``prompt_photon_probabilities`` and ``prompt_photon_energies``. The first decay channel is defined by the first elements of the above lists; the second, by the second elements, and so on. As a consequence, all of these five parameters must be passed a list of equal length. Also, at least one decay channel must be defined.

For instance, in the example given above, the first decay channel has a probability of 10% of emitting a 1244 MeV prompt photon, and a probability of 40% of forming a positronium. If formed, this positronium will have a lifetime of 0.122 ns, then will annihilate into 2 gammas.

The list given to ``positronium_fractions`` does not necessarily add up to 1, as the values are internally renormalized.
The values given to ``decay_kinds`` must be either ``"k2Gamma"`` or ``"k3Gamma"`` and correspond to annihilation into 2 gammas or 3 gammas, respectively. It is not (yet) possible to generate annihilation into more than 3 gammas. The values given to ``prompt_photon_probabilities`` must naturally be between 0 (no prompt photon) and 1 (there will always be a prompt photon).


Reference
---------

.. autoclass :: opengate.sources.positroniumsources.PositroniumSource


