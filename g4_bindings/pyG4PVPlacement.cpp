/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4Version.hh"
#include "G4PVPlacement.hh"
#include "G4LogicalVolume.hh"
#include "G4Exception.hh"

void init_G4PVPlacement(py::module &m) {
    py::class_<G4PVPlacement, G4VPhysicalVolume>(m, "G4PVPlacement")

            .def(py::init<G4RotationMatrix *, const G4ThreeVector &,
                    G4LogicalVolume *, const G4String &,
                    G4LogicalVolume *, G4bool, G4int>())

            .def(py::init<const G4Transform3D &, G4LogicalVolume *,
                    const G4String &, G4LogicalVolume *, G4bool, G4int>())

            .def(py::init<G4RotationMatrix *, const G4ThreeVector &,
                    const G4String, G4LogicalVolume *,
                    G4VPhysicalVolume *, G4bool, G4int>())

            .def(py::init<const G4Transform3D &, const G4String &,
                    G4LogicalVolume *, G4VPhysicalVolume *, G4bool, G4int>())

            .def(py::init<G4RotationMatrix *, const G4ThreeVector &,
                    G4LogicalVolume *, const G4String &,
                    G4LogicalVolume *, G4bool, G4int, G4bool>())

            .def(py::init<const G4Transform3D &, G4LogicalVolume *,
                    const G4String &, G4LogicalVolume *, G4bool, G4int, G4bool>())

            .def(py::init<G4RotationMatrix *, const G4ThreeVector &,
                    const G4String, G4LogicalVolume *,
                    G4VPhysicalVolume *, G4bool, G4int, G4bool>())

            .def(py::init<const G4Transform3D &, const G4String &,
                    G4LogicalVolume *, G4VPhysicalVolume *, G4bool, G4int, G4bool>())

            .def("CheckOverlaps", &G4PVPlacement::CheckOverlaps)

        // debug destructor
        /*
        .def("__del__",
             [](const G4PVPlacement &s) -> void {
                 std::cerr << "deleting G4PVPlacement " << s.GetName() << std::endl;
             })
             */;
}
