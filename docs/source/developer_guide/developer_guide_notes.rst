Notes for developers
====================

Pybind11 hints
--------------

Below are a list of hints (compared to boost-python).

-  https://github.com/KratosMultiphysics/Kratos/wiki/Porting-to-PyBind11---common-steps
-  bases is not any longer required. Only its template argument must
   remain, in the same position of what was there before.
-  The noncopyable template argument should not be provided (everything
   is noncopyable unless specified) - if something is to be made
   copyable, a copy constructor should be provided to python
-  return policies, see
   https://pybind11.readthedocs.io/en/stable/advanced/functions.html
-  ``return_value_policy<reference_existing_object>`` –>
   ``py::return_value_policy::reference``
-  ``return_internal_reference<>()`` –>
   ``py::return_value_policy::reference_internal``
-  ``return_value_policy<return_by_value>()`` –>
   ``py::return_value_policy::copy``
-  ``add_property`` –> ``.def_readwrite``
-  Overloading methods, i.e.:
   ``py::overload_cast<G4VUserPrimaryGeneratorAction*>(&G4RunManager::SetUserAction))``
-  Pure virtual need a trampoline class
   https://pybind11.readthedocs.io/en/stable/advanced/classes.html
-  Python debug: ``python -q -X faulthandler``

Memory management between Python and Geant4 - Why is there a segmentation fault?
--------------------------------------------------------------------------------

Code and memory (objects) can be on the python and/or C++(Geant4)-side.
To avoid memory leakage, the G4 objects need to be deleted at some
point, either by the C++-side, meaning G4, or by the garbage collector
on the python-side. This requires some understanding of how lifetime is
managed in G4. GATE 10 uses the G4RunManager to initialize, run, and
deconstruct a simulation. The G4RunManager’s destructor triggers a
nested sequence of calls to the destructors of many objects the run
manager handles, e.g. geometry and physics. These objects, if they are
created on the python-side, e.g. because the Construct() method is
implemented in python, should never be deleted on the python-side
because the G4RunManager is responsible for deletion and segfaults occur
if the objects exist now longer at the time of supposed destruction. In
this case, the no ``py::nodelete`` option in pybind11 is the correct
way.

There is also the python-side concerning objects which are deleted by
the G4RunManager: If python stores a reference to the object, and it
generally should (see below), this reference will not find the object
anymore once the G4RunManager has been deleted. Therefore, we have
implemented a mechanism which makes sure that references to G4 objects
are unset before the G4RunManager is garbage collected (and thus its
destructor is called). This is done via the close() and
release_g4_references() methods combined with a
``with SimulationEngine as se`` context clause.

The situation is somewhat different for objects that are not
automatically deleted by the Geant4 session. This concerns objects which
a G4 user would manually destruct and delete. The “user”, from a G4
perspective, is the python-side of GATE, specifically the
SimulationEngine, which creates and controls the G4RunManager. The
objects in question should be destroyed on the python side, and in fact
they (normally) are via garbage collection. To this end, they should
**not** be bound with the ``py::nodelete`` option - which would prevent
garbage collection.

In any case, G4 objects created on the python-side should not be
destroyed (garbage collected) too early, i.e. not before the end of the
G4 simulation, to avoid segfaults when G4 tries to a find the object to
which it holds a pointer. It is important to note here that garbage
collection in python is strongly tied to reference counting, meaning,
objects may be garbage collected as soon as there are no more references
pointing to them. Or in other words: you can prevent garbage collection
by keeping a reference. In practice: If you create a G4 object that is
required to persist for the duration of the simulation and you create
this object in a local scope, e.g. in a function, you need to make sure
to store a reference somewhere so that it lives beyond the local scope.
Otherwise, when the function goes out of scope, the local reference no
longer exists and the G4 object may be garbage collected. This is the
reason why GATE 10 stores references to G4 objects in class attributes,
either as plane reference, or via lists or dictionaries. A nasty detail:
in case of a G4 object that is only referenced locally (implementation
error), the moment when the segfault occurs might vary because garbage
collection in python is typically scheduled (for performance reasons),
meaning objects are collected any time after their last reference is
released, but not necessarily at that moment. This can cause a seeming
randomness in the segfaults.

So, after a long explanation, the key points are:

-  check the nature of your G4 object. if it is designed to be deleted
   by the G4RunManager, add the ``py::no_delete`` option in the pybind11
   binding.

-  In any case, make sure to store a non-local persistent reference on
   the python-side, ideally as a class attribute.

-  Add a “release statement” in the release_g4_references() method for
   each G4 reference (strictly only to RunManager-handled objects, but
   it does not hurt for others) in the class, and make sure the
   release_g4_references() method is called by the class’s close()
   method.

An example may be the implementation of the Tesselated Volume (STL).

Pybindings in pyG4TriangularFacet.cpp:

``py::class_<G4TriangularFacet, G4VFacet>(m, "G4TriangularFacet")``

will cause a segmentation fault

``py::class_<G4TriangularFacet,  G4VFacet, std::unique_ptr<G4TriangularFacet, py::nodelete>>(m, "G4TriangularFacet")``

will work as python is instructed not to delete the object.

On the python-side in geometry/solids.py:

.. code:: python

   def __init__(self, *args, **kwargs):
       super().__init__(*args, **kwargs)

       self.g4_solid = None
       self.g4_tessellated_solid = None
       self.g4_facets = None

