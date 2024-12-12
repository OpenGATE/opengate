/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4Material.hh"
#include "G4MaterialCutsCouple.hh"

void init_G4MaterialCutsCouple(py::module &m) {

  py::class_<G4MaterialCutsCouple>(m, "G4MaterialCutsCouple")

      .def(py::init<>())
      .def(py::init<const G4Material *>())
      .def("GetMaterial", &G4MaterialCutsCouple::GetMaterial);
}