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
  using G4UserStackingAction::G4UserStackingAction;

  G4ClassificationOfNewTrack ClassifyNewTrack(const G4Track *aTrack) override {
    PYBIND11_OVERLOAD(G4ClassificationOfNewTrack, G4UserStackingAction,
                      ClassifyNewTrack, aTrack);
  }

  void NewStage() override {
    PYBIND11_OVERLOAD(void, G4UserStackingAction, NewStage, );
  }

  void PrepareNewEvent() override {
    PYBIND11_OVERLOAD(void, G4UserStackingAction, PrepareNewEvent, );
  }
};

void init_G4UserStackingAction(py::module &m) {

  py::class_<G4UserStackingAction, PyG4UserStackingAction>(
      m, "G4UserStackingAction")
      .def(py::init())
      .def("ClassifyNewTrack", &G4UserStackingAction::ClassifyNewTrack)
      .def("NewStage", &G4UserStackingAction::NewStage)
      .def("PrepareNewEvent", &G4UserStackingAction::PrepareNewEvent);
}
