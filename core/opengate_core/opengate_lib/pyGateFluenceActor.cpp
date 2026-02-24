/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GateFluenceActor.h"

class PyGateFluenceActor : public GateFluenceActor {
public:
  // Inherit the constructors
  using GateFluenceActor::GateFluenceActor;

  void BeginOfRunActionMasterThread(int run_id) override {
    PYBIND11_OVERLOAD(void, GateFluenceActor, BeginOfRunActionMasterThread,
                      run_id);
  }

  int EndOfRunActionMasterThread(int run_id) override {
    PYBIND11_OVERLOAD(int, GateFluenceActor, EndOfRunActionMasterThread,
                      run_id);
  }
};

void init_GateFluenceActor(py::module &m) {
  py::class_<GateFluenceActor, PyGateFluenceActor,
             std::unique_ptr<GateFluenceActor, py::nodelete>, GateVActor>(
      m, "GateFluenceActor")
      .def(py::init<py::dict &>())
      .def("BeginOfRunActionMasterThread",
           &GateFluenceActor::BeginOfRunActionMasterThread)
      .def("EndOfRunActionMasterThread",
           &GateFluenceActor::EndOfRunActionMasterThread)
      .def("GetPhysicalVolumeName", &GateFluenceActor::GetPhysicalVolumeName)
      .def("SetPhysicalVolumeName", &GateFluenceActor::SetPhysicalVolumeName)
      .def("SetSumTracksFlag", &GateFluenceActor::SetSumTracksFlag)
      .def("GetSumTracksFlag", &GateFluenceActor::GetSumTracksFlag)
      .def("SetFluenceScoringMode", &GateFluenceActor::SetFluenceScoringMode)
      .def("GetFluenceScoringMode", &GateFluenceActor::GetFluenceScoringMode)
      .def_readwrite("NbOfEvent", &GateFluenceActor::NbOfEvent)
      .def_readwrite("cpp_fluence_image", &GateFluenceActor::cpp_fluence_image)
      .def_readwrite("cpp_fluence_sum_tracks_image", &GateFluenceActor::cpp_fluence_sum_tracks_image);
}
