How to implement an actor
=========================

Mandatory basic class structure
-------------------------------

1) Implement an ``initialize()`` method which should at least:

-  call the ``initialize()`` method from the python super class.
-  call the ``InitializeCpp()`` method from the C++ super class
-  call the ``InitializeUserInput()`` method from the C++ super class
-  If you need to perform specific checks, e.g. plausibility of user
   input parameters, you will probably want to do that before calling
   the C++ methods.
-  Example:
   ``python     def initialize(self):         ActorBase.initialize(self)         # possibly implement some checks here ...         self.InitializeUserInput(self.user_info)         self.InitializeCpp()``

2) Implement a ``__initcpp__()`` method. This should at least call the
   C++ constructor method and add actions if needed. Example:
   ``python     def __initcpp__(self):         g4.GateSimulationStatisticsActor.__init__(self, self.user_info)         self.AddActions({"StartSimulationAction", "EndSimulationAction"})``
   Do **not** call the C++ constructor in the python ``__init__()``
   method. This will cause problems when a simulation is run in a
   subprocess. Reason: The subprocessing mechanism relies on
   de-/serialization and GATE expects a ``__initcpp__()`` method to make
   sure the C++ constructor is called after deserialization (see
   ``__setstate__()`` in *actors/base.py*)

3) Inherit first from the python base class and then from the C++ base
   class. In other words, write:
   ``python     class SimulationStatisticsActor(ActorBase, g4.GateSimulationStatisticsActor):``
   Do **not** write:
   ``python     class SimulationStatisticsActor( g4.GateSimulationStatisticsActor, ActorBase):``

4) Refer to the super class explicitly and do **not** use the
   ``super()`` builtin from python because it cannot resolve C++ super
   classes.

Inheritance in actor classes
----------------------------

FIXME: Inherit first from python base class and then from C++ base
class.
