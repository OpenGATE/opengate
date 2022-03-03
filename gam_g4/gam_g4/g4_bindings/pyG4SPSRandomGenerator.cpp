/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4SPSRandomGenerator.hh"

void init_G4SPSRandomGenerator(py::module &m) {

    py::class_<G4SPSRandomGenerator>(m, "G4SPSRandomGenerator")
        .def(py::init());
}

