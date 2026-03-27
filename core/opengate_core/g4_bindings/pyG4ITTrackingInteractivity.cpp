/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4ITTrackingInteractivity.hh"
#include "G4Track.hh"
#include "G4Step.hh"

class PyG4ITTrackingInteractivity : public G4ITTrackingInteractivity {
public:
  using G4ITTrackingInteractivity::G4ITTrackingInteractivity;

  void StartTracking(G4Track *track) override {
    PYBIND11_OVERLOAD(void, G4ITTrackingInteractivity, StartTracking, track);
  }

  void AppendStep(G4Track *track, G4Step *step) override {
    PYBIND11_OVERLOAD(void, G4ITTrackingInteractivity, AppendStep, track, step);
  }

  void EndTracking(G4Track *track) override {
    PYBIND11_OVERLOAD(void, G4ITTrackingInteractivity, EndTracking, track);
  }
};

void init_G4ITTrackingInteractivity(py::module &m) {

  py::class_<G4ITTrackingInteractivity, PyG4ITTrackingInteractivity,
             std::unique_ptr<G4ITTrackingInteractivity, py::nodelete>>(
      m, "G4ITTrackingInteractivity")
      .def(py::init())
      .def("StartTracking", &G4ITTrackingInteractivity::StartTracking)
      .def("AppendStep", &G4ITTrackingInteractivity::AppendStep)
      .def("EndTracking", &G4ITTrackingInteractivity::EndTracking);
}
