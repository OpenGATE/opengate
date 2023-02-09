/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4Track.hh"
#include "G4UserLimits.hh"

void init_G4UserLimits(py::module &m) {

  py::class_<G4UserLimits>(m, "G4UserLimits")
      .def(py::init())
      .def("SetMaxAllowedStep", &G4UserLimits::SetMaxAllowedStep)
      .def("SetUserMaxTrackLength", &G4UserLimits::SetUserMaxTrackLength)
      .def("SetUserMaxTime", &G4UserLimits::SetUserMaxTime)
      .def("SetUserMinEkine", &G4UserLimits::SetUserMinEkine)
      .def("SetUserMinRange", &G4UserLimits::SetUserMinRange)

      .def("GetMaxAllowedStep", &G4UserLimits::GetMaxAllowedStep)
      .def("GetUserMaxTrackLength", &G4UserLimits::GetUserMaxTrackLength)
      .def("GetUserMaxTime", &G4UserLimits::GetUserMaxTime)
      .def("GetUserMinEkine", &G4UserLimits::GetUserMinEkine)
      .def("GetUserMinRange", &G4UserLimits::GetUserMinRange);
}
