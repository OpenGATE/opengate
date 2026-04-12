/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "GateVChemistryActor.h"

class PyGateVChemistryActor : public GateVChemistryActor {
public:
  using GateVChemistryActor::GateVChemistryActor;

  void InitializeChemistryTracking() override {
    PYBIND11_OVERLOAD(void, GateVChemistryActor, InitializeChemistryTracking);
  }

  void AppendChemistryStep(G4Track *track, G4Step *step) override {
    PYBIND11_OVERLOAD(void, GateVChemistryActor, AppendChemistryStep, track,
                      step);
  }

  void StartChemistryTracking(G4Track *track) override {
    PYBIND11_OVERLOAD(void, GateVChemistryActor, StartChemistryTracking, track);
  }

  void EndChemistryTracking(G4Track *track) override {
    PYBIND11_OVERLOAD(void, GateVChemistryActor, EndChemistryTracking, track);
  }

  void FinalizeChemistryTracking() override {
    PYBIND11_OVERLOAD(void, GateVChemistryActor, FinalizeChemistryTracking);
  }
};

void init_GateVChemistryActor(py::module &m) {
  py::class_<GateVChemistryActor, PyGateVChemistryActor,
             std::unique_ptr<GateVChemistryActor, py::nodelete>, GateVActor>(
      m, "GateVChemistryActor")
      .def(py::init<py::dict &>())
      .def("InitializeChemistryTracking",
           &GateVChemistryActor::InitializeChemistryTracking)
      .def("AppendChemistryStep", &GateVChemistryActor::AppendChemistryStep)
      .def("StartChemistryTracking",
           &GateVChemistryActor::StartChemistryTracking)
      .def("EndChemistryTracking", &GateVChemistryActor::EndChemistryTracking)
      .def("FinalizeChemistryTracking",
           &GateVChemistryActor::FinalizeChemistryTracking)
      .def("StartProcessing", &GateVChemistryActor::StartProcessing)
      .def("UserPreTimeStepAction", &GateVChemistryActor::UserPreTimeStepAction)
      .def("UserPostTimeStepAction",
           &GateVChemistryActor::UserPostTimeStepAction)
      .def("EndProcessing", &GateVChemistryActor::EndProcessing);
}
