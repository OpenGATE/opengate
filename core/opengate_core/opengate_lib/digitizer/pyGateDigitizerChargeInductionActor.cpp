/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateDigitizerChargeInductionActor.h"
#include <pybind11/numpy.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

void init_GateDigitizerChargeInductionActor(py::module &m) {

  py::class_<GateDigitizerChargeInductionActor,
             std::unique_ptr<GateDigitizerChargeInductionActor, py::nodelete>,
             GateVDigitizerWithOutputActor>(m,
                                            "GateDigitizerChargeInductionActor")
      .def(py::init<py::dict &>())
      .def("SetCrystalDepth",
           &GateDigitizerChargeInductionActor::SetCrystalDepth)
      .def("SetCrystalThickness",
           &GateDigitizerChargeInductionActor::SetCrystalThickness)
      .def("SetGrid", &GateDigitizerChargeInductionActor::SetGrid)
      .def("SetPixelVolume", &GateDigitizerChargeInductionActor::SetPixelVolume)
      .def("SetTables", &GateDigitizerChargeInductionActor::SetTables)
      .def("SetCloudTables", &GateDigitizerChargeInductionActor::SetCloudTables)
      .def("GetEta", &GateDigitizerChargeInductionActor::GetEta)
      .def("GetIgnoredHitsCount",
           &GateDigitizerChargeInductionActor::GetIgnoredHitsCount);
}
