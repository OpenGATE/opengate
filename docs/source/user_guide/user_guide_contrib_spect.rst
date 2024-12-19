SPECT imaging systems
=====================

**Important Notice**: Please be aware that the models provided within the OpenGate toolkit are based on approximate simulations. Users are strongly encouraged to independently verify these models against empirical data to ensure their applicability and accuracy for specific use cases.

GE Discovery 670 SPECT
----------------------

The GE Discovery NM670 SPECT system can be simulated using the following commands:


.. code-block:: python

    import opengate as gate
    import opengate.contrib.spect.ge_discovery_nm670 as discovery

    sim = gate.Simulation()
    spect = discovery.add_spect_head(sim, "discovery1", collimator_type="melp")
    crystal = sim.volume_manager.get_volume(f"{spect.name}_crystal")
    discovery.add_digitizer_tc99m(sim, crystal.name, "digit_tc99m")

    spect = discovery.add_spect_head(sim, "discovery12", collimator_type="lehr")
    crystal = sim.volume_manager.get_volume(f"{spect.name}_crystal")
    discovery.add_digitizer_lu177(sim, crystal.name, "digit_lu177", rotation_deg=15, crystal_size="5/8")

This configuration allows the simulation of two SPECT heads with different collimators (MELP and LEHR) and digitizers optimized for Tc99m and Lu177, respectively. There are three collimator types: "lehr", "megp" and "hegp". There are two crystal size "3/8" and "5/8". Also the collimator can be rotated by few degrees, usually 15 deg like in reality.

Detail of the head description is `available here <https://github.com/OpenGATE/opengate/blob/master/opengate/contrib/spect/ge_discovery_nm670.py#L53>`_

**Note**: the digitizer is still a very simple one, validation are still in progress.


Siemens Symbia Intevo Bold SPECT
--------------------------------

The Siemens Symbia Intevo Bold SPECT system can be simulated with the following commands:


.. code-block:: python

    import opengate as gate
    import opengate.contrib.spect.siemens_intevo as intevo

    sim = gate.Simulation()
    spect = intevo.add_spect_head(sim, "intevo1", collimator_type="melp")
    crystal = sim.volume_manager.get_volume(f"{spect.name}_crystal")
    intevo.add_digitizer_tc99m(sim, crystal.name, "digit_tc99m")

    spect = discovery.add_spect_head(sim, "intevo2", collimator_type="lehr")
    crystal = sim.volume_manager.get_volume(f"{spect.name}_crystal")
    intevo.add_digitizer_lu177(sim, crystal.name, "digit_lu177")


There are three collimators:
- Collimator LEHR: Low Energy High Resolution    (for Tc99m), 1.11 mm holes
- Collimator MELP: Medium Energy Low Penetration (for In111, Lu177), 2.94 mm holes
- Collimator HE:   High Energy General Purpose   (for I131), 4 mm holes

Detail of the head description is `available here <https://github.com/OpenGATE/opengate/blob/master/opengate/contrib/spect/siemens_intevo.py#L19>`_



**Note**: the digitizer is still a very simple one, validation are still in progress.
