.. _fields-reference-label:

Details: Electromagnetic fields
================================

[TO BE COMPLETED]

Base class reference
--------------------

.. autoclass:: opengate.geometry.fields.FieldBase
   :members:
   :show-inheritance:

.. autoclass:: opengate.geometry.fields.MagneticField
   :members:
   :show-inheritance:

.. autoclass:: opengate.geometry.fields.ElectroMagneticField
   :members:
   :show-inheritance:

.. autoclass:: opengate.geometry.fields.ElectricField
   :members:
   :show-inheritance:

.. note::

     The class documention of G4FieldManager is incomplete (lacking method signatures and descriptions of what they actually do). It's kind of a place holder and helps to get the number of Sphinx warnings to be zero.

G4 Field Manager class reference
--------------------------------

.. py:class:: opengate_core.G4FieldManager

      .. py:method:: SetDetectorField()

      .. py:method:: ProposeDetectorField()

      .. py:method:: ChangeDetectorField()

      .. py:method:: GetDetectorField()

      .. py:method:: DoesFieldExist()

      .. py:method:: CreateChordFinder()

      .. py:method:: SetChordFinder()

      .. py:method:: GetChordFinder()

      .. py:method:: ConfigureForTrack()

      .. py:method:: GetDeltaIntersection()

      .. py:method:: GetDeltaOneStep()

      .. py:method:: SetAccuraciesWithDeltaOneStep()

      .. py:method:: SetDeltaOneStep()

      .. py:method:: SetDeltaIntersection()

      .. py:method:: GetMinimumEpsilonStep()

      .. py:method:: SetMinimumEpsilonStep()

      .. py:method:: GetMaximumEpsilonStep()

      .. py:method:: SetMaximumEpsilonStep()

      .. py:method:: DoesFieldChangeEnergy()

      .. py:method:: SetFieldChangesEnergy()

      .. py:method:: GetMaxAcceptedEpsilon()

      .. py:method:: SetMaxAcceptedEpsilon()
