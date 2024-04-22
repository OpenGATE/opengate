/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4ProcessVector.hh"
#include "G4VProcess.hh"

void init_G4ProcessVector(py::module &m) {

  py::class_<G4ProcessVector>(m, "G4ProcessVector")
      .def("size", &G4ProcessVector::size)
      // Bracket operator
      .def("__getitem__", [](const G4ProcessVector &s, int i) { return s[i]; });
}
