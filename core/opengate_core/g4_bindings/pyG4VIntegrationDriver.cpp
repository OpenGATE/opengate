/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4VIntegrationDriver.hh"

void init_G4VIntegrationDriver(py::module &m) {

  py::class_<G4VIntegrationDriver, std::unique_ptr<G4VIntegrationDriver, py::nodelete>>(
      m, "G4VIntegrationDriver")

      .def("SetEquationOfMotion", &G4VIntegrationDriver::SetEquationOfMotion)
      .def("GetEquationOfMotion", &G4VIntegrationDriver::GetEquationOfMotion,
           py::return_value_policy::reference_internal)
      .def("SetVerboseLevel", &G4VIntegrationDriver::SetVerboseLevel)
      .def("GetVerboseLevel", &G4VIntegrationDriver::GetVerboseLevel)

      ;
}
