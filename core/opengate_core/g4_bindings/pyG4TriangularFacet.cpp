/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4TriangularFacet.hh"

void init_G4TriangularFacet(py::module &m) {
  // py::class_<G4TriangularFacet, G4VFacet>(m, "G4TriangularFacet")
  py::class_<G4TriangularFacet, G4VFacet,
             std::unique_ptr<G4TriangularFacet, py::nodelete>>(
      m, "G4TriangularFacet")

      .def(py::init<const G4ThreeVector &, const G4ThreeVector &,
                    const G4ThreeVector &, G4FacetVertexType>())

      .def("SetVertex", &G4TriangularFacet::SetVertex)
      .def("GetVertex", &G4TriangularFacet::GetVertex);
}
