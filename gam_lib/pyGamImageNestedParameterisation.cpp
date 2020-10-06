/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GamImageNestedParameterisation.h"
#include "G4VNestedParameterisation.hh"

void init_GamImageNestedParameterisation(py::module &m) {

    py::class_<GamImageNestedParameterisation, G4VNestedParameterisation>(m, "GamImageNestedParameterisation")
        .def(py::init<>())
        //.def("initialize", GamImageNestedParameterisation::initialize)
        ;
}

