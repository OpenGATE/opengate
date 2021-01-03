/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>

#include "G4PVParameterised.hh"
#include "G4LogicalVolume.hh"
#include "G4VPVParameterisation.hh"

namespace py = pybind11;

void init_G4PVParameterised(py::module &m) {

    py::class_<G4PVParameterised, G4PVReplica>(m, "G4PVParameterised")

            .def(py::init<const G4String &,
                    G4LogicalVolume *, G4LogicalVolume *,
                    EAxis, G4int, G4VPVParameterisation *, G4bool>());
}
