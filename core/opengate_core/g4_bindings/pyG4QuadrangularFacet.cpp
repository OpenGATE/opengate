/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4QuadrangularFacet.hh"

void init_G4QuadrangularFacet(py::module &m) {
  // py::class_<G4QuadrangularFacet, G4VFacet>(m, "G4QuadrangularFacet")
  py::class_<G4QuadrangularFacet, G4VFacet,
             std::unique_ptr<G4QuadrangularFacet, py::nodelete>>(
      m, "G4QuadrangularFacet")

      .def(py::init<const G4ThreeVector, const G4ThreeVector,
                    const G4ThreeVector, const G4ThreeVector,
                    G4FacetVertexType>());
}
