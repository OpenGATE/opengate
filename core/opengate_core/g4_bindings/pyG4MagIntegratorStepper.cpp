/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4MagIntegratorStepper.hh"
#include "G4EquationOfMotion.hh"

void init_G4MagIntegratorStepper(py::module &m) {

  py::class_<G4MagIntegratorStepper, std::unique_ptr<G4MagIntegratorStepper, py::nodelete>>(
      m, "G4MagIntegratorStepper")


    .def("GetNumberOfVariables", &G4MagIntegratorStepper::GetNumberOfVariables)
    .def("GetNumberOfStateVariables", &G4MagIntegratorStepper::GetNumberOfStateVariables)
    .def("IntegratorOrder", &G4MagIntegratorStepper::IntegratorOrder)

    ;
}
