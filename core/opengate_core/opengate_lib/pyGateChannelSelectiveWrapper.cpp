/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "G4VPhysicsConstructor.hh"
#include "GateChannelSelectiveWrapper.h"

void init_GateChannelSelectiveWrapperPhysics(py::module &m) {
  // Expose GateChannelSelectiveWrapperPhysics as a G4VPhysicsConstructor
  // subclass.  py::nodelete is required because G4VModularPhysicsList takes
  // ownership of the raw C++ pointer after RegisterPhysics() is called —
  // Python must not call the destructor when it GC's the Python wrapper.
  py::class_<GateChannelSelectiveWrapperPhysics, G4VPhysicsConstructor,
             std::unique_ptr<GateChannelSelectiveWrapperPhysics, py::nodelete>>(
      m, "GateChannelSelectiveWrapperPhysics")
      .def(py::init<G4double, const std::vector<std::vector<int>> &>(),
           py::arg("xs_scaling"), py::arg("desired_channel"),
           "Construct the physics constructor.\n\n"
           "xs_scaling      -- factor applied to the total alphaInelastic XS.\n"
           "desired_channel -- list of [Z, A] pairs that must appear in the\n"
           "                   reaction products (subset match).\n"
           "                   Example He3+n+X: [[2,3],[0,1]]")
      // Static counter accessors (thread-safe, accumulated across workers)
      .def_static("get_total_count",
                  &GateChannelSelectiveWrapperPhysics::GetTotalCount,
                  "Total alphaInelastic interactions seen.")
      .def_static("get_desired_count",
                  &GateChannelSelectiveWrapperPhysics::GetDesiredCount,
                  "Interactions matching the desired channel.")
      .def_static("get_rollback_count",
                  &GateChannelSelectiveWrapperPhysics::GetRollbackCount,
                  "Unwanted interactions suppressed by Russian roulette.")
      .def_static("reset_counts",
                  &GateChannelSelectiveWrapperPhysics::ResetCounts,
                  "Reset all counters to zero.");
}
