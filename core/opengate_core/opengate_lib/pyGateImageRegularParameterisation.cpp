/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateImageRegularParameterisation.h"
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

void init_GateImageRegularParameterisation(py::module &m) {

  py::class_<GateImageRegularParameterisation, G4VPVParameterisation>(
      m, "GateImageRegularParameterisation")
      .def(py::init<>())
      .def_readwrite("cpp_edep_image",
                     &GateImageRegularParameterisation::cpp_image)
      .def("initialize_image",
           &GateImageRegularParameterisation::initialize_image)
      .def("initialize_material",
           &GateImageRegularParameterisation::initialize_material)
      .def("Construct", &GateImageRegularParameterisation::Construct);
}
