/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GateBeamQualityActor.h"

class PyGateBeamQualityActor : public GateBeamQualityActor {
public:
  // Inherit the constructors
  using GateBeamQualityActor::GateBeamQualityActor;

  void BeginOfRunActionMasterThread(int run_id) override {
    PYBIND11_OVERLOAD(void, GateBeamQualityActor, BeginOfRunActionMasterThread,
                      run_id);
  }

  int EndOfRunActionMasterThread(int run_id) override {
    PYBIND11_OVERLOAD(int, GateBeamQualityActor, EndOfRunActionMasterThread,
                      run_id);
  }
};

void init_GateBeamQualityActor(py::module &m) {
  py::class_<GateBeamQualityActor, PyGateBeamQualityActor,
             std::unique_ptr<GateBeamQualityActor, py::nodelete>,
             GateWeightedEdepActor>(m, "GateBeamQualityActor")
      .def(py::init<py::dict &>())
      .def("BeginOfRunActionMasterThread",
           &GateBeamQualityActor::BeginOfRunActionMasterThread)
      .def("EndOfRunActionMasterThread",
           &GateBeamQualityActor::EndOfRunActionMasterThread)
      .def_readwrite("cpp_numerator_alpha_image",
                     &GateBeamQualityActor::cpp_numerator_image)
      .def_readwrite("cpp_numerator_beta_image",
                     &GateBeamQualityActor::cpp_second_numerator_image)
      // .def_readwrite("cpp_dose_image", &GateBeamQualityActor::cpp_dose_image)
      .def_readwrite("cpp_denominator_image",
                     &GateBeamQualityActor::cpp_denominator_image)
      // .def_readwrite("cpp_nucleus_dose_image",
      // &GateBeamQualityActor::cpp_nucleus_dose_image)
      .def_readwrite("NbOfEvent", &GateBeamQualityActor::NbOfEvent)
      .def_readwrite("ZMinTable", &GateBeamQualityActor::ZMinTable)
      .def_readwrite("ZMaxTable", &GateBeamQualityActor::ZMaxTable)
      .def_readwrite("fSmax", &GateBeamQualityActor::fSmax)
      .def_readwrite("fAreaNucl", &GateBeamQualityActor::fAreaNucl)
      .def("GetPhysicalVolumeName",
           &GateBeamQualityActor::GetPhysicalVolumeName)
      .def("SetPhysicalVolumeName",
           &GateBeamQualityActor::SetPhysicalVolumeName);
  //      .def_readwrite("fPhysicalVolumeName",
  //      &GateBeamQualityActor::fPhysicalVolumeName);
}
