/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4ParticleDefinition.hh"
#include "G4VDecayChannel.hh"

void init_G4VDecayChannel(py::module &m) {
  py::class_<G4VDecayChannel>(m, "G4VDecayChannel")
      .def("GetKinematicsName", &G4VDecayChannel::GetKinematicsName)
      .def("GetBR", &G4VDecayChannel::GetBR)
      .def("GetNumberOfDaughters", &G4VDecayChannel::GetNumberOfDaughters)
      .def("GetParent", &G4VDecayChannel::GetParent,
           py::return_value_policy::reference)
      .def("GetDaughter", &G4VDecayChannel::GetDaughter,
           py::return_value_policy::reference)
      .def("GetDaughterName", &G4VDecayChannel::GetDaughterName)
      .def("GetParentMass", &G4VDecayChannel::GetParentMass)
      .def("GetDaughterMass", &G4VDecayChannel::GetDaughterMass);
}
