/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "GateAttenuationImageActor.h"
#include "GateHelpers.h"

class PyGateAttenuationImageActor : public GateAttenuationImageActor {
public:
  // Inherit the constructors
  using GateAttenuationImageActor::GateAttenuationImageActor;

  void BeginOfRunAction(const G4Run *Run) override {
    PYBIND11_OVERLOAD(void, GateAttenuationImageActor, BeginOfRunAction, Run);
  }
};

void init_GateAttenuationImageActor(py::module &m) {
  py::class_<GateAttenuationImageActor, PyGateAttenuationImageActor,
             std::unique_ptr<GateAttenuationImageActor, py::nodelete>,
             GateVActor>(m, "GateAttenuationImageActor")
      .def(py::init<py::dict &>())
      .def("BeginOfRunAction", &GateAttenuationImageActor::BeginOfRunAction);
}