All data which is sent to Geant4 is included as a variable to the class.
As such, it is only deleted at the end of the simulation, not when the
function ends. Which, would cause a segmentation fault.

ITK
---

-  The following
   `issue <https://github.com/OpenGATE/opengate/issues/216>`__ occured
   in the past and was solved by updating ITK:
   test058_calc_uncertainty_MT.py was failing because of a TypeError
   raised by ITK. Specifically:
   ``TypeError: in method 'itkImageIOFactory_CreateImageIO', argument 1 of type 'char const *'``
   After updating ITK (via pip) from 5.2.1.post1 to 5.3.0, the error is
   gone. If you get a similar error, try updating ITK first, by
   ``pip install itk --upgrade``

-  Here is another `ITK-related
   issue <https://github.com/OpenGATE/opengate/issues/232>`__ that has
   occured in the past: The following exception was raised while trying
   to run test015_iec_phantom_1.py:
   ``module 'itk' has no attribute 'ChangeInformationImageFilter'``.
   This kind of issue is also documented in ITK’s issue tracker:
   https://discourse.itk.org/t/changeinformationimagefilter-missing-from-pip-installed-itk-5-3rc4post3/5375

   Solution:

   1) Uninstall ITK
   2) Manually remove all traces of ITK from your python environment
   3) re-install ITK

   For me, this was:
   ``pip uninstall itk   rm -r /Users/nkrah/.virtualenvs/opengate/lib/python3.9/site-packages/itk*   pip install --upgrade --pre itk``

Geant4 seems to be frozen/sleeping - the GIL is to blame - here is why
----------------------------------------------------------------------

This is taken from Issue #145 which is now closed.

So here is what happened to me: While working on a branch, I implemented
an alternative binding of the G4MTRunManager. The binding includes the
function G4MTRunManager::Initialize(). The naïve implementation is:

::

     .def("Initialize", &G4MTRunManager::Initialize)

When I tried to run a test with threads>1, Geant4 simply stopped at some
point, namely when geometry and physics list were apparently set up. No
error, no segfault, no further output, no CPU load, just frozen. Umpf.
After a scattering cout’s through the Geant4 source could, I understood
the problem, and why others, like David S, had used a smarter, less
naïve binding of the Initialize() function.

Here is what went wrong: G4MTRunManager::Initialize() function first
calls the single thread G4RunManager::Initialize() and then does a fake
run by calling BeamOn(0); The argument n–event=zero is internally
interpreted as fake run and not all steps are performed as would be in a
real BeamOn(). The purpose of the fake run is to set-up the worker run
managers. BeamOn(0) does trigger G4RunManager::DoEventLoop() and this in
turn triggers G4MTRunManager::InitializeEventLoop (the overridden
version from the inherited G4MTRunManager!). At the very end, after
creating and starting workers, there is a WaitForReadyWorkers(); This
function contains
beginOfEventLoopBarrier.Wait(GetNumberActiveThreads()); which
essentially waits until all workers release locks. Specifically, it
triggers a call to G4MTBarrier::Wait() which contains a while(true) loop
to repeatedly check the number of locks on the shared resource, and
breaks the loop when the number of locks equals the number of threads.

Now, admittedly, I do not understand every detail here, but it is clear
that Geant4’s implementation relies on locks to establish whether
workers are ready. So when my simulation_engine (i.e., Gate internally)
called g4_RunManager.Initialize(), it ended up stuck in the while loop
waiting for the locks to decrease, which never happened. Why?

This is where the so-called Global Interpreter Lock comes into play.
Read this to understand the details: https://realpython.com/python-gil/,
or don’t if you are smarter than I am. Essentially, at least in the
CPython implementation, there is a lock (mutex) on all resources linked
to the python interpreter. Historically, the GIL was a pragmatic choice
to easily integrate C-extensions into python even if they were not
thread-safe. What does that have to do with Gate? Well, many objects
such as physics lists, are created in python, and then communicated to
the Geant4 RunManager (e.g. via SetUserInitializaition). There is thus a
lock on these resources, namely the GIL. The multithread mechanism in
Geant4, on the other hand, does not know about the GIL and thus cannot
account for this additional lock, so the lock counter never decreases
sufficiently to satisfy Geant4. A way to resolve this dilemma, without
hacking around in the Geant4 code, is to instruct pybind to release the
Global Interpreter Lock within the scope of the call to a C++ function,
such as Initialize(). One way to achieve this is to replace the naïve

::

   .def("Initialize", &G4MTRunManager::Initialize)

by

::

         .def("Initialize",
              [](G4MTRunManager *mt) {
                py::gil_scoped_release release;
                mt->Initialize();
              })

The key here is the “py::gil_scoped_release release” statement. It
instructs pybind to release the GIL before calling the function
Initialize(). There is actually a useful passage in pybind’s doc:
https://pybind11.readthedocs.io/en/stable/advanced/misc.html

I think, in the case of Gate/Geant4, it is safe to release the GIL
because we know that Geant4 handles shared resources in a thread-safe
way. Quite the contrary: the GIL actually breaks G4’s mechanism.

So what I learned from this: Any Geant4 function which relies on
Geant4’s MT mechanism based on locks needs to be bound to python with a
“py::gil_scoped_release release” statement as above. The serial version
G4RunManager::Initialize() does not need this statement (and should not
have it) because it does not check locks at any point.
