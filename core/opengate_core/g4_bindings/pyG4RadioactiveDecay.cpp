/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4DecayTable.hh"
#include "G4Ions.hh"
#include "G4RadioactiveDecay.hh"
#include "G4VRestDiscreteProcess.hh"

void init_G4RadioactiveDecay(py::module &m) {
  py::class_<G4RadioactiveDecay, G4VRestDiscreteProcess>(m,
                                                         "G4RadioactiveDecay")
      .def("LoadDecayTable", &G4RadioactiveDecay::LoadDecayTable)
      .def("GetDecayTable", &G4RadioactiveDecay::GetDecayTable);
}
