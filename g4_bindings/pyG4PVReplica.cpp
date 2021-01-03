/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>

#include "G4PVReplica.hh"
#include "G4LogicalVolume.hh"

namespace py = pybind11;

void init_G4PVReplica(py::module &m) {

    py::enum_<EAxis>(m, "EAxis")
            .value("kXAxis", kXAxis)
            .value("kYAxis", kYAxis)
            .value("kZAxis", kZAxis)
            .value("kRho", kRho)
            .value("kRadial3D", kRadial3D)
            .value("kPhi", kPhi)
            .value("kUndefined", kUndefined)
            .export_values();

    py::class_<G4PVReplica, G4VPhysicalVolume>(m, "G4PVReplica")

            .def(py::init<const G4String &,
                    G4LogicalVolume *, G4LogicalVolume *,
                    EAxis, G4int, G4double, G4double>());
}
