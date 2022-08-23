/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "G4VNestedParameterisation.hh"
#include "GateImageNestedParameterisation.h"

void init_GateImageNestedParameterisation(py::module &m) {

  py::class_<GateImageNestedParameterisation, G4VNestedParameterisation>(
      m, "GateImageNestedParameterisation")
      .def(py::init<>())
      .def_readwrite("cpp_edep_image",
                     &GateImageNestedParameterisation::cpp_image)
      .def("initialize_image",
           &GateImageNestedParameterisation::initialize_image)
      .def("initialize_material",
           &GateImageNestedParameterisation::initialize_material);
}
