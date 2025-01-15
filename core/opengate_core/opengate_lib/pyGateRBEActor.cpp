/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GateRBEActor.h"

class PyGateRBEActor : public GateRBEActor {
public:
  // Inherit the constructors
  using GateRBEActor::GateRBEActor;

  void BeginOfRunActionMasterThread(int run_id) override {
    PYBIND11_OVERLOAD(void, GateRBEActor, BeginOfRunActionMasterThread, run_id);
  }

  int EndOfRunActionMasterThread(int run_id) override {
    PYBIND11_OVERLOAD(int, GateRBEActor, EndOfRunActionMasterThread, run_id);
  }
};

void init_GateRBEActor(py::module &m) {
  py::class_<GateRBEActor, PyGateRBEActor,
             std::unique_ptr<GateRBEActor, py::nodelete>, GateWeightedEdepActor>(
      m, "GateRBEActor")
      .def(py::init<py::dict &>())
      .def("BeginOfRunActionMasterThread",
           &GateRBEActor::BeginOfRunActionMasterThread)
      .def("EndOfRunActionMasterThread",
           &GateRBEActor::EndOfRunActionMasterThread)
      .def_readwrite("cpp_numerator_image", &GateRBEActor::cpp_numerator_image)
      .def_readwrite("cpp_numerator_beta_image", &GateRBEActor::cpp_numerator_beta_image)
      .def_readwrite("cpp_dose_image", &GateRBEActor::cpp_dose_image)
      .def_readwrite("cpp_denominator_image",
                     &GateRBEActor::cpp_denominator_image)
      .def_readwrite("cpp_nucleus_dose_image", &GateRBEActor::cpp_nucleus_dose_image)
      .def_readwrite("NbOfEvent", &GateRBEActor::NbOfEvent)
      .def("GetPhysicalVolumeName", &GateRBEActor::GetPhysicalVolumeName)
      .def("SetPhysicalVolumeName", &GateRBEActor::SetPhysicalVolumeName);
  //      .def_readwrite("fPhysicalVolumeName",
  //      &GateRBEActor::fPhysicalVolumeName);
}
