/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4TessellatedSolid.hh"

void init_G4TessellatedSolid(py::module &m) {
  py::class_<G4TessellatedSolid, G4VSolid>(m, "G4TessellatedSolid")

      .def(py::init<const G4String &>())

      .def("AddFacet", &G4TessellatedSolid::AddFacet)
      .def("GetNumberOfFacets", &G4TessellatedSolid::GetNumberOfFacets)
      .def("GetCubicVolume", &G4TessellatedSolid::GetCubicVolume)
      .def("SetSolidClosed", &G4TessellatedSolid::SetSolidClosed);
}
