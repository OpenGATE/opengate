/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4Track.hh"
#include "G4UserTimeStepAction.hh"

class PyG4UserTimeStepAction : public G4UserTimeStepAction {
public:
  using G4UserTimeStepAction::G4UserTimeStepAction;

  void StartProcessing() override {
    PYBIND11_OVERLOAD(void, G4UserTimeStepAction, StartProcessing, );
  }

  void NewStage() override {
    PYBIND11_OVERLOAD(void, G4UserTimeStepAction, NewStage, );
  }

  void UserPreTimeStepAction() override {
    PYBIND11_OVERLOAD(void, G4UserTimeStepAction, UserPreTimeStepAction, );
  }

  void UserPostTimeStepAction() override {
    PYBIND11_OVERLOAD(void, G4UserTimeStepAction, UserPostTimeStepAction, );
  }

  void UserReactionAction(const G4Track &trackA, const G4Track &trackB,
                          const std::vector<G4Track *> *products) override {
    PYBIND11_OVERLOAD(void, G4UserTimeStepAction, UserReactionAction, trackA,
                      trackB, products);
  }

  void EndProcessing() override {
    PYBIND11_OVERLOAD(void, G4UserTimeStepAction, EndProcessing, );
  }
};

void init_G4UserTimeStepAction(py::module &m) {

  py::class_<G4UserTimeStepAction, PyG4UserTimeStepAction,
             std::unique_ptr<G4UserTimeStepAction, py::nodelete>>(
      m, "G4UserTimeStepAction")
      .def(py::init())
      .def("StartProcessing", &G4UserTimeStepAction::StartProcessing)
      .def("NewStage", &G4UserTimeStepAction::NewStage)
      .def("UserPreTimeStepAction", &G4UserTimeStepAction::UserPreTimeStepAction)
      .def("UserPostTimeStepAction",
           &G4UserTimeStepAction::UserPostTimeStepAction)
      .def("UserReactionAction", &G4UserTimeStepAction::UserReactionAction)
      .def("EndProcessing", &G4UserTimeStepAction::EndProcessing);
}
