/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4MagIntegratorDriver.hh"
#include "G4MagIntegratorStepper.hh"
#include "G4VIntegrationDriver.hh"

void init_G4MagInt_Driver(py::module &m) {

  py::class_<G4MagInt_Driver, G4VIntegrationDriver,
             std::unique_ptr<G4MagInt_Driver, py::nodelete>>(m,
                                                             "G4MagInt_Driver")

      .def(py::init<G4double, G4MagIntegratorStepper *, G4int, G4int>())

      .def("GetHmin", &G4MagInt_Driver::GetHmin)

      ;
}
