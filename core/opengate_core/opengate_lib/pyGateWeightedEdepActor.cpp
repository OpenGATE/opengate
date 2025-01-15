/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GateWeightedEdepActor.h"

class PyGateWeightedEdepActor : public GateWeightedEdepActor {
public:
  // Inherit the constructors
  using GateWeightedEdepActor::GateWeightedEdepActor;

  void BeginOfRunActionMasterThread(int run_id) override {
    PYBIND11_OVERLOAD(void, GateWeightedEdepActor, BeginOfRunActionMasterThread, run_id);
  }

  int EndOfRunActionMasterThread(int run_id) override {
    PYBIND11_OVERLOAD(int, GateWeightedEdepActor, EndOfRunActionMasterThread, run_id);
  }
};

void init_GateWeightedEdepActor(py::module &m) {
  py::class_<GateWeightedEdepActor, PyGateWeightedEdepActor,
             std::unique_ptr<GateWeightedEdepActor, py::nodelete>, GateVActor>(
      m, "GateWeightedEdepActor")
      .def(py::init<py::dict &>())
      .def("BeginOfRunActionMasterThread",
           &GateWeightedEdepActor::BeginOfRunActionMasterThread)
      .def("EndOfRunActionMasterThread",
           &GateWeightedEdepActor::EndOfRunActionMasterThread)
      .def_readwrite("cpp_numerator_image", &GateWeightedEdepActor::cpp_numerator_image)
      .def_readwrite("cpp_denominator_image",
                     &GateWeightedEdepActor::cpp_denominator_image)
      .def_readwrite("NbOfEvent", &GateWeightedEdepActor::NbOfEvent)
      .def("GetPhysicalVolumeName", &GateWeightedEdepActor::GetPhysicalVolumeName)
      .def("SetPhysicalVolumeName", &GateWeightedEdepActor::SetPhysicalVolumeName);
  //      .def_readwrite("fPhysicalVolumeName",
  //      &GateWeightedEdepActor::fPhysicalVolumeName);
}
