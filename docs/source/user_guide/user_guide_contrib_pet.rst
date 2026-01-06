PET imaging systems
===================

**Important Notice**: Please be aware that the models provided within the OpenGate toolkit are based on approximate simulations. Users are strongly encouraged to independently verify these models against empirical data to ensure their applicability and accuracy for specific use cases.


Philips Vereos Digital PET
--------------------------

The Philips Vereos Digital PET model can be included in your simulation using the following command:


.. code-block:: python

    import opengate as gate
    import opengate.contrib.pet.philipsvereos as pet_vereos
    sim = gate.Simulation()
    pet = pet_vereos.add_pet(sim, "my_pet")


This command will include the whole PET head as described in `[Salvadori2020, EJNMMI] <http://doi.org/10.1186/s40658-020-00288-w>`_. It comprises 18 modules, each containing 4x5 stacks of 4x4 die, with each die consisting of 2x2 crystals.

Details of the head description are `available here <https://github.com/OpenGATE/opengate/blob/master/opengate/contrib/pet/philipsvereos.py#L39>`_

.. note:: A validated digitizer for this PET model is not yet available. Development is ongoing. For examples, refer to the test037 test case.

Siemens Biograph Vision PET
---------------------------

To include the Siemens Biograph Vision PET model in your simulation, use the following commands:


.. code-block:: python

    import opengate as gate
    import opengate.contrib.pet.siemensbiograph as pet_biograph
    sim = gate.Simulation()
    pet = pet_biograph.add_pet(sim, "my_pet")
    singles = pet_biograph.add_digitizer(sim, pet.name, "singles.root", hits_name="Hits", singles_name="Singles")


This command will include the whole PET head as described in `[Salvadori2024, PMB] <http://doi.org/10.1088/1361-6560/ad638c>`_ or `[O'Briain 2022 MedPhys] <http://doi.org/10.1002/mp.16032>`_.

Detail of the head description is `available here <https://github.com/OpenGATE/opengate/blob/master/opengate/contrib/pet/siemensbiograph.py#L15>`_

**Note**: The provided digitizer is an illustrative example and has not yet been validated. For additional context, refer to the test049 test case.
