/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4VFacet.hh"

void init_G4VFacet(py::module &m) {
  py::class_<G4VFacet>(m, "G4VFacet");
  py::enum_<G4FacetVertexType>(m, "G4FacetVertexType")
      .value("ABSOLUTE", G4FacetVertexType::ABSOLUTE)
      .value("RELATIVE", G4FacetVertexType::RELATIVE);
}
