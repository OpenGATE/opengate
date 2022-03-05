/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "G4Polyhedra.hh"

/*
 This class is needed to convert vector (from python) to double*
 */
class GamPolyhedra : public G4Polyhedra {
public:
    GamPolyhedra(const G4String &name,
                 G4double phiStart,    // initial phi starting angle
                 G4double phiTotal,    // total phi angle
                 G4int vnumSide,        // number sides
                 G4int numZPlanes,     // number of z planes
                 const std::vector<G4double> zPlane,    // position of z planes
                 const std::vector<G4double> rInner,    // tangent distance to inner surface
                 const std::vector<G4double> rOuter) :
        G4Polyhedra(name, phiStart, phiTotal, vnumSide, numZPlanes,
                    &(zPlane[0]),
                    &(rInner[0]),
                    &(rOuter[0])) {}
};

void init_G4Polyhedra(py::module &m) {
    py::class_<GamPolyhedra, G4VSolid,
        std::unique_ptr<GamPolyhedra, py::nodelete>>(m, "G4Polyhedra")

        .def(py::init<const G4String &,
            G4double, G4double, //phi start & total
            G4int, G4int, // nb sides, nb zplanes
            const std::vector<G4double>,    // position of z planes
            const std::vector<G4double>,    // tangent distance to inner surface
            const std::vector<G4double>>());
}
