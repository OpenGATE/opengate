/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "GateHelpers.h"
#include "GateVActor.h"

/*
 * The "trampoline" functions below are required if we want to
 * allow callbacks on the py side.
 *
 * If it is not needed: do not define trampoline functions in class that inherit
 * from VActor.
 *
 * It must be defined also in all classes that inherit from GateVActor
 *
 * Hence, BeginOfRunAction, BeginOfEventAction etc maybe define in py side
 * (but it will be slower, especially for steps)
 */

// for the moment, we dont need that. So it is commented

class PyGateVActor : public GateVActor {
public:
  // Inherit the constructors
  using GateVActor::GateVActor;

  void BeginOfRunActionMasterThread(int run_id) override {
    PYBIND11_OVERLOAD(void, GateVActor, BeginOfRunActionMasterThread, run_id);
  }

  //    void SteppingAction(G4Step *step) override {
  //        PYBIND11_OVERLOAD(void, GateVActor, SteppingAction, step);
  //    }
  //
  //    void BeginOfRunAction(const G4Run *Run) override {
  //        PYBIND11_OVERLOAD(void, GateVActor, BeginOfRunAction, Run);
  //    }
  //
  //    void EndOfRunAction(const G4Run *Run) override {
  //        PYBIND11_OVERLOAD(void, GateVActor, EndOfRunAction, Run);
  //    }
  //
  //    void BeginOfEventAction(const G4Event *event) override {
  //        PYBIND11_OVERLOAD(void, GateVActor, BeginOfEventAction, event);
  //    }
  //
  //    void EndOfEventAction(const G4Event *event) override {
  //        PYBIND11_OVERLOAD(void, GateVActor, EndOfEventAction, event);
  //    }
  //
  //    void PreUserTrackingAction(const G4Track *track) override {
  //        PYBIND11_OVERLOAD(void, GateVActor, PreUserTrackingAction, track);
  //    }
  //
  //    void PostUserTrackingAction(const G4Track *track) override {
  //        PYBIND11_OVERLOAD(void, GateVActor, PostUserTrackingAction, track);
  //    }
};

void init_GateVActor(py::module &m) {

  py::class_<GateVActor, PyGateVActor, // do not inherit from trampoline for
                                       // the moment (not needed)
             std::unique_ptr<GateVActor, py::nodelete>>(m, "GateVActor")
      .def(py::init<py::dict &>())
      .def("RegisterSD", &GateVActor::RegisterSD)
      .def_readonly("fActions", &GateVActor::fActions)
      .def_readwrite("fFilters", &GateVActor::fFilters)
      .def("ActorInitialize", &GateVActor::ActorInitialize)
      .def("AddActions", &GateVActor::AddActions)
      .def("StartSimulationAction", &GateVActor::StartSimulationAction)
      .def("EndSimulationAction", &GateVActor::EndSimulationAction)
      .def("BeginOfRunAction", &GateVActor::BeginOfRunAction)
      .def("BeginOfRunActionMasterThread",
           &GateVActor::BeginOfRunActionMasterThread)
      .def("EndOfRunAction", &GateVActor::EndOfRunAction)
      .def("BeginOfEventAction", &GateVActor::BeginOfEventAction)
      .def("EndOfEventAction", &GateVActor::EndOfEventAction)
      .def("PreUserTrackingAction", &GateVActor::PreUserTrackingAction)
      .def("PostUserTrackingAction", &GateVActor::PostUserTrackingAction)
      .def("SteppingAction", &GateVActor::SteppingAction);
}
