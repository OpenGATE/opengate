/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4UserStackingAction.hh"

class PyG4UserStackingAction : public G4UserStackingAction {
public:
  /* Inherit the constructors */
  using G4UserStackingAction::G4UserStackingAction;

  void NewStage() override {
    PYBIND11_OVERLOAD(void, G4UserStackingAction, NewStage);
  }
};

void init_G4UserStackingAction(py::module &m) {

  py::class_<G4UserStackingAction, PyG4UserStackingAction>(
      m, "G4UserStackingAction")
      .def(py::init())
      .def("NewStage", &G4UserStackingAction::NewStage);
}
